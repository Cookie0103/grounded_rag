"""按鉴权、缓存、读取、裁剪、限长和记录的顺序执行工具。"""

import asyncio
import hashlib
from collections.abc import Callable, Mapping
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
)

from app.core.resilience import CircuitBreaker
from app.providers.mock_core import MockCoreReply, MockCoreRequest, MockCoreTransport
from app.tools.cache import ToolCache
from app.tools.definitions import (
    TOOL_DEFINITIONS,
    ContractArguments,
    RepaymentScheduleArguments,
    RepaymentScheduleData,
    ToolArguments,
    ToolData,
    ToolDefinition,
    ToolName,
)

DEFAULT_TIMEOUT_SECONDS = 2.0
AUTHORIZATION_PATH = "/authorization"
RETRYABLE = frozenset({"timeout", "upstream_error"})

type ToolStatus = Literal["ok", "denied", "failed"]
type ToolReason = Literal[
    "missing_context",
    "not_authorized",
    "invalid_arguments",
    "timeout",
    "upstream_error",
    "invalid_response",
    "circuit_open",
]
type _RequestReply = MockCoreReply | ToolResult


class ToolContext(BaseModel):
    """由工作台提供的当前坐席与客户。"""

    model_config = ConfigDict(frozen=True)

    agent_id: Annotated[str, StringConstraints(strip_whitespace=True)] | None = None
    customer_id: Annotated[str, StringConstraints(strip_whitespace=True)] | None = None


class ToolResult(BaseModel):
    status: ToolStatus
    data: ToolData | None = None
    total: int | None = None
    reason: ToolReason | None = None
    cached: bool = False
    elapsed_ms: float = 0.0
    synthetic: Literal[True] | None = None


class ToolArgumentSummary(BaseModel):
    has_contract_id: bool = False
    start_period: int | None = None
    end_period: int | None = None


class ToolTrace(BaseModel):
    tool_name: ToolName
    arguments: ToolArgumentSummary
    status: ToolStatus
    reason: ToolReason | None
    cached: bool
    elapsed_ms: float
    total: int | None
    returned_count: int | None


class _Authorization(BaseModel):
    model_config = ConfigDict(strict=True)

    authorized: bool


class _WirePayload(BaseModel):
    synthetic: Literal[True]
    data: dict[str, object]
    total: Annotated[int, Field(strict=True, ge=0)] | None

    @field_validator("synthetic", mode="before")
    @classmethod
    def validate_synthetic(cls, value: object) -> Literal[True]:
        """只接受明确标为合成的业务响应。"""
        if value is not True:
            raise ValueError("模拟业务响应必须明确标注 synthetic 为 true")
        return True


class ToolRunner:
    def __init__(
        self,
        transport: MockCoreTransport,
        cache: ToolCache,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        recorder: Callable[[ToolTrace], None] | None = None,
        breaker_factory: Callable[[], CircuitBreaker] = CircuitBreaker,
    ) -> None:
        self._transport = transport
        self._cache = cache
        self._timeout = timeout_seconds
        self._recorder = recorder
        self._breakers = {item.path: breaker_factory() for item in TOOL_DEFINITIONS.values()}
        self._breakers[AUTHORIZATION_PATH] = breaker_factory()

    async def call(
        self,
        name: ToolName,
        context: ToolContext,
        arguments: Mapping[str, object] | ToolArguments,
        *,
        recorder: Callable[[ToolTrace], None] | None = None,
    ) -> ToolResult:
        """在整个工具调用的时间预算内完成查询，发送仅含脱敏信息的记录。"""
        definition = TOOL_DEFINITIONS[name]
        clock = asyncio.get_running_loop().time
        started = clock()
        summary = ToolArgumentSummary()
        try:
            request = _prepare_request(definition, context, arguments)
        except ValidationError:
            result = ToolResult(status="failed", reason="invalid_arguments")
        else:
            if request is None:
                result = ToolResult(status="denied", reason="missing_context")
            else:
                summary = ToolArgumentSummary(
                    has_contract_id=request.contract_id is not None,
                    start_period=request.start_period,
                    end_period=request.end_period,
                )
                result = await self._read_with_deadline(
                    definition, request, started + self._timeout
                )
        result.elapsed_ms = (clock() - started) * 1_000
        sink = recorder if recorder is not None else self._recorder
        if sink is not None:
            sink(_make_trace(definition, summary, result))
        return result

    async def _read_with_deadline(
        self, definition: ToolDefinition, request: MockCoreRequest, deadline: float
    ) -> ToolResult:
        try:
            async with asyncio.timeout_at(deadline):
                return await self._read(definition, request, deadline)
        except TimeoutError:
            return ToolResult(status="failed", reason="timeout")

    async def _read(
        self, definition: ToolDefinition, request: MockCoreRequest, deadline: float
    ) -> ToolResult:
        rejected, retry_available = await self._authorize(request, deadline)
        if rejected is not None:
            return rejected

        # 散列包含完整调用范围，Redis 键不暴露坐席、客户或合同编号。
        key = hashlib.sha256(f"{definition.name}:{request.model_dump_json()}".encode()).hexdigest()
        cached = await self._cache.get(key)
        if cached is not None:
            result = _read_cached(definition, cached)
            if result is not None:
                return result

        reply, _ = await self._request(
            definition.path, request, deadline, retry_available=retry_available
        )
        if isinstance(reply, ToolResult):
            return reply
        use_default_window = request.start_period is None and request.end_period is None
        try:
            result = _project(
                definition,
                _WirePayload.model_validate(reply.body),
                cached=False,
                use_default_window=use_default_window,
            )
        except ValidationError:
            return ToolResult(status="failed", reason="invalid_response")
        await self._cache.set(key, result.model_dump_json(include={"synthetic", "data", "total"}))
        return result

    async def _authorize(
        self, request: MockCoreRequest, deadline: float
    ) -> tuple[ToolResult | None, bool]:
        scope = request.model_copy(update={"start_period": None, "end_period": None})
        reply, retry_available = await self._request(
            AUTHORIZATION_PATH, scope, deadline, retry_available=True
        )
        if isinstance(reply, ToolResult):
            return reply, retry_available
        try:
            allowed = _Authorization.model_validate(reply.body).authorized
        except ValidationError:
            return ToolResult(status="failed", reason="invalid_response"), retry_available
        if not allowed:
            return ToolResult(status="denied", reason="not_authorized"), retry_available
        return None, retry_available

    async def _request(
        self, path: str, request: MockCoreRequest, deadline: float, *, retry_available: bool
    ) -> tuple[_RequestReply, bool]:
        breaker = self._breakers[path]
        if not breaker.allow():
            return ToolResult(status="failed", reason="circuit_open"), retry_available

        try:
            remaining = deadline - asyncio.get_running_loop().time()
            # 首次调用可重试时给下一次预留一半时间，两个端点共享一次重试额度。
            reply = await self._attempt(
                path, request, remaining / 2 if retry_available else remaining
            )
            if retry_available and reply.status in RETRYABLE:
                retry_available = False
                remaining = deadline - asyncio.get_running_loop().time()
                reply = await self._attempt(path, request, remaining)
        except asyncio.CancelledError:
            breaker.record_failure()
            raise

        status = reply.status
        if status == "ok":
            breaker.record_success()
            return reply, retry_available
        if status == "denied":
            breaker.record_success()
            return ToolResult(status="denied", reason="not_authorized"), retry_available
        breaker.record_failure()
        return ToolResult(status="failed", reason=status), retry_available

    async def _attempt(self, path: str, request: MockCoreRequest, budget: float) -> MockCoreReply:
        if budget <= 0:
            return MockCoreReply(status="timeout")
        try:
            async with asyncio.timeout(budget):
                return await self._transport.get(path, request, timeout_seconds=budget)
        except TimeoutError:
            return MockCoreReply(status="timeout")


def _prepare_request(
    definition: ToolDefinition,
    context: ToolContext,
    arguments: Mapping[str, object] | ToolArguments,
) -> MockCoreRequest | None:
    agent, customer = context.agent_id, context.customer_id
    if not agent or not customer or not agent.isascii() or not agent.isprintable():
        return None
    raw = arguments.model_dump() if isinstance(arguments, ToolArguments) else arguments
    parsed = definition.arguments_model.model_validate(raw)
    return MockCoreRequest(
        agent_id=agent,
        customer_id=customer,
        contract_id=parsed.contract_id if isinstance(parsed, ContractArguments) else None,
        start_period=parsed.start_period
        if isinstance(parsed, RepaymentScheduleArguments)
        else None,
        end_period=parsed.end_period if isinstance(parsed, RepaymentScheduleArguments) else None,
    )


def _read_cached(definition: ToolDefinition, cached: str) -> ToolResult | None:
    try:
        return _project(definition, _WirePayload.model_validate_json(cached), cached=True)
    except ValidationError:
        return None


def _project(
    definition: ToolDefinition,
    payload: _WirePayload,
    *,
    cached: bool,
    use_default_window: bool = False,
) -> ToolResult:
    data = definition.data_model.model_validate(payload.data)
    total = payload.total
    if definition.list_field is not None:
        rows = getattr(data, definition.list_field)
        total = len(rows) if total is None else max(total, len(rows))
        if use_default_window and isinstance(data, RepaymentScheduleData):
            next_date = data.next_payment_date
            if next_date is None:
                rows = data.schedule[-definition.list_limit :]
            else:
                rows = [row for row in data.schedule if row.due_date >= next_date]
        data = data.model_copy(update={definition.list_field: rows[: definition.list_limit]})
    return ToolResult(
        status="ok", synthetic=payload.synthetic, data=data, total=total, cached=cached
    )


def _make_trace(
    definition: ToolDefinition, summary: ToolArgumentSummary, result: ToolResult
) -> ToolTrace:
    count = None
    if definition.list_field is not None and result.data is not None:
        count = len(getattr(result.data, definition.list_field))
    return ToolTrace(
        tool_name=definition.name,
        arguments=summary,
        status=result.status,
        reason=result.reason,
        cached=result.cached,
        elapsed_ms=result.elapsed_ms,
        total=result.total,
        returned_count=count,
    )
