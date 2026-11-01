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
from .export.router import router as export_router
from .generic.router import router as generic_router
from .materials.router import router as materials_router
from .projects.router import router as projects_router
from .writing.router import router as writing_router

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="FairyReport Engine", version="1.6.5")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router)
app.include_router(materials_router)
app.include_router(generic_router)
app.include_router(writing_router)
app.include_router(export_router)

db.create_tables()


@app.get("/health")
def health():
    """健康检查。"""
    return {"status": "ok", "host": settings.host}


# ── 静态 Web 资源托管（支持云端单端口一键托管浏览器界面）──
import os
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

_web_dist_candidates = [
    Path(__file__).resolve().parents[2] / "desktop" / "dist",
    Path(__file__).resolve().parents[2] / "web_dist",
    Path("desktop/dist"),
    Path("web_dist"),
]
_web_dist = next((p for p in _web_dist_candidates if p.is_dir() and (p / "index.html").is_file()), None)
if _web_dist:
    if (_web_dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=str(_web_dist / "assets")), name="assets")

    @app.get("/")
    @app.get("/index.html")
    def serve_index():
        """提供 Web 前端单页应用入口。"""
        return FileResponse(str(_web_dist / "index.html"))



def main() -> None:
    """启动服务。"""
    import argparse
    import os
    import uvicorn

    parser = argparse.ArgumentParser(description="FairyReport Local Engine")
    parser.add_argument("--host", default=os.environ.get("HOST", settings.host), help="绑定主机地址")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", str(settings.port))), help="绑定端口")
    args = parser.parse_args()

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
