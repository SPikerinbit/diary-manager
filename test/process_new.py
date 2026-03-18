import sys
import os
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import get_session, Category, ProcessedFile, init_db
from pathlib import Path
from app.processor import TimeRecordProcessor

# 初始化数据库表
init_db()

s = get_session()

# 初始化根分类（如果不存在）
roots = [
    {"name": "工作", "code": "工作"},
    {"name": "学习", "code": "学习"},
    {"name": "睡觉", "code": "睡觉"},
    {"name": "玩耍", "code": "玩耍"},
    {"name": "吃饭", "code": "吃饭"},
    {"name": "通勤", "code": "通勤"},
    {"name": "整理仪容仪表", "code": "整理仪容仪表"},
]
for root in roots:
    existing = s.query(Category).filter(Category.code == root["code"]).first()
    if not existing:
        s.add(Category(name=root["name"], code=root["code"], level=0))
s.commit()
s.close()

# 处理新文件
input_dir = Path("data/input")
processed_dir = Path("data/processed")
files = list(input_dir.glob("*.html"))

print(f"Found {len(files)} HTML files in input folder")

if len(files) == 0:
    print("No files to process, starting web server...")
else:
    processed_count = 0
    for f in files:
        from app.models import compute_file_hash

        file_hash = compute_file_hash(f)
        print(f"Checking: {f.name}, hash: {file_hash[:16]}...")

        # 检查是否已处理 - 强制不跳过
        # s = get_session()
        # existing = (
        #     s.query(ProcessedFile).filter(ProcessedFile.file_hash == file_hash).first()
        # )
        # s.close()
        #
        # if existing:
        #     print(f"Skipped: {f.name} (already processed)")
        #     continue

        print(f"Processing: {f.name}")
        result = TimeRecordProcessor.process_file(f)

        print(
            f"  Result: {result.get('status')}, records: {len(result.get('records', []))}"
        )

        if result.get("status") == "success":
            # 移动到已处理目录
            import datetime

            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            target_dir = processed_dir / date_str
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / f.name

            # 如果目标文件已存在，先删除
            if target_path.exists():
                target_path.unlink()

            shutil.move(str(f), str(target_path))
            print(f"  Moved to: {target_path}")
        else:
            print(f"  失败原因: {result.get('message', '未知')}")

    print(f"\nDone! Processed {processed_count} new files")

print("Starting web server...")
