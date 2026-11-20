import json
from collections.abc import AsyncIterator
from datetime import date
from math import log
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.core.config import Settings
from app.core.errors import BudgetExceededError, ConfigError, DependencyUnavailableError
from app.providers.base import (
    ChatDelta,
    ChatMessage,
    ChatTier,
    Completion,
    FunctionCall,
    FunctionTool,
    StreamingChatModel,
)
from app.providers.budget import BudgetLedger
from app.providers.deepseek import DeepSeekChat, cost_cny
from app.providers.factory import get_chat_model
from app.providers.fakes import FakeChatModel
from app.providers.gateway import GatewayChat

MESSAGES = [ChatMessage(role="user", content="你好")]
OK = {
    "model": "deepseek-flash",
    "choices": [{"message": {"content": "你好！"}}],
    "usage": {"prompt_tokens": 1000, "completion_tokens": 500},
}


def _chat(
    handler: httpx.MockTransport | None = None,
    *,
    ledger: BudgetLedger | None = None,
    api_key: str | None = "sk-test",
) -> DeepSeekChat:
    client = httpx.AsyncClient(base_url="https://x", transport=handler)
    return DeepSeekChat(
        api_key=api_key,
        base_url="https://x",
        model="deepseek-flash",
        ledger=ledger,
        client=client,
        retry_delay_seconds=0,
    )


def _transport(
    *responses: httpx.Response | Exception,
) -> tuple[httpx.MockTransport, list[dict[str, Any]]]:
    queue = list(responses)
    seen: list[dict[str, Any]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(
            {
                "headers": dict(request.headers),
                "body": json.loads(request.content),
                "method": request.method,
                "path": request.url.path,
            }
        )
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    return httpx.MockTransport(handle), seen


class _Stream(httpx.AsyncByteStream):
    def __init__(self, *chunks: bytes | httpx.TransportError) -> None:
        self._chunks = chunks
        self.read_count = 0
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self._chunks:
            self.read_count += 1
            if isinstance(chunk, httpx.TransportError):
                raise chunk
            yield chunk

    async def aclose(self) -> None:
        self.closed = True


def _sse_data(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\r\n\r\n".encode()


async def test_gateway_streams_visible_text_then_reports_usage(tmp_path: Path) -> None:
    first = b': keepalive\r\n\r\ndata: {"choices":\r\ndata: [{"delta":{"content":"'
    first += 'ご案内"}}]}\r\n\r\n'.encode()
    split = first.index("ご".encode()) + 1
    upstream = _Stream(
        _sse_data({"choices": [{"delta": {"role": "assistant", "reasoning_content": "非公開"}}]}),
        first[:split],
        first[split:],
        _sse_data({"choices": [{"delta": {"content": "します。"}}], "usage": None}),
        _sse_data({"choices": [{"delta": {}, "finish_reason": "stop"}]}),
        _sse_data(
            {
                "model": "upstream",
                "choices": [],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            }
        ),
        b"data: [DONE]\r\n\r\n",
    )
    transport, seen = _transport(httpx.Response(200, stream=upstream))
    ledger = BudgetLedger(tmp_path, daily_limit_cny=10)
    async with httpx.AsyncClient(base_url="http://gateway/v1", transport=transport) as client:
        chat = GatewayChat(
            api_key="key",
            base_url="http://gateway/v1",
            model="deepseek-v4-pro",
            ledger=ledger,
            client=client,
        )
        assert isinstance(chat, StreamingChatModel)
        stream = chat.stream(MESSAGES)
        assert await anext(stream) == ChatDelta(text="ご案内")
        assert upstream.read_count == 3
        assert ledger.spent() == 0
        rest = [item async for item in stream]

    assert seen[0]["method"] == "POST"
    assert seen[0]["path"] == "/v1/chat/completions"
    assert seen[0]["headers"]["authorization"] == "Bearer key"
    assert seen[0]["body"]["stream"] is True
    assert seen[0]["body"]["stream_options"] == {"include_usage": True}
    assert len(rest) == 2
    assert rest[0] == ChatDelta(text="します。")
    completion = rest[1]
    assert isinstance(completion, Completion)
    assert completion.text == "ご案内します。"
    assert completion.model == "upstream"
    assert (completion.prompt_tokens, completion.completion_tokens) == (100, 50)
    assert completion.cost_cny == pytest.approx(0.002376)
    assert ledger.spent() == pytest.approx(0.002376)
    assert upstream.closed


@pytest.mark.parametrize("usage", [None, {"prompt_tokens": 0, "completion_tokens": 0}])
async def test_stream_never_estimates_usage_from_text(
    usage: dict[str, int] | None, tmp_path: Path
) -> None:
    response = httpx.Response(
        200,
        content=(
            _sse_data({"choices": [{"delta": {"content": "確認しました。"}}], "usage": usage})
            + b"data: [DONE]\n\n"
        ),
    )
    transport, _ = _transport(response)
    ledger = BudgetLedger(tmp_path, daily_limit_cny=10)

    events = [event async for event in _chat(transport, ledger=ledger).stream(MESSAGES)]

    assert len(events) == 2
    completion = events[-1]
    assert isinstance(completion, Completion)
    assert (completion.prompt_tokens, completion.completion_tokens) == (0, 0)
    assert completion.cost_cny == (None if usage is None else 0.0)
    assert ledger.spent() == 0


@pytest.mark.parametrize(
    "failure",
    [
        b"",
        b"data: {invalid}\n\n",
        _sse_data({"error": {"message": "非公開"}}),
        httpx.ReadTimeout("slow"),
    ],
)
async def test_interrupted_stream_closes_without_reissuing_the_request(
    failure: bytes | httpx.TransportError, tmp_path: Path
) -> None:
    upstream = _Stream(_sse_data({"choices": [{"delta": {"content": "受付"}}]}), failure)
    transport, seen = _transport(httpx.Response(200, stream=upstream))
    ledger = BudgetLedger(tmp_path, daily_limit_cny=10)
    stream = _chat(transport, ledger=ledger).stream(MESSAGES)

    assert await anext(stream) == ChatDelta(text="受付")
    with pytest.raises(DependencyUnavailableError, match="DeepSeek"):
        await anext(stream)

    assert len(seen) == 1
    assert upstream.closed
    assert ledger.spent() == 0


async def test_interrupted_stream_records_usage_when_already_reported(tmp_path: Path) -> None:
    upstream = _Stream(
        _sse_data({"choices": [], "usage": {"prompt_tokens": 1000, "completion_tokens": 500}}),
        httpx.ReadTimeout("slow"),
    )
    transport, seen = _transport(httpx.Response(200, stream=upstream))
    ledger = BudgetLedger(tmp_path, daily_limit_cny=10)

    with pytest.raises(DependencyUnavailableError):
        await anext(_chat(transport, ledger=ledger).stream(MESSAGES))

    assert len(seen) == 1
    assert ledger.spent() == pytest.approx(0.00648)
    assert upstream.closed


async def test_stream_checks_remaining_budget_before_request(tmp_path: Path) -> None:
    transport, seen = _transport()
    ledger = BudgetLedger(tmp_path, daily_limit_cny=1)
    ledger.add(1)

    with pytest.raises(BudgetExceededError):
        await anext(_chat(transport, ledger=ledger).stream(MESSAGES))

    assert not seen


async def test_successful_call_returns_text_tokens_and_sends_expected_request() -> None:
    transport, seen = _transport(httpx.Response(200, json=OK))

    completion = await _chat(transport).complete(MESSAGES, json_mode=True)

    assert completion.text == "你好！"
    assert (completion.prompt_tokens, completion.completion_tokens) == (1000, 500)
    request = seen[0]
    assert request["headers"]["authorization"] == "Bearer sk-test"
    assert request["body"]["temperature"] == 0
    assert request["body"]["response_format"] == {"type": "json_object"}
    assert request["body"]["messages"] == [{"role": "user", "content": "你好"}]


async def test_plain_call_has_no_response_format() -> None:
    transport, seen = _transport(httpx.Response(200, json=OK))

    await _chat(transport).complete(MESSAGES)

    assert "response_format" not in seen[0]["body"]
    assert "tools" not in seen[0]["body"]
    assert "logprobs" not in seen[0]["body"]


async def test_function_call_round_trips_schema_arguments_and_usage(tmp_path: Path) -> None:
    function = {
        "name": "get_payment",
        "description": "返済額を照会する",
        "parameters": {
            "type": "object",
            "properties": {"month": {"type": "string"}},
            "required": ["month"],
            "additionalProperties": False,
        },
    }
    returned = {
        "id": "call_1",
        "type": "function",
        "function": {"name": "get_payment", "arguments": '{"month":"2026-12"}'},
    }
    payload = {**OK, "choices": [{"message": {"content": None, "tool_calls": [returned]}}]}
    transport, seen = _transport(httpx.Response(200, json=payload))
    ledger = BudgetLedger(tmp_path, daily_limit_cny=1)

    result = await _chat(transport, ledger=ledger).complete(
        MESSAGES, tools=[FunctionTool.model_validate(function)]
    )

    assert seen[0]["body"]["tools"] == [{"type": "function", "function": function}]
    assert result.text == ""
    assert result.tool_calls == [FunctionCall(name="get_payment", arguments='{"month":"2026-12"}')]
    assert (result.prompt_tokens, result.completion_tokens) == (1000, 500)
    assert ledger.spent() == pytest.approx(cost_cny(1000, 500))


async def test_classification_confidence_uses_only_tokens_overlapping_intent_value() -> None:
    tokens = [
        {"token": '{"intent', "logprob": 0},
        {"token": '":"in', "logprob": log(0.8)},
        {"token": 'quiry"', "logprob": log(0.6)},
        {"token": ',"secondary_intent":"policy"}', "logprob": log(0.2)},
    ]
    payload = {
        **OK,
        "choices": [
            {
                "message": {"content": '{"intent":"inquiry","secondary_intent":"policy"}'},
                "logprobs": {"content": tokens},
            },
        ],
    }
    transport, seen = _transport(httpx.Response(200, json=payload))

    result = await _chat(transport).complete(MESSAGES, json_mode=True, logprobs=True)

    assert seen[0]["body"]["logprobs"] is True
    assert result.confidence == pytest.approx(0.48)


@pytest.mark.parametrize(
    "logprob_content",
    [
        None,
        [],
        [{"token": '{"intent":"policy"}', "logprob": 0.0}],
        [{"token": '{"intent":"inquiry"}', "logprob": -9999.0}],
    ],
)
async def test_confidence_is_unavailable_without_aligned_logprobs(
    logprob_content: list[dict[str, Any]] | None,
) -> None:
    payload = {
        **OK,
        "choices": [
            {
                "message": {"content": '{"intent":"inquiry"}'},
                "logprobs": {"content": logprob_content},
            },
        ],
    }
    transport, _ = _transport(httpx.Response(200, json=payload))

    result = await _chat(transport).complete(MESSAGES, json_mode=True, logprobs=True)

    assert result.confidence is None


async def test_retries_rate_limits_and_server_errors_then_succeeds() -> None:
    transport, seen = _transport(
        httpx.Response(429), httpx.Response(503), httpx.Response(200, json=OK)
    )

    completion = await _chat(transport).complete(MESSAGES)

    assert completion.text == "你好！"
    assert len(seen) == 3


async def test_gives_up_after_the_retries() -> None:
    transport, seen = _transport(*[httpx.Response(500)] * 3)

    with pytest.raises(DependencyUnavailableError, match="500"):
        await _chat(transport).complete(MESSAGES)

    assert len(seen) == 3


async def test_client_errors_are_not_retried() -> None:
    transport, seen = _transport(httpx.Response(401, text="bad key"))

    with pytest.raises(DependencyUnavailableError, match="401"):
        await _chat(transport).complete(MESSAGES)

    assert len(seen) == 1


async def test_network_failures_are_retried_and_then_reported() -> None:
    error = httpx.ConnectTimeout("slow")
    transport, seen = _transport(error, httpx.Response(200, json=OK))
    assert (await _chat(transport).complete(MESSAGES)).text == "你好！"

    transport, seen = _transport(error, error, error)
    with pytest.raises(DependencyUnavailableError, match="不可用"):
        await _chat(transport).complete(MESSAGES)
    assert len(seen) == 3


async def test_missing_key_is_a_config_error() -> None:
    with pytest.raises(ConfigError, match="DEEPSEEK_API_KEY"):
        await _chat(api_key=None).complete(MESSAGES)


def test_cost_uses_the_configured_prices() -> None:
    assert cost_cny(1_000_000, 0) == pytest.approx(0.3 * 7.2)
    assert cost_cny(0, 1_000_000) == pytest.approx(1.2 * 7.2)


async def test_calls_are_billed_and_stop_when_the_budget_is_used_up(tmp_path: Path) -> None:
    ledger = BudgetLedger(tmp_path, daily_limit_cny=0.005)
    transport, seen = _transport(httpx.Response(200, json=OK), httpx.Response(200, json=OK))
    chat = _chat(transport, ledger=ledger)

    await chat.complete(MESSAGES)
    assert ledger.spent() == pytest.approx(cost_cny(1000, 500))
    with pytest.raises(BudgetExceededError):
        await chat.complete(MESSAGES)

    assert len(seen) == 1


def test_ledger_resets_each_day_and_zero_means_unlimited(tmp_path: Path) -> None:
    today = [date(2026, 10, 16)]
    ledger = BudgetLedger(tmp_path, 1.0, today=lambda: today[0])
    ledger.add(2.0)
    with pytest.raises(BudgetExceededError):
        ledger.check()

    today[0] = date(2026, 10, 17)
    ledger.check()
    assert ledger.spent() == 0.0

    unlimited = BudgetLedger(tmp_path, 0.0, today=lambda: today[0])
    unlimited.add(999)
    unlimited.check()


def test_corrupt_ledger_file_starts_from_zero(tmp_path: Path) -> None:
    ledger = BudgetLedger(tmp_path, 1.0, today=lambda: date(2026, 10, 16))
    (tmp_path / "2026-10-16.json").write_text("not json", encoding="utf-8")

    assert ledger.spent() == 0.0


def test_factory_picks_the_chat_model(tmp_path: Path) -> None:
    assert isinstance(get_chat_model(Settings(chat_model="fake")), FakeChatModel)
    assert isinstance(get_chat_model(Settings(chat_model="deepseek")), DeepSeekChat)
    with pytest.raises(ConfigError):
        get_chat_model(Settings(chat_model="gpt"))


@pytest.mark.parametrize(
    ("tier", "alias", "expected_cost"),
    [
        ("small", "small", 0.0),
        ("large", "deepseek-v4-pro", (1000 * 1.32 + 500 * 3.96) * 7.2 / 1_000_000),
    ],
)
async def test_gateway_routes_by_tier_and_records_only_paid_usage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tier: ChatTier,
    alias: str,
    expected_cost: float,
) -> None:
    transport, seen = _transport(httpx.Response(200, json=OK))
    client = httpx.AsyncClient(base_url="http://gateway/v1", transport=transport)
    monkeypatch.setattr("app.providers.factory.CACHE_DIR", tmp_path)
    model = get_chat_model(
        Settings(chat_model="gateway", gateway_api_key="local-key"),
        tier=tier,
        client=client,
    )

    completion = await model.complete(MESSAGES, json_mode=True, logprobs=True)

    assert seen[0]["headers"]["authorization"] == "Bearer local-key"
    assert seen[0]["body"]["model"] == alias
    assert seen[0]["body"]["response_format"] == {"type": "json_object"}
    assert ("logprobs" in seen[0]["body"]) == (tier == "large")
    assert completion.confidence is None
    assert (completion.prompt_tokens, completion.completion_tokens) == (1000, 500)
    assert completion.cost_cny == pytest.approx(expected_cost)
    assert BudgetLedger(tmp_path / "budget", daily_limit_cny=10).spent() == pytest.approx(
        expected_cost
    )
