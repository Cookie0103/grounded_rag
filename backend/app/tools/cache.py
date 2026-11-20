"""只缓存已经裁剪的工具结果。"""

import asyncio
import time
from collections.abc import Callable
from typing import Protocol

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.cache import TtlCache

DEFAULT_TTL_SECONDS = 5
REDIS_TIMEOUT_SECONDS = 0.2
MEMORY_MAX_ENTRIES = 1024


class ToolCache(Protocol):
    async def get(self, key: str) -> str | None:
        """读取已裁剪的序列化结果。"""

    async def set(self, key: str, value: str) -> None:
        """在短期内复用已裁剪的序列化结果。"""


class RedisToolCache:
    def __init__(
        self,
        url: str,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        *,
        key_prefix: str = "grounded-rag:tools:v1:",
    ) -> None:
        self._client = Redis.from_url(url, decode_responses=True)
        self._prefix = key_prefix
        self._ttl = ttl_seconds

    async def get(self, key: str) -> str | None:
        """Redis 暂时不可用时按未命中处理。"""
        try:
            async with asyncio.timeout(REDIS_TIMEOUT_SECONDS):
                value = await self._client.get(self._prefix + key)
        except (RedisError, TimeoutError):
            return None
        return value if isinstance(value, str) else None

    async def set(self, key: str, value: str) -> None:
        """写入带过期时间的结果，避免缓存故障丢掉已有业务结果。"""
        try:
            async with asyncio.timeout(REDIS_TIMEOUT_SECONDS):
                await self._client.set(self._prefix + key, value, ex=self._ttl)
        except (RedisError, TimeoutError):
            return

    async def aclose(self) -> None:
        """释放 Redis 连接池。"""
        await self._client.aclose()


class MemoryToolCache:
    def __init__(
        self, ttl_seconds: int = DEFAULT_TTL_SECONDS, *, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._cache = TtlCache[str, str](MEMORY_MAX_ENTRIES, ttl_seconds, clock)

    async def get(self, key: str) -> str | None:
        """从进程内存读缓存。"""
        return self._cache.get(key)

    async def set(self, key: str, value: str) -> None:
        """将已裁剪结果存入进程内存。"""
        self._cache.put(key, value)
