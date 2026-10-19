import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.main import create_app
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


async def test_health_returns_200_with_real_database(engine: AsyncEngine) -> None:
    app = create_app()
    app.state.engine = engine  # 不跑 lifespan，直接用连测试库的引擎

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["database"] == "ok"
