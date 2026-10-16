from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import EMBEDDING_DIMENSION
from app.core.errors import CorpusError
from app.db.corpus import document_hashes, table_counts
from app.db.tables import chunk_embeddings, chunks, documents
from app.ingest import pipeline
from app.ingest.pipeline import ingest_corpus
from app.providers.fakes import FakeEmbedder

pytestmark = pytest.mark.integration


class CountingEmbedder(FakeEmbedder):
    """记录 embed_documents 一共嵌入了多少段文字。"""

    def __init__(self, dimension: int = EMBEDDING_DIMENSION) -> None:
        super().__init__(dimension)
        self.embedded_texts = 0

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.embedded_texts += len(texts)
        return await super().embed_documents(texts)


def _write(raw_dir: Path, relative: str, body: str, *, title: str) -> None:
    path = raw_dir / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\ntitle: {title}\n---\n\n{body}\n", encoding="utf-8", newline="\n")


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    root = tmp_path / "raw"
    _write(
        root,
        "zh/learn/alpha.mdx",
        "## 上传\n\n单次最多上传 5 个文件。\n\n## 大小\n\n单个文件最大 15 MB。",
        title="甲",
    )
    _write(
        root,
        "zh/cloud/use-dify/knowledge/beta.mdx",
        "云版的说明。\n\n<Note>\n注意事项\n</Note>",
        title="乙",
    )
    return root


async def _document_rows(engine: AsyncEngine) -> dict[str, tuple[str, str, str, str]]:
    async with engine.connect() as connection:
        rows = await connection.execute(
            select(
                documents.c.id,
                documents.c.path,
                documents.c.edition,
                documents.c.category,
                documents.c.title,
            )
        )
        return {row.id: (row.path, row.edition, row.category, row.title) for row in rows}


async def test_first_run_stores_documents_chunks_and_embeddings(
    raw_dir: Path, engine: AsyncEngine
) -> None:
    embedder = CountingEmbedder()

    stats = await ingest_corpus(raw_dir, embedder, engine, commit="abc1234")

    assert (stats.added, stats.changed, stats.unchanged, stats.removed) == (2, 0, 0, 0)
    assert await _document_rows(engine) == {
        "learn/alpha": ("zh/learn/alpha.mdx", "common", "learn", "甲"),
        "cloud/use-dify/knowledge/beta": (
            "zh/cloud/use-dify/knowledge/beta.mdx",
            "cloud",
            "knowledge",
            "乙",
        ),
    }
    async with engine.connect() as connection:
        counts = await table_counts(connection)
        child_rows = (
            await connection.execute(select(chunks.c.id, chunks.c.parent_id, chunks.c.heading_path))
        ).all()
        models = {row.model for row in await connection.execute(select(chunk_embeddings.c.model))}
    assert counts["documents"] == 2
    assert counts["chunk_embeddings"] == counts["chunks"] == embedder.embedded_texts > 0
    assert models == {"fake"}
    assert ("learn/alpha#c0", "learn/alpha#p0", "甲 > 上传") in [tuple(row) for row in child_rows]


async def test_second_run_changes_nothing_and_embeds_nothing(
    raw_dir: Path, engine: AsyncEngine
) -> None:
    await ingest_corpus(raw_dir, CountingEmbedder(), engine)
    before = await _snapshot(engine)
    embedder = CountingEmbedder()

    stats = await ingest_corpus(raw_dir, embedder, engine)

    assert (stats.added, stats.changed, stats.unchanged, stats.removed) == (0, 0, 2, 0)
    assert embedder.embedded_texts == 0
    assert await _snapshot(engine) == before


async def test_only_the_edited_document_is_rebuilt(raw_dir: Path, engine: AsyncEngine) -> None:
    await ingest_corpus(raw_dir, CountingEmbedder(), engine)
    beta_before = await _snapshot(engine, "cloud/use-dify/knowledge/beta")
    _write(raw_dir, "zh/learn/alpha.mdx", "## 上传\n\n单次最多上传 10 个文件。", title="甲")
    embedder = CountingEmbedder()

    stats = await ingest_corpus(raw_dir, embedder, engine)

    assert (stats.added, stats.changed, stats.unchanged, stats.removed) == (0, 1, 1, 0)
    assert embedder.embedded_texts == 1  # 新的 alpha 只有一个子块
    assert await _snapshot(engine, "cloud/use-dify/knowledge/beta") == beta_before
    alpha_texts = [row[2] for row in await _snapshot(engine, "learn/alpha")]
    assert alpha_texts == ["单次最多上传 10 个文件。"]


async def test_removed_files_are_deleted_and_new_files_are_added(
    raw_dir: Path, engine: AsyncEngine
) -> None:
    await ingest_corpus(raw_dir, CountingEmbedder(), engine)
    (raw_dir / "zh/cloud/use-dify/knowledge/beta.mdx").unlink()
    _write(raw_dir, "zh/learn/gamma.mdx", "新文档。", title="丙")

    stats = await ingest_corpus(raw_dir, CountingEmbedder(), engine)

    assert (stats.added, stats.changed, stats.unchanged, stats.removed) == (1, 0, 1, 1)
    assert set(await _document_rows(engine)) == {"learn/alpha", "learn/gamma"}
    async with engine.connect() as connection:
        counts = await table_counts(connection)
    assert counts["chunk_embeddings"] == counts["chunks"]  # beta 的块和向量都级联删掉了


async def test_new_ingest_version_rebuilds_every_document(
    raw_dir: Path, engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    await ingest_corpus(raw_dir, CountingEmbedder(), engine)
    monkeypatch.setattr(pipeline, "INGEST_VERSION", "2")

    stats = await ingest_corpus(raw_dir, CountingEmbedder(), engine)

    assert (stats.added, stats.changed, stats.unchanged) == (0, 2, 0)


async def test_cleaning_statistics_are_collected(tmp_path: Path, engine: AsyncEngine) -> None:
    _write(tmp_path, "zh/learn/odd.mdx", "<Mystery>\n内容\n</Mystery>", title="怪")

    stats = await ingest_corpus(tmp_path, CountingEmbedder(), engine)

    assert dict(stats.unknown_components) == {"Mystery": 1}
    assert stats.residual_tags == 0


async def test_empty_raw_directory_is_an_error(tmp_path: Path, engine: AsyncEngine) -> None:
    with pytest.raises(CorpusError, match="fetch-docs"):
        await ingest_corpus(tmp_path, CountingEmbedder(), engine)


async def test_wrong_vector_dimension_is_rejected_before_anything_is_written(
    raw_dir: Path, engine: AsyncEngine
) -> None:
    with pytest.raises(CorpusError, match="1024"):
        await ingest_corpus(raw_dir, CountingEmbedder(dimension=8), engine)

    async with engine.connect() as connection:
        assert await document_hashes(connection) == {}


async def _snapshot(engine: AsyncEngine, document: str | None = None) -> list[tuple[str, str, str]]:
    """(子块 ID, 所属父块, 正文)，按 ID 排序；可只看一篇文档。"""
    statement = select(chunks.c.id, chunks.c.parent_id, chunks.c.text).order_by(chunks.c.id)
    if document is not None:
        statement = statement.where(chunks.c.document_id == document)
    async with engine.connect() as connection:
        return [tuple(row) for row in await connection.execute(statement)]
