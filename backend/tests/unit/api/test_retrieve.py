from collections.abc import Sequence

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.api.retrieve import get_retriever
from app.retrieval.retriever import Candidate, ChunkInfo, ParentContext, RetrievalResult


class StubRetriever:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        editions: Sequence[str] | None = None,
        rerank: bool = True,
    ) -> RetrievalResult:
        self.calls.append({"query": query, "top_k": top_k, "editions": editions, "rerank": rerank})
        chunk = ChunkInfo("d#c0", "d", "d#p0", "标题 > 节", "正文", "self_host")
        candidate = Candidate(
            rank=1,
            chunk=chunk,
            vector_rank=2,
            vector_distance=0.2,
            bm25_rank=1,
            bm25_score=3.5,
            rrf_score=0.03,
            rerank_score=0.9,
        )
        parent = ParentContext("d#p0", "d", "标题 > 节", "父块正文")
        return RetrievalResult(query, [candidate], [parent], {"total": 1.5})


@pytest.fixture
def stub(app: FastAPI) -> StubRetriever:
    retriever = StubRetriever()
    app.dependency_overrides[get_retriever] = lambda: retriever
    return retriever


async def test_retrieve_returns_candidates_parents_and_timings(
    client: AsyncClient, stub: StubRetriever
) -> None:
    response = await client.post("/retrieve", json={"query": "怎么上传", "top_k": 3})

    assert response.status_code == 200
    body = response.json()
    assert body["trace_id"] == response.headers["X-Trace-Id"]
    assert body["query"] == "怎么上传"
    assert body["candidates"] == [
        {
            "rank": 1,
            "chunk_id": "d#c0",
            "document_id": "d",
            "parent_id": "d#p0",
            "heading_path": "标题 > 节",
            "text": "正文",
            "edition": "self_host",
            "vector_rank": 2,
            "vector_distance": 0.2,
            "bm25_rank": 1,
            "bm25_score": 3.5,
            "rrf_score": 0.03,
            "rerank_score": 0.9,
        }
    ]
    assert body["parents"] == [
        {"id": "d#p0", "document_id": "d", "heading_path": "标题 > 节", "text": "父块正文"}
    ]
    assert body["timings_ms"] == {"total": 1.5}
    assert stub.calls == [{"query": "怎么上传", "top_k": 3, "editions": None, "rerank": True}]


@pytest.mark.parametrize(
    ("edition", "editions"),
    [("self_host", ("self_host", "common")), ("cloud", ("cloud", "common"))],
)
async def test_edition_includes_common_documents(
    client: AsyncClient, stub: StubRetriever, edition: str, editions: tuple[str, ...]
) -> None:
    await client.post("/retrieve", json={"query": "x", "edition": edition, "rerank": False})

    assert stub.calls[0]["editions"] == editions
    assert stub.calls[0]["rerank"] is False


async def test_query_is_stripped_before_use(client: AsyncClient, stub: StubRetriever) -> None:
    await client.post("/retrieve", json={"query": "  怎么上传  "})

    assert stub.calls[0]["query"] == "怎么上传"


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"query": ""},
        {"query": "   "},
        {"query": "字" * 501},
        {"query": "x", "top_k": 0},
        {"query": "x", "top_k": 21},
        {"query": "x", "edition": "enterprise"},
    ],
)
async def test_invalid_requests_get_the_unified_422(
    client: AsyncClient, stub: StubRetriever, body: dict[str, object]
) -> None:
    response = await client.post("/retrieve", json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"
    assert stub.calls == []
