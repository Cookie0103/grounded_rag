"""规程库专用的写锁、快照读取与版本发布。"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date

from sqlalchemy import or_, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from app.core.errors import CorpusError
from app.core.policy import PolicyChunk, PolicyMetadata
from app.db.tables import chunks, documents

_WRITER_LOCK = 391107


@asynccontextmanager
async def policy_writer(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    """事务提交后仍持有写锁，直到 ES 快照发布结束。"""
    async with engine.connect() as connection:
        await connection.execute(text("SELECT pg_advisory_lock(:lock)"), {"lock": _WRITER_LOCK})
        await connection.commit()
        try:
            yield connection
        finally:
            try:
                await connection.rollback()
                await connection.execute(
                    text("SELECT pg_advisory_unlock(:lock)"), {"lock": _WRITER_LOCK}
                )
                await connection.commit()
            except (DBAPIError, asyncio.CancelledError):
                await connection.invalidate()
                raise


async def policy_document_hashes(connection: AsyncConnection) -> dict[str, str]:
    """只读第二版语料的文档哈希。"""
    rows = await connection.execute(
        select(documents.c.id, documents.c.content_hash).where(documents.c.source.is_not(None))
    )
    return {row.id: row.content_hash for row in rows}


async def load_policy_chunks(connection: AsyncConnection) -> list[PolicyChunk]:
    """从 PostgreSQL 读取实际已提交的规程块快照。"""
    rows = await connection.execute(
        select(chunks).where(chunks.c.source.is_not(None)).order_by(chunks.c.id)
    )
    return [
        PolicyChunk(
            id=row["id"],
            document_id=row["document_id"],
            heading_path=row["heading_path"],
            text=row["text"],
            policy=PolicyMetadata.model_validate(
                {name: row[name] for name in PolicyMetadata.model_fields}
            ),
        )
        for row in rows.mappings()
    ]


async def valid_policy_document_ids(
    connection: AsyncConnection, policy_id: str, as_of: date
) -> list[str]:
    """按查询日期返回已发表的版本，下线版本仍可被历史日期命中。"""
    rows = await connection.scalars(
        select(documents.c.id)
        .where(
            documents.c.policy_id == policy_id,
            documents.c.status.in_(("online", "offline")),
            documents.c.effective_from <= as_of,
            or_(documents.c.effective_to.is_(None), as_of < documents.c.effective_to),
        )
        .order_by(documents.c.id)
    )
    return list(rows)


async def publish_policy(connection: AsyncConnection, document_id: str) -> None:
    """在同一事务上线新版并结束旧版有效期。"""
    candidate = (
        (
            await connection.execute(
                select(documents)
                .where(documents.c.id == document_id, documents.c.source.is_not(None))
                .with_for_update()
            )
        )
        .mappings()
        .one_or_none()
    )
    if candidate is None:
        raise CorpusError(f"找不到规程文档：{document_id}")
    if candidate["status"] == "online":
        return
    if candidate["status"] != "draft":
        raise CorpusError("仅能发布草稿规程")
    start = candidate["effective_from"]
    old_versions = (
        await connection.execute(
            select(documents.c.id, documents.c.effective_from)
            .where(
                documents.c.policy_id == candidate["policy_id"],
                documents.c.product_line == candidate["product_line"],
                documents.c.status == "online",
            )
            .with_for_update()
        )
    ).all()
    if any(old.effective_from >= start for old in old_versions):
        raise CorpusError("新版生效时间必须晚于当前已上线版本")
    await _update_version(connection, [document_id], "online", candidate["effective_to"])
    if old_versions:
        await _update_version(connection, [old.id for old in old_versions], "offline", start)


async def _update_version(
    connection: AsyncConnection, ids: list[str], status: str, effective_to: date | None
) -> None:
    values = {"status": status, "effective_to": effective_to}
    await connection.execute(update(documents).where(documents.c.id.in_(ids)).values(**values))
    await connection.execute(update(chunks).where(chunks.c.document_id.in_(ids)).values(**values))
