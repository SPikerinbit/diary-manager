# parser/__init__.py
from .pdf_parser import parse_pdf
from .markdown_parser import parse_markdown
from .word_parser import parse_word


def parse_document(file_path):
    """根据文件类型解析文档"""
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        return parse_pdf(file_path)
    elif suffix in [".md", ".markdown"]:
        return parse_markdown(file_path)
    elif suffix in [".docx", ".doc"]:
        return parse_word(file_path)
    else:
        raise ValueError(f"不支持的文件类型: {suffix}")
