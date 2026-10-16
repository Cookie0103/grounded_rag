"""语料表的读写和最近邻查询。SQL 只写在 app/db/ 里。"""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import bindparam, delete, func, insert, select, text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.tables import chunk_embeddings, chunks, documents, parent_chunks


@dataclass(frozen=True)
class DocumentRecord:
    id: str
    path: str
    edition: str
    category: str
    title: str
    description: str | None
    content_hash: str
    corpus_commit: str


@dataclass(frozen=True)
class ParentRecord:
    id: str
    ordinal: int
    heading_path: str
    text: str


@dataclass(frozen=True)
class ChunkRecord:
    id: str
    parent_id: str
    ordinal: int
    heading_path: str
    text: str
    embedding: list[float]


@dataclass(frozen=True)
class NearestChunk:
    chunk_id: str
    document_id: str
    parent_id: str
    heading_path: str
    text: str
    distance: float  # 余弦距离 = 1 - 余弦相似度，越小越相似


async def document_hashes(connection: AsyncConnection) -> dict[str, str]:
    """库里已有的文档 → 内容哈希，用来判断哪些文档变了。"""
    rows = await connection.execute(select(documents.c.id, documents.c.content_hash))
    return {row.id: row.content_hash for row in rows}


async def delete_documents(connection: AsyncConnection, document_ids: Sequence[str]) -> None:
    """删除文档；它的父块、子块、向量由外键级联删除。"""
    if document_ids:
        await connection.execute(delete(documents).where(documents.c.id.in_(document_ids)))


async def replace_document(
    connection: AsyncConnection,
    document: DocumentRecord,
    parents: Sequence[ParentRecord],
    chunk_records: Sequence[ChunkRecord],
    model: str,
) -> None:
    """删掉旧文档再整篇重建。调用方负责放在同一个事务里。"""
    await delete_documents(connection, [document.id])
    await connection.execute(insert(documents).values(**document.__dict__))
    if parents:
        await connection.execute(
            insert(parent_chunks),
            [{"document_id": document.id, **parent.__dict__} for parent in parents],
        )
    if chunk_records:
        await connection.execute(
            insert(chunks),
            [
                {"document_id": document.id, **_without(chunk.__dict__, "embedding")}
                for chunk in chunk_records
            ],
        )
        await connection.execute(
            insert(chunk_embeddings),
            [
                {"chunk_id": chunk.id, "model": model, "embedding": chunk.embedding}
                for chunk in chunk_records
            ],
        )


def _without(values: dict[str, object], key: str) -> dict[str, object]:
    return {name: value for name, value in values.items() if name != key}


async def nearest_chunks(
    connection: AsyncConnection,
    embedding: Sequence[float],
    *,
    model: str,
    limit: int,
    edition: str | None = None,
) -> list[NearestChunk]:
    """按余弦距离取最近的子块；可以只查某个版本的文档。

    带 WHERE 过滤时，HNSW 索引是先找近邻再过滤，可能不足 limit 条，所以开启迭代扫描。
    模型名直接写进 SQL（literal_execute），这样部分索引的 WHERE 条件才能被规划器识别。
    """
    await connection.execute(text("SET LOCAL hnsw.iterative_scan = relaxed_order"))
    distance = chunk_embeddings.c.embedding.cosine_distance(list(embedding))
    statement = (
        select(
            chunks.c.id,
            chunks.c.document_id,
            chunks.c.parent_id,
            chunks.c.heading_path,
            chunks.c.text,
            distance.label("distance"),
        )
        .select_from(
            chunk_embeddings.join(chunks, chunks.c.id == chunk_embeddings.c.chunk_id).join(
                documents, documents.c.id == chunks.c.document_id
            )
        )
        .where(chunk_embeddings.c.model == bindparam("model", model, literal_execute=True))
        .order_by(distance)
        .limit(limit)
    )
    if edition is not None:
        statement = statement.where(documents.c.edition == edition)
    rows = await connection.execute(statement)
    return [
        NearestChunk(
            row.id, row.document_id, row.parent_id, row.heading_path, row.text, row.distance
        )
        for row in rows
    ]


async def table_counts(connection: AsyncConnection) -> dict[str, int]:
    """各表的行数，数据报告和测试用。"""
    counts: dict[str, int] = {}
    for table in (documents, parent_chunks, chunks, chunk_embeddings):
        counts[table.name] = int(
            await connection.scalar(select(func.count()).select_from(table)) or 0
        )
    return counts
