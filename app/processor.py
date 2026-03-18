# processor.py - 核心业务处理逻辑
import json
from datetime import datetime
from pathlib import Path

from app.models import (
    Category,
    TimeRecord,
    ProcessedFile,
    get_session,
    compute_file_hash,
)
from app.parser import parse_document, extract_date_from_document
from app.llm import get_llm_client
from app.config import config


def _format_categories_for_prompt(categories, indent=0):
    """将分类树格式化为prompt字符串"""
    lines = []
    prefix = "  " * indent
    for cat in categories:
        lines.append(f"{prefix}- {cat['name']}")
        if cat.get("children"):
            lines.append(_format_categories_for_prompt(cat["children"], indent + 1))
    return "\n".join(lines)


class CategoryManager:
    """分类树管理器"""

    @staticmethod
    def get_or_create_category(category_path: list) -> Category:
        """
        根据分类路径获取或创建分类节点
        category_path: ["学习", "学数学", "高等数学"]
        """
        session = get_session()
        try:
            parent_id = None

            for i, name in enumerate(category_path):
                code = "_".join(category_path[: i + 1])
                existing = session.query(Category).filter(Category.code == code).first()

                if existing:
                    parent_id = existing.id
                else:
                    new_category = Category(
                        name=name, code=code, parent_id=parent_id, level=i
                    )
                    session.add(new_category)
                    session.flush()
                    parent_id = new_category.id

            session.commit()

            return (
                session.query(Category)
                .filter(Category.code == "_".join(category_path))
                .first()
            )
        finally:
            session.close()

    @staticmethod
    def get_category_tree() -> list:
        """获取完整的分类树"""
        session = get_session()
        try:
            roots = session.query(Category).filter(Category.parent_id == None).all()
            return [r.to_dict(include_children=True) for r in roots]
        finally:
            session.close()


class TimeRecordProcessor:
    """时间记录处理器"""

    @staticmethod
    def _get_root_category(event_name: str) -> str:
        """根据事件名确定根分类"""
        event = event_name.lower()

        if "起床" in event or "睡觉" in event or "整理" in event:
            return "睡觉"
        elif "吃" in event:
            return "吃饭"
        elif "通勤" in event:
            return "通勤"
        elif "工作" in event:
            return "工作"
        elif "学习" in event:
            return "学习"
        elif "玩耍" in event or "玩" in event:
            return "玩耍"
        else:
            return "工作"

    @staticmethod
    def _get_or_create_category(session, category_path: list) -> Category:
        """在指定session中获取或创建分类"""
        parent_id = None

        for i, name in enumerate(category_path):
            code = "_".join(category_path[: i + 1])
            existing = session.query(Category).filter(Category.code == code).first()

            if existing:
                parent_id = existing.id
            else:
                new_category = Category(
                    name=name, code=code, parent_id=parent_id, level=i
                )
                session.add(new_category)
                session.flush()
                parent_id = new_category.id

        return (
            session.query(Category)
            .filter(Category.code == "_".join(category_path))
            .first()
        )

    @staticmethod
    def process_file(file_path: Path) -> dict:
        """处理单个文件，提取时间数据

        流程：
        1. 第1次LLM调用：提取时间点序列
        2. 外部逻辑：计算duration
        3. 第2次LLM调用：分类事件
        """
        file_hash = compute_file_hash(file_path)

        session = get_session()
        try:
            existing = (
                session.query(ProcessedFile)
                .filter(ProcessedFile.file_hash == file_hash)
                .first()
            )

            if existing:
                return {
                    "status": "skipped",
                    "reason": "already_processed",
                    "file": str(file_path),
                }
        finally:
            session.close()

        text = parse_document(file_path)

        # 从文档内容中提取日期，而不是从文件名
        date_str = extract_date_from_document(file_path)
        if not date_str:
            date_str = file_path.stem.split("_")[0]
            print(f"  警告: 无法从内容解析日期，使用文件名日期: {date_str}")
        else:
            print(f"  日记日期: {date_str}")

        llm_client = get_llm_client()
        existing_cats = CategoryManager.get_category_tree()
        categories_str = _format_categories_for_prompt(existing_cats)

        try:
            # 第1次LLM调用：提取时间点序列
            time_points = llm_client.extract_time_points(text, date_str, categories_str)
            print(f"  时间点提取: {len(time_points)} 个")
            # 打印提取的时间点便于调试
            for tp in time_points[:10]:
                print(f"    - {tp.get('time')}: {tp.get('event')}")
            if len(time_points) > 10:
                print(f"    ... 共{len(time_points)}个时间点")
        except Exception as e:
            return {
                "status": "error",
                "message": f"第1次LLM调用失败: {str(e)}",
                "file": str(file_path),
            }

        # 外部逻辑：计算duration
        events = TimeRecordProcessor._calculate_durations(time_points, date_str)
        print(f"  计算事件: {len(events)} 个")
        # 打印事件便于调试
        for e in events[:5]:
            print(f"    - {e.get('event')}: {e.get('duration')}分钟")
        if len(events) > 5:
            print(f"    ... 共{len(events)}个事件")

        if not events:
            return {
                "status": "error",
                "message": "未能从日记中提取到有效时间信息",
                "file": str(file_path),
            }

        try:
            # 第2次LLM调用：询问每个事件具体在做什么
            details = llm_client.extract_event_details(text, time_points)
            print(f"  事件详情: {len(details)} 个")
            for d in details[:5]:
                print(f"    - {d.get('event')}: {d.get('detail')}")
        except Exception as e:
            return {
                "status": "error",
                "message": f"第2次LLM调用失败: {str(e)}",
                "file": str(file_path),
            }

        # 第3步：将事件与详情结合，并确定分类
        # 构建事件到详情的映射
        event_to_detail = {d.get("event"): d.get("detail", "") for d in details}
        print(f"  事件映射: {event_to_detail}")

        # 存储到数据库
        processed_records = []
        session = get_session()
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")

            for event in events:
                event_name = event.get("event", "")
                duration = event.get("duration", 0)
                detail = event_to_detail.get(event_name, "")

                print(f"    处理: {event_name} -> {detail} ({duration}分钟)")

                # 确定分类路径
                root_category = TimeRecordProcessor._get_root_category(event_name)
                category_path = [root_category]

                # 添加子分类
                if detail:
                    category_path.append(detail)

                # 获取或创建分类（使用主session避免锁定）
                category = TimeRecordProcessor._get_or_create_category(
                    session, category_path
                )

                # 检查该分类在该日期是否已存在，如果存在则累加时间
                existing = (
                    session.query(TimeRecord)
                    .filter(
                        TimeRecord.category_id == category.id, TimeRecord.date == date
                    )
                    .first()
                )

                if existing:
                    existing.duration_minutes += duration
                    print(f"      累加到已有记录: {category.name}")
                else:
                    record = TimeRecord(
                        category_id=category.id,
                        date=date,
                        duration_minutes=duration,
                        source_file=file_path.name,
                        raw_text=json.dumps({"event": event_name, "detail": detail}),
                    )
                    session.add(record)
                    processed_records.append(record.to_dict())

            session.flush()  # 确保更新生效

            processed_file = ProcessedFile(
                file_hash=file_hash, original_path=str(file_path)
            )
            session.add(processed_file)
            session.commit()

            print(f"  存储成功: {len(processed_records)} 条记录")

            return {
                "status": "success",
                "records": processed_records,
                "file": str(file_path),
            }
        except Exception as e:
            session.rollback()
            print(f"  存储失败: {str(e)}")
            return {"status": "error", "message": str(e)}
        finally:
            session.close()

    @staticmethod
    def _calculate_durations(time_points: list, date_str: str) -> list:
        """根据时间点序列计算每个事件的duration"""
        import re
        from collections import defaultdict

        def parse_time(time_str):
            """解析时间字符串为分钟数"""
            if not time_str:
                return None

            time_str = time_str.strip()

            patterns = [
                (r"^(\d{1,2}):(\d{2})$", 0),  # 07:30
                (r"^(\d{1,2})点(\d{1,2})?分?$", 1),  # 7点30分, 7点
                (r"^早上(\d{1,2})点?(\d{1,2})?分?$", 2),  # 早上7点
                (r"^中午(\d{1,2})点?(\d{1,2})?分?$", 3),  # 中午12点
                (r"^下午(\d{1,2})点?(\d{1,2})?分?$", 4),  # 下午3点
                (r"^晚上(\d{1,2})点?(\d{1,2})?分?$", 5),  # 晚上10点
                (r"^凌晨(\d{1,2})点?(\d{1,2})?分?$", 6),  # 凌晨1点
                (r"^深夜(\d{1,2})点?(\d{1,2})?分?$", 7),  # 深夜
            ]

            for pattern, pattern_type in patterns:
                match = re.match(pattern, time_str)
                if match:
                    groups = match.groups()
                    hour = int(groups[0])
                    minute = int(groups[1]) if groups[1] else 0

                    if pattern_type == 2 and hour < 12:  # 早上
                        pass
                    elif pattern_type == 3 and hour < 12:  # 中午 -> 12-13点
                        hour = hour if hour >= 11 else hour + 12
                    elif pattern_type == 4 and hour < 12:  # 下午 -> 13点起
                        hour = hour + 12
                    elif pattern_type == 5 and hour < 12:  # 晚上 -> 18点起
                        hour = hour + 12 if hour <= 6 else hour
                    elif pattern_type == 6:  # 凌晨
                        pass  # 凌晨就是凌晨
                    elif pattern_type == 7:  # 深夜
                        pass

                    minutes = hour * 60 + minute

                    # 00:00 应该被视为 24:00 (1440分钟)，用于计算当天时间
                    if minutes == 0:
                        minutes = 24 * 60

                    return minutes

            return None

        valid_points = []
        failed_parsing = []
        for tp in time_points:
            time_str = tp.get("time")
            if not time_str:
                continue
            time_val = parse_time(time_str)
            if time_val is not None:
                valid_points.append(
                    {
                        "time": time_val,
                        "event": tp.get("event", ""),
                        "raw_time": time_str,
                    }
                )
            else:
                failed_parsing.append(time_str)

        if failed_parsing:
            print(f"  警告: 以下时间格式解析失败: {failed_parsing}")

        if not valid_points:
            return []

        # 按时间排序
        valid_points.sort(key=lambda x: x["time"])

        # 如果第一个时间点不是00:00，前面补一个00:00睡觉
        if valid_points[0]["time"] > 0:
            valid_points.insert(0, {"time": 0, "event": "睡觉", "raw_time": "00:00"})

        # 如果最后一个时间点不是00:00，后面补一个00:00睡觉
        if valid_points[-1]["time"] < 24 * 60:
            valid_points.append({"time": 24 * 60, "event": "睡觉", "raw_time": "24:00"})

        events = []

        for i in range(len(valid_points) - 1):
            current = valid_points[i]
            next_point = valid_points[i + 1]
            duration = next_point["time"] - current["time"]

            if duration <= 0:
                continue

            current_event = current.get("event", "")
            next_event = next_point.get("event", "")

            # 确定事件名称
            if i == 0:
                # 00:00 → 起床 = 睡觉
                event_name = "睡觉"
            elif "起" in current_event:
                # 起床 → 第一个事务 = 整理仪容仪表
                event_name = "整理仪容仪表"
            elif "睡" in next_event:
                # 事务n → 睡觉 = 事务n
                event_name = current_event
            else:
                # 事务 → 事务 = 当前事务
                event_name = current_event

            events.append(
                {
                    "event": event_name,
                    "duration": duration,
                    "start_time": current["raw_time"],
                }
            )

        # 计算总时长
        total_minutes = sum(e["duration"] for e in events)
        print(
            f"  时间点: {len(valid_points)}个, 总时长: {total_minutes}分钟 ({total_minutes / 60:.1f}小时)"
        )

        # 不允许时间缺口 - 如果不足24小时，报错
        if total_minutes < 24 * 60:
            missing = 24 * 60 - total_minutes
            print(f"  错误: LLM输出时间不完整，缺口{missing}分钟")
            # 返回空让上层处理
            return []

        return events

    @staticmethod
    def get_statistics(start_date=None, end_date=None, category_id=None) -> dict:
        """获取统计数据"""
        session = get_session()
        try:
            from sqlalchemy import func

            query = (
                session.query(
                    Category.id,
                    Category.name,
                    Category.code,
                    Category.parent_id,
                    Category.level,
                    func.sum(TimeRecord.duration_minutes).label("total_minutes"),
                )
                .join(TimeRecord)
                .group_by(Category.id)
            )

            if start_date:
                query = query.filter(TimeRecord.date >= start_date)
            if end_date:
                query = query.filter(TimeRecord.date <= end_date)
            if category_id:
                query = query.filter(Category.id == category_id)

            results = query.all()

            stats = {}
            for r in results:
                stats[r.code] = {
                    "name": r.name,
                    "total_minutes": r.total_minutes or 0,
                    "total_hours": round((r.total_minutes or 0) / 60, 2),
                    "level": r.level,
                    "parent_id": r.parent_id,
                }

            return stats
        finally:
            session.close()

    @staticmethod
    def get_hierarchical_stats(start_date=None, end_date=None) -> dict:
        """获取层级化统计数据"""
        stats = TimeRecordProcessor.get_statistics(start_date, end_date)

        # 构建层级结构
        tree = {}
        for code, data in stats.items():
            levels = code.split("_")
            current = tree
            for level in levels[:-1]:
                if level not in current:
                    current[level] = {"_data": {}, "_children": {}}
                current = current[level]["_children"]
            current[levels[-1]] = {"_data": data, "_children": {}}

        return tree
