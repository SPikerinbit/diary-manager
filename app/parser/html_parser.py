# html_parser.py
import re
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime


def parse_html(file_path: Path) -> str:
    """解析HTML文件，返回文本内容"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    soup = BeautifulSoup(content, "html.parser")

    for script in soup(["script", "style"]):
        script.decompose()

    text = soup.get_text(separator="\n", strip=True)

    lines = [line for line in text.split("\n") if line.strip()]
    return "\n".join(lines)


def extract_date_from_content(file_path: Path) -> str:
    """从HTML内容中提取日期，返回 YYYY-MM-DD 格式"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    soup = BeautifulSoup(content, "html.parser")
    first_text = (
        soup.get_text(strip=True).split("\n")[0] if soup.get_text(strip=True) else ""
    )

    patterns = [
        (r"(\d{4})年(\d{1,2})月(\d{1,2})日", "YYYY-MM-DD"),
        (r"(\d{4})-(\d{1,2})-(\d{1,2})", "YYYY-MM-DD"),
        (r"(\d{1,2})/(\d{1,2})/(\d{4})", "MM/DD/YYYY"),
        (r"^(\d{4})(\d{2})(\d{2})$", "YYYYMMDD"),
    ]

    for pattern, fmt in patterns:
        match = re.search(pattern, first_text)
        if match:
            groups = match.groups()
            if fmt == "YYYY-MM-DD":
                year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                return f"{year:04d}-{month:02d}-{day:02d}"
            elif fmt == "MM/DD/YYYY":
                month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                return f"{year:04d}-{month:02d}-{day:02d}"
            elif fmt == "YYYYMMDD":
                year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                return f"{year:04d}-{month:02d}-{day:02d}"

    # 尝试从标题或h1标签获取
    title = soup.find("title")
    if title:
        match = re.search(pattern, title.get_text())
        if match:
            groups = match.groups()
            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
            return f"{year:04d}-{month:02d}-{day:02d}"

    h1 = soup.find("h1")
    if h1:
        for pattern, _ in patterns:
            match = re.search(pattern, h1.get_text())
            if match:
                groups = match.groups()
                year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                return f"{year:04d}-{month:02d}-{day:02d}"

    return None
