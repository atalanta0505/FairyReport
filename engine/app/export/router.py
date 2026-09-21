"""
导出路由 — 合并章节 markdown 导出 docx。

POST /export/docx {project, title, chapters{seq: md}, include_refs 默认 true}
→ 按 seq 合并 → 全局参考文献表（复用 writing.refs）→ 生成 docx 到 ENGINE_DATA_DIR/exports/
→ 返回 {path, size_bytes}；chapters 空/非法 → 422。
"""
import os
import re
import subprocess
import sys
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
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
        final_md = build_merged_md(req.chapters, include_refs=req.include_refs, project=req.project)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"合并失败：{e}")

    if not final_md.strip():
        raise HTTPException(status_code=422, detail="合并后内容为空")

    # 生成 docx
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{_safe_filename(req.project)}_{stamp}.docx"
    out_path = os.path.join(_exports_dir(), fname)

    try:
        md_to_docx(final_md, out_path, title=req.title, project=req.project)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"docx 生成失败：{e}")

    size = os.path.getsize(out_path)
    return {"path": out_path, "size_bytes": size, "filename": fname}


class ExportMdRequest(BaseModel):
    project: str = ""
    title: str = ""
    chapters: dict = Field(default_factory=dict)
    include_refs: bool = True


@router.post("/md")
def export_md(req: ExportMdRequest):
    """合并章节 markdown 导出 .md 成果文件；chapters 空/非法 → 422。"""
    if not req.chapters or not isinstance(req.chapters, dict):
        raise HTTPException(status_code=422, detail="chapters 不能为空")
    for k, v in req.chapters.items():
        if not isinstance(v, str):
            raise HTTPException(status_code=422, detail=f"chapter {k} 内容必须为字符串")

    try:
        final_md = build_merged_md(req.chapters, include_refs=req.include_refs, project=req.project)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"合并失败：{e}")

    if not final_md.strip():
        raise HTTPException(status_code=422, detail="合并后内容为空")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{_safe_filename(req.project)}_{stamp}.md"
    out_path = os.path.join(_exports_dir(), fname)

    try:
        with open(out_path, "w", encoding="utf-8") as f:
            if req.title:
                f.write(f"# {req.title}\n\n")
            f.write(final_md)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"md 导出失败：{e}")

    size = os.path.getsize(out_path)
    return {"path": out_path, "size_bytes": size, "content": final_md, "filename": fname}


@router.get("/download/{filename}")
def download_export(filename: str):
    """跨网下载导出的成果文件（docx/md）。"""
    cleaned = os.path.basename(filename.strip())
    fpath = os.path.join(_exports_dir(), cleaned)
    if not os.path.isfile(fpath):
        raise HTTPException(status_code=404, detail=f"成果文件不存在：{cleaned}")
    return FileResponse(
        fpath,
        filename=cleaned,
        media_type="application/octet-stream",
    )


class OpenExportFolderRequest(BaseModel):
    path: str = ""
    project: str = ""


@router.post("/open-folder")
def open_export_folder_endpoint(req: OpenExportFolderRequest = None):
    """在系统资源管理器中打开导出成果文件夹（若传入 path 则直接定位并高亮选中该文件）。"""
    exports_dir = _exports_dir()
    target_path = req.path.strip() if req and req.path else ""

    if target_path and os.path.exists(target_path):
        try:
            if os.name == "nt":
                # Windows 下使用 explorer.exe /select,"<file_path>" 精确高亮选中导出的文件
                norm_p = os.path.normpath(target_path)
                subprocess.Popen(f'explorer.exe /select,"{norm_p}"')
                return {"path": target_path}
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", target_path])
                return {"path": target_path}
            else:
                subprocess.Popen(["xdg-open", os.path.dirname(target_path)])
                return {"path": target_path}
        except Exception:
            pass

    # fallback: 直接打开 exports 目录
    try:
        if os.name == "nt":
            os.startfile(exports_dir)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", exports_dir])
        else:
            subprocess.Popen(["xdg-open", exports_dir])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"打开导出文件夹失败: {e}")
    return {"path": exports_dir}
