import math

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import EMBEDDING_DIMENSION, QWEN3_MODEL_NAME
from app.db.corpus import (
    ChunkRecord,
    DocumentRecord,
    ParentRecord,
    delete_documents,
    document_hashes,
    nearest_chunks,
    replace_document,
    table_counts,
)
from app.providers.fakes import FakeEmbedder

pytestmark = pytest.mark.integration

MODEL = QWEN3_MODEL_NAME


def _document(
    doc_id: str, *, edition: str = "self_host", content_hash: str = "h1"
) -> DocumentRecord:
    return DocumentRecord(
        id=doc_id,
        path=f"zh/{doc_id}.mdx",
        edition=edition,
        category="knowledge",
        title=f"标题 {doc_id}",
        description=None,
        content_hash=content_hash,
        corpus_commit="c80a318",
    )


async def _records(
    doc_id: str, texts: list[str], embedder: FakeEmbedder
) -> tuple[list[ParentRecord], list[ChunkRecord]]:
    parents = [ParentRecord(f"{doc_id}#p0", 0, "标题", "\n\n".join(texts))]
    vectors = await embedder.embed_documents(texts)
    chunk_records = [
        ChunkRecord(f"{doc_id}#c{i}", f"{doc_id}#p0", i, "标题", text_, vector)
        for i, (text_, vector) in enumerate(zip(texts, vectors, strict=True))
    ]
    return parents, chunk_records


async def _store(
    engine: AsyncEngine, document: DocumentRecord, texts: list[str], embedder: FakeEmbedder
) -> None:
    parents, chunk_records = await _records(document.id, texts, embedder)
    async with engine.begin() as connection:
        await replace_document(connection, document, parents, chunk_records, MODEL)


async def test_stored_document_is_visible_with_its_hash_and_counts(engine: AsyncEngine) -> None:
    embedder = FakeEmbedder(EMBEDDING_DIMENSION)

    await _store(engine, _document("a"), ["第一块", "第二块", "第三块"], embedder)

    async with engine.connect() as connection:
        assert await document_hashes(connection) == {"a": "h1"}
        assert await table_counts(connection) == {
            "documents": 1,
            "parent_chunks": 1,
            "chunks": 3,
            "chunk_embeddings": 3,
        }


async def test_replacing_a_document_removes_its_old_rows(engine: AsyncEngine) -> None:
    embedder = FakeEmbedder(EMBEDDING_DIMENSION)
    await _store(engine, _document("a"), ["旧一", "旧二", "旧三"], embedder)

    await _store(engine, _document("a", content_hash="h2"), ["新一"], embedder)

    async with engine.connect() as connection:
        assert await document_hashes(connection) == {"a": "h2"}
        counts = await table_counts(connection)
        assert (counts["chunks"], counts["chunk_embeddings"]) == (1, 1)


async def test_deleting_documents_cascades_to_chunks_and_embeddings(engine: AsyncEngine) -> None:
    embedder = FakeEmbedder(EMBEDDING_DIMENSION)
    await _store(engine, _document("a"), ["甲"], embedder)
    await _store(engine, _document("b"), ["乙"], embedder)

    async with engine.begin() as connection:
        await delete_documents(connection, ["a"])
        await delete_documents(connection, [])  # 空列表什么都不做

    async with engine.connect() as connection:
        assert set(await document_hashes(connection)) == {"b"}
        counts = await table_counts(connection)
        assert (counts["parent_chunks"], counts["chunks"], counts["chunk_embeddings"]) == (1, 1, 1)


async def test_failed_replacement_rolls_back_and_keeps_the_old_document(
    engine: AsyncEngine,
) -> None:
    embedder = FakeEmbedder(EMBEDDING_DIMENSION)
    await _store(engine, _document("a"), ["旧内容"], embedder)
    parents, chunk_records = await _records("a", ["新内容"], embedder)
    broken = [ChunkRecord("a#c0", "不存在的父块", 0, "标题", "新内容", chunk_records[0].embedding)]

    with pytest.raises(IntegrityError, match="fk_chunks_parent_id"):
        async with engine.begin() as connection:
            await replace_document(
                connection, _document("a", content_hash="h2"), parents, broken, MODEL
            )

    async with engine.connect() as connection:
        assert await document_hashes(connection) == {"a": "h1"}


async def test_nearest_chunks_are_ordered_by_similarity(engine: AsyncEngine) -> None:
    embedder = FakeEmbedder(EMBEDDING_DIMENSION)
    await _store(
        engine,
        _document("a"),
        ["知识库上传文件大小限制", "数据库连接超时设置", "上传文件的大小上限"],
        embedder,
    )
    query = (await embedder.embed_queries(["上传文件大小限制"]))[0]

    async with engine.connect() as connection:
        found = await nearest_chunks(connection, query, model=MODEL, limit=3)

    assert [chunk.text for chunk in found][:2] == ["知识库上传文件大小限制", "上传文件的大小上限"]
    assert found[0].distance < found[1].distance < found[2].distance
    assert found[0].document_id == "a"
    assert found[0].parent_id == "a#p0"


async def test_nearest_chunks_only_returns_the_requested_model(engine: AsyncEngine) -> None:
    embedder = FakeEmbedder(EMBEDDING_DIMENSION)
    await _store(engine, _document("a"), ["上传文件大小限制"], embedder)
    query = (await embedder.embed_queries(["上传文件大小限制"]))[0]

    async with engine.connect() as connection:
        assert await nearest_chunks(connection, query, model="bge-m3", limit=3) == []


async def test_edition_filter_returns_enough_rows_when_the_nearest_ones_are_another_edition(
    engine: AsyncEngine,
) -> None:
    """近邻全是云版时，只查自部署版也要返回满 limit 条（靠 hnsw.iterative_scan 补足）。

    用随机的稠密向量：HNSW 对大量完全正交、距离相同的稀疏向量表现不正常，不能代表真实数据。
    """
    query = _wave(0.0, 1.0)
    for index in range(80):  # 云版：都紧挨着查询
        noise = _wave(index + 1.0, 3.7 + index)
        await _store_vector(
            engine,
            _document(f"cloud{index:02}", edition="cloud"),
            _unit([q + 0.3 * n for q, n in zip(query, noise, strict=True)]),
        )
    for index in range(5):  # 自部署版：和查询无关
        await _store_vector(engine, _document(f"self{index}"), _wave(100.0 + index, 5.3 + index))

    async with engine.begin() as connection:
        await connection.execute(text("SET LOCAL enable_seqscan = off"))  # 尽量走 HNSW 索引
        found = await nearest_chunks(
            connection, query, model=MODEL, limit=5, editions=("self_host",)
        )
        setting = await connection.scalar(text("SHOW hnsw.iterative_scan"))

    # HNSW 是近似检索，图是随机建的，个别点可能搜不到（CI 上有一次只返回 4 条），
    # 所以不要求恰好 5 条；要点是最近的 40 个都是云版时，仍然能找到自部署版，而不是 0 条
    assert len(found) >= 3
    assert all(chunk.document_id.startswith("self") for chunk in found)
    assert setting == "relaxed_order"  # nearest_chunks 在事务内开启了迭代扫描


def _wave(phase: float, frequency: float) -> list[float]:
    """确定性的「随机」稠密向量（单位长度）；测试里不需要真正的随机数。"""
    return _unit([math.sin(frequency * i + phase) for i in range(EMBEDDING_DIMENSION)])


def _unit(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vector))
    return [x / norm for x in vector]


async def _store_vector(engine: AsyncEngine, document: DocumentRecord, vector: list[float]) -> None:
    parents = [ParentRecord(f"{document.id}#p0", 0, "标题", "正文")]
    chunk_records = [
        ChunkRecord(f"{document.id}#c0", f"{document.id}#p0", 0, "标题", "正文", vector)
    ]
    async with engine.begin() as connection:
        await replace_document(connection, document, parents, chunk_records, MODEL)
