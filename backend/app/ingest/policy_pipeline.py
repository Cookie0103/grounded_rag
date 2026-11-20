"""第二版语料加载、幂等入库与双索引同步。"""

import asyncio
import hashlib
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from app.core.config import POLICY_CHILD_MAX_CHARS, POLICY_CHILD_TARGET_CHARS
from app.core.errors import CorpusError
from app.core.policy import PolicyChunk
from app.db.corpus import DocumentRecord, delete_documents, replace_document
from app.db.policy import load_policy_chunks, policy_document_hashes, policy_writer, publish_policy
from app.db.policy_index import PolicyIndex
from app.ingest.chunker import chunk_document
from app.ingest.pipeline import (
    IngestStats,
    PreparedDocument,
    chunk_records,
    embed_prepared,
    parent_records,
)
from app.ingest.policy_corpus import PolicyMaterial
from app.ingest.source_loader import load_source
from app.providers.base import Embedder

POLICY_INGEST_VERSION = "policy-v2-1"


def read_policy_manifest(root: Path) -> list[PolicyMaterial]:
    """读取生成的入库清单。"""
    path = root / "policy_index.jsonl"
    if not path.is_file():
        raise CorpusError("缺少语料入库清单，先生成日文规程语料")
    return [
        PolicyMaterial.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def prepare_policy_document(root: Path, item: PolicyMaterial) -> PreparedDocument:
    """保留来源、有效期与稳定 ID，再按日文档位进行结构切块。"""
    path = (root / item.path).resolve()
    if not path.is_relative_to(root.resolve()):
        raise CorpusError("语料文件必须位于本机语料目录")
    original = path.read_bytes()
    digest = hashlib.sha256(item.path.encode() + b"\0" + original)
    source_id = f"{item.id}@{digest.hexdigest()[:16]}"
    # 发表状态与截止日期由发布事务管理，重复导入同一文件时保留已发布的版本。
    stable_policy = item.policy.model_dump_json(exclude={"status", "effective_to"})
    digest.update((POLICY_INGEST_VERSION + stable_policy).encode())
    document = load_source(path)
    record = DocumentRecord(
        id=source_id,
        path=item.path,
        edition="common",
        category=item.policy.policy_type,
        title=document.title,
        description=document.description,
        content_hash=digest.hexdigest(),
        corpus_commit=POLICY_INGEST_VERSION,
        policy=item.policy,
    )
    chunked = chunk_document(
        document.title,
        document.markdown,
        child_target=POLICY_CHILD_TARGET_CHARS,
        child_maximum=POLICY_CHILD_MAX_CHARS,
    )
    if not chunked.children:
        raise CorpusError(f"规程没有可入库的子块：{item.id}")
    return PreparedDocument(record, chunked)


async def ingest_policy_corpus(
    root: Path, embedder: Embedder, engine: AsyncEngine, index: PolicyIndex
) -> tuple[IngestStats, list[PolicyChunk]]:
    """以 PostgreSQL 为准写入变更，并发布一致的 ES 关键词快照。"""
    pending = await asyncio.to_thread(_read_documents, root)
    stats = IngestStats()
    async with policy_writer(engine) as connection:
        async with connection.begin():
            await _store_documents(connection, pending, embedder, stats)
        current = await load_policy_chunks(connection)
        await index.sync(current)
    return stats, current


def _read_documents(root: Path) -> list[PreparedDocument]:
    pending = [prepare_policy_document(root, item) for item in read_policy_manifest(root)]
    if not pending:
        raise CorpusError("规程入库清单为空")
    if len({item.record.id for item in pending}) != len(pending):
        raise CorpusError("规程入库清单有重复文档 ID")
    return pending


async def _store_documents(
    connection: AsyncConnection,
    pending: list[PreparedDocument],
    embedder: Embedder,
    stats: IngestStats,
) -> None:
    known = await policy_document_hashes(connection)
    current_ids = {item.record.id for item in pending}
    stale = sorted(set(known) - current_ids)
    to_write = []
    for item in pending:
        prior = known.get(item.record.id)
        if prior == item.record.content_hash:
            stats.unchanged += 1
        else:
            to_write.append(item)
            if prior is None:
                stats.added += 1
            else:
                stats.changed += 1
    vectors = await embed_prepared(embedder, to_write, stats)
    await delete_documents(connection, stale)
    stats.removed = len(stale)
    for item, document_vectors in zip(to_write, vectors, strict=True):
        await replace_document(
            connection,
            item.record,
            parent_records(item),
            chunk_records(item, document_vectors),
            embedder.name,
        )


async def publish_policy_version(engine: AsyncEngine, index: PolicyIndex, document_id: str) -> int:
    """在 PG 事务发布新版本，再将结果同步至 ES。"""
    async with policy_writer(engine) as connection:
        async with connection.begin():
            await publish_policy(connection, document_id)
        return await index.sync(await load_policy_chunks(connection))
