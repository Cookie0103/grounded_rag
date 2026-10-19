"""用真实的库和配置组装检索器。"""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings
from app.core.text import search_text
from app.db.corpus import load_chunks, load_parents, nearest_chunks
from app.providers.base import Embedder, Reranker
from app.providers.factory import get_embedder, get_reranker
from app.retrieval.bm25 import Bm25Index, Tokenizer
from app.retrieval.retriever import ChunkInfo, HybridRetriever, ParentContext, VectorHit
from app.retrieval.tokenizer import tokenize


class DatabaseStorage:
    """检索器要的两个数据库操作：向量最近邻、按 ID 取父块。"""

    def __init__(self, engine: AsyncEngine, model: str) -> None:
        self._engine = engine
        self._model = model

    async def vector_search(
        self, embedding: Sequence[float], limit: int, editions: Sequence[str] | None
    ) -> list[VectorHit]:
        async with self._engine.connect() as connection:
            found = await nearest_chunks(
                connection, embedding, model=self._model, limit=limit, editions=editions
            )
        return [VectorHit(chunk.chunk_id, chunk.distance) for chunk in found]

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
    tokenizer: Tokenizer = tokenize,
) -> HybridRetriever:
    """从库里读出所有子块建 BM25 索引；嵌入和精排模型按配置创建（也可以显式传入）。"""
    async with engine.connect() as connection:
        rows = await load_chunks(connection)
    chunks = [
        ChunkInfo(r.id, r.document_id, r.parent_id, r.heading_path, r.text, r.edition) for r in rows
    ]
    bm25 = Bm25Index(
        [chunk.id for chunk in chunks],
        [search_text(chunk.heading_path, chunk.text) for chunk in chunks],
        tokenizer,
    )
    embedder = embedder or get_embedder(settings.embedding_model, settings)
    reranker = reranker if reranker is not None else get_reranker(settings.reranker_model, settings)
    return HybridRetriever(
        chunks=chunks,
        bm25=bm25,
        embedder=embedder,
        storage=DatabaseStorage(engine, embedder.name),
        reranker=reranker,
    )
