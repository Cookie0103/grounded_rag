from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
from elasticsearch import AsyncElasticsearch, NotFoundError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings
from app.core.policy import PolicyMetadata, PolicyStatus
from app.db.policy import valid_policy_document_ids
from app.db.policy_index import PolicyIndex
from app.ingest.policy_corpus import PolicyMaterial
from app.ingest.policy_pipeline import ingest_policy_corpus, publish_policy_version
from app.providers.fakes import FakeEmbedder

pytestmark = pytest.mark.integration

_OLD_DAY = date(2026, 10, 1)
_NEW_DAY = date(2026, 11, 1)
_POLICY_ID = "HL-TEST"


def _write_policy(root: Path, name: str, start: date, status: PolicyStatus) -> PolicyMaterial:
    filename = f"{name}.md"
    (root / filename).write_text(
        f"# {name}\n\n合成資料（検証専用）。返済手続を案内します。\n", encoding="utf-8"
    )
    return PolicyMaterial(
        id=name,
        path=filename,
        policy=PolicyMetadata(
            source="internal",
            synthetic=True,
            product_line="home_loan",
            policy_type="procedure",
            policy_id=_POLICY_ID,
            effective_from=start,
            status=status,
            corpus_tier="S",
            based_on=("public/synthetic-fixture",),
        ),
    )


async def test_policy_ingest_is_idempotent_and_publishes_consistent_dated_versions(
    engine: AsyncEngine, tmp_path: Path
) -> None:
    docs = [
        _write_policy(tmp_path, "old", _OLD_DAY, "online"),
        _write_policy(tmp_path, "new", _NEW_DAY, "draft"),
    ]
    (tmp_path / "policy_index.jsonl").write_text(
        "".join(item.model_dump_json() + "\n" for item in docs), encoding="utf-8"
    )
    settings = Settings()
    alias = f"grounded-rag-policy-it-{uuid4().hex}"
    index = PolicyIndex(settings.elasticsearch_url, alias)
    try:
        first, chunks = await ingest_policy_corpus(tmp_path, FakeEmbedder(), engine, index)
        old_id = next(chunk.document_id for chunk in chunks if chunk.policy.status == "online")
        new_id = next(chunk.document_id for chunk in chunks if chunk.policy.status == "draft")
        assert first.added == 2
        assert await publish_policy_version(engine, index, new_id) == len(chunks)
        repeat, current = await ingest_policy_corpus(tmp_path, FakeEmbedder(), engine, index)

        assert (repeat.added, repeat.changed, repeat.embedded_chunks) == (0, 0, 0)
        assert len(current) == len(chunks)
        async with engine.connect() as connection:
            assert await valid_policy_document_ids(connection, _POLICY_ID, _OLD_DAY) == [old_id]
            assert await valid_policy_document_ids(connection, _POLICY_ID, _NEW_DAY) == [new_id]
        async with AsyncElasticsearch(settings.elasticsearch_url, request_timeout=10) as es:
            assert (await es.count(index=alias))["count"] == len(current)
            assert await _visible_index_ids(es, alias, _OLD_DAY) == {old_id}
            assert await _visible_index_ids(es, alias, _NEW_DAY) == {new_id}
    finally:
        await index.close()
        async with AsyncElasticsearch(settings.elasticsearch_url, request_timeout=10) as es:
            try:
                names = (await es.indices.get_alias(name=alias)).body
            except NotFoundError:
                names = {}
            if names:
                await es.indices.delete(index=list(names), ignore_unavailable=True)


async def _visible_index_ids(es: AsyncElasticsearch, alias: str, when: date) -> set[str]:
    result = await es.search(
        index=alias,
        query={
            "bool": {
                "filter": [
                    {"term": {"policy_id": _POLICY_ID}},
                    {"terms": {"status": ["online", "offline"]}},
                    {"range": {"effective_from": {"lte": when.isoformat()}}},
                    {
                        "bool": {
                            "should": [
                                {"range": {"effective_to": {"gt": when.isoformat()}}},
                                {"bool": {"must_not": {"exists": {"field": "effective_to"}}}},
                            ],
                            "minimum_should_match": 1,
                        },
                    },
                ],
            },
        },
    )
    return {item["_source"]["document_id"] for item in result["hits"]["hits"]}
