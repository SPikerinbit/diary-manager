# markdown_parser.py
import markdown
from pathlib import Path


def parse_markdown(file_path: Path) -> str:
    """解析Markdown文件，返回原始文本内容"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 转换为纯文本（去掉markdown标记）
    md = markdown.Markdown(extensions=["strip"])
    text = md.convert(content)

    # 如果转换后为空，返回原始内容
    return text if text else content
