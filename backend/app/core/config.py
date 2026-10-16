"""应用配置：环境变量只在这里读取。"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py → 仓库根目录
REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data"
CACHE_DIR = REPO_ROOT / ".cache"


class Settings(BaseSettings):
    """从环境变量和仓库根目录的 `.env` 读取；字段与 `.env.example` 保持一致。"""

    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://grounded:grounded@localhost:5432/grounded_rag"
    db_timeout_seconds: float = 5.0
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
