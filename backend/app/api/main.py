"""FastAPI 应用入口：`uvicorn app.api.main:create_app --factory`。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.health import router as health_router
from app.api.middleware import TraceMiddleware
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.engine import create_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    app.state.engine = create_engine(settings)
    try:
        yield
    finally:
        await app.state.engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="grounded_rag", lifespan=lifespan)
    app.add_middleware(TraceMiddleware)
    register_error_handlers(app)
    app.include_router(health_router)
    return app
