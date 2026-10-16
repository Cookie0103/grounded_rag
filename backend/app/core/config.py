"""应用配置：环境变量只在这里读取。"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py → 仓库根目录
REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data"
CACHE_DIR = REPO_ROOT / ".cache"
MODEL_CACHE_DIR = CACHE_DIR / "models"

# 入库流程的参数：改了清洗或切块逻辑就把 INGEST_VERSION 加 1，下次入库会全量重建
INGEST_VERSION = "1"
CHILD_TARGET_CHARS = 300
CHILD_MAX_CHARS = 500
PARENT_MAX_CHARS = 4000
CODE_BLOCK_MAX_CHARS = 1500

# Qwen3-Embedding 只给查询加指令，文档不加
QWEN3_QUERY_INSTRUCTION = (
    "Given a question about the Dify platform, retrieve documentation passages that answer it"
)


class Settings(BaseSettings):
    """从环境变量和仓库根目录的 `.env` 读取；字段与 `.env.example` 保持一致。"""

    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://grounded:grounded@localhost:5432/grounded_rag"
    db_timeout_seconds: float = 5.0
    log_level: str = "INFO"
    embedding_model: str = "qwen3"  # qwen3 / bge-m3 / fake
    embed_device: str = "cuda"
    embed_batch_size: int = 32


@lru_cache
def get_settings() -> Settings:
    return Settings()
