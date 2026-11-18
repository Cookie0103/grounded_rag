from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import uuid4

import httpx
import pytest

from app.core.config import Settings
from app.orchestration.models import Step, tool_trace_step
from app.providers.mock_core import MockCoreClient
from app.tools.cache import RedisToolCache
from app.tools.middleware import ToolContext, ToolRunner

pytestmark = pytest.mark.integration

_OWNER = ToolContext(agent_id="A001", customer_id="C0001")
_OTHER_OWNER = ToolContext(agent_id="A020", customer_id="C0001")
_OUTSIDER = ToolContext(agent_id="A002", customer_id="C0001")
_CONTRACT = {"contract_id": "L0001"}
_PATHS = ("/loan-contracts", "/repayment-schedule", "/delinquency", "/rate-terms", "/benefits")


@dataclass(frozen=True)
class Runtime:
    runner: ToolRunner
    raw: httpx.AsyncClient
    steps: list[Step]


@pytest.fixture
async def tools_runtime() -> AsyncIterator[Runtime]:
    settings = Settings()
    cache = RedisToolCache(settings.redis_url, key_prefix=f"grounded-rag:it:{uuid4().hex}:")
    steps: list[Step] = []
    async with httpx.AsyncClient(base_url=settings.mock_core_base_url, timeout=8) as raw:
        client = MockCoreClient(settings.mock_core_base_url, client=raw)
        try:
            runner = ToolRunner(
                client, cache, recorder=lambda entry: steps.append(tool_trace_step(entry))
            )
            yield Runtime(runner, raw, steps)
        finally:
            await client.aclose()
            await cache.aclose()


async def test_mock_api_requires_agent_for_all_read_only_endpoints(tools_runtime: Runtime) -> None:
    for path in _PATHS:
        params = {"customer_id": "C0001", "contract_id": "L0001"}
        response = await tools_runtime.raw.get(path, params=params)
        assert response.status_code == 401
        assert (await tools_runtime.raw.post(path, params=params)).status_code == 405


async def test_all_five_queries_are_synthetic_and_exclude_sensitive_db_fields(
    tools_runtime: Runtime,
) -> None:
    runner = tools_runtime.runner
    results = [
        await runner.call("query_loan_contracts", _OWNER, {}),
        await runner.call("query_repayment_schedule", _OWNER, _CONTRACT),
        await runner.call("query_delinquency", _OWNER, {}),
        await runner.call("query_rate_terms", _OWNER, _CONTRACT),
        await runner.call("query_benefits", _OWNER, {}),
    ]
    for result in results:
        assert result.status == "ok"
        assert result.synthetic is True
        assert result.data is not None
        encoded = result.model_dump_json()
        assert all(
            name not in encoded
            for name in ("account_number", "phone_number", "address", "マイナンバー")
        )
    for step in tools_runtime.steps:
        assert step.details is not None
        assert step.details.tool_call is not None
        assert step.details.tool_call.status == "ok"
        assert "A001" not in step.model_dump_json()
        assert "C0001" not in step.model_dump_json()


async def test_redis_scopes_cache_to_agent_and_keeps_repayment_row_total(
    tools_runtime: Runtime,
) -> None:
    runner = tools_runtime.runner
    raw = await tools_runtime.raw.get(
        "/repayment-schedule",
        headers={"X-Agent-Id": "A001"},
        params={"customer_id": "C0001", **_CONTRACT},
    )
    raw.raise_for_status()
    assert raw.json()["synthetic"] is True
    assert len(raw.json()["data"]["schedule"]) == 420

    first = await runner.call("query_repayment_schedule", _OWNER, _CONTRACT)
    repeat = await runner.call("query_repayment_schedule", _OWNER, _CONTRACT)
    different_seat = await runner.call("query_repayment_schedule", _OTHER_OWNER, _CONTRACT)
    assert first.status == repeat.status == different_seat.status == "ok"
    assert repeat.synthetic is True
    assert [first.cached, repeat.cached, different_seat.cached] == [False, True, False]
    assert first.total == 420
    data = first.model_dump(mode="json")["data"]
    assert len(data["schedule"]) == 5


async def test_ownership_and_workbench_customer_are_checked_even_with_cache(
    tools_runtime: Runtime,
) -> None:
    runner = tools_runtime.runner
    assert (await runner.call("query_repayment_schedule", _OWNER, _CONTRACT)).status == "ok"
    denied = await runner.call("query_repayment_schedule", _OUTSIDER, _CONTRACT)
    wrong_contract = await runner.call("query_repayment_schedule", _OWNER, {"contract_id": "L0002"})
    assert denied.status == wrong_contract.status == "denied"
    assert denied.data is wrong_contract.data is None


@pytest.mark.parametrize("fault", ["timeout", "5xx"])
async def test_real_injected_failure_returns_a_sanitized_failure_within_budget(fault: str) -> None:
    async def inject(request: httpx.Request) -> None:
        if request.url.path == "/repayment-schedule":
            request.headers["X-Mock-Fault"] = fault

    settings = Settings()
    cache = RedisToolCache(settings.redis_url, key_prefix=f"grounded-rag:it:{uuid4().hex}:")
    async with httpx.AsyncClient(
        base_url=settings.mock_core_base_url, event_hooks={"request": [inject]}, timeout=8
    ) as raw:
        client = MockCoreClient(settings.mock_core_base_url, client=raw)
        try:
            runner = ToolRunner(client, cache)
            result = await runner.call("query_repayment_schedule", _OWNER, _CONTRACT)
        finally:
            await client.aclose()
            await cache.aclose()
    assert result.status == "failed"
    assert result.data is None
    assert result.reason
    assert result.elapsed_ms < 2300
