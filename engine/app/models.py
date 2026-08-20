"""
FairyReport 本地引擎 — ORM 模型（Project / Material）。
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, utcnow


class Project(Base):
    """项目：name 唯一，对应文件目录与向量目录。"""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class Material(Base):
    """资料记录：按 source_id（文件名）幂等，重复摄取覆盖。"""

    __tablename__ = "materials"
    __table_args__ = (UniqueConstraint("project_id", "source_id", name="uq_project_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_id: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    ext: Mapped[str] = mapped_column(String(16), nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
