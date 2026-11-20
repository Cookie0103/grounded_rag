"""Elasticsearch 规程索引的快照构建与发布。"""

import hashlib
from uuid import uuid4

from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch.helpers import async_bulk

from app.core.errors import CorpusError
from app.core.policy import PolicyChunk

_KEYWORD_FIELDS = (
    "document_id",
    "source",
    "product_line",
    "policy_type",
    "policy_id",
    "status",
    "corpus_tier",
    "based_on",
    "source_url",
)
_INDEX_TIMEOUT = 30


class PolicyIndex:
    """写好并核对完整快照后，一次切换查询别名。"""

    def __init__(self, url: str, alias: str) -> None:
        self._client = AsyncElasticsearch(url, request_timeout=_INDEX_TIMEOUT)
        self.alias = alias

    async def close(self) -> None:
        """关闭 Elasticsearch 客户端连接。"""
        await self._client.close()

    async def sync(self, chunks: list[PolicyChunk]) -> int:
        """把 PG 当前快照同步到 ES，未变化时直接使用已有索引。"""
        checksum = hashlib.sha256("\n".join(item.model_dump_json() for item in chunks).encode())
        prefix = f"{self.alias}-{checksum.hexdigest()[:16]}"
        previous = await self._aliased_names()
        if len(previous) == 1 and previous[0].startswith(prefix):
            current = await self._count(previous[0])
            if current == len(chunks):
                return current
        name = f"{prefix}-{uuid4().hex[:8]}"
        await self._build_and_publish(name, previous, chunks)
        return len(chunks)

    async def _aliased_names(self) -> list[str]:
        try:
            response = await self._client.indices.get_alias(name=self.alias)
        except NotFoundError:
            return []
        return sorted(response.body)

    async def _count(self, target: str) -> int:
        response = await self._client.count(index=target)
        return int(response["count"])

    async def _build_and_publish(
        self, name: str, previous: list[str], chunks: list[PolicyChunk]
    ) -> None:
        await self._client.indices.create(index=name, body={"mappings": _mapping()})
        published = False
        try:
            _, failed = await async_bulk(
                self._client,
                (_action(name, chunk) for chunk in chunks),
                stats_only=True,
                raise_on_error=False,
            )
            if failed:
                raise CorpusError(f"Elasticsearch 批量写入失败块数 {failed}")
            await self._client.indices.refresh(index=name)
            if await self._count(name) != len(chunks):
                raise CorpusError("PostgreSQL 与 Elasticsearch 的子块数不一致")
            actions = [{"remove": {"index": old, "alias": self.alias}} for old in previous]
            actions.append({"add": {"index": name, "alias": self.alias}})
            await self._client.indices.update_aliases(body={"actions": actions})
            published = True
        finally:
            if not published and name not in await self._aliased_names():
                await self._client.indices.delete(index=name, ignore_unavailable=True)
        for stale in previous:
            if stale.startswith(f"{self.alias}-"):
                await self._client.indices.delete(index=stale, ignore_unavailable=True)


def _mapping() -> dict[str, object]:
    fields = {field: {"type": "keyword"} for field in _KEYWORD_FIELDS}
    for field in ("text", "heading_path"):
        fields[field] = {"type": "text", "analyzer": "kuromoji"}
    for field in ("effective_from", "effective_to"):
        fields[field] = {"type": "date"}
    fields["synthetic"] = {"type": "boolean"}
    return {"dynamic": "strict", "properties": fields}


def _action(index: str, chunk: PolicyChunk) -> dict[str, object]:
    return {
        "_index": index,
        "_id": chunk.id,
        "_source": {
            "document_id": chunk.document_id,
            "heading_path": chunk.heading_path,
            "text": chunk.text,
            **chunk.policy.model_dump(mode="json"),
        },
    }
