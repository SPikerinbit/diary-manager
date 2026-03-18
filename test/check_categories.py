import sys

sys.path.insert(0, ".")
from pathlib import Path
from app.parser import parse_document
from app.llm import get_llm_client
from app.processor import CategoryManager

# 获取已有分类
existing_cats = CategoryManager.get_category_tree()


def format_cats(cats, indent=0):
    lines = []
    for c in cats:
        lines.append("  " * indent + f"- {c['name']}")
        if c.get("children"):
            lines.extend(format_cats(c["children"], indent + 1))
    return lines


categories_str = "\n".join(format_cats(existing_cats))
print("已有分类:\n" + categories_str)

# 测试LLM
text = parse_document(Path("data/input/2026-03-15_日记.html"))
print("\n===== LLM返回结果 =====")
client = get_llm_client()
result = client.extract_time_blocks(text, categories_str)

for i, block in enumerate(result):
    print(f"{i + 1}. activity: {block.get('activity')}")
    print(f"   category_path: {block.get('category_path')}")
    print(f"   duration: {block.get('duration_minutes')}")
    print()
