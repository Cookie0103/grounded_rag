from collections.abc import Sequence

import pytest

from app.core.cache import TtlCache
from app.core.errors import DependencyUnavailableError
from app.core.resilience import OPEN, CircuitBreaker
from app.providers.cached import CachedEmbedder
from app.providers.fakes import FakeEmbedder
from app.retrieval.resilient import ResilientRetriever
from app.retrieval.retriever import HYBRID, RetrievalResult


class FlakyRetriever:
    def __init__(
        self, *, rerank_fails: bool = False, always_fails: bool = False, db_down: bool = False
    ) -> None:
        self.rerank_fails = rerank_fails
        self.always_fails = always_fails
        self.db_down = db_down
        self.calls: list[bool] = []

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        editions: Sequence[str] | None = None,
        rerank: bool = True,
        mode: str = HYBRID,
    ) -> RetrievalResult:
        self.calls.append(rerank)
        if self.db_down:
            raise DependencyUnavailableError("db")
        if self.always_fails or (rerank and self.rerank_fails):
            raise RuntimeError("CUDA out of memory")
        return RetrievalResult(query, [], [])


def _retriever(inner: FlakyRetriever, threshold: int = 3) -> ResilientRetriever:
    return ResilientRetriever(inner, cache=TtlCache(10, 60), breaker=CircuitBreaker(threshold, 30))


async def test_results_are_cached_per_query_and_options() -> None:
    inner = FlakyRetriever()
    retriever = _retriever(inner)

    first = await retriever.retrieve("问题")
    second = await retriever.retrieve("问题")
    await retriever.retrieve("问题", editions=["cloud", "common"])
    await retriever.retrieve("问题", rerank=False)

    assert inner.calls == [True, True, False]
    assert not first.cached
    assert second.cached


async def test_rerank_failure_degrades_to_plain_retrieval_and_is_not_cached() -> None:
    inner = FlakyRetriever(rerank_fails=True)
    retriever = _retriever(inner)

    first = await retriever.retrieve("问题")
    inner.rerank_fails = False
    second = await retriever.retrieve("问题")

    assert first.degraded
    assert not second.degraded  # 降级的结果没进缓存，精排恢复后马上用上
    assert inner.calls == [True, False, True]


async def test_breaker_opens_after_repeated_rerank_failures_and_skips_rerank() -> None:
    inner = FlakyRetriever(rerank_fails=True)
    breaker = CircuitBreaker(2, 30)
    retriever = ResilientRetriever(inner, cache=TtlCache(10, 60), breaker=breaker)

    for number in range(4):
        result = await retriever.retrieve(f"问题{number}")
        assert result.degraded

    assert breaker.state == OPEN
    assert inner.calls == [True, False, True, False, False, False]  # 熔断后不再碰精排


async def test_errors_that_also_break_plain_retrieval_are_raised() -> None:
    retriever = _retriever(FlakyRetriever(always_fails=True))

    with pytest.raises(RuntimeError):
        await retriever.retrieve("问题")


async def test_plain_retrieval_errors_pass_through_without_touching_the_breaker() -> None:
    breaker = CircuitBreaker(1, 30)
    retriever = ResilientRetriever(
        FlakyRetriever(db_down=True), cache=TtlCache(10, 60), breaker=breaker
    )

    with pytest.raises(DependencyUnavailableError):
        await retriever.retrieve("问题", rerank=False)

    assert breaker.allow()


async def test_embedder_cache_computes_each_query_once() -> None:
    inner = FakeEmbedder()
    calls: list[list[str]] = []
    original = inner.embed_queries

    async def spy(texts: list[str]) -> list[list[float]]:
        calls.append(list(texts))
        return await original(texts)

    inner.embed_queries = spy  # type: ignore[method-assign]
    embedder = CachedEmbedder(inner, TtlCache(10, 60))

    first = await embedder.embed_queries(["甲", "乙", "甲"])
    second = await embedder.embed_queries(["乙", "丙"])

    assert calls == [["甲", "乙"], ["丙"]]
    assert first[0] == first[2]
    assert second[0] == first[1]
    assert (embedder.name, embedder.dimension) == (inner.name, inner.dimension)
    assert await embedder.embed_documents(["文档"]) == await inner.embed_documents(["文档"])
