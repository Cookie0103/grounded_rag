import pytest

from app.core.config import MODEL_CACHE_DIR, Settings
from app.core.errors import ConfigError
from app.providers.factory import SPECS, get_embedder
from app.providers.fakes import FakeEmbedder
from app.providers.local_embedder import SentenceTransformerEmbedder


def _settings() -> Settings:
    return Settings(_env_file=None, embed_device="cpu", embed_batch_size=7)


def test_fake_embedder_is_returned_for_fake() -> None:
    embedder = get_embedder("fake", _settings())

    assert isinstance(embedder, FakeEmbedder)
    assert embedder.name == "fake"


@pytest.mark.parametrize(
    ("name", "model_name", "model_id"),
    [
        ("qwen3", "qwen3-embedding-0.6b", "Qwen/Qwen3-Embedding-0.6B"),
        ("bge-m3", "bge-m3", "BAAI/bge-m3"),
    ],
)
def test_local_models_get_their_database_names_without_loading_anything(
    name: str, model_name: str, model_id: str
) -> None:
    embedder = get_embedder(name, _settings())

    assert isinstance(embedder, SentenceTransformerEmbedder)  # 创建时不加载 torch 和模型
    assert (embedder.name, embedder.dimension) == (model_name, 1024)
    assert SPECS[name].model_id == model_id


def test_only_qwen3_gets_a_query_instruction_and_left_padding() -> None:
    assert SPECS["qwen3"].query_instruction is not None
    assert SPECS["qwen3"].padding_side == "left"
    assert SPECS["bge-m3"].query_instruction is None
    assert SPECS["bge-m3"].padding_side == "right"


def test_models_are_cached_inside_the_repository() -> None:
    assert MODEL_CACHE_DIR.parts[-2:] == (".cache", "models")


def test_unknown_model_name_is_rejected_with_the_valid_choices() -> None:
    with pytest.raises(ConfigError, match="qwen3, bge-m3, fake"):
        get_embedder("gpt", _settings())
