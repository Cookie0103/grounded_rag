"""混合检索：向量 + BM25 并行 → RRF 融合 → 精排 → 取前 K → 带出父块。"""

import asyncio
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from typing import Protocol

from app.core.config import FINAL_TOP_K, FUSION_TOP_K, RETRIEVE_TOP_K
from app.core.text import search_text
from app.providers.base import Embedder, Reranker
from app.retrieval.bm25 import Bm25Index
from app.retrieval.fusion import rrf


@dataclass(frozen=True)
class ChunkInfo:
    id: str
    document_id: str
    parent_id: str
    heading_path: str
    text: str
    edition: str


@dataclass(frozen=True)
class ParentContext:
    id: str
    document_id: str
    heading_path: str
    text: str


@dataclass(frozen=True)
class VectorHit:
    chunk_id: str
    distance: float


@dataclass(frozen=True)
class Candidate:
    rank: int
    chunk: ChunkInfo
    vector_rank: int | None = None
    vector_distance: float | None = None
    bm25_rank: int | None = None
    bm25_score: float | None = None
    rrf_score: float = 0.0
    rerank_score: float | None = None


@dataclass(frozen=True)
class RetrievalResult:
    query: str
    candidates: list[Candidate]
    parents: list[ParentContext]
    timings_ms: dict[str, float] = field(default_factory=dict)
    degraded: bool = False  # 精排不可用，跳过了精排
    recall_candidates: list[Candidate] = field(default_factory=list)
    reranked_candidates: list[Candidate] = field(default_factory=list)
    cached: bool = False


HYBRID, VECTOR, BM25 = "hybrid", "vector", "bm25"


class Retriever(Protocol):
    """API 层依赖的接口；单元测试里用假的。"""

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = FINAL_TOP_K,
        editions: Sequence[str] | None = None,
        rerank: bool = True,
        mode: str = HYBRID,
    ) -> RetrievalResult: ...


class Storage(Protocol):
    """检索器需要的两个数据库操作；生产环境由 factory 用真实的库实现。"""

    async def vector_search(
        self, embedding: Sequence[float], limit: int, editions: Sequence[str] | None
    ) -> list[VectorHit]: ...

    async def load_parents(self, parent_ids: Sequence[str]) -> dict[str, ParentContext]: ...


class HybridRetriever:
    def __init__(
        self,
        *,
        chunks: Sequence[ChunkInfo],
        bm25: Bm25Index,
        embedder: Embedder,
        storage: Storage,
        reranker: Reranker | None = None,
    ) -> None:
        self._chunks = {chunk.id: chunk for chunk in chunks}
        self._bm25 = bm25
        self._embedder = embedder
        self._storage = storage
        self._reranker = reranker

    def with_reranker(self, reranker: Reranker | None) -> "HybridRetriever":
        """同样的索引和存储，换一个精排模型（对比实验用）。"""
        return HybridRetriever(
            chunks=list(self._chunks.values()),
            bm25=self._bm25,
            embedder=self._embedder,
            storage=self._storage,
            reranker=reranker,
        )

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = FINAL_TOP_K,
        editions: Sequence[str] | None = None,
        rerank: bool = True,
        mode: str = HYBRID,
    ) -> RetrievalResult:
        """mode：hybrid（向量 + BM25）、vector（只用向量）、bm25（只用 BM25）；后两个做消融实验。"""
        timings: dict[str, float] = {}
        started = time.perf_counter()
        vector_hits, bm25_hits = await self._first_stage(query, editions, mode, timings)

        with _timed(timings, "fuse"):
            fused = rrf([[hit.chunk_id for hit in vector_hits], [cid for cid, _ in bm25_hits]])
        recall = self._candidates(fused, vector_hits, bm25_hits)
        candidates = recall[:FUSION_TOP_K]
        reranked: list[Candidate] = []
        if rerank and self._reranker is not None and candidates:
            candidates = await self._rerank(self._reranker, query, candidates, timings)
            reranked = candidates
        top = [replace(c, rank=rank) for rank, c in enumerate(candidates[:top_k], start=1)]

        parents = await self._parents(top, timings)
        timings["total"] = _ms(time.perf_counter() - started)
        return RetrievalResult(
            query, top, parents, timings, recall_candidates=recall, reranked_candidates=reranked
        )

    async def _first_stage(
        self,
        query: str,
        editions: Sequence[str] | None,
        mode: str,
        timings: dict[str, float],
    ) -> tuple[list[VectorHit], list[tuple[str, float]]]:
        use_vector, use_bm25 = mode in (HYBRID, VECTOR), mode in (HYBRID, BM25)
        vector: list[float] = []
        if use_vector:
            with _timed(timings, "embed"):
                vector = (await self._embedder.embed_queries([query]))[0]
        allowed = (
            None
            if editions is None
            else frozenset(c.id for c in self._chunks.values() if c.edition in editions)
        )

        async def run_vector() -> list[VectorHit]:
            if not use_vector:
                return []
            with _timed(timings, "vector"):
                return await self._storage.vector_search(vector, RETRIEVE_TOP_K, editions)

        async def run_bm25() -> list[tuple[str, float]]:
            if not use_bm25:
                return []
            with _timed(timings, "bm25"):
                return await asyncio.to_thread(self._bm25.search, query, RETRIEVE_TOP_K, allowed)

        return await asyncio.gather(run_vector(), run_bm25())

    def _candidates(
        self,
        fused: list[tuple[str, float]],
        vector_hits: list[VectorHit],
        bm25_hits: list[tuple[str, float]],
    ) -> list[Candidate]:
        vector_info = {h.chunk_id: (rank, h.distance) for rank, h in enumerate(vector_hits, 1)}
        bm25_info = {cid: (rank, score) for rank, (cid, score) in enumerate(bm25_hits, 1)}
        candidates: list[Candidate] = []
        for rank, (chunk_id, score) in enumerate(fused, start=1):
            vector_rank, distance = vector_info.get(chunk_id, (None, None))
            bm25_rank, bm25_score = bm25_info.get(chunk_id, (None, None))
            candidates.append(
                Candidate(
                    rank=rank,
                    chunk=self._chunks[chunk_id],
                    vector_rank=vector_rank,
                    vector_distance=distance,
                    bm25_rank=bm25_rank,
                    bm25_score=bm25_score,
                    rrf_score=score,
                )
            )
        return candidates

    @staticmethod
    async def _rerank(
        reranker: Reranker, query: str, candidates: list[Candidate], timings: dict[str, float]
    ) -> list[Candidate]:
        with _timed(timings, "rerank"):
            scores = await reranker.rerank(
                query, [search_text(c.chunk.heading_path, c.chunk.text) for c in candidates]
            )
        scored = [replace(c, rerank_score=s) for c, s in zip(candidates, scores, strict=True)]
        return sorted(scored, key=lambda c: -(c.rerank_score or 0.0))

    async def _parents(
        self, candidates: list[Candidate], timings: dict[str, float]
    ) -> list[ParentContext]:
        parent_ids = list(dict.fromkeys(c.chunk.parent_id for c in candidates))
        with _timed(timings, "parents"):
            loaded = await self._storage.load_parents(parent_ids)
        return [loaded[pid] for pid in parent_ids if pid in loaded]


@contextmanager
def _timed(timings: dict[str, float], name: str) -> Iterator[None]:
    started = time.perf_counter()
    try:
        yield
    finally:
        timings[name] = _ms(time.perf_counter() - started)


def _ms(seconds: float) -> float:
    return round(seconds * 1000, 2)
