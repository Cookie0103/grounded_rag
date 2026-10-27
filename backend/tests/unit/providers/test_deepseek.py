import json
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.core.config import Settings
from app.core.errors import BudgetExceededError, ConfigError, DependencyUnavailableError
from app.providers.base import ChatMessage
from app.providers.budget import BudgetLedger
from app.providers.deepseek import DeepSeekChat, cost_cny
from app.providers.factory import get_chat_model
from app.providers.fakes import FakeChatModel

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
        seen.append({"headers": dict(request.headers), "body": json.loads(request.content)})
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    return httpx.MockTransport(handle), seen


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
