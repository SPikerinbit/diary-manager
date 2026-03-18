# routes/api.py
from flask import jsonify, request
from datetime import datetime, timedelta
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

    # 获取层级结构
    tree = CategoryManager.get_category_tree()

    # 计算每个节点及其子节点的总时间
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

    session = get_session()
    try:
        records = (
            session.query(TimeRecord, Category)
            .join(Category, TimeRecord.category_id == Category.id)
            .order_by(TimeRecord.date.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

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
