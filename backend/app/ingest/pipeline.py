"""入库流程：清洗 → 切块 → 嵌入 → 写库。内容没变的文档不重复处理。"""

import hashlib
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import EMBEDDING_DIMENSION, INGEST_VERSION
from app.core.errors import CorpusError
from app.core.text import search_text
from app.db.corpus import (
    ChunkRecord,
    DocumentRecord,
    ParentRecord,
    delete_documents,
    document_hashes,
    replace_document,
)
from app.ingest.chunker import ChunkedDocument, chunk_document
from app.ingest.cleaner import clean_mdx, count_residual_tags
from app.ingest.corpus import (
    CORPUS_COMMIT,
    category_of,
    document_id,
    edition_of,
    list_raw_files,
)
from app.providers.base import Embedder

EMBED_SLICE = 256  # 一次交给嵌入模型的文本数，防止一次占太多显存


@dataclass
class IngestStats:
    added: int = 0
    changed: int = 0
    unchanged: int = 0
    removed: int = 0
    embedded_chunks: int = 0
    embed_seconds: float = 0.0
    residual_tags: int = 0
    unknown_components: Counter[str] = field(default_factory=Counter)

    @property
    def documents(self) -> int:
        return self.added + self.changed + self.unchanged


@dataclass
class _Prepared:
    record: DocumentRecord
    chunked: ChunkedDocument


def content_hash(raw: bytes) -> str:
    """文件内容 + 入库流程版本：改了清洗或切块规则（INGEST_VERSION 加 1）就会触发重建。"""
    return hashlib.sha256(raw + INGEST_VERSION.encode()).hexdigest()


async def ingest_corpus(
    raw_dir: Path, embedder: Embedder, engine: AsyncEngine, *, commit: str = CORPUS_COMMIT
) -> IngestStats:
    files = list_raw_files(raw_dir)
    if not files:
        raise CorpusError(f"{raw_dir} 里没有语料文件，先运行 uv run poe fetch-docs")
    stats = IngestStats()
    async with engine.connect() as connection:
        existing = await document_hashes(connection)

    to_write: list[_Prepared] = []
    current_ids: set[str] = set()
    for path in files:
        prepared = _prepare(path, raw_dir, commit, stats)
        doc_id = prepared.record.id
        current_ids.add(doc_id)
        if doc_id not in existing:
            stats.added += 1
            to_write.append(prepared)
        elif existing[doc_id] != prepared.record.content_hash:
            stats.changed += 1
            to_write.append(prepared)
        else:
            stats.unchanged += 1

    stale = sorted(set(existing) - current_ids)
    stats.removed = len(stale)
    vectors = await _embed_all(embedder, to_write, stats)
    async with engine.begin() as connection:
        await delete_documents(connection, stale)
    for prepared, doc_vectors in zip(to_write, vectors, strict=True):
        async with engine.begin() as connection:  # 一篇文档一个事务：失败时这篇保持原样
            await replace_document(
                connection,
                prepared.record,
                _parent_records(prepared),
                _chunk_records(prepared, doc_vectors),
                embedder.name,
            )
    return stats


def _prepare(path: Path, raw_dir: Path, commit: str, stats: IngestStats) -> _Prepared:
    raw = path.read_bytes()
    relative = path.relative_to(raw_dir).as_posix()
    cleaned = clean_mdx(raw.decode("utf-8"), path=relative)
    stats.residual_tags += count_residual_tags(cleaned.markdown)
    stats.unknown_components.update(cleaned.unknown_components)
    doc_id = document_id(relative)
    record = DocumentRecord(
        id=doc_id,
        path=relative,
        edition=edition_of(doc_id),
        category=category_of(doc_id),
        title=cleaned.title,
        description=cleaned.description,
        content_hash=content_hash(raw),
        corpus_commit=commit,
    )
    return _Prepared(record, chunk_document(cleaned.title, cleaned.markdown))


async def _embed_all(
    embedder: Embedder, prepared: list[_Prepared], stats: IngestStats
) -> list[list[list[float]]]:
    """所有要写入的子块一起分批嵌入，再按文档拆回去。"""
    texts = [
        search_text(child.heading_path, child.text)
        for item in prepared
        for child in item.chunked.children
    ]
    started = time.perf_counter()
    vectors: list[list[float]] = []
    for start in range(0, len(texts), EMBED_SLICE):
        vectors += await embedder.embed_documents(texts[start : start + EMBED_SLICE])
    stats.embed_seconds = time.perf_counter() - started
    stats.embedded_chunks = len(texts)
    if any(len(vector) != EMBEDDING_DIMENSION for vector in vectors):
        raise CorpusError(f"嵌入向量的维度必须是 {EMBEDDING_DIMENSION}")

    per_document: list[list[list[float]]] = []
    position = 0
    for item in prepared:
        count = len(item.chunked.children)
        per_document.append(vectors[position : position + count])
        position += count
    return per_document


def _parent_records(prepared: _Prepared) -> list[ParentRecord]:
    doc_id = prepared.record.id
    return [
        ParentRecord(
            f"{doc_id}#p{parent.ordinal}", parent.ordinal, parent.heading_path, parent.text
        )
        for parent in prepared.chunked.parents
    ]


def _chunk_records(prepared: _Prepared, vectors: list[list[float]]) -> list[ChunkRecord]:
    doc_id = prepared.record.id
    return [
        ChunkRecord(
            id=f"{doc_id}#c{child.ordinal}",
            parent_id=f"{doc_id}#p{child.parent_ordinal}",
            ordinal=child.ordinal,
            heading_path=child.heading_path,
            text=child.text,
            embedding=vector,
        )
        for child, vector in zip(prepared.chunked.children, vectors, strict=True)
    ]
