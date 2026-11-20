"""PostgreSQL 和 Elasticsearch 使用同一份规程检索过滤条件。"""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import ColumnElement, or_

from app.core.policy import CorpusTier
from app.db.tables import chunks

_PUBLISHED_STATUSES = ("online", "offline")


class MetaFilter(BaseModel):
    """按业务日期过滤有效版；L 档包含 S 与放大语料。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    product_line: str | None = "home_loan"
    policy_type: str | None = None
    as_of: date = Field(default_factory=date.today)
    corpus_tier: CorpusTier = "L"

    def _terms(self) -> dict[str, str]:
        values = {
            "product_line": self.product_line,
            "policy_type": self.policy_type,
            "corpus_tier": "S" if self.corpus_tier == "S" else None,
        }
        return {field: value for field, value in values.items() if value is not None}

    def sql_conditions(self) -> list[ColumnElement[bool]]:
        """生成 pgvector 候选的 SQL WHERE 条件。"""
        return [
            chunks.c.source.is_not(None),
            chunks.c.status.in_(_PUBLISHED_STATUSES),
            chunks.c.effective_from <= self.as_of,
            or_(chunks.c.effective_to.is_(None), chunks.c.effective_to > self.as_of),
            *(chunks.c[field] == value for field, value in self._terms().items()),
        ]

    def elasticsearch_filters(self) -> list[dict[str, object]]:
        """生成 kuromoji 查询的 Elasticsearch filter。"""
        day = self.as_of.isoformat()
        filters: list[dict[str, object]] = [
            {"exists": {"field": "source"}},
            {"terms": {"status": _PUBLISHED_STATUSES}},
            {"range": {"effective_from": {"lte": day}}},
            {
                "bool": {
                    "minimum_should_match": 1,
                    "should": [
                        {"range": {"effective_to": {"gt": day}}},
                        {"bool": {"must_not": {"exists": {"field": "effective_to"}}}},
                    ],
                }
            },
        ]
        for field, value in self._terms().items():
            filters.append({"term": {field: value}})
        return filters
