import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import get_session, TimeRecord, ProcessedFile, Category
from app.config import config

s = get_session()

# 清空数据
s.query(TimeRecord).delete()
s.query(ProcessedFile).delete()
s.query(Category).delete()
s.commit()
print("Deleted all records")

# 重新初始化根分类
roots = [
    {"name": "学习", "code": "学习"},
    {"name": "睡觉", "code": "睡觉"},
    {"name": "玩耍", "code": "玩耍"},
    {"name": "吃饭", "code": "吃饭"},
    {"name": "工作", "code": "工作"},
]
for r in roots:
    s.add(Category(name=r["name"], code=r["code"], level=0))
s.commit()
print("Initialized root categories")

s.close()

# 处理文件
from pathlib import Path
from app.processor import TimeRecordProcessor

files = list(Path("data/input").glob("*.html"))
print(f"Found {len(files)} files")

for f in files:
    print(f"Processing: {f.name}")
    result = TimeRecordProcessor.process_file(f)
    print(
        f"  Result: {result.get('status')}, records: {len(result.get('records', []))}"
    )

print("Done!")
