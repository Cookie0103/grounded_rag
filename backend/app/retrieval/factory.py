"""用真实的库和配置组装检索器。"""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings
from app.db.corpus import load_parents, nearest_chunks
from app.db.policy import load_policy_chunks
from app.db.policy_filter import MetaFilter
from app.providers.base import Embedder, Reranker
from app.providers.factory import get_embedder, get_reranker
from app.retrieval.keyword import ElasticsearchKeywords
from app.retrieval.retriever import (
    ChunkInfo,
    HybridRetriever,
    KeywordSearch,
    ParentContext,
    VectorHit,
)


class DatabaseStorage:
    """检索器要的两个数据库操作：向量最近邻、按 ID 取父块。"""

    def __init__(self, engine: AsyncEngine, model: str) -> None:
        self._engine = engine
        self._model = model

    async def vector_search(
        self, embedding: Sequence[float], limit: int, filters: MetaFilter
    ) -> list[VectorHit]:
        async with self._engine.connect() as connection:
            found = await nearest_chunks(
                connection, embedding, model=self._model, limit=limit, filters=filters
            )
        return [VectorHit(chunk.chunk_id, chunk.distance) for chunk in found]

    async def load_children(
        self, chunk_ids: Sequence[str], filters: MetaFilter
    ) -> dict[str, ChunkInfo]:
        async with self._engine.connect() as connection:
            rows = await load_policy_chunks(connection, ids=chunk_ids, filters=filters)
        return {
            row.id: ChunkInfo(
                row.id,
                row.document_id,
                row.parent_id,
                row.heading_path,
                row.text,
                policy=row.policy,
            )
            for row in rows
        }

    async def load_parents(self, parent_ids: Sequence[str]) -> dict[str, ParentContext]:
        async with self._engine.connect() as connection:
            rows = await load_parents(connection, parent_ids)
        return {
            row.id: ParentContext(row.id, row.document_id, row.heading_path, row.text)
            for row in rows.values()
        }


async def build_retriever(
    engine: AsyncEngine,
    settings: Settings,
    *,
    embedder: Embedder | None = None,
    reranker: Reranker | None = None,
    keyword: KeywordSearch | None = None,
) -> HybridRetriever:
    """组装实时查询两种存储的规程检索器。"""
    embedder = embedder or get_embedder(settings.embedding_model, settings)
    reranker = reranker if reranker is not None else get_reranker(settings.reranker_model, settings)
    return HybridRetriever(
        keyword=keyword or ElasticsearchKeywords(settings.elasticsearch_url),
        embedder=embedder,
        storage=DatabaseStorage(engine, embedder.name),
        reranker=reranker,
    )
