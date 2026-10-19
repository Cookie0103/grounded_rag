"""带缓存的嵌入器：同一个查询不重复算（文档嵌入不缓存，入库时一次性算）。"""

from app.core.cache import TtlCache
from app.providers.base import Embedder


class CachedEmbedder:
    def __init__(self, inner: Embedder, cache: TtlCache[str, list[float]]) -> None:
        self.name = inner.name
        self.dimension = inner.dimension
        self._inner = inner
        self._cache = cache

    async def embed_queries(self, texts: list[str]) -> list[list[float]]:
        vectors: dict[str, list[float]] = {}
        for text in dict.fromkeys(texts):
            cached = self._cache.get(text)
            if cached is not None:
                vectors[text] = cached
        missing = [text for text in dict.fromkeys(texts) if text not in vectors]
        if missing:
            for text, vector in zip(missing, await self._inner.embed_queries(missing), strict=True):
                vectors[text] = vector
                self._cache.put(text, vector)
        return [vectors[text] for text in texts]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._inner.embed_documents(texts)
