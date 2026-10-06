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

    # ── LLM 网关（Key 只从环境变量/.env 读取，禁止硬编码）──
    llm_api_keys: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model_allowlist: str = "deepseek-flash,deepseek-v4-pro"
    llm_timeout: int = 120

    # ── 通用知识包目录（JWT 保护下发；manifest.json + pack.zip）──
    pack_dir: str = "pack"

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def llm_key_list(self) -> list[str]:
        """LLM_API_KEYS 逗号分隔的 Key 池（去除空白与空项）。"""
        return [k.strip() for k in self.llm_api_keys.split(",") if k.strip()]

    @property
    def llm_model_allowlist_items(self) -> list[str]:
        """LLM_MODEL_ALLOWLIST 逗号分隔的模型白名单。"""
        return [m.strip() for m in self.llm_model_allowlist.split(",") if m.strip()]


settings = Settings()
