"""
FairyReport Backend — 全局配置（pydantic-settings）

优先级：环境变量 > backend/.env > 默认值（与根 config.py 的 .env 覆盖风格一致）。
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """后端运行配置；所有项均可通过环境变量或 backend/.env 覆盖。"""

    # ── 数据库 ──
    database_url: str = "sqlite:///./backend_dev.db"

    # ── JWT ──
    jwt_secret: str = "dev-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7

    # ── 邮箱验证码 ──
    auth_code_expire_minutes: int = 10
    auth_code_resend_interval_seconds: int = 60
    auth_code_daily_limit: int = 10

    # ── QQ SMTP（凭据只从环境变量/.env 读取，禁止硬编码）──
    smtp_host: str = "smtp.qq.com"
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_auth_code: str = ""
    smtp_from_name: str = "FairyReport"

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
