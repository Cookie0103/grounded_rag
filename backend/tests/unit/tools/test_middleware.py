import asyncio
from collections.abc import Iterable

import httpx
import pytest

from app.core.resilience import CircuitBreaker
from app.providers.mock_core import MockCoreClient
from app.tools.cache import MemoryToolCache
from app.tools.definitions import TOOL_DEFINITIONS, RepaymentScheduleData, ToolName
from app.tools.middleware import ToolContext, ToolRunner, ToolTrace

CONTEXT = ToolContext(agent_id="A001", customer_id="C0001")
AUTH_PATH = "/authorization"
HTTP_METHOD = "GET"
CONTRACTS_PATH = "/loan-contracts"
SCHEDULE_PATH = "/repayment-schedule"
CONTRACT_ARGS = {"contract_id": "L0001"}


def _ok(data: dict[str, object], total: int | None = None) -> httpx.Response:
    return httpx.Response(200, json={"synthetic": True, "data": data, "total": total})


def _authorization(allowed: bool = True) -> httpx.Response:
    return httpx.Response(200, json={"authorized": allowed})


def _contracts() -> httpx.Response:
    return _ok({"contracts": []}, 0)


def _installment(period: int) -> dict[str, object]:
    return {
        "period": period,
        "due_date": "2027-01-26",
        "amount_yen": 100_000,
        "principal_yen": 90_000,
        "interest_yen": 10_000,
        "account_number": "hidden-row",
    }


def _schedule(installments: Iterable[int] = ()) -> dict[str, object]:
    return {
        "next_payment_date": "2027-01-26",
        "next_payment_yen": 100_000,
        "outstanding_principal_yen": 35_000_000,
        "remaining_installments": 420,
        "schedule": [_installment(period) for period in installments],
    }


@pytest.mark.parametrize(
    "context",
    [ToolContext(), ToolContext(agent_id=" ", customer_id="C0001"), ToolContext(agent_id="A001")],
)
async def test_missing_context_rejects_without_http(context: ToolContext) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        pytest.fail(f"缺少上下文时发出了请求：{request.url.path}")

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        runner = ToolRunner(MockCoreClient("http://mock-core", client=http), MemoryToolCache())
        result = await runner.call("query_loan_contracts", context, {})

    assert (result.status, result.reason) == ("denied", "missing_context")


@pytest.mark.parametrize("payload", [{"authorized": False}, {"authorized": "false"}])
async def test_authorization_checks_requested_contract_before_any_data_request(
    payload: dict[str, object],
) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path == AUTH_PATH
        assert request.headers["X-Agent-Id"] == CONTEXT.agent_id
        assert request.url.params == httpx.QueryParams(customer_id="C0001", contract_id="L0001")
        return httpx.Response(200, json=payload)

    client = MockCoreClient("http://mock-core", transport=httpx.MockTransport(respond))
    try:
        runner = ToolRunner(client, MemoryToolCache())
        result = await runner.call("query_repayment_schedule", CONTEXT, CONTRACT_ARGS)
    finally:
        await client.aclose()

    assert result.status == ("denied" if payload["authorized"] is False else "failed")
    assert result.data is None


@pytest.mark.parametrize(
    "arguments",
    [
        {"contract_id": "L0001", "customer_id": "C9999"},
        {"contract_id": "L0001", "agent_id": "A009"},
    ],
)
async def test_arguments_cannot_override_trusted_identity(arguments: dict[str, object]) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        pytest.fail(f"非法入参发出了请求：{request.url.path}")

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        runner = ToolRunner(MockCoreClient("http://mock-core", client=http), MemoryToolCache())
        result = await runner.call("query_repayment_schedule", CONTEXT, arguments)

    assert (result.status, result.reason) == ("failed", "invalid_arguments")


async def test_hot_cache_does_not_bypass_revoked_authorization() -> None:
    allowed = True
    calls: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return _authorization(allowed) if request.url.path == AUTH_PATH else _contracts()

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        runner = ToolRunner(MockCoreClient("http://mock-core", client=http), MemoryToolCache())
        assert (await runner.call("query_loan_contracts", CONTEXT, {})).status == "ok"
        allowed = False
        denied = await runner.call("query_loan_contracts", CONTEXT, {})

    assert denied.status == "denied"
    assert not denied.cached
    assert calls == [AUTH_PATH, CONTRACTS_PATH, AUTH_PATH]


async def test_cache_respects_agent_and_customer_scope_and_expires() -> None:
    calls: list[tuple[str, str]] = []
    now = 0.0

    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path == AUTH_PATH:
            return _authorization()
        calls.append((request.headers["X-Agent-Id"], request.url.params["customer_id"]))
        return _contracts()

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        runner = ToolRunner(
            MockCoreClient("http://mock-core", client=http), MemoryToolCache(clock=lambda: now)
        )
        assert not (await runner.call("query_loan_contracts", CONTEXT, {})).cached
        assert (await runner.call("query_loan_contracts", CONTEXT, {})).cached
        other_agent = ToolContext(agent_id="A002", customer_id=CONTEXT.customer_id)
        assert not (await runner.call("query_loan_contracts", other_agent, {})).cached
        other_customer = ToolContext(agent_id=CONTEXT.agent_id, customer_id="C0002")
        assert not (await runner.call("query_loan_contracts", other_customer, {})).cached
        now = 5.001
        assert not (await runner.call("query_loan_contracts", CONTEXT, {})).cached

    assert calls == [("A001", "C0001"), ("A002", "C0001"), ("A001", "C0002"), ("A001", "C0001")]


@pytest.mark.parametrize(
    ("name", "path", "data"),
    [
        (
            "query_loan_contracts",
            CONTRACTS_PATH,
            {
                "contracts": [
                    {
                        "contract_id": "L0001",
                        "product": "住宅ローン",
                        "principal_yen": 10,
                        "disbursed_on": "2020-01-01",
                        "status": "active",
                        "phone": "hidden-row",
                    }
                ]
            },
        ),
        ("query_repayment_schedule", SCHEDULE_PATH, _schedule(iter([1]))),
        (
            "query_delinquency",
            "/delinquency",
            {"days_overdue": 0, "amount_yen": 0, "late_fee_yen": 0},
        ),
        (
            "query_rate_terms",
            "/rate-terms",
            {
                "annual_rate_percent": 1.56,
                "rate_type": "固定金利",
                "fixed_until": None,
                "insurance_type": "一般団信",
                "insurance_increment_percent": 0.0,
            },
        ),
        (
            "query_benefits",
            "/benefits",
            {"benefits": [{"name": "優遇", "status": "適用", "address": "hidden-row"}]},
        ),
    ],
)
async def test_every_tool_projects_only_approved_response_fields(
    name: ToolName, path: str, data: dict[str, object]
) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.method == HTTP_METHOD
        if request.url.path == AUTH_PATH:
            return _authorization()
        assert request.url.path == path
        return _ok(
            {**data, "account_number": "hidden-top", "phone": "hidden-top", "address": "hidden-top"}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        runner = ToolRunner(MockCoreClient("http://mock-core", client=http), MemoryToolCache())
        arguments = (
            CONTRACT_ARGS if name in {"query_repayment_schedule", "query_rate_terms"} else {}
        )
        result = await runner.call(name, CONTEXT, arguments)

    assert result.status == "ok"
    assert result.data is not None
    assert result.synthetic is True
    assert result.data.model_dump().keys() == data.keys()
    assert "hidden" not in result.model_dump_json()


async def test_schedule_truncates_details_preserves_total_and_records_redacted_summary() -> None:
    traces: list[ToolTrace] = []

    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path == AUTH_PATH:
            return _authorization()
        assert request.url.path == SCHEDULE_PATH
        return _ok(_schedule(iter(range(1, 421))), 420)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        runner = ToolRunner(
            MockCoreClient("http://mock-core", client=http),
            MemoryToolCache(),
            recorder=traces.append,
        )
        result = await runner.call("query_repayment_schedule", CONTEXT, CONTRACT_ARGS)
        cached = await runner.call("query_repayment_schedule", CONTEXT, CONTRACT_ARGS)

    assert result.data is not None
    assert [entry["period"] for entry in result.data.model_dump()["schedule"]] == [1, 2, 3, 4, 5]
    assert result.total == cached.total == 420
    assert len(traces) == 2
    assert traces[0].tool_name == "query_repayment_schedule"
    assert traces[0].total == 420
    assert traces[0].returned_count == traces[1].returned_count == 5
    assert traces[0].elapsed_ms == result.elapsed_ms
    assert traces[1].cached
    assert all(
        identifier not in traces[0].model_dump_json() for identifier in ("A001", "C0001", "L0001")
    )


@pytest.mark.parametrize(
    ("next_date", "periods"), [("2026-04-26", [4, 5, 6, 7, 8]), (None, [6, 7, 8, 9, 10])]
)
async def test_default_schedule_keeps_nearest_installments(
    next_date: str | None, periods: list[int]
) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path == AUTH_PATH:
            return _authorization()
        rows = [
            {**_installment(period), "due_date": f"2026-{period:02}-26"} for period in range(1, 11)
        ]
        return _ok({**_schedule(), "next_payment_date": next_date, "schedule": rows}, 10)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        runner = ToolRunner(MockCoreClient("http://mock-core", client=http), MemoryToolCache())
        result = await runner.call("query_repayment_schedule", CONTEXT, CONTRACT_ARGS)

    assert isinstance(result.data, RepaymentScheduleData)
    assert [entry.period for entry in result.data.schedule] == periods
    assert result.total == 10


@pytest.mark.parametrize("marker", [None, False, 1])
async def test_service_data_requires_explicit_synthetic_marker(marker: object) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path == AUTH_PATH:
            return _authorization()
        return httpx.Response(
            200, json={"synthetic": marker, "data": {"contracts": []}, "total": 0}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        runner = ToolRunner(MockCoreClient("http://mock-core", client=http), MemoryToolCache())
        result = await runner.call("query_loan_contracts", CONTEXT, {})

    assert (result.status, result.reason) == ("failed", "invalid_response")
    assert result.data is None


async def test_explicit_schedule_window_is_forwarded_only_to_the_data_endpoint() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.params["contract_id"] == "L0001"
        if request.url.path == AUTH_PATH:
            assert "start_period" not in request.url.params
            return _authorization()
        assert request.url.params["start_period"] == "50"
        assert request.url.params["end_period"] == "53"
        return _ok(_schedule(iter(range(50, 54))), 4)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        runner = ToolRunner(MockCoreClient("http://mock-core", client=http), MemoryToolCache())
        result = await runner.call(
            "query_repayment_schedule",
            CONTEXT,
            {**CONTRACT_ARGS, "start_period": 50, "end_period": 53},
        )

    assert result.status == "ok"
    assert result.total == 4


def test_definitions_offer_planner_schema_without_identity_fields() -> None:
    assert len(TOOL_DEFINITIONS) == 5
    schedule = TOOL_DEFINITIONS["query_repayment_schedule"]
    assert "返済" in schedule.description
    properties = schedule.parameters["properties"]
    assert isinstance(properties, dict)
    assert properties.keys() == {"contract_id", "start_period", "end_period"}
    assert schedule.parameters["required"] == ["contract_id"]


async def test_5xx_retries_once_and_failed_result_is_not_cached() -> None:
    traces: list[ToolTrace] = []
    business_calls = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal business_calls
        if request.url.path == AUTH_PATH:
            return _authorization()
        business_calls += 1
        assert request.headers["X-Mock-Fault"] == "test-fault"
        return httpx.Response(500) if business_calls < 3 else _contracts()

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(respond), headers={"X-Mock-Fault": "test-fault"}
    ) as http:
        runner = ToolRunner(
            MockCoreClient("http://mock-core", client=http),
            MemoryToolCache(),
            recorder=traces.append,
        )
        failed = await runner.call("query_loan_contracts", CONTEXT, {})
        assert business_calls == 2
        retried = await runner.call("query_loan_contracts", CONTEXT, {})

    assert (failed.status, failed.reason) == ("failed", "upstream_error")
    assert retried.status == "ok"
    assert not retried.cached
    assert traces[0].reason == "upstream_error"


async def test_retry_budget_is_shared_by_authorization_and_business() -> None:
    calls: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == AUTH_PATH and len(calls) == 2:
            return _authorization()
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        runner = ToolRunner(MockCoreClient("http://mock-core", client=http), MemoryToolCache())
        result = await runner.call("query_loan_contracts", CONTEXT, {})

    assert (result.status, result.reason) == ("failed", "upstream_error")
    assert calls == [AUTH_PATH, AUTH_PATH, CONTRACTS_PATH]


async def test_timeout_cancels_a_hung_http_transport_within_total_budget() -> None:
    started = asyncio.Event()
    stops = 0

    async def respond(request: httpx.Request) -> httpx.Response:
        nonlocal stops
        if request.url.path == AUTH_PATH:
            return _authorization()
        try:
            await started.wait()
        finally:
            stops += 1
        pytest.fail("挂起的工具请求必须被超时取消")

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        runner = ToolRunner(
            MockCoreClient("http://mock-core", client=http), MemoryToolCache(), timeout_seconds=0.04
        )
        result = await asyncio.wait_for(
            runner.call("query_loan_contracts", CONTEXT, {}), timeout=0.5
        )

    assert (result.status, result.reason) == ("failed", "timeout")
    assert stops == 2


async def test_open_business_circuit_still_checks_authorization() -> None:
    calls: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return _authorization() if request.url.path == AUTH_PATH else httpx.Response(500)

    def breaker_factory() -> CircuitBreaker:
        return CircuitBreaker(threshold=1)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        runner = ToolRunner(
            MockCoreClient("http://mock-core", client=http),
            MemoryToolCache(),
            breaker_factory=breaker_factory,
        )
        assert (await runner.call("query_loan_contracts", CONTEXT, {})).reason == "upstream_error"
        result = await runner.call("query_loan_contracts", CONTEXT, {})

    assert result.reason == "circuit_open"
    assert calls == [AUTH_PATH, CONTRACTS_PATH, CONTRACTS_PATH, AUTH_PATH]
