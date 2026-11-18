"""Dify 1.19 Chatflow 应用 API 的流式传输。"""

import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.core.errors import DependencyUnavailableError

TIMEOUT_SECONDS = 90.0
MILLISECONDS_PER_SECOND = 1000.0
ANSWER_EVENTS = frozenset({"message", "agent_message", "message_replace"})
WORKFLOW_SUCCESS = frozenset({"succeeded", "partial-succeeded"})


class DifyRequest(BaseModel):
    """Dify 应用的对话请求。"""

    query: str
    user: str
    inputs: dict[str, str] = Field(default_factory=dict)
    conversation_id: str | None = None
    response_mode: Literal["streaming"] = "streaming"
    auto_generate_name: Literal[False] = False


class DifyNode(BaseModel):
    """Service API 返回的节点完成事件。"""

    node_id: str
    node_type: str
    status: str
    elapsed_time: float = Field(ge=0)
    inputs: dict[str, Any] | None = None
    outputs: dict[str, Any] | None = None
    outputs_truncated: bool = False

    @property
    def latency_ms(self) -> float:
        return self.elapsed_time * MILLISECONDS_PER_SECOND


class DifyTurn(BaseModel):
    """一次可完整消费的 Chatflow 回复。"""

    answer: str
    conversation_id: str
    latency_ms: float
    first_token_ms: float | None
    nodes: list[DifyNode]
    workflow_status: str | None
    workflow_run_id: str | None
    metadata: dict[str, Any]


class _Event(BaseModel):
    event: str
    answer: str = ""
    conversation_id: str | None = None
    workflow_run_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    data: dict[str, Any] = Field(default_factory=dict)


@dataclass
class _TurnState:
    parts: list[str] = field(default_factory=list)
    nodes: list[DifyNode] = field(default_factory=list)
    conversation_id: str | None = None
    workflow_run_id: str | None = None
    workflow_status: str | None = None
    first_token_ms: float | None = None

    def consume(self, event: _Event, elapsed: Callable[[], float]) -> DifyTurn | None:
        self.conversation_id = event.conversation_id or self.conversation_id
        self.workflow_run_id = event.workflow_run_id or self.workflow_run_id
        if event.event in ANSWER_EVENTS and event.answer:
            if self.first_token_ms is None:
                self.first_token_ms = elapsed()
            if event.event == "message_replace":
                self.parts.clear()
            self.parts.append(event.answer)
        if event.event == "node_finished":
            self.nodes.append(DifyNode.model_validate(event.data))
        if event.event == "workflow_finished":
            self.workflow_status = event.data.get("status")
            if self.workflow_status not in WORKFLOW_SUCCESS:
                raise DependencyUnavailableError("Dify 返回失败的工作流终态")
        if event.event == "error":
            raise DependencyUnavailableError("Dify 返回流式错误")
        if event.event != "message_end":
            return None
        if not self.conversation_id:
            raise DependencyUnavailableError("Dify 终态缺少会话 ID")
        return DifyTurn(
            answer="".join(self.parts),
            conversation_id=self.conversation_id,
            latency_ms=elapsed(),
            first_token_ms=self.first_token_ms,
            nodes=self.nodes,
            workflow_status=self.workflow_status,
            workflow_run_id=self.workflow_run_id,
            metadata=event.metadata,
        )


async def _events(response: httpx.Response) -> AsyncIterator[_Event]:
    response.encoding = "utf-8-sig"
    lines: list[str] = []
    async for line in response.aiter_lines():
        if not line and lines:
            yield _Event.model_validate_json("\n".join(lines))
            lines.clear()
        elif line == "data" or line.startswith("data:"):
            lines.append(line.partition(":")[2].removeprefix(" "))


class DifyClient:
    """发起一次应用请求，保留实际接收首段和终态的时间。"""

    def __init__(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        *,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._client = client
        self._api_key = api_key
        self._clock = clock

    async def chat(self, request: DifyRequest) -> DifyTurn:
        """读取到 message_end；错误或提前断开时保留失败状态。"""
        started = self._clock()
        state = _TurnState()

        def elapsed() -> float:
            return (self._clock() - started) * MILLISECONDS_PER_SECOND

        try:
            async with self._client.stream(
                "POST",
                "chat-messages",
                json=request.model_dump(exclude_none=True),
                headers={"Authorization": f"Bearer {self._api_key}", "Accept": "text/event-stream"},
            ) as response:
                if not response.is_success:
                    raise DependencyUnavailableError(f"Dify API 返回 HTTP {response.status_code}")
                async for event in _events(response):
                    if result := state.consume(event, elapsed):
                        return result
        except httpx.RequestError:
            raise DependencyUnavailableError("Dify API 请求中断") from None
        except ValidationError:
            raise DependencyUnavailableError("Dify API 返回无效的流式事件") from None
        raise DependencyUnavailableError("Dify 流在答复终态前结束")


@asynccontextmanager
async def dify_connection(base_url: str, api_key: str) -> AsyncIterator[DifyClient]:
    """为同一次串行回放复用 HTTP 连接。"""
    async with httpx.AsyncClient(
        base_url=base_url, timeout=TIMEOUT_SECONDS, trust_env=False
    ) as client:
        yield DifyClient(client, api_key)
