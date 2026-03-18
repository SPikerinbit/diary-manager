# watcher.py - 文件监控模块
import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .config import config
from .processor import TimeRecordProcessor
from .models import compute_file_hash, ProcessedFile, get_session


logger = logging.getLogger(__name__)


class FileHandler(FileSystemEventHandler):
    """文件处理事件处理器"""

    SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown", ".docx", ".doc"}

    def on_created(self, event):
        """文件创建事件"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
            logger.info(f"检测到新文件: {file_path}")
            self.process_file(file_path)

    def process_file(self, file_path: Path):
        """处理文件"""
        # 等待文件写入完成
        time.sleep(1)

        # 检查是否已处理
        session = get_session()
        try:
            file_hash = compute_file_hash(file_path)
            existing = (
                session.query(ProcessedFile)
                .filter(ProcessedFile.file_hash == file_hash)
                .first()
            )

            if existing:
                logger.info(f"文件已处理过，跳过: {file_path}")
                return
        finally:
            session.close()

        # 处理文件
        result = TimeRecordProcessor.process_file(file_path)

        if result["status"] == "success":
            logger.info(
                f"文件处理成功: {file_path}, 提取 {len(result.get('records', []))} 条记录"
            )

            # 移动到已处理目录
            self.move_to_processed(file_path)
        else:
            logger.error(
                f"文件处理失败: {file_path}, {result.get('message', '未知错误')}"
            )

    def move_to_processed(self, file_path: Path):
        """移动文件到已处理目录"""
        import shutil
        from datetime import datetime

        processed_dir = config["directories"]["processed"] / datetime.now().strftime(
            "%Y-%m-%d"
        )
        processed_dir.mkdir(parents=True, exist_ok=True)

        dest = processed_dir / file_path.name
        shutil.move(str(file_path), str(dest))
        logger.info(f"文件已移动到: {dest}")


def start_file_watcher():
    """启动文件监控"""
    input_dir = config["directories"]["input"]
    input_dir.mkdir(parents=True, exist_ok=True)

    event_handler = FileHandler()
    observer = Observer()
    observer.schedule(event_handler, str(input_dir), recursive=False)
    observer.start()

    logger.info(f"文件监控已启动，监听目录: {input_dir}")
    return observer


def process_existing_files():
    """处理input目录中已存在的文件"""
    input_dir = config["directories"]["input"]

    if not input_dir.exists():
        return

    for file_path in input_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in {
            ".pdf",
            ".md",
            ".markdown",
            ".docx",
            ".doc",
        }:
            logger.info(f"处理已存在文件: {file_path}")
            result = TimeRecordProcessor.process_file(file_path)

            if result["status"] == "success":
                # 移动到已处理目录
                import shutil
                from datetime import datetime

                processed_dir = config["directories"][
                    "processed"
                ] / datetime.now().strftime("%Y-%m-%d")
                processed_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), processed_dir / file_path.name)
