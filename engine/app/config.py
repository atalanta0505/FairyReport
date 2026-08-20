"""
FairyReport 本地引擎 — 全局配置（pydantic-settings）。

优先级：环境变量 > 默认值。ENGINE_DATA_DIR 默认 %LOCALAPPDATA%/FairyReport。
"""
import os
import warnings
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_engine_data_dir() -> str:
    """解析引擎数据根目录：环境变量 ENGINE_DATA_DIR 优先，否则 %LOCALAPPDATA%/FairyReport。"""
    env = os.environ.get("ENGINE_DATA_DIR")
    if env:
        return env
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return str(Path(local) / "FairyReport")
    return str(Path.home() / "FairyReport")


class Settings(BaseSettings):
    """引擎运行配置；所有项均可通过环境变量覆盖。"""

    # ── 数据目录 ──
    engine_data_dir: str = ""

    # ── 分块参数 ──
    chunk_size: int = 800
    chunk_overlap: int = 100

    # ── 嵌入模型 ──
    embed_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    # ── 服务绑定（仅本机）──
    host: str = "127.0.0.1"
    port: int = 8001

    model_config = SettingsConfigDict(extra="ignore")

    @property
    def database_url(self) -> str:
        """SQLite 数据库 URL（位于数据根目录下）。"""
        p = Path(self.engine_data_dir) / "engine.db"
        p.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{p.as_posix()}"

    @property
    def projects_dir(self) -> Path:
        """项目根目录：ENGINE_DATA_DIR/projects。"""
        return Path(self.engine_data_dir) / "projects"

    def project_dir(self, name: str) -> Path:
        return self.projects_dir / name

    def files_dir(self, name: str) -> Path:
        return self.projects_dir / name / "files"

    def vector_dir(self, name: str) -> Path:
        return self.projects_dir / name / "vector"


settings = Settings(engine_data_dir=_default_engine_data_dir())

# FRL-003：确保 overlap < size，防止 _chunk_segment 死循环
if settings.chunk_overlap >= settings.chunk_size:
    warnings.warn(
        f"CHUNK_OVERLAP ({settings.chunk_overlap}) >= CHUNK_SIZE ({settings.chunk_size}),"
        f" clamping overlap to size//4"
    )
    settings.chunk_overlap = max(0, settings.chunk_size // 4)
