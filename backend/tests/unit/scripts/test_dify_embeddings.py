import base64
import struct

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.providers.local_embedder import SentenceTransformerEmbedder
from scripts import dify_embeddings


class StubEmbedder(SentenceTransformerEmbedder):
    def __init__(self) -> None:
        self.name = "qwen3-embedding-0.6b"
        self.dimension = 2

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]

    async def document_tokens(self, texts: list[str]) -> int:
        return 3 * len(texts)


@pytest.fixture
def embedding_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(dify_embeddings, "get_embedder", lambda *_: StubEmbedder())
    config = Settings(_env_file=None, gateway_api_key="synthetic-unit-key")
    return TestClient(dify_embeddings.create_app(config))


def test_embedding_route_requires_gateway_bearer(embedding_client: TestClient) -> None:
    response = embedding_client.post(
        "/v1/embeddings", json={"model": "qwen3-embedding-0.6b", "input": "合成"}
    )
    assert response.status_code == 401


def test_openai_compatible_base64_and_usage_are_counted(embedding_client: TestClient) -> None:
    response = embedding_client.post(
        "/v1/embeddings",
        headers={"Authorization": "Bearer synthetic-unit-key"},
        json={
            "model": "qwen3-embedding-0.6b",
            "input": ["合成例", "手続"],
            "encoding_format": "base64",
            "dimensions": 2,
        },
    )
    result = response.json()
    assert response.status_code == 200
    assert result["usage"] == {"prompt_tokens": 6, "total_tokens": 6}
    assert [item["index"] for item in result["data"]] == [0, 1]
    assert struct.unpack("<2f", base64.b64decode(result["data"][0]["embedding"])) == (1.0, 0.0)
