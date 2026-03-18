# app/__init__.py
import os
from flask import Flask
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import config, BASE_DIR


def create_app():
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )
    CORS(app)

    app.config["SECRET_KEY"] = "diary-time-tracker-secret-key"

    # 注册蓝图
    from app.routes import api_bp, views_bp

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(views_bp)

    return app


def init_scheduler():
    """初始化定时任务调度器"""
    scheduler = BackgroundScheduler()
    from app.scheduler.weekly_task import schedule_weekly_task

    schedule_weekly_task(scheduler)
    scheduler.start()
    return scheduler
