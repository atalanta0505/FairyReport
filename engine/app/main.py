"""
FairyReport 本地引擎 — FastAPI 入口（仅绑定 127.0.0.1）。

运行（仓库根目录）：
    python -m engine.app.main
或
    uvicorn engine.app.main:app --host 127.0.0.1 --port 8001
"""
from fastapi import FastAPI

from . import db, models  # noqa: F401（注册 ORM 模型）
from .config import settings
from .materials.router import router as materials_router
from .projects.router import router as projects_router

app = FastAPI(title="FairyReport Engine", version="1.0.0")

app.include_router(projects_router)
app.include_router(materials_router)

db.create_tables()


@app.get("/health")
def health():
    """健康检查。"""
    return {"status": "ok", "host": settings.host}


def main() -> None:
    """本机启动（仅 127.0.0.1）。"""
    import uvicorn

    uvicorn.run(
        "engine.app.main:app",
        host=settings.host,  # 仅 127.0.0.1
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
