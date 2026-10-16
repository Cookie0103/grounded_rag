import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.engine import ping

pytestmark = pytest.mark.integration


async def test_pgvector_extension_exists_after_migration(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        extension = await connection.scalar(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        )

    assert extension == "vector"


async def test_ping_succeeds_against_the_real_database(engine: AsyncEngine) -> None:
    await ping(engine, timeout_seconds=5.0)
