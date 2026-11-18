"""让 SSE 订阅和问答生产任务拥有独立的生命周期。"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from fastapi.responses import StreamingResponse

from app.core.errors import ReplayExpiredError
from app.db.chat_replay import ReplayFrame

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OutgoingEvent:
    name: str
    payload: dict[str, object]


class ReplayStore(Protocol):
    async def start(self, response_id: str) -> None: ...

    async def append(
        self,
        response_id: str,
        event: str,
        payload: dict[str, object],
        *,
        terminal: bool = False,
    ) -> None: ...

    async def exists(self, response_id: str) -> bool: ...

    def replay(self, response_id: str, last_id: int = 0) -> AsyncIterator[ReplayFrame | None]: ...

    async def close(self) -> None: ...


class ChatStreams:
    def __init__(self, store: ReplayStore) -> None:
        self._store = store
        self._active: set[asyncio.Task[None]] = set()

    async def start(self, events: AsyncIterator[OutgoingEvent]) -> StreamingResponse:
        response_id = uuid4().hex
        await self._store.start(response_id)
        producer = asyncio.create_task(self._produce(response_id, events))
        self._active.add(producer)
        producer.add_done_callback(self._finished)
        return self._response(response_id, 0)

    async def resume(self, response_id: str, last_id: int) -> StreamingResponse:
        if not await self._store.exists(response_id):
            raise ReplayExpiredError("流式响应的续推缓冲已过期")
        return self._response(response_id, last_id)

    def _response(self, response_id: str, last_id: int) -> StreamingResponse:
        return StreamingResponse(
            self._subscribe(response_id, last_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "X-Response-Id": response_id,
            },
        )

    async def _produce(self, response_id: str, events: AsyncIterator[OutgoingEvent]) -> None:
        async for event in events:
            terminal = event.name in {"answer", "error"}
            await self._store.append(
                response_id,
                event.name,
                {**event.payload, "response_id": response_id},
                terminal=terminal,
            )
            if terminal:
                return
        await self._store.append(
            response_id,
            "error",
            {"response_id": response_id, "code": "INTERNAL_ERROR", "message": "流式响应未完成"},
            terminal=True,
        )

    async def _subscribe(self, response_id: str, last_id: int) -> AsyncIterator[str]:
        try:
            async for frame in self._store.replay(response_id, last_id):
                if frame is None:
                    yield ": heartbeat\n\n"
                else:
                    payload = json.dumps(frame.payload, ensure_ascii=False)
                    yield f"id: {frame.id}\nevent: {frame.event}\ndata: {payload}\n\n"
        except ReplayExpiredError:
            # 订阅响应已发出时无法再改变 HTTP 状态码，重连会收到 410。
            return

    def _finished(self, producer: asyncio.Task[None]) -> None:
        self._active.discard(producer)
        if not producer.cancelled() and (error := producer.exception()) is not None:
            logger.error("流式生产任务终止：%s", type(error).__name__)

    async def close(self) -> None:
        producers = list(self._active)
        for producer in producers:
            producer.cancel()
        await asyncio.gather(*producers, return_exceptions=True)
        await self._store.close()
