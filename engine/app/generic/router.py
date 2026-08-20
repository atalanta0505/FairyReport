"""
通用知识路由 — 状态/更新/检索。

- GET /generic/status — 已装版本/未装
- POST /generic/update — 凭 server_url+token 下载安装（sha256 校验、原子切换）
- GET /generic/query?text=&n= — 本地检索（未装 404；嵌入走可注入接口）
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .store import (
    GenericNotInstalled,
    GenericServerError,
    GenericStore,
    GenericTamperError,
    set_transport,
)

router = APIRouter(prefix="/generic", tags=["generic"])


class UpdateRequest(BaseModel):
    server_url: str = Field(..., min_length=1)
    token: str = Field(..., min_length=1)


@router.get("/status")
def status():
    """通用知识安装状态。"""
    return GenericStore.status()


@router.post("/update")
def update(body: UpdateRequest):
    """下载并安装通用知识包（sha256 校验、原子切换、幂等）。"""
    try:
        return GenericStore.update(body.server_url, body.token)
    except GenericServerError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except GenericTamperError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/query")
def query(
    text: str = Query(..., min_length=1),
    n: int = Query(5, ge=1, le=50),
):
    """对已装通用知识本地检索；未装 → 404。"""
    try:
        results = GenericStore.query(text, n=n)
    except GenericNotInstalled:
        raise HTTPException(status_code=404, detail="通用知识未安装，请先 update")
    return {"results": results}
