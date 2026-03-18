# models.py - 数据库模型
from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from pathlib import Path
import hashlib

from .config import config

Base = declarative_base()


class Category(Base):
    """分类树节点"""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)  # 分类名称
    code = Column(String(50), unique=True)  # 唯一编码
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    level = Column(Integer, default=0)  # 层级深度
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    parent = relationship("Category", remote_side=[id], backref="children")
    time_records = relationship("TimeRecord", back_populates="category")

    def to_dict(self, include_children=False):
        result = {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "parent_id": self.parent_id,
            "level": self.level,
        }
        if include_children and self.children:
            result["children"] = [
                c.to_dict(include_children=True) for c in self.children
            ]
        return result


class TimeRecord(Base):
    """时间记录"""

    __tablename__ = "time_records"

    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    date = Column(DateTime, nullable=False)  # 日期
    duration_minutes = Column(Integer, nullable=False)  # 时长（分钟）
    source_file = Column(String(255))  # 来源文件
    raw_text = Column(Text)  # 大模型原始输出
    created_at = Column(DateTime, default=datetime.now)

    category = relationship("Category", back_populates="time_records")

    def to_dict(self):
        return {
            "id": self.id,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "date": self.date.strftime("%Y-%m-%d"),
            "duration_minutes": self.duration_minutes,
            "duration_hours": round(self.duration_minutes / 60, 2),
            "source_file": self.source_file,
        }


class ProcessedFile(Base):
    """已处理文件记录"""

    __tablename__ = "processed_files"

    id = Column(Integer, primary_key=True)
    file_hash = Column(String(64), unique=True)  # 文件hash
    original_path = Column(String(500))
    processed_at = Column(DateTime, default=datetime.now)


class WeeklyReport(Base):
    """周报"""

    __tablename__ = "weekly_reports"

    id = Column(Integer, primary_key=True)
    week_start = Column(DateTime, nullable=False)  # 周开始日期
    week_end = Column(DateTime, nullable=False)  # 周结束日期
    summary = Column(Text)  # 总结JSON
    created_at = Column(DateTime, default=datetime.now)


def get_engine():
    """获取数据库引擎"""
    db_path = config["directories"]["database"]
    engine = create_engine(f"sqlite:///{db_path}")
    return engine


def get_session():
    """获取数据库会话"""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def init_db():
    """初始化数据库"""
    engine = get_engine()
    Base.metadata.create_all(engine)

    # 初始化根分类
    session = get_session()
    try:
        existing = session.query(Category).filter(Category.parent_id == None).first()
        if not existing:
            roots = config.get("categories", {}).get("roots", [])
            for root in roots:
                category = Category(
                    name=root["name"], code=root["code"], parent_id=None, level=0
                )
                session.add(category)
            session.commit()
    finally:
        session.close()


def compute_file_hash(file_path):
    """计算文件MD5 hash"""
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5.update(chunk)
    return md5.hexdigest()
