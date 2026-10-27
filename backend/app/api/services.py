"""请求里取服务、限流。服务第一次用到（或启动预热）时才建：读库建索引、加载模型要几十秒。"""

from fastapi import Request
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.errors import DependencyUnavailableError, RateLimitedError
from app.orchestration.factory import Services, build_services


async def get_services(request: Request) -> Services:
    state = request.app.state
    if state.services is None:
        async with state.services_lock:
            if state.services is None:
                try:
                    state.services = await build_services(state.engine, get_settings())
                except (SQLAlchemyError, OSError) as error:
                    raise DependencyUnavailableError("服务初始化失败：数据库不可用") from error
    services: Services = state.services
    return services


async def enforce_rate_limit(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    if not request.app.state.limiter.allow(client):
        raise RateLimitedError("请求太频繁，请稍后再试")
