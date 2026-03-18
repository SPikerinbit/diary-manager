# pdf_parser.py
import PyPDF2
from pathlib import Path


def parse_pdf(file_path: Path) -> str:
    """解析PDF文件，返回文本内容"""
    text_parts = []

    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                text_parts.append(text)

    return "\n\n".join(text_parts)
