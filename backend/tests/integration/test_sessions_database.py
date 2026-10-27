import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.session import Session, Turn
from app.db.sessions import PostgresSessionStore

pytestmark = pytest.mark.integration


async def test_session_round_trip_and_upsert(engine: AsyncEngine) -> None:
    store = PostgresSessionStore(engine)
    assert await store.load("s1") is None

    await store.save(Session(id="s1", edition="cloud", turns=[Turn(question="问", answer="答")]))
    await store.save(
        Session(
            id="s1", edition="self_host", summary="摘要", turns=[Turn(question="问2", answer="答2")]
        )
    )

    loaded = await store.load("s1")
    assert loaded == Session(
        id="s1", edition="self_host", summary="摘要", turns=[Turn(question="问2", answer="答2")]
    )


async def test_purge_removes_only_expired_sessions(engine: AsyncEngine) -> None:
    store = PostgresSessionStore(engine)
    await store.save(Session(id="old"))
    await store.save(Session(id="new"))
    async with engine.begin() as connection:
        await connection.execute(
            text("UPDATE sessions SET updated_at = now() - interval '10 days' WHERE id = 'old'")
        )

    assert await store.purge_expired(7) == 1
    assert await store.load("old") is None
    assert await store.load("new") is not None


async def test_edition_check_constraint(engine: AsyncEngine) -> None:
    with pytest.raises(IntegrityError):
        await PostgresSessionStore(engine).save(Session(id="s", edition="mars"))
