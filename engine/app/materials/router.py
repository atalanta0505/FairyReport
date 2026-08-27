"""
资料路由 — 摄取/列出/按来源删除资料。

摄取：按本地文件路径解析-分块-向量化入库（重复摄取 upsert 覆盖）。
"""
import os
import shutil

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import db as db_module
from .. import models
from ..config import settings
from ..embedding import get_embedder
from .chunking import ALLOWED_EXTS, chunk_text
from .converters import to_markdown
from .vectorstore import ProjectVectorStore

router = APIRouter(prefix="/projects/{name}/materials", tags=["materials"])


def _get_project(session: Session, name: str) -> models.Project:
    proj = session.execute(
        select(models.Project).where(models.Project.name == name)
    ).scalars().first()
    if not proj:
        raise HTTPException(status_code=404, detail=f"项目不存在：{name}")
    return proj


class IngestRequest(BaseModel):
    file_paths: list[str] = Field(..., min_length=1)


class IngestResult(BaseModel):
    source_id: str
    filename: str
    ext: str
    chunk_count: int
    size_bytes: int
    status: str
    error: str | None = None


class MaterialOut(BaseModel):
    id: int
    source_id: str
    filename: str
    ext: str
    chunk_count: int
    size_bytes: int
    created_at: str

    @classmethod
    def from_orm(cls, m: "models.Material") -> "MaterialOut":
        return cls(
            id=m.id,
            source_id=m.source_id,
            filename=m.filename,
            ext=m.ext,
            chunk_count=m.chunk_count,
            size_bytes=m.size_bytes,
            created_at=m.created_at.isoformat(),
        )


def _process_file(
    session: Session,
    proj: models.Project,
    store: ProjectVectorStore,
    embedder,
    fpath: str,
    copy_dest_dir: str | None = None,
) -> IngestResult:
    """解析、分块、向量化并入库单个文件。"""
    filename = os.path.basename(fpath)
    ext = os.path.splitext(filename)[1].lower()
    size_bytes = os.path.getsize(fpath) if os.path.exists(fpath) else 0

    try:
        # 解析 → Markdown
        md_text = to_markdown(fpath)
        if not md_text or not md_text.strip():
            return IngestResult(
                source_id=filename,
                filename=filename,
                ext=ext,
                chunk_count=0,
                size_bytes=size_bytes,
                status="error",
                error="转换后内容为空",
            )

        # 分块
        chunks = chunk_text(md_text, source_name=filename, source_id=filename)
        if not chunks:
            return IngestResult(
                source_id=filename,
                filename=filename,
                ext=ext,
                chunk_count=0,
                size_bytes=size_bytes,
                status="error",
                error="切片后无内容",
            )

        # 向量化
        embeddings = embedder.encode([c["text"] for c in chunks])

        # 幂等：先删旧同源向量再 upsert，保证不累积
        store.delete_by_source(filename)
        store.upsert(chunks, embeddings)

        # 拷贝文件到 files 目录（若需要且路径不同）
        if copy_dest_dir:
            dest_path = os.path.join(copy_dest_dir, filename)
            if os.path.abspath(fpath) != os.path.abspath(dest_path):
                shutil.copy2(fpath, dest_path)

        # upsert 资料记录
        existing = session.execute(
            select(models.Material).where(
                models.Material.project_id == proj.id,
                models.Material.source_id == filename,
            )
        ).scalars().first()
        if existing:
            existing.filename = filename
            existing.ext = ext
            existing.chunk_count = len(chunks)
            existing.size_bytes = size_bytes
        else:
            session.add(
                models.Material(
                    project_id=proj.id,
                    source_id=filename,
                    filename=filename,
                    ext=ext,
                    chunk_count=len(chunks),
                    size_bytes=size_bytes,
                )
            )
        session.commit()

        return IngestResult(
            source_id=filename,
            filename=filename,
            ext=ext,
            chunk_count=len(chunks),
            size_bytes=size_bytes,
            status="ok",
            error=None,
        )
    except Exception as e:
        session.rollback()
        return IngestResult(
            source_id=filename,
            filename=filename,
            ext=ext,
            chunk_count=0,
            size_bytes=size_bytes,
            status="error",
            error=f"摄取失败: {str(e)}",
        )


@router.post("/ingest", response_model=list[IngestResult])
def ingest_materials(
    name: str,
    body: IngestRequest,
    session: Session = Depends(db_module.get_db),
):
    """按本地文件路径摄取资料（docx/xlsx/csv/md/txt）。"""
    proj = _get_project(session, name)
    files_dir = settings.files_dir(name)
    files_dir.mkdir(parents=True, exist_ok=True)
    vector_dir = settings.vector_dir(name)
    vector_dir.mkdir(parents=True, exist_ok=True)

    store = ProjectVectorStore.get(name, vector_dir)
    embedder = get_embedder()

    results: list[IngestResult] = []
    for fpath in body.file_paths:
        fpath = fpath.strip()
        filename = os.path.basename(fpath)
        ext = os.path.splitext(filename)[1].lower()

        # 路径不存在 → 4xx
        if not os.path.exists(fpath):
            raise HTTPException(
                status_code=400, detail=f"路径不存在：{fpath}"
            )
        # 扩展名非法 → 4xx
        if ext not in ALLOWED_EXTS:
            raise HTTPException(
                status_code=415, detail=f"不支持的扩展名：{ext}（仅支持 docx/xlsx/csv/md/txt）"
            )

        res = _process_file(session, proj, store, embedder, fpath, copy_dest_dir=str(files_dir))
        results.append(res)

    return results


@router.post("/scan", response_model=list[IngestResult])
def scan_materials(
    name: str,
    session: Session = Depends(db_module.get_db),
):
    """扫描项目 files 目录下的所有资料文件并自动分块向量化入库。"""
    proj = _get_project(session, name)
    files_dir = settings.files_dir(name)
    files_dir.mkdir(parents=True, exist_ok=True)
    vector_dir = settings.vector_dir(name)
    vector_dir.mkdir(parents=True, exist_ok=True)

    store = ProjectVectorStore.get(name, vector_dir)
    embedder = get_embedder()

    results: list[IngestResult] = []
    for entry in sorted(os.listdir(files_dir)):
        fpath = os.path.join(files_dir, entry)
        if not os.path.isfile(fpath):
            continue
        ext = os.path.splitext(entry)[1].lower()
        if ext not in ALLOWED_EXTS:
            continue

        res = _process_file(session, proj, store, embedder, fpath, copy_dest_dir=None)
        results.append(res)

    return results


@router.get("", response_model=list[MaterialOut])
def list_materials(name: str, session: Session = Depends(db_module.get_db)):
    """列出项目下所有资料。"""
    proj = _get_project(session, name)
    rows = session.execute(
        select(models.Material)
        .where(models.Material.project_id == proj.id)
        .order_by(models.Material.id)
    ).scalars().all()
    return [MaterialOut.from_orm(r) for r in rows]


@router.delete("/{source_id}", status_code=204)
def delete_material(name: str, source_id: str, session: Session = Depends(db_module.get_db)):
    """按来源删除资料（文件 + 向量同步删除）。"""
    proj = _get_project(session, name)
    mat = session.execute(
        select(models.Material).where(
            models.Material.project_id == proj.id,
            models.Material.source_id == source_id,
        )
    ).scalars().first()
    if not mat:
        raise HTTPException(status_code=404, detail=f"资料不存在：{source_id}")

    # 删向量
    store = ProjectVectorStore.get(name, settings.vector_dir(name))
    store.delete_by_source(source_id)

    # 删拷贝文件
    fpath = os.path.join(settings.files_dir(name), source_id)
    if os.path.exists(fpath):
        try:
            os.remove(fpath)
        except OSError:
            pass

    # 删 DB 记录
    session.delete(mat)
    session.commit()
    return None
