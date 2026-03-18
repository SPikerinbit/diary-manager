#!/usr/bin/env python
# run.py - 项目入口文件
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    """主入口"""
    logger.info("启动日记时间统计 Agent...")

    # 初始化数据库
    from app.models import init_db

    init_db()
    logger.info("数据库初始化完成")

    # 创建Flask应用
    from app import create_app, init_scheduler

    app = create_app()

    # 启动定时任务
    scheduler = init_scheduler()
    logger.info("定时任务已启动")

    # 启动文件监控
    from app.watcher import start_file_watcher

    watcher = start_file_watcher()

    # 启动Web服务器
    from app.config import config

    app_config = config["app"]

    logger.info(f"Web服务器启动: http://{app_config['host']}:{app_config['port']}")

    try:
        app.run(
            host=app_config["host"],
            port=app_config["port"],
            debug=app_config.get("debug", False),
            use_reloader=False,  # 避免重复加载
        )
    except KeyboardInterrupt:
        logger.info("收到退出信号，正在关闭...")
    finally:
        watcher.stop()
        watcher.join()
        scheduler.shutdown()
        logger.info("服务已关闭")


if __name__ == "__main__":
    main()
