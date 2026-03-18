# scheduler/weekly_task.py
import json
from datetime import datetime, timedelta
from apscheduler.triggers.cron import CronTrigger

from app.config import config
from app.models import WeeklyReport, TimeRecord, Category, get_session
from app.llm import get_llm_client
from app.llm.prompt import WEEKLY_SUMMARY_PROMPT


def generate_weekly_report(week_start: datetime, week_end: datetime) -> dict:
    """生成周报"""
    session = get_session()
    try:
        # 获取本周数据
        records = (
            session.query(TimeRecord, Category)
            .join(Category, TimeRecord.category_id == Category.id)
            .filter(TimeRecord.date >= week_start, TimeRecord.date <= week_end)
            .all()
        )

        # 按分类汇总
        category_stats = {}
        for record, category in records:
            code = category.code
            if code not in category_stats:
                category_stats[code] = {"name": category.name, "minutes": 0}
            category_stats[code]["minutes"] += record.duration_minutes

        # 转换为小时并计算百分比
        total_minutes = sum(s["minutes"] for s in category_stats.values())
        for stat in category_stats.values():
            stat["hours"] = round(stat["minutes"] / 60, 2)
            stat["percentage"] = (
                round(stat["minutes"] / total_minutes * 100, 1)
                if total_minutes > 0
                else 0
            )

        # 按小时排序
        sorted_stats = sorted(
            category_stats.values(), key=lambda x: x["hours"], reverse=True
        )

        # 准备大模型总结数据
        data_for_llm = {
            "week_start": week_start.strftime("%Y-%m-%d"),
            "week_end": week_end.strftime("%Y-%m-%d"),
            "total_hours": round(total_minutes / 60, 2),
            "categories": sorted_stats[:10],
        }

        # 调用大模型生成洞察
        llm_client = get_llm_client()
        llm_summary = {}
        try:
            llm_result = llm_client.client.chat.completions.create(
                model=llm_client.model,
                messages=[
                    {"role": "system", "content": WEEKLY_SUMMARY_PROMPT},
                    {
                        "role": "user",
                        "content": f"数据如下：\n{json.dumps(data_for_llm, ensure_ascii=False)}",
                    },
                ],
                temperature=0.5,
                response_format={"type": "json_object"},
            )
            llm_summary = json.loads(llm_result.choices[0].message.content)
        except Exception as e:
            print(f"大模型总结生成失败: {e}")
            llm_summary = {}

        # 保存周报
        report = WeeklyReport(
            week_start=week_start,
            week_end=week_end,
            summary=json.dumps(
                {"statistics": sorted_stats, "llm_summary": llm_summary},
                ensure_ascii=False,
            ),
        )
        session.add(report)
        session.commit()

        return {
            "week_start": week_start.strftime("%Y-%m-%d"),
            "week_end": week_end.strftime("%Y-%m-%d"),
            "total_hours": round(total_minutes / 60, 2),
            "categories": sorted_stats,
            "llm_summary": llm_summary.get("summary", {}),
        }
    finally:
        session.close()


def weekly_task_job():
    """每周定时任务"""
    today = datetime.now()
    # 获取本周开始日期（周一）
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_end.replace(hour=23, minute=59, second=59, microsecond=0)

    print(
        f"生成周报: {week_start.strftime('%Y-%m-%d')} - {week_end.strftime('%Y-%m-%d')}"
    )
    return generate_weekly_report(week_start, week_end)


def schedule_weekly_task(scheduler):
    """配置每周定时任务"""
    scheduler_config = config.get("scheduler", {})

    if not scheduler_config.get("enabled", True):
        return

    day_map = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    day = scheduler_config.get("weekly_report_day", "sunday")
    hour = scheduler_config.get("weekly_report_hour", 20)

    trigger = CronTrigger(day_of_week=day_map.get(day, 6), hour=hour, minute=0)

    scheduler.add_job(weekly_task_job, trigger, id="weekly_report", name="每周生成周报")

    print(f"定时任务已配置: 每周{day} {hour}:00")
