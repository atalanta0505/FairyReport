"""
导出路由 — 合并章节 markdown 导出 docx。

POST /export/docx {project, title, chapters{seq: md}, include_refs 默认 true}
→ 按 seq 合并 → 全局参考文献表（复用 writing.refs）→ 生成 docx 到 ENGINE_DATA_DIR/exports/
→ 返回 {path, size_bytes}；chapters 空/非法 → 422。
"""
import os
import re
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..config import settings
from .docx_builder import build_merged_md, md_to_docx

router = APIRouter(prefix="/export", tags=["export"])


class ExportDocxRequest(BaseModel):
    project: str = ""
    title: str = ""
    chapters: dict = Field(default_factory=dict)
    include_refs: bool = True


def _safe_filename(name: str) -> str:
    """文件名安全化：保留字母数字下划线连字符，其余替换。"""
    cleaned = re.sub(r"[^\w\-]", "_", name or "report")
    return cleaned.strip("_") or "report"


def _exports_dir() -> str:
    d = os.path.join(settings.engine_data_dir, "exports")
    os.makedirs(d, exist_ok=True)
    return d


@router.post("/docx")
def export_docx(req: ExportDocxRequest):
    """合并章节 markdown 导出 docx；chapters 空/非法 → 422。"""
    # chapters 非空且为 dict[str, str]
    if not req.chapters or not isinstance(req.chapters, dict):
        raise HTTPException(status_code=422, detail="chapters 不能为空")
    for k, v in req.chapters.items():
        if not isinstance(v, str):
            raise HTTPException(status_code=422, detail=f"chapter {k} 内容必须为字符串")

    # 按 seq 合并 + 全局参考文献表
    try:
        final_md = build_merged_md(req.chapters, include_refs=req.include_refs)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"合并失败：{e}")

    if not final_md.strip():
        raise HTTPException(status_code=422, detail="合并后内容为空")

    # 生成 docx
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{_safe_filename(req.project)}_{stamp}.docx"
    out_path = os.path.join(_exports_dir(), fname)

    try:
        md_to_docx(final_md, out_path, title=req.title)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"docx 生成失败：{e}")

    size = os.path.getsize(out_path)
    return {"path": out_path, "size_bytes": size}
