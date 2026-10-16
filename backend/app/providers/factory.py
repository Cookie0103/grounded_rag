"""按配置里的名字创建嵌入模型。"""

from app.core.config import (
    BGE_M3_MODEL_NAME,
    MODEL_CACHE_DIR,
    QWEN3_MODEL_NAME,
    QWEN3_QUERY_INSTRUCTION,
    Settings,
)
from app.core.errors import ConfigError
from app.providers.base import Embedder
from app.providers.fakes import FAKE_MODEL_NAME, FakeEmbedder
from app.providers.local_embedder import EmbedderSpec, SentenceTransformerEmbedder

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
