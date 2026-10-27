"""本机 GPU 测试：`uv run poe test-gpu`。第一次运行会下载约 1.2GB 的模型到 .cache/models/。"""

import importlib
import math

import pytest

from app.core.config import EMBEDDING_DIMENSION, Settings
from app.providers.factory import get_embedder

pytestmark = pytest.mark.gpu


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_gpu_is_available_and_is_the_blackwell_card() -> None:
    torch = importlib.import_module("torch")

    assert torch.cuda.is_available()
    assert torch.cuda.get_device_capability() == (12, 0)  # RTX 5070 Ti = sm_120


async def test_qwen3_embeddings_are_1024d_normalized_and_semantically_ordered() -> None:
    embedder = get_embedder("qwen3", Settings(_env_file=None))
    documents = [
        "单次最多可上传 5 个文件，通过 UPLOAD_FILE_BATCH_LIMIT 设置。",
        "在监控页面可以查看应用的调用次数和响应时间。",
    ]

    doc_vectors = await embedder.embed_documents(documents)
    query_vector = (await embedder.embed_queries(["知识库一次最多能上传几个文件"]))[0]

    assert len(doc_vectors) == 2
    assert all(len(vector) == EMBEDDING_DIMENSION for vector in [*doc_vectors, query_vector])
    for vector in [*doc_vectors, query_vector]:
        assert math.isclose(math.sqrt(sum(x * x for x in vector)), 1.0, abs_tol=1e-3)
    assert _cosine(query_vector, doc_vectors[0]) > _cosine(query_vector, doc_vectors[1])


async def test_query_and_document_embeddings_differ_because_only_queries_get_the_instruction() -> (
    None
):
    embedder = get_embedder("qwen3", Settings(_env_file=None))
    text = "怎么修改上传文件的大小限制"

    as_query = (await embedder.embed_queries([text]))[0]
    as_document = (await embedder.embed_documents([text]))[0]

    assert _cosine(as_query, as_document) < 0.9999
