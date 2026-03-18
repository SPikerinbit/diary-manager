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
from app.parser import parse_document
from app.llm import get_llm_client
from app.config import config


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
            level = 0

            for name in category_path:
                code = "_".join(category_path[: category_path.index(name) + 1])
                existing = session.query(Category).filter(Category.code == code).first()

                if existing:
                    parent_id = existing.id
                    level = existing.level
                else:
                    new_category = Category(
                        name=name, code=code, parent_id=parent_id, level=level
                    )
                    session.add(new_category)
                    session.flush()
                    parent_id = new_category.id
                    level = level + 1

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
    def process_file(file_path: Path) -> dict:
        """
        处理单个文件，提取时间数据
        """
        # 计算文件hash
        file_hash = compute_file_hash(file_path)

        # 检查是否已处理过
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

        # 解析文档
        text = parse_document(file_path)

        # 调用大模型提取时间块
        llm_client = get_llm_client()
        time_blocks = llm_client.extract_time_blocks(text, "")

        # 处理每个时间块
        processed_records = []
        session = get_session()
        try:
            for block in time_blocks:
                # 获取或创建分类
                category_path = block.get("category_path", [])
                if not category_path:
                    category_path = ["其他"]

                category = CategoryManager.get_or_create_category(category_path)

                # 解析日期
                date_str = block.get("date")
                if date_str:
                    date = datetime.strptime(date_str, "%Y-%m-%d")
                else:
                    date = datetime.now()

                # 创建时间记录
                duration = block.get("duration_minutes", 0)
                record = TimeRecord(
                    category_id=category.id,
                    date=date,
                    duration_minutes=duration,
                    source_file=file_path.name,
                    raw_text=json.dumps(block),
                )
                session.add(record)
                processed_records.append(record.to_dict())

            # 记录已处理文件
            processed_file = ProcessedFile(
                file_hash=file_hash, original_path=str(file_path)
            )
            session.add(processed_file)
            session.commit()

            return {
                "status": "success",
                "records": processed_records,
                "file": str(file_path),
            }
        except Exception as e:
            session.rollback()
            return {"status": "error", "message": str(e)}
        finally:
            session.close()

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
