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

# 嵌入向量的维度和库里的模型名；Qwen3-Embedding-0.6B 与 bge-m3 都是 1024 维
EMBEDDING_DIMENSION = 1024
QWEN3_MODEL_NAME = "qwen3-embedding-0.6b"
BGE_M3_MODEL_NAME = "bge-m3"

# Qwen3-Embedding 只给查询加指令，文档不加
QWEN3_QUERY_INSTRUCTION = (
    "Given a question about the Dify platform, retrieve documentation passages that answer it"
)


# 检索：向量和 BM25 各取前 RETRIEVE_TOP_K，RRF 融合后取前 FUSION_TOP_K 送去精排，最后留 FINAL_TOP_K
RETRIEVE_TOP_K = 30
FUSION_TOP_K = 20
FINAL_TOP_K = 5
RRF_K = 60
QWEN3_RERANKER_NAME = "qwen3-reranker-0.6b"
BGE_RERANKER_NAME = "bge-reranker-v2-m3"
# 版本过滤：只看自部署版 / 云版时，同时包含「通用」文档
EDITION_FILTERS = {
    "self_host": ("self_host", "common"),
    "cloud": ("cloud", "common"),
}

# DeepSeek（deepseek-flash）按高峰时段、缓存未命中的价格保守估算（美元/百万 token），
# 价格页 https://api-docs.deepseek.com/quick_start/pricing，2026-10-16 核对；官方改价后要更新
DEEPSEEK_INPUT_USD_PER_MILLION = 0.3
DEEPSEEK_OUTPUT_USD_PER_MILLION = 1.2
USD_TO_CNY = 7.2


class Settings(BaseSettings):
    """从环境变量和仓库根目录的 `.env` 读取；字段与 `.env.example` 保持一致。"""

    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://grounded:grounded@localhost:5432/grounded_rag"
    db_timeout_seconds: float = 5.0
    log_level: str = "INFO"
    embedding_model: str = "qwen3"  # qwen3 / bge-m3 / fake
    embed_device: str = "cuda"
    embed_batch_size: int = 32
    reranker_model: str = "qwen3"  # qwen3 / bge / fake / none
    chat_model: str = "deepseek"  # deepseek / fake
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"
    daily_budget_cny: float = 10.0  # 0 表示不限制（作者手动测试用）


@lru_cache
def get_settings() -> Settings:
    return Settings()
