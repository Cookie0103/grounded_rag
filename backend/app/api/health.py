"""GET /health：健康检查，同时检查数据库。"""

from collections.abc import Awaitable, Callable
from functools import partial
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import get_settings
from app.core.trace import trace_id_var
from app.db.engine import ping

DatabasePing = Callable[[], Awaitable[None]]

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    database: str
    trace_id: str


def get_database_ping(request: Request) -> DatabasePing:
    """单元测试用 `app.dependency_overrides` 替换成假实现。"""
    engine: AsyncEngine = request.app.state.engine
    return partial(ping, engine, get_settings().db_timeout_seconds)


@router.get("/health")
async def health(
    database_ping: Annotated[DatabasePing, Depends(get_database_ping)],
) -> HealthResponse:
    await database_ping()
    return HealthResponse(status="ok", database="ok", trace_id=trace_id_var.get())
