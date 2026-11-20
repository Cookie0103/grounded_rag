"""使用 kuromoji 和精确规程编号执行关键词检索。"""

import re
import unicodedata

from elasticsearch import ApiError, AsyncElasticsearch, TransportError

from app.core.config import POLICY_INDEX_ALIAS
from app.core.errors import DependencyUnavailableError
from app.db.policy_filter import MetaFilter

_POLICY_NUMBER = re.compile(r"(?<![A-Z0-9-])[A-Z][A-Z0-9]+(?:-[A-Z0-9]+)+(?![A-Z0-9-])")
_TIMEOUT_SECONDS = 2.0
_EXACT_POLICY_BOOST = 12.0


def policy_numbers(query: str) -> tuple[str, ...]:
    """识别日文问句中的显式规程编号，包含全角输入。"""
    normalized = unicodedata.normalize("NFKC", query).upper()
    return tuple(dict.fromkeys(_POLICY_NUMBER.findall(normalized)))


class ElasticsearchKeywords:
    """在已发布的规程索引中返回子块 ID 与关键词分数。"""

    def __init__(self, url: str, index: str = POLICY_INDEX_ALIAS) -> None:
        self._url = url
        self._index = index

    async def search(self, query: str, limit: int, filters: MetaFilter) -> list[tuple[str, float]]:
        """只返回满足元数据条件的关键词候选。"""
        should: list[dict[str, object]] = [
            {"multi_match": {"query": query, "fields": ["text", "heading_path^2"]}}
        ]
        should.extend(
            {"term": {"policy_id": {"value": name, "boost": _EXACT_POLICY_BOOST}}}
            for name in policy_numbers(query)
        )
        try:
            async with AsyncElasticsearch(
                self._url, request_timeout=_TIMEOUT_SECONDS, max_retries=0
            ) as client:
                response = await client.search(
                    index=self._index,
                    size=limit,
                    source=False,
                    track_total_hits=False,
                    query={
                        "bool": {
                            "filter": filters.elasticsearch_filters(),
                            "should": should,
                            "minimum_should_match": 1,
                        }
                    },
                )
        except (ApiError, TransportError) as error:
            raise DependencyUnavailableError("Elasticsearch 关键词检索不可用") from error
        return [
            (str(hit["_id"]), float(hit["_score"]))
            for hit in response["hits"]["hits"]
            if hit.get("_score") is not None
        ]
