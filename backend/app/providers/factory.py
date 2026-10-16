"""按配置里的名字创建嵌入模型和精排模型。"""

from app.core.config import (
    BGE_M3_MODEL_NAME,
    BGE_RERANKER_NAME,
    MODEL_CACHE_DIR,
    QWEN3_MODEL_NAME,
    QWEN3_QUERY_INSTRUCTION,
    QWEN3_RERANKER_NAME,
    Settings,
)
from app.core.errors import ConfigError
from app.providers.base import Embedder, Reranker
from app.providers.fakes import FAKE_MODEL_NAME, FakeEmbedder, FakeReranker
from app.providers.local_embedder import EmbedderSpec, SentenceTransformerEmbedder
from app.providers.local_reranker import CrossEncoderReranker, Qwen3Reranker

SPECS = {
    "qwen3": EmbedderSpec(
        name=QWEN3_MODEL_NAME,
        model_id="Qwen/Qwen3-Embedding-0.6B",
        query_instruction=QWEN3_QUERY_INSTRUCTION,
        padding_side="left",
    ),
    "bge-m3": EmbedderSpec(
        name=BGE_M3_MODEL_NAME,
        model_id="BAAI/bge-m3",
        query_instruction=None,
        padding_side="right",
    ),
}
RERANK_BATCH_SIZE = 8
RERANKER_NAMES = ("qwen3", "bge", FAKE_MODEL_NAME, "none")


def get_embedder(name: str, settings: Settings) -> Embedder:
    """name: qwen3 / bge-m3 / fake。"""
    if name == FAKE_MODEL_NAME:
        return FakeEmbedder()
    spec = SPECS.get(name)
    if spec is None:
        raise ConfigError(f"未知的嵌入模型 {name!r}，可选：{', '.join([*SPECS, FAKE_MODEL_NAME])}")
    return SentenceTransformerEmbedder(
        spec,
        device=settings.embed_device,
        batch_size=settings.embed_batch_size,
        cache_dir=MODEL_CACHE_DIR,
    )


def get_reranker(name: str, settings: Settings) -> Reranker | None:
    """name: qwen3 / bge / fake / none（none 返回 None，表示不精排）。"""
    if name == "none":
        return None
    if name == FAKE_MODEL_NAME:
        return FakeReranker()
    if name == "qwen3":
        return Qwen3Reranker(
            QWEN3_RERANKER_NAME,
            "Qwen/Qwen3-Reranker-0.6B",
            device=settings.embed_device,
            batch_size=RERANK_BATCH_SIZE,
            cache_dir=MODEL_CACHE_DIR,
        )
    if name == "bge":
        return CrossEncoderReranker(
            BGE_RERANKER_NAME,
            "BAAI/bge-reranker-v2-m3",
            device=settings.embed_device,
            batch_size=RERANK_BATCH_SIZE,
            cache_dir=MODEL_CACHE_DIR,
        )
    raise ConfigError(f"未知的精排模型 {name!r}，可选：{', '.join(RERANKER_NAMES)}")
