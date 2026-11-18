from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
from elasticsearch import AsyncElasticsearch, NotFoundError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings
from app.core.policy import CorpusTier, PolicyMetadata
from app.db.corpus import chunks_without_embedding, table_counts
from app.db.policy_filter import MetaFilter
from app.db.policy_index import PolicyIndex
from app.ingest.pipeline import add_missing_embeddings
from app.ingest.policy_corpus import PolicyMaterial
from app.ingest.policy_pipeline import ingest_policy_corpus
from app.providers.fakes import FakeEmbedder, FakeReranker
from app.retrieval.factory import build_retriever
from app.retrieval.keyword import ElasticsearchKeywords

pytestmark = pytest.mark.integration

SETTINGS = Settings(embedding_model="fake", reranker_model="fake")
DAY = date(2026, 11, 18)


def _fixture_document(root: Path, name: str, body: str, tier: CorpusTier) -> PolicyMaterial:
    filename = f"{name}.md"
    (root / filename).write_text(f"# 合成手順書\n\n{body}\n", encoding="utf-8")
    return PolicyMaterial(
        id=name,
        path=filename,
        policy=PolicyMetadata(
            source="internal",
            synthetic=True,
            product_line="home_loan",
            policy_type="procedure",
            policy_id=f"HL-{name.upper()}",
            effective_from=DAY,
            status="online",
            corpus_tier=tier,
            based_on=("public/test-fixture",),
        ),
    )


@pytest.fixture
async def ingested(
    tmp_path: Path, engine: AsyncEngine
) -> AsyncIterator[tuple[AsyncEngine, ElasticsearchKeywords]]:
    documents = [
        _fixture_document(
            tmp_path, "repayment", "HL-REPAYMENT 返済日の確認手続を案内します。", "S"
        ),
        _fixture_document(tmp_path, "balance", "残高証明書に関する手続を確認します。", "S"),
        _fixture_document(tmp_path, "history", "過去の利用状況に関する手続を案内します。", "L"),
    ]
    (tmp_path / "policy_index.jsonl").write_text(
        "".join(document.model_dump_json() + "\n" for document in documents), encoding="utf-8"
    )
    alias = f"grounded-rag-retrieve-it-{uuid4().hex}"
    index = PolicyIndex(SETTINGS.elasticsearch_url, alias)
    try:
        await ingest_policy_corpus(tmp_path, FakeEmbedder(), engine, index)
        yield engine, ElasticsearchKeywords(SETTINGS.elasticsearch_url, alias)
    finally:
        await index.close()
        async with AsyncElasticsearch(SETTINGS.elasticsearch_url, request_timeout=10) as es:
            try:
                names = (await es.indices.get_alias(name=alias)).body
            except NotFoundError:
                names = {}
            if names:
                await es.indices.delete(index=list(names), ignore_unavailable=True)


async def test_retriever_built_from_the_database_finds_chunks_and_loads_parents(
    ingested: tuple[AsyncEngine, ElasticsearchKeywords],
) -> None:
    engine, keyword = ingested
    retriever = await build_retriever(
        engine, SETTINGS, embedder=FakeEmbedder(), reranker=FakeReranker(), keyword=keyword
    )

    result = await retriever.retrieve(
        "HL-REPAYMENT 返済日の確認手続", filters=MetaFilter(as_of=DAY), rerank=True
    )

    first = result.candidates[0]
    assert first.chunk.document_id.startswith("repayment@")
    assert first.chunk.policy is not None
    assert first.chunk.policy.policy_id == "HL-REPAYMENT"
    assert first.bm25_rank == 1
    assert first.rerank_score is not None
    assert result.parents[0].id == first.chunk.parent_id
    assert "返済日の確認手続" in result.parents[0].text


async def test_filter_excludes_l_tier_before_both_retrieval_paths(
    ingested: tuple[AsyncEngine, ElasticsearchKeywords],
) -> None:
    engine, keyword = ingested
    retriever = await build_retriever(engine, SETTINGS, embedder=FakeEmbedder(), keyword=keyword)

    result = await retriever.retrieve("手続", filters=MetaFilter(as_of=DAY, corpus_tier="S"))

    tiers = {
        candidate.chunk.policy.corpus_tier
        for candidate in result.candidates
        if candidate.chunk.policy
    }
    assert tiers == {"S"}


async def test_vector_and_keyword_modes_keep_only_their_own_ranks(
    ingested: tuple[AsyncEngine, ElasticsearchKeywords],
) -> None:
    engine, keyword = ingested
    retriever = await build_retriever(engine, SETTINGS, embedder=FakeEmbedder(), keyword=keyword)
    filters = MetaFilter(as_of=DAY)

    vector_only = await retriever.retrieve("手続", mode="vector", filters=filters)
    keyword_only = await retriever.retrieve("手続", mode="keyword", filters=filters)

    assert vector_only.candidates
    assert keyword_only.candidates
    assert all(c.bm25_rank is None and c.vector_rank for c in vector_only.candidates)
    assert all(c.vector_rank is None and c.bm25_rank for c in keyword_only.candidates)
    assert "embed" not in keyword_only.timings_ms
    assert "keyword" not in vector_only.timings_ms


async def test_a_second_embedding_model_can_be_added_without_touching_the_first(
    ingested: tuple[AsyncEngine, ElasticsearchKeywords],
) -> None:
    engine, keyword = ingested
    second = FakeEmbedder()
    second.name = "second"
    async with engine.connect() as connection:
        before = await table_counts(connection)
        missing = await chunks_without_embedding(connection, "second")
    assert len(missing) == before["chunks"]

    added = await add_missing_embeddings(second, engine)
    added_again = await add_missing_embeddings(second, engine)

    assert (added, added_again) == (before["chunks"], 0)
    async with engine.connect() as connection:
        after = await table_counts(connection)
    assert after["chunk_embeddings"] == 2 * before["chunks"]
    retriever = await build_retriever(engine, SETTINGS, embedder=second, keyword=keyword)
    result = await retriever.retrieve("返済日の確認", mode="vector", filters=MetaFilter(as_of=DAY))
    assert result.candidates
