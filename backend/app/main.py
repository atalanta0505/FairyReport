"""
FairyReport Backend — FastAPI 入口

运行（仓库根目录）：uvicorn backend.app.main:app --reload
"""
from fastapi import FastAPI

from . import db, models  # noqa: F401（注册 ORM 模型）
from .auth.router import auth_router, users_router
from .llm.router import llm_router
from .pack.router import pack_router

app = FastAPI(title="FairyReport Backend", version="2.0.0-dev")

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(llm_router)
app.include_router(pack_router)

db.create_tables()


@app.get("/api/health")
def health():
    """健康检查。"""
    return {"status": "ok"}
