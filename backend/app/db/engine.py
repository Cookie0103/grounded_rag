"""数据库引擎与连通性检查。SQL 只写在 app/db/ 里。"""

import asyncio

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import Settings
from app.core.errors import DependencyUnavailableError


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(settings.database_url, pool_pre_ping=True)


async def ping(engine: AsyncEngine, timeout_seconds: float) -> None:
    """执行 `SELECT 1`；任何失败或超时都转成 DependencyUnavailableError。"""
    try:
        async with asyncio.timeout(timeout_seconds), engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError, TimeoutError) as error:
        raise DependencyUnavailableError("数据库不可用") from error
