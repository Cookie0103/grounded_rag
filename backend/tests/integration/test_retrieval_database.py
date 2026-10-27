from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings
from app.db.corpus import chunks_without_embedding, table_counts
from app.ingest.pipeline import add_missing_embeddings, ingest_corpus
from app.providers.fakes import FakeEmbedder, FakeReranker
from app.retrieval.factory import build_retriever

pytestmark = pytest.mark.integration

SETTINGS = Settings(_env_file=None, embedding_model="fake", reranker_model="fake")


def _write(raw_dir: Path, relative: str, body: str, *, title: str) -> None:
    path = raw_dir / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\ntitle: {title}\n---\n\n{body}\n", encoding="utf-8", newline="\n")


@pytest.fixture
async def ingested(tmp_path: Path, engine: AsyncEngine) -> AsyncEngine:
    raw = tmp_path / "raw"
    _write(
        raw,
        "zh/learn/alpha.mdx",
        "## 上传\n\n单次最多上传 5 个文件，由 UPLOAD_FILE_BATCH_LIMIT 控制。",
        title="甲",
    )
    _write(
        raw,
        "zh/self-host/use-dify/knowledge/beta.mdx",
        "自部署版的知识库说明，支持父子分段。",
        title="乙",
    )
    _write(
        raw,
        "zh/cloud/use-dify/knowledge/gamma.mdx",
        "云版的知识库说明，在监控页面查看用量。",
        title="丙",
    )
    await ingest_corpus(raw, FakeEmbedder(), engine)
    return engine


async def test_retriever_built_from_the_database_finds_chunks_and_loads_parents(
    ingested: AsyncEngine,
) -> None:
    retriever = await build_retriever(
        ingested, SETTINGS, embedder=FakeEmbedder(), reranker=FakeReranker()
    )

    result = await retriever.retrieve("UPLOAD_FILE_BATCH_LIMIT 是什么")

    first = result.candidates[0]
    assert first.chunk.document_id == "learn/alpha"
    assert first.bm25_rank == 1
    assert first.rerank_score is not None
    assert result.parents[0].id == first.chunk.parent_id
    assert "单次最多上传 5 个文件" in result.parents[0].text


async def test_edition_filter_keeps_only_the_requested_editions_on_both_paths(
    ingested: AsyncEngine,
) -> None:
    retriever = await build_retriever(ingested, SETTINGS, embedder=FakeEmbedder())

    result = await retriever.retrieve("知识库说明", editions=("cloud", "common"))

    editions = {candidate.chunk.edition for candidate in result.candidates}
    assert editions <= {"cloud", "common"}
    assert "cloud" in editions


async def test_vector_only_and_bm25_only_modes(ingested: AsyncEngine) -> None:
    retriever = await build_retriever(ingested, SETTINGS, embedder=FakeEmbedder())

    vector_only = await retriever.retrieve("知识库说明", mode="vector")
    bm25_only = await retriever.retrieve("知识库说明", mode="bm25")

    assert all(c.bm25_rank is None and c.vector_rank for c in vector_only.candidates)
    assert all(c.vector_rank is None and c.bm25_rank for c in bm25_only.candidates)
    assert "embed" not in bm25_only.timings_ms
    assert "bm25" not in vector_only.timings_ms


async def test_a_second_embedding_model_can_be_added_without_touching_the_first(
    ingested: AsyncEngine,
) -> None:
    second = FakeEmbedder()
    second.name = "second"
    async with ingested.connect() as connection:
        before = await table_counts(connection)
        missing = await chunks_without_embedding(connection, "second")
    assert len(missing) == before["chunks"]

    added = await add_missing_embeddings(second, ingested)
    added_again = await add_missing_embeddings(second, ingested)

    assert (added, added_again) == (before["chunks"], 0)
    async with ingested.connect() as connection:
        after = await table_counts(connection)
    assert after["chunk_embeddings"] == 2 * before["chunks"]
    retriever = await build_retriever(ingested, SETTINGS, embedder=second)
    result = await retriever.retrieve("UPLOAD_FILE_BATCH_LIMIT", mode="vector")
    assert result.candidates
