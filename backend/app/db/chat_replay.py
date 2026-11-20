"""将 SSE 事件保存在 Redis，以便断线重连后按序续推。"""

import asyncio
import json
from collections.abc import AsyncGenerator, Awaitable
from dataclasses import dataclass

from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
from redis.exceptions import RedisError

from app.core.errors import DependencyUnavailableError, ReplayExpiredError

_ACTIVE_TTL_SECONDS = 3600
_REDIS_TIMEOUT_SECONDS = 2
_READ_BATCH_SIZE = 128
_MAX_FRAME_ID = 2**64 - 2

# 0-1 标记已创建的流。Redis 分配后续的 0-* 序号，SSE 序号从 1 起。
_START = """
if redis.call('EXISTS', KEYS[1]) == 0 then
    redis.call('XADD', KEYS[1], '0-1', 'terminal', '0')
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
"""

_APPEND = """
local last = redis.call('XREVRANGE', KEYS[1], '+', '-', 'COUNT', 1)
if #last == 0 then
    return 0
end
if last[1][2][2] == '1' then
    return -1
end
redis.call('XADD', KEYS[1], '0-*', 'terminal', ARGV[1], 'event', ARGV[2], 'payload', ARGV[3])
redis.call('EXPIRE', KEYS[1], ARGV[4])
return 1
"""

type _Entry = tuple[str, dict[str, str]]


@dataclass(frozen=True)
class ReplayFrame:
    """带响应内序号的单个 SSE 事件。"""

    id: int
    event: str
    payload: dict[str, object]


class RedisChatReplay:
    """使用单键 Redis Stream 保存一个响应的全部事件。"""

    def __init__(
        self,
        url: str,
        *,
        ttl_seconds: int = 120,
        heartbeat_ms: int = 15000,
        key_prefix: str = "grounded-rag:chat-replay:v1:",
    ) -> None:
        if ttl_seconds <= 0 or heartbeat_ms <= 0:
            raise ValueError("续推保留时间和心跳间隔必须大于零")
        # 响应丢失时重试 XADD 可能重复写入同一事件。
        self._redis = Redis.from_url(
            url, decode_responses=True, protocol=2, retry=Retry(NoBackoff(), 0)
        )
        self._key_prefix = key_prefix
        self._ttl_seconds = ttl_seconds
        self._heartbeat_ms = heartbeat_ms
        self._start = self._redis.register_script(_START)
        self._append = self._redis.register_script(_APPEND)

    async def start(self, response_id: str) -> None:
        """创建可跟随的响应，供首个事件到来前的读者等待。"""
        await _redis_call(
            self._start(keys=[self._key_prefix + response_id], args=[_ACTIVE_TTL_SECONDS])
        )

    async def append(
        self,
        response_id: str,
        event: str,
        payload: dict[str, object],
        *,
        terminal: bool = False,
    ) -> None:
        """写入下一个事件，终止事件同时开始计算完整缓冲的有效期。"""
        ttl_seconds = self._ttl_seconds if terminal else _ACTIVE_TTL_SECONDS
        result = await _redis_call(
            self._append(
                keys=[self._key_prefix + response_id],
                args=[int(terminal), event, json.dumps(payload, ensure_ascii=False), ttl_seconds],
            )
        )
        if result == 0:
            raise ReplayExpiredError("流式响应缓冲已过期")
        if result == -1:
            raise ValueError("流式响应已经终止")

    async def exists(self, response_id: str) -> bool:
        """检查响应是否拥有可续推的缓冲。"""
        return bool(await _redis_call(self._redis.exists(self._key_prefix + response_id)))

    async def replay(
        self, response_id: str, last_id: int = 0
    ) -> AsyncGenerator[ReplayFrame | None]:
        """从最后接收序号之后补发和跟随，空闲时产出一次心跳。"""
        key = self._key_prefix + response_id
        last_id = max(0, min(last_id, _MAX_FRAME_ID))
        if await self._is_at_end(key, last_id):
            return
        cursor = f"0-{last_id + 1}"
        while True:
            streams: list[tuple[str, list[_Entry]]] = await _redis_call(
                self._redis.xread({key: cursor}, count=_READ_BATCH_SIZE, block=self._heartbeat_ms),
                timeout_seconds=_REDIS_TIMEOUT_SECONDS + self._heartbeat_ms / 1000,
            )
            if not streams:
                if await self._is_at_end(key, last_id):
                    return
                yield None
                continue
            for cursor, fields in streams[0][1]:
                last_id = _frame_id(cursor)
                yield ReplayFrame(last_id, fields["event"], json.loads(fields["payload"]))
                if fields["terminal"] == "1":
                    return

    async def close(self) -> None:
        """释放 Redis 连接池。"""
        await _redis_call(self._redis.aclose())

    async def _is_at_end(self, key: str, last_id: int) -> bool:
        entries: list[_Entry] = await _redis_call(self._redis.xrevrange(key, count=1))
        if not entries:
            raise ReplayExpiredError("流式响应缓冲已过期")
        cursor, fields = entries[0]
        return fields["terminal"] == "1" and _frame_id(cursor) <= last_id


def _frame_id(cursor: str) -> int:
    return int(cursor.split("-", maxsplit=1)[1]) - 1


async def _redis_call[T](
    command: Awaitable[T], *, timeout_seconds: float = _REDIS_TIMEOUT_SECONDS
) -> T:
    try:
        async with asyncio.timeout(timeout_seconds):
            return await command
    except (RedisError, TimeoutError) as error:
        raise DependencyUnavailableError("Redis 流式响应缓冲不可用") from error
