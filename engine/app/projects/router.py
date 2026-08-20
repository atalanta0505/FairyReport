"""
项目路由 — 创建/列出/删除项目。
"""
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import db as db_module
from .. import models
from ..config import settings
from ..materials.vectorstore import remove_project_data

router = APIRouter(prefix="/projects", tags=["projects"])

# 项目名：禁止路径分隔符与特殊字符，防目录穿越
_NAME_RE = re.compile(r"^[^/\\:*?\"<>|\s]+$")


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def _safe_name(cls, v: str) -> str:
        v = v.strip()
        if v in (".", ".."):
            raise ValueError("项目名不能为 '.' 或 '..'")
        if not _NAME_RE.match(v):
            raise ValueError("项目名含非法字符（路径分隔符或特殊符号）")
        return v


class ProjectOut(BaseModel):
    id: int
    name: str
    created_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, p: "models.Project") -> "ProjectOut":
        return cls(id=p.id, name=p.name, created_at=p.created_at.isoformat())


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectCreate, session: Session = Depends(db_module.get_db)):
    """创建项目（含 files 与 vector 目录）。"""
    exists = session.execute(
        select(models.Project).where(models.Project.name == body.name)
    ).scalars().first()
    if exists:
        raise HTTPException(status_code=409, detail=f"项目已存在：{body.name}")

    proj = models.Project(name=body.name)
    session.add(proj)
    session.commit()
    session.refresh(proj)

    # 建目录
    settings.files_dir(body.name).mkdir(parents=True, exist_ok=True)
    settings.vector_dir(body.name).mkdir(parents=True, exist_ok=True)

    return ProjectOut.from_orm(proj)


@router.get("", response_model=list[ProjectOut])
def list_projects(session: Session = Depends(db_module.get_db)):
    rows = session.execute(select(models.Project).order_by(models.Project.id)).scalars().all()
    return [ProjectOut.from_orm(r) for r in rows]


@router.delete("/{name}", status_code=204)
def delete_project(name: str, session: Session = Depends(db_module.get_db)):
    """删除项目（连同 files 与 vector 目录）。"""
    proj = session.execute(
        select(models.Project).where(models.Project.name == name)
    ).scalars().first()
    if not proj:
        raise HTTPException(status_code=404, detail=f"项目不存在：{name}")

    session.delete(proj)
    session.commit()

    # 先关闭向量库缓存释放锁，再删目录
    remove_project_data(name)
    return None
