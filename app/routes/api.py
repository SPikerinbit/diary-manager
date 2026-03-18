# routes/api.py
from flask import jsonify, request
from datetime import datetime, timedelta
from sqlalchemy import func
import json

from app.routes import api_bp
from app.models import Category, TimeRecord, WeeklyReport, get_session
from app.processor import CategoryManager, TimeRecordProcessor
from app.scheduler.weekly_task import generate_weekly_report


@api_bp.route("/categories", methods=["GET"])
def get_categories():
    """获取分类树"""
    tree = CategoryManager.get_category_tree()
    return jsonify({"categories": tree})


@api_bp.route("/statistics", methods=["GET"])
def get_statistics():
    """获取统计数据"""
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    category_id = request.args.get("category_id", type=int)

    start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
    end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

    stats = TimeRecordProcessor.get_statistics(start, end, category_id)

    tree = CategoryManager.get_category_tree()

    def calc_hours(node, stats):
        node_hours = (
            stats.get(node["code"], {}).get("total_hours", 0) if node.get("code") else 0
        )
        children_hours = 0
        if node.get("children"):
            for child in node["children"]:
                children_hours += calc_hours(child, stats)
        return node_hours + children_hours

    result = []
    for root in tree:
        hours = calc_hours(root, stats)
        if hours > 0:
            result.append(
                {
                    "name": root["name"],
                    "code": root["code"],
                    "hours": hours,
                    "level": root["level"],
                }
            )

    return jsonify({"statistics": result})


@api_bp.route("/statistics/by-level", methods=["GET"])
def get_statistics_by_level():
    """获取指定层级的统计数据（包括所有分类，父分类时间=子分类之和）"""
    level = request.args.get("level", 0, type=int)
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
    end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

    session = get_session()
    try:
        from sqlalchemy import func

        # 获取该层级的所有分类
        categories = session.query(Category).filter(Category.level == level).all()

        # 获取所有分类（用于构建children_map）
        all_categories = session.query(Category).all()

        # 构建子分类映射：parent_id -> [child_ids]
        children_map = {}
        cat_id_to_level = {}
        for c in all_categories:
            cat_id_to_level[c.id] = c.level
            if c.parent_id is not None:
                if c.parent_id not in children_map:
                    children_map[c.parent_id] = []
                children_map[c.parent_id].append(c.id)

        # 获取所有时间记录（带日期过滤）
        time_query = session.query(
            TimeRecord.category_id,
            func.sum(TimeRecord.duration_minutes).label("total_minutes"),
        ).group_by(TimeRecord.category_id)

        if start:
            time_query = time_query.filter(TimeRecord.date >= start)
        if end:
            time_query = time_query.filter(TimeRecord.date <= end)

        time_stats = {t.category_id: t.total_minutes or 0 for t in time_query.all()}

        # 计算每个分类的时间（包括子分类）
        def calc_total_minutes(cat_id):
            total = time_stats.get(cat_id, 0)
            if cat_id in children_map:
                for child_id in children_map[cat_id]:
                    total += calc_total_minutes(child_id)
            return total

        result = []
        for cat in categories:
            minutes = calc_total_minutes(cat.id)
            result.append(
                {
                    "id": cat.id,
                    "name": cat.name,
                    "code": cat.code,
                    "level": cat.level,
                    "parent_id": cat.parent_id,
                    "hours": round(minutes / 60, 2),
                    "minutes": minutes,
                }
            )

        return jsonify({"statistics": result})
    finally:
        session.close()


@api_bp.route("/statistics/by-category", methods=["GET"])
def get_statistics_by_category():
    """获取指定分类的子节点统计"""
    category_id = request.args.get("category_id", type=int)
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
    end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

    session = get_session()
    try:
        if not category_id:
            return jsonify({"statistics": []})

        category = session.query(Category).filter(Category.id == category_id).first()
        if not category:
            return jsonify({"statistics": []})

        # 获取该分类的所有子节点
        children = (
            session.query(Category).filter(Category.parent_id == category_id).all()
        )

        # 如果没有子节点，返回空
        if not children:
            return jsonify({"statistics": []})

        # 获取所有时间记录（带日期过滤）
        time_query = session.query(
            TimeRecord.category_id,
            func.sum(TimeRecord.duration_minutes).label("total_minutes"),
        ).group_by(TimeRecord.category_id)

        if start:
            time_query = time_query.filter(TimeRecord.date >= start)
        if end:
            time_query = time_query.filter(TimeRecord.date <= end)

        time_stats = {t.category_id: t.total_minutes or 0 for t in time_query.all()}

        # 构建子分类映射
        all_cats = session.query(Category).all()
        children_map = {}
        for c in all_cats:
            if c.parent_id is not None:
                if c.parent_id not in children_map:
                    children_map[c.parent_id] = []
                children_map[c.parent_id].append(c.id)

        # 计算每个分类的时间（包括子分类）
        def calc_total_minutes(cat_id):
            total = time_stats.get(cat_id, 0)
            if cat_id in children_map:
                for child_id in children_map[cat_id]:
                    total += calc_total_minutes(child_id)
            return total

        result = []
        for child in children:
            minutes = calc_total_minutes(child.id)
            result.append(
                {
                    "id": child.id,
                    "name": child.name,
                    "code": child.code,
                    "level": child.level,
                    "parent_id": child.parent_id,
                    "hours": round(minutes / 60, 2),
                    "minutes": minutes,
                }
            )

        return jsonify({"statistics": result})
    finally:
        session.close()


@api_bp.route("/timeline/dates", methods=["GET"])
def get_timeline_dates():
    """获取时间线日期"""
    granularity = request.args.get("granularity", "month")

    session = get_session()
    try:
        from sqlalchemy import func, extract

        if granularity == "year":
            query = session.query(
                extract("year", TimeRecord.date).label("period")
            ).distinct()
        elif granularity == "month":
            query = session.query(
                extract("year", TimeRecord.date).label("year"),
                extract("month", TimeRecord.date).label("period"),
            ).distinct()
        else:
            query = session.query(
                extract("year", TimeRecord.date).label("year"),
                extract("week", TimeRecord.date).label("period"),
            ).distinct()

        results = query.all()

        dates = []
        if granularity == "year":
            dates = [str(int(r.period)) for r in results if r.period]
        elif granularity == "month":
            dates = [
                f"{int(r.year)}-{int(r.period):02d}"
                for r in results
                if r.year and r.period
            ]
        else:
            dates = [
                f"{int(r.year)}-W{int(r.period):02d}"
                for r in results
                if r.year and r.period
            ]

        return jsonify({"dates": sorted(dates, reverse=True)})
    finally:
        session.close()


@api_bp.route("/statistics/hierarchical", methods=["GET"])
def get_hierarchical_statistics():
    """获取层级化统计数据（用于树状展开）"""
    category_id = request.args.get("category_id", type=int)

    if category_id:
        stats = TimeRecordProcessor.get_statistics(category_id=category_id)
    else:
        stats = TimeRecordProcessor.get_statistics()

    return jsonify(stats)


@api_bp.route("/records", methods=["GET"])
def get_records():
    """获取时间记录"""
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
    end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

    session = get_session()
    try:
        query = session.query(TimeRecord, Category).join(
            Category, TimeRecord.category_id == Category.id
        )

        if start:
            query = query.filter(TimeRecord.date >= start)
        if end:
            query = query.filter(TimeRecord.date <= end)

        query = query.order_by(TimeRecord.date.desc()).limit(limit).offset(offset)

        records = query.all()

        result = []
        for record, category in records:
            result.append(
                {
                    "id": record.id,
                    "date": record.date.strftime("%Y-%m-%d"),
                    "category": category.name,
                    "category_code": category.code,
                    "duration_minutes": record.duration_minutes,
                    "duration_hours": round(record.duration_minutes / 60, 2),
                    "source_file": record.source_file,
                }
            )

        return jsonify({"records": result})
    finally:
        session.close()


@api_bp.route("/weekly-report", methods=["GET"])
def get_weekly_report():
    """获取周报"""
    weeks_ago = request.args.get("weeks_ago", 0, type=int)

    today = datetime.now()
    week_start = today - timedelta(days=today.weekday() + weeks_ago * 7)
    week_end = week_start + timedelta(days=6)

    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_end.replace(hour=23, minute=59, second=59, microsecond=0)

    session = get_session()
    try:
        report = (
            session.query(WeeklyReport)
            .filter(
                WeeklyReport.week_start >= week_start, WeeklyReport.week_end <= week_end
            )
            .first()
        )

        if report:
            return jsonify(
                {
                    "week_start": report.week_start.strftime("%Y-%m-%d"),
                    "week_end": report.week_end.strftime("%Y-%m-%d"),
                    "summary": json.loads(report.summary),
                }
            )
        else:
            # 生成新周报
            new_report = generate_weekly_report(week_start, week_end)
            return jsonify(new_report)
    finally:
        session.close()


@api_bp.route("/weekly-report/generate", methods=["POST"])
def generate_weekly_report_manual():
    """手动生成周报"""
    data = request.get_json() or {}
    weeks_ago = data.get("weeks_ago", 0)

    today = datetime.now()
    week_start = today - timedelta(days=today.weekday() + weeks_ago * 7)
    week_end = week_start + timedelta(days=6)

    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_end.replace(hour=23, minute=59, second=59, microsecond=0)

    report = generate_weekly_report(week_start, week_end)
    return jsonify(report)


@api_bp.route("/files/pending", methods=["GET"])
def get_pending_files():
    """获取待处理文件列表"""
    from ..config import config
    import os

    input_dir = config["directories"]["input"]
    files = []

    for f in os.listdir(input_dir):
        file_path = input_dir / f
        if file_path.is_file() and file_path.suffix.lower() in [
            ".pdf",
            ".md",
            ".markdown",
            ".docx",
            ".doc",
            ".html",
            ".htm",
        ]:
            files.append(
                {
                    "name": f,
                    "size": os.path.getsize(file_path),
                    "modified": datetime.fromtimestamp(
                        os.path.getmtime(file_path)
                    ).strftime("%Y-%m-%d %H:%M"),
                }
            )

    return jsonify({"files": files})


@api_bp.route("/files/process", methods=["POST"])
def process_file():
    """手动触发文件处理"""
    from ..processor import TimeRecordProcessor
    from ..config import config
    import shutil
    from pathlib import Path

    data = request.get_json()
    filename = data.get("filename")

    if not filename:
        return jsonify({"error": "文件名不能为空"}), 400

    input_dir = config["directories"]["input"]
    file_path = input_dir / filename

    if not file_path.exists():
        return jsonify({"error": "文件不存在"}), 404

    # 处理文件
    result = TimeRecordProcessor.process_file(file_path)

    if result["status"] == "success":
        # 移动到已处理目录
        processed_dir = config["directories"]["processed"] / datetime.now().strftime(
            "%Y-%m-%d"
        )
        processed_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(file_path), processed_dir / filename)

    return jsonify(result)
