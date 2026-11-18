from collections.abc import Sequence
from dataclasses import replace
from datetime import date

from app.core.errors import DependencyUnavailableError
from app.core.policy import PolicyMetadata
from app.core.text import search_text
from app.db.policy_filter import MetaFilter
from app.providers.fakes import FakeEmbedder, FakeReranker
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
        self.filters_seen: list[MetaFilter] = []
        self.parent_requests: list[list[str]] = []

    async def vector_search(
        self, embedding: Sequence[float], limit: int, filters: MetaFilter
    ) -> list[VectorHit]:
        self.filters_seen.append(filters)
        vectors = await self._embedder.embed_documents(
            [search_text(c.heading_path, c.text) for c in CHUNKS]
        )
        scored = [
            VectorHit(chunk.id, 1 - sum(a * b for a, b in zip(embedding, vector, strict=True)))
            for chunk, vector in zip(CHUNKS, vectors, strict=True)
            if _allowed(chunk, filters)
        ]
        return sorted(scored, key=lambda hit: hit.distance)[:limit]

    async def load_children(
        self, chunk_ids: Sequence[str], filters: MetaFilter
    ) -> dict[str, ChunkInfo]:
        return {c.id: c for c in CHUNKS if c.id in chunk_ids and _allowed(c, filters)}

    async def load_parents(self, parent_ids: Sequence[str]) -> dict[str, ParentContext]:
        self.parent_requests.append(list(parent_ids))
        return {
            pid: ParentContext(pid, pid.split("#")[0], "标题", f"父块 {pid}") for pid in parent_ids
        }


def _allowed(chunk: ChunkInfo, filters: MetaFilter) -> bool:
    return filters.corpus_tier == "L" or chunk.edition != "cloud"


class StubKeywords:
    def __init__(self, *, unavailable: bool = False) -> None:
        self._unavailable = unavailable

    async def search(self, query: str, limit: int, filters: MetaFilter) -> list[tuple[str, float]]:
        if self._unavailable:
            raise DependencyUnavailableError("ES 不可用")
        if query == "完全无关的内容":
            return []
        matches = [
            (chunk.id, float(len(set(query) & set(chunk.text))))
            for chunk in CHUNKS
            if _allowed(chunk, filters)
        ]
        return sorted(matches, key=lambda value: -value[1])[:limit]


def _retriever(
    *, reranker: FakeReranker | None = None, unavailable: bool = False
) -> tuple[HybridRetriever, InMemoryStorage]:
    embedder = FakeEmbedder()
    storage = InMemoryStorage(embedder)
    retriever = HybridRetriever(
        keyword=StubKeywords(unavailable=unavailable),
        embedder=embedder,
        storage=storage,
        reranker=reranker,
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

    result = await retriever.retrieve("监控页面查看调用次数", rerank=True)

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


async def test_recall_and_reranking_keep_candidates_removed_by_top_k() -> None:
    retriever, _ = _retriever(reranker=FakeReranker())

    result = await retriever.retrieve("上传文件", top_k=1, rerank=True)

    assert len(result.recall_candidates) > len(result.candidates)
    assert {c.chunk.id for c in result.recall_candidates} == {
        c.chunk.id for c in result.reranked_candidates
    }
    assert all(c.rerank_score is None for c in result.recall_candidates)
    assert all(c.rerank_score is not None for c in result.reranked_candidates)
    assert result.candidates[0].chunk == result.reranked_candidates[0].chunk


async def test_metadata_filter_applies_to_both_retrieval_paths() -> None:
    retriever, storage = _retriever()

    filters = MetaFilter(corpus_tier="S")
    result = await retriever.retrieve("监控页面查看调用次数", filters=filters)

    assert {c.chunk.edition for c in result.candidates} <= {"self_host", "common"}
    assert storage.filters_seen == [filters]
    assert "d2#c0" not in {c.chunk.id for c in result.candidates}


async def test_parents_are_deduplicated_in_candidate_order() -> None:
    retriever, storage = _retriever()

    result = await retriever.retrieve("上传文件", top_k=3)

    parent_ids = [p.id for p in result.parents]
    assert parent_ids == list(dict.fromkeys(c.chunk.parent_id for c in result.candidates))
    assert storage.parent_requests == [parent_ids]


async def test_timings_cover_every_stage() -> None:
    retriever, _ = _retriever(reranker=FakeReranker())

    result = await retriever.retrieve("上传文件", rerank=True)

    expected = {"embed", "vector", "keyword", "fuse", "hydrate", "rerank", "parents", "total"}
    assert set(result.timings_ms) >= expected


async def test_query_with_no_lexical_match_still_returns_vector_neighbours() -> None:
    retriever, _ = _retriever()

    result = await retriever.retrieve("完全无关的内容")

    assert result.candidates
    assert all(c.bm25_rank is None for c in result.candidates)


async def test_elasticsearch_failure_uses_filtered_vector_retrieval() -> None:
    retriever, storage = _retriever(reranker=FakeReranker(), unavailable=True)
    filters = MetaFilter(corpus_tier="S")

    result = await retriever.retrieve("返済の手続", filters=filters, rerank=True)

    assert result.degraded
    assert result.candidates
    assert all(c.bm25_rank is None and c.vector_rank for c in result.candidates)
    assert all(c.rerank_score is None for c in result.candidates)
    assert storage.filters_seen == [filters]


async def test_explicit_policy_identifier_survives_fusion_when_vector_has_no_match() -> None:
    metadata = PolicyMetadata(
        source="internal",
        synthetic=True,
        product_line="home_loan",
        policy_type="procedure",
        policy_id="HL-TEST",
        effective_from=date(2026, 11, 1),
        status="online",
        corpus_tier="S",
        based_on=("public/test-fixture",),
    )
    match = replace(CHUNKS[1], policy=metadata)
    other = CHUNKS[0]

    class VectorStorage(InMemoryStorage):
        async def vector_search(
            self, embedding: Sequence[float], limit: int, filters: MetaFilter
        ) -> list[VectorHit]:
            return [VectorHit(other.id, 0.1)]

        async def load_children(
            self, chunk_ids: Sequence[str], filters: MetaFilter
        ) -> dict[str, ChunkInfo]:
            return {item.id: item for item in (match, other) if item.id in chunk_ids}

    class ExactKeywords:
        async def search(
            self, query: str, limit: int, filters: MetaFilter
        ) -> list[tuple[str, float]]:
            return [(match.id, 100.0), (other.id, 1.0)]

    embedder = FakeEmbedder()
    retriever = HybridRetriever(
        keyword=ExactKeywords(), embedder=embedder, storage=VectorStorage(embedder)
    )
    result = await retriever.retrieve("ＨＬ－ＴＥＳＴの受付", top_k=1)

    assert [candidate.chunk.id for candidate in result.candidates] == [match.id]
