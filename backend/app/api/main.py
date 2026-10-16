"""FastAPI 应用入口：`uvicorn app.api.main:create_app --factory`。"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

from app.api.chat import router as chat_router
from app.api.errors import register_error_handlers
from app.api.health import router as health_router
from app.api.middleware import TraceMiddleware
from app.api.observability import router as observability_router
from app.api.retrieve import router as retrieve_router
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging
from app.core.resilience import TokenBucketLimiter
from app.db.engine import create_engine
from app.orchestration.factory import build_services

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    app.state.engine = create_engine(settings)
    if settings.prewarm:
        try:
            app.state.services = await build_services(app.state.engine, settings)
            logger.info("预热完成")
        except (SQLAlchemyError, OSError, AppError, RuntimeError) as error:
            logger.warning("预热失败，等第一次请求再试：%r", error)
    try:
        yield
    finally:
        await app.state.engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="grounded_rag", lifespan=lifespan)
    app.state.services = None  # 没开预热或预热失败时，第一次请求再建
    app.state.services_lock = asyncio.Lock()
    app.state.limiter = TokenBucketLimiter(get_settings().rate_limit_per_minute)
    app.add_middleware(TraceMiddleware)
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(retrieve_router)
    app.include_router(chat_router)
    app.include_router(observability_router)
    return app
