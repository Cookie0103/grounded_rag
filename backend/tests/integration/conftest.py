"""集成测试夹具：独立的测试库 grounded_rag_test，开发库永远不碰。"""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import Settings

BACKEND_DIR = Path(__file__).resolve().parents[2]
TEST_DATABASE = "grounded_rag_test"


async def _create_test_database(admin_url: str) -> None:
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as connection:
            exists = await connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = 'grounded_rag_test'")
            )
            if not exists:
                await connection.execute(text("CREATE DATABASE grounded_rag_test"))
    finally:
        await engine.dispose()


def _alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """开发库的连接串换成测试库名；库不存在就创建，并迁移到最新版本。"""
    base = make_url(Settings().database_url)
    admin_url = base.set(database="postgres").render_as_string(hide_password=False)
    test_url = base.set(database=TEST_DATABASE).render_as_string(hide_password=False)
    asyncio.run(_create_test_database(admin_url))
    command.upgrade(_alembic_config(test_url), "head")
    return test_url


@pytest.fixture
async def engine(test_database_url: str) -> AsyncIterator[AsyncEngine]:
    test_engine = create_async_engine(test_database_url)
    try:
        async with test_engine.begin() as connection:  # 每个测试从空表开始
            await connection.execute(text("TRUNCATE documents, sessions CASCADE"))
        yield test_engine
    finally:
        await test_engine.dispose()
