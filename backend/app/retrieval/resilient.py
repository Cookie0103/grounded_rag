"""给检索器加缓存、精排熔断和降级。

精排挂了（异常，或熔断器打开）就跳过精排，结果标记 `degraded=True`；
降级的结果不进缓存，免得精排恢复后还在返回没精排的结果。
"""

import logging
from collections.abc import Sequence
from dataclasses import replace

from app.core.cache import TtlCache
from app.core.config import FINAL_TOP_K
from app.core.errors import AppError
from app.core.resilience import CircuitBreaker
from app.retrieval.retriever import HYBRID, RetrievalResult, Retriever

logger = logging.getLogger(__name__)
type CacheKey = tuple[str, int, tuple[str, ...] | None, bool, str]


class ResilientRetriever:
    def __init__(
        self,
        inner: Retriever,
        *,
        cache: TtlCache[CacheKey, RetrievalResult],
        breaker: CircuitBreaker,
    ) -> None:
        self._inner = inner
        self._cache = cache
        self._breaker = breaker

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = FINAL_TOP_K,
        editions: Sequence[str] | None = None,
        rerank: bool = True,
        mode: str = HYBRID,
    ) -> RetrievalResult:
        key = (query, top_k, tuple(editions) if editions else None, rerank, mode)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        result = await self._retrieve(query, top_k, editions, rerank, mode)
        if not result.degraded:
            self._cache.put(key, result)
        return result

    async def _retrieve(
        self,
        query: str,
        top_k: int,
        editions: Sequence[str] | None,
        rerank: bool,
        mode: str,
    ) -> RetrievalResult:
        if not rerank:
            return await self._inner.retrieve(
                query, top_k=top_k, editions=editions, rerank=False, mode=mode
            )
        if not self._breaker.allow():
            return await self._without_rerank(query, top_k, editions, mode)
        try:
            result = await self._inner.retrieve(
                query, top_k=top_k, editions=editions, rerank=True, mode=mode
            )
        except (AppError, RuntimeError, OSError) as error:
            logger.warning("精排检索失败，降级为不精排：%r", error)
            self._breaker.record_failure()
            return await self._without_rerank(query, top_k, editions, mode)
        self._breaker.record_success()
        return result

    async def _without_rerank(
        self, query: str, top_k: int, editions: Sequence[str] | None, mode: str
    ) -> RetrievalResult:
        result = await self._inner.retrieve(
            query, top_k=top_k, editions=editions, rerank=False, mode=mode
        )
        return replace(result, degraded=True)
