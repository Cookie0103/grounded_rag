"""Dify Chatflow 流式协议的本地测试。"""

import json
from collections.abc import AsyncIterator

import httpx
import pytest

from app.core.errors import DependencyUnavailableError
from app.providers.dify import DifyClient, DifyRequest


class _Stream(httpx.AsyncByteStream):
    def __init__(self, events: list[dict[str, object]]) -> None:
        self.events = events

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b"event: ping\r\n\r\n"
        for event in self.events:
            yield f"data: {json.dumps(event, ensure_ascii=False)}\r\n\r\n".encode()


@pytest.mark.asyncio
@pytest.mark.parametrize("workflow_finishes_first", [True, False])
async def test_chatflow_preserves_session_and_measures_stream_boundaries(
    workflow_finishes_first: bool,
) -> None:
    terminal_events: list[dict[str, object]] = [
        {"event": "workflow_finished", "data": {"status": "succeeded"}},
        {"event": "message_end", "metadata": {"final": True}, "conversation_id": "conversation"},
    ]
    if not workflow_finishes_first:
        terminal_events.reverse()
    events: list[dict[str, object]] = [
        {
            "event": "node_finished",
            "data": {
                "node_id": "intent",
                "node_type": "question-classifier",
                "outputs": {"class_name": "policy"},
                "elapsed_time": 0.2,
                "status": "succeeded",
            },
        },
        {"event": "message", "answer": "住宅ローン", "conversation_id": "conversation"},
        {"event": "message_replace", "answer": "住宅ローンのご案内です。"},
        *terminal_events,
    ]

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat-messages"
        assert request.headers["Authorization"] == "Bearer app-example"
        assert json.loads(request.content) == {
            "query": "手続きは？",
            "inputs": {"channel": "customer"},
            "user": "session",
            "conversation_id": "conversation",
            "response_mode": "streaming",
            "auto_generate_name": False,
        }
        return httpx.Response(200, stream=_Stream(events))

    times = iter((1.0, 1.25, 2.0))
    async with httpx.AsyncClient(
        base_url="http://localhost/v1", transport=httpx.MockTransport(respond)
    ) as http:
        result = await DifyClient(http, "app-example", clock=lambda: next(times)).chat(
            DifyRequest(
                query="手続きは？",
                inputs={"channel": "customer"},
                user="session",
                conversation_id="conversation",
            )
        )

    assert result.answer == "住宅ローンのご案内です。"
    assert result.conversation_id == "conversation"
    assert result.first_token_ms == 250
    assert result.latency_ms == 1000
    assert result.workflow_status == "succeeded"
    assert result.metadata == {"final": True}
    assert result.nodes[0].outputs == {"class_name": "policy"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "finish",
    [
        [],
        [{"event": "error", "message": "private"}],
        [{"event": "message_end", "conversation_id": "conversation"}],
        [
            {"event": "message_end", "conversation_id": "conversation"},
            {"event": "workflow_finished", "data": {"status": "failed"}},
        ],
    ],
)
async def test_incomplete_or_failed_stream_is_not_a_completed_answer(
    finish: list[dict[str, object]],
) -> None:
    def respond(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, stream=_Stream([{"event": "message", "answer": "途中"}, *finish])
        )

    async with httpx.AsyncClient(
        base_url="http://localhost/v1", transport=httpx.MockTransport(respond)
    ) as http:
        with pytest.raises(DependencyUnavailableError, match="Dify") as error:
            await DifyClient(http, "app-example").chat(
                DifyRequest(query="手続きは？", user="session")
            )
    assert "private" not in str(error.value)
