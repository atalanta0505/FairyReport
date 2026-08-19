"""
FairyReport Backend — 数据库引擎与会话管理（SQLAlchemy 同步）
"""
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import settings


def utcnow() -> datetime:
    """返回 naive UTC 当前时间（数据库字段统一存储时区）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def make_engine(url: str):
    """按给定 URL 创建引擎；SQLite 追加线程/内存库所需连接参数。"""
    kwargs = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
    return create_engine(url, **kwargs)


class Base(DeclarativeBase):
    """全部 ORM 模型的声明基类。"""


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_tables() -> None:
    """创建全部数据表（先导入 models 确保表已注册）。"""
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI 依赖：提供请求级数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
