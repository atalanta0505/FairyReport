"""
FairyReport Backend — 通用知识包下发端点（JWT 保护）。

- GET /api/pack/manifest → 返回 PACK_DIR/manifest.json（缺失 404）
- GET /api/pack/download → FileResponse 返回 PACK_DIR/pack.zip（缺失 404）
"""
import os

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..auth.router import current_user
from ..config import settings
from ..db import get_db

pack_router = APIRouter(prefix="/api/pack", tags=["pack"])


def _pack_path(filename: str) -> str:
    return os.path.join(settings.pack_dir, filename)


@pack_router.get("/manifest")
def manifest(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    """返回知识包 manifest.json（需有效 JWT 或演示 Token）。"""
    if authorization != "Bearer demo-access-token":
        current_user(authorization, db)  # JWT 门控
    path = _pack_path("manifest.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="知识包 manifest 不存在")
    with open(path, "r", encoding="utf-8") as f:
        import json

        return json.load(f)


@pack_router.get("/download")
def download(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    """流式返回知识包 pack.zip（需有效 JWT 或演示 Token）。"""
    if authorization != "Bearer demo-access-token":
        current_user(authorization, db)  # JWT 门控
    path = _pack_path("pack.zip")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="知识包包体不存在")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="pack.zip",
    )
