from collections.abc import Sequence

from app.core.text import search_text
from app.providers.fakes import FakeEmbedder, FakeReranker
from app.retrieval.bm25 import Bm25Index
from app.retrieval.retriever import (
    ChunkInfo,
    HybridRetriever,
    ParentContext,
    VectorHit,
)

CHUNKS = [
    ChunkInfo(
        "d1#c0",
        "d1",
        "d1#p0",
        "上传",
        "单次最多上传 5 个文件，上限由 UPLOAD_FILE_BATCH_LIMIT 控制",
        "self_host",
    ),
    ChunkInfo(
        "d1#c1",
        "d1",
        "d1#p1",
        "大小",
        "单个文件最大 15 MB，由 UPLOAD_FILE_SIZE_LIMIT 控制",
        "self_host",
    ),
    ChunkInfo("d2#c0", "d2", "d2#p0", "监控", "在监控页面查看调用次数和响应时间", "cloud"),
    ChunkInfo("d3#c0", "d3", "d3#p0", "通用", "所有版本都可以使用工作流", "common"),
]


class InMemoryStorage:
    """用假嵌入在内存里做「向量检索」；并记录收到的版本过滤。"""

    def __init__(self, embedder: FakeEmbedder) -> None:
        self._embedder = embedder
        self.editions_seen: list[Sequence[str] | None] = []
        self.parent_requests: list[list[str]] = []

    async def vector_search(
        self, embedding: Sequence[float], limit: int, editions: Sequence[str] | None
    ) -> list[VectorHit]:
        self.editions_seen.append(editions)
        vectors = await self._embedder.embed_documents(
            [search_text(c.heading_path, c.text) for c in CHUNKS]
        )
        scored = [
            VectorHit(chunk.id, 1 - sum(a * b for a, b in zip(embedding, vector, strict=True)))
            for chunk, vector in zip(CHUNKS, vectors, strict=True)
            if editions is None or chunk.edition in editions
        ]
        return sorted(scored, key=lambda hit: hit.distance)[:limit]

    async def load_parents(self, parent_ids: Sequence[str]) -> dict[str, ParentContext]:
        self.parent_requests.append(list(parent_ids))
        return {
            pid: ParentContext(pid, pid.split("#")[0], "标题", f"父块 {pid}") for pid in parent_ids
        }


def _retriever(*, reranker: FakeReranker | None = None) -> tuple[HybridRetriever, InMemoryStorage]:
    embedder = FakeEmbedder()
    storage = InMemoryStorage(embedder)
    bm25 = Bm25Index([c.id for c in CHUNKS], [search_text(c.heading_path, c.text) for c in CHUNKS])
    retriever = HybridRetriever(
        chunks=CHUNKS, bm25=bm25, embedder=embedder, storage=storage, reranker=reranker
    )
    return retriever, storage


async def test_exact_variable_name_ranks_its_chunk_first_even_without_reranking() -> None:
    retriever, _ = _retriever()

    result = await retriever.retrieve("UPLOAD_FILE_SIZE_LIMIT 是什么")

    first = result.candidates[0]
    assert first.chunk.id == "d1#c1"
    assert first.rank == 1
    assert first.bm25_rank == 1
    assert first.rerank_score is None


async def test_candidates_carry_both_ranks_and_the_fused_score() -> None:
    retriever, _ = _retriever()

    result = await retriever.retrieve("上传文件")

    assert [c for c in result.candidates if c.vector_rank and c.bm25_rank]
    scores = [c.rrf_score for c in result.candidates]
    assert all(score > 0 for score in scores)
    assert scores == sorted(scores, reverse=True)
    assert [c.rank for c in result.candidates] == list(range(1, len(result.candidates) + 1))


async def test_reranker_reorders_the_candidates_and_scores_are_reported() -> None:
    retriever, _ = _retriever(reranker=FakeReranker())

    result = await retriever.retrieve("监控页面查看调用次数")

    assert result.candidates[0].chunk.id == "d2#c0"
    scores = [c.rerank_score for c in result.candidates if c.rerank_score is not None]
    assert len(scores) == len(result.candidates)
    assert scores == sorted(scores, reverse=True)
    assert "rerank" in result.timings_ms


async def test_rerank_false_skips_the_reranker() -> None:
    retriever, _ = _retriever(reranker=FakeReranker())

    result = await retriever.retrieve("监控页面查看调用次数", rerank=False)

    assert all(c.rerank_score is None for c in result.candidates)
    assert "rerank" not in result.timings_ms


async def test_top_k_limits_the_candidates() -> None:
    retriever, _ = _retriever()

    assert len((await retriever.retrieve("上传文件", top_k=2)).candidates) == 2


async def test_edition_filter_applies_to_both_retrieval_paths() -> None:
    retriever, storage = _retriever()

    result = await retriever.retrieve("监控页面查看调用次数", editions=("self_host", "common"))

    assert {c.chunk.edition for c in result.candidates} <= {"self_host", "common"}
    assert storage.editions_seen == [("self_host", "common")]
    assert "d2#c0" not in {c.chunk.id for c in result.candidates}


async def test_parents_are_deduplicated_in_candidate_order() -> None:
    retriever, storage = _retriever()

    result = await retriever.retrieve("上传文件", top_k=3)

    parent_ids = [p.id for p in result.parents]
    assert parent_ids == list(dict.fromkeys(c.chunk.parent_id for c in result.candidates))
    assert storage.parent_requests == [parent_ids]


async def test_timings_cover_every_stage() -> None:
    retriever, _ = _retriever(reranker=FakeReranker())

    result = await retriever.retrieve("上传文件")

    expected = {"embed", "vector", "bm25", "fuse", "rerank", "parents", "total"}
    assert set(result.timings_ms) >= expected


async def test_query_with_no_lexical_match_still_returns_vector_neighbours() -> None:
    retriever, _ = _retriever()

    result = await retriever.retrieve("完全无关的内容")

    assert result.candidates
    assert all(c.bm25_rank is None for c in result.candidates)
