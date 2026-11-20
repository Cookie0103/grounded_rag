"""用独立的 Redis 连接验证 SSE 续推缓冲。"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import aclosing
from dataclasses import dataclass
from hashlib import sha256
from uuid import uuid4

import pytest
from redis.asyncio import Redis

from app.core.config import Settings
from app.core.errors import ReplayExpiredError
from app.db.chat_replay import RedisChatReplay, ReplayFrame

pytestmark = pytest.mark.integration

_RESPONSE_ID = "synthetic-response"
_SYNTHETIC_TEXT = (
    "synthetic: 合成の住宅ローン案内です。固定金利と変動金利の条件は、商品説明書をご確認ください。"
    * 3
)


@dataclass(frozen=True)
class ReplayRuntime:
    writer: RedisChatReplay
    reader: RedisChatReplay
    redis: Redis
    key: str


@pytest.fixture
async def replay_runtime(request: pytest.FixtureRequest) -> AsyncIterator[ReplayRuntime]:
    url = Settings().redis_url
    prefix = f"grounded-rag:it:replay:{uuid4().hex}:"
    ttl_seconds: int | None = getattr(request, "param", None)
    if ttl_seconds is None:
        writer = RedisChatReplay(url, key_prefix=prefix)
    else:
        writer = RedisChatReplay(url, ttl_seconds=ttl_seconds, key_prefix=prefix)
    reader = RedisChatReplay(url, heartbeat_ms=25, key_prefix=prefix)
    redis = Redis.from_url(url, socket_timeout=2)
    key = prefix + _RESPONSE_ID
    try:
        yield ReplayRuntime(writer, reader, redis, key)
    finally:
        await writer.close()
        await reader.close()
        try:
            await redis.delete(key)
        finally:
            await redis.aclose()


async def _publish(replay: RedisChatReplay) -> None:
    await replay.start(_RESPONSE_ID)
    await replay.append(_RESPONSE_ID, "step", {"response_id": _RESPONSE_ID})
    for char in _SYNTHETIC_TEXT:
        await replay.append(_RESPONSE_ID, "delta", {"text": char})
    await replay.append(_RESPONSE_ID, "answer", {"text": _SYNTHETIC_TEXT}, terminal=True)


async def _read_frames(replay: RedisChatReplay, last_id: int = 0) -> list[ReplayFrame]:
    async with asyncio.timeout(3), aclosing(replay.replay(_RESPONSE_ID, last_id)) as stream:
        return [frame async for frame in stream if frame is not None]


def _join_deltas(frames: list[ReplayFrame]) -> str:
    return "".join(str(frame.payload["text"]) for frame in frames if frame.event == "delta")


async def test_replay_matches_uninterrupted_stream_at_fifty_random_breakpoints(
    replay_runtime: ReplayRuntime,
) -> None:
    await _publish(replay_runtime.writer)
    baseline = await _read_frames(replay_runtime.writer)

    assert baseline[0] == ReplayFrame(1, "step", {"response_id": _RESPONSE_ID})
    assert _join_deltas(baseline) == _SYNTHETIC_TEXT
    assert [frame.id for frame in baseline] == list(range(1, len(baseline) + 1))
    assert await _read_frames(replay_runtime.reader, baseline[-1].id) == []

    breakpoints = sorted(
        range(len(baseline) + 1), key=lambda index: sha256(f"35:{index}".encode()).digest()
    )[:50]
    for stop in breakpoints:
        async with aclosing(replay_runtime.writer.replay(_RESPONSE_ID)) as stream:
            prefix = [await anext(stream) for _ in range(stop)]
        last_id = baseline[stop - 1].id if stop else 0
        remainder = await _read_frames(replay_runtime.reader, last_id)
        assert prefix + remainder == baseline


async def test_overlapping_reconnect_deduplicates_by_sequence_number(
    replay_runtime: ReplayRuntime,
) -> None:
    await _publish(replay_runtime.writer)
    baseline = await _read_frames(replay_runtime.writer)
    received = baseline[:15] + await _read_frames(replay_runtime.reader, 10)
    deduplicated = list({frame.id: frame for frame in received}.values())

    assert len(received) == len(baseline) + 5
    assert deduplicated == baseline
    assert _join_deltas(deduplicated) == _SYNTHETIC_TEXT


async def test_replay_heartbeats_then_follows_an_active_stream(
    replay_runtime: ReplayRuntime,
) -> None:
    writer, reader = replay_runtime.writer, replay_runtime.reader
    await writer.start(_RESPONSE_ID)
    assert await reader.exists(_RESPONSE_ID)

    async with asyncio.timeout(3), aclosing(reader.replay(_RESPONSE_ID)) as stream:
        assert await anext(stream) is None
        await writer.append(_RESPONSE_ID, "delta", {"text": "synthetic"})
        assert await anext(stream) == ReplayFrame(1, "delta", {"text": "synthetic"})
        assert await anext(stream) is None
        await writer.append(_RESPONSE_ID, "error", {}, terminal=True)
        assert await anext(stream) == ReplayFrame(2, "error", {})
        assert [frame async for frame in stream] == []


async def test_concurrent_append_keeps_unique_contiguous_ids(replay_runtime: ReplayRuntime) -> None:
    writer, reader = replay_runtime.writer, replay_runtime.reader
    await writer.start(_RESPONSE_ID)
    await asyncio.gather(
        *(writer.append(_RESPONSE_ID, "delta", {"index": index}) for index in range(32))
    )
    await writer.append(_RESPONSE_ID, "answer", {}, terminal=True)
    frames = await _read_frames(reader)

    assert [frame.id for frame in frames] == list(range(1, 34))
    assert {frame.payload["index"] for frame in frames[:-1]} == set(range(32))


async def test_completion_sets_default_retention_for_entire_buffer(
    replay_runtime: ReplayRuntime,
) -> None:
    writer, raw, key = replay_runtime.writer, replay_runtime.redis, replay_runtime.key
    await writer.start(_RESPONSE_ID)
    await writer.append(_RESPONSE_ID, "delta", {"text": "synthetic"})
    assert await raw.pttl(key) > 120_000

    await writer.append(_RESPONSE_ID, "answer", {}, terminal=True)

    assert 119_000 < await raw.pttl(key) <= 120_000
    assert [frame.event for frame in await _read_frames(replay_runtime.reader)] == [
        "delta",
        "answer",
    ]


async def test_duplicate_start_preserves_terminal_history(replay_runtime: ReplayRuntime) -> None:
    writer, reader = replay_runtime.writer, replay_runtime.reader
    await writer.start(_RESPONSE_ID)
    await writer.append(_RESPONSE_ID, "answer", {}, terminal=True)
    retention_before = await replay_runtime.redis.pttl(replay_runtime.key)

    await reader.start(_RESPONSE_ID)
    with pytest.raises(ValueError, match="已经终止"):
        await writer.append(_RESPONSE_ID, "delta", {})

    assert await replay_runtime.redis.pttl(replay_runtime.key) <= retention_before
    assert await _read_frames(reader) == [ReplayFrame(1, "answer", {})]


@pytest.mark.parametrize("replay_runtime", [1], indirect=True)
async def test_redis_expires_completed_history(replay_runtime: ReplayRuntime) -> None:
    writer, reader = replay_runtime.writer, replay_runtime.reader
    await writer.start(_RESPONSE_ID)
    await writer.append(_RESPONSE_ID, "answer", {}, terminal=True)
    assert await reader.exists(_RESPONSE_ID)

    await asyncio.sleep(1.05)
    assert not await reader.exists(_RESPONSE_ID)

    with pytest.raises(ReplayExpiredError):
        await _read_frames(reader)
    with pytest.raises(ReplayExpiredError):
        await writer.append(_RESPONSE_ID, "delta", {})
