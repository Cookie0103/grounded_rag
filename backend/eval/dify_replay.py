"""将 Dify 应用的节点与网关证据对齐到同题评测契约。"""

import asyncio
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from time import monotonic
from typing import Annotated, Any, Literal, Protocol
from uuid import uuid4
from zipfile import ZipFile

from pydantic import BaseModel, Field, ValidationError

from app.core.errors import DependencyUnavailableError
from app.orchestration.models import Intent, Step, tool_trace_step
from app.providers.budget import BudgetLedger
from app.providers.deepseek import cost_cny
from app.providers.dify import DifyNode, DifyRequest, DifyTurn
from app.tools.definitions import ToolName
from app.tools.middleware import ToolArgumentSummary, ToolReason, ToolStatus, ToolTrace
from eval.copilot_cases import CopilotCase
from eval.copilot_observations import TurnObservation
from eval.copilot_report import FaultMode, Tier
from eval.metrics import ranked_documents

AS_OF = date(2026, 11, 18)
SYSTEM = "Dify V3"
_SMALL_NODES = {"intent", "plan_tools"}
_INTENTS: dict[str, Intent] = {
    "smalltalk": "smalltalk",
    "complaint": "complaint",
    "policy": "policy",
    "lookup": "lookup",
    "lookup_policy": "lookup",
    "policy_lookup": "policy",
}
_NODE_STEPS = {"intent": "intent", "plan_tools": "plan", "standalone": "standalone"}
_POLL_SECONDS = 0.05
_WAIT_SECONDS = 2.0


class _Document(BaseModel):
    document_id: str
    source_id: str
    file: str
    status: Literal["draft", "online", "offline"]
    effective_from: date
    effective_to: date | None

    def expired(self, as_of: date) -> bool:
        return (
            self.status == "draft"
            or self.effective_from > as_of
            or (self.effective_to is not None and as_of >= self.effective_to)
        )


@dataclass(frozen=True)
class DocumentCatalog:
    """用 S 档出题包把 Dify 的文件名映射到同一版本 ID。"""

    by_id: Mapping[str, _Document]
    by_name: Mapping[str, _Document]

    @classmethod
    def from_question_pack(cls, path: Path) -> "DocumentCatalog":
        with ZipFile(path) as bundle:
            lines = bundle.read("index.jsonl").splitlines()
        documents = [_Document.model_validate_json(line) for line in lines if line.strip()]
        return cls(
            {item.document_id: item for item in documents},
            {
                name: item
                for item in documents
                for name in (item.source_id, item.file, Path(item.file).stem)
            },
        )

    def identify(self, item: Mapping[str, Any]) -> str | None:
        metadata = item.get("metadata") or item.get("_metadata") or {}
        doc_metadata = metadata.get("doc_metadata") or {}
        for value in (
            doc_metadata.get("document_id"),
            doc_metadata.get("doc_id"),
            metadata.get("document_id"),
            metadata.get("document_name"),
            item.get("document_name"),
            item.get("title"),
        ):
            if isinstance(value, str) and (doc := self.by_id.get(value) or self.by_name.get(value)):
                return doc.document_id
        return None


class GatewayCall(BaseModel):
    """网关回调记录的单次实际用量。"""

    request_id: str = Field(min_length=1)
    model: str
    prompt_tokens: Annotated[int, Field(ge=0, strict=True)]
    completion_tokens: Annotated[int, Field(ge=0, strict=True)]


class GatewayJournal:
    """在独占且串行的网关窗口采集模型回调。"""

    def __init__(self, path: Path, *, wait_seconds: float = _WAIT_SECONDS) -> None:
        self.path = path
        self.wait_seconds = wait_seconds

    def position(self) -> int:
        return self.path.stat().st_size if self.path.exists() else 0

    def _read(self, position: int) -> list[GatewayCall]:
        if not self.path.exists():
            return []
        with self.path.open("rb") as journal:
            journal.seek(position)
            raw = journal.read()
        lines = raw.splitlines() if raw.endswith(b"\n") else raw.splitlines()[:-1]
        unique: dict[str, GatewayCall] = {}
        for line in lines:
            call = GatewayCall.model_validate_json(line)
            if unique.setdefault(call.request_id, call) != call:
                raise ValueError("网关同一请求 ID 的用量记录冲突")
        return list(unique.values())

    async def collect(self, position: int, expected: Counter[str] | None) -> list[GatewayCall]:
        """等待工作流节点对应的网关成功回调落盘。"""
        end = monotonic() + self.wait_seconds
        while True:
            if self.position() < position:
                raise ValueError("网关用量记录在回放期间被截断")
            calls = await asyncio.to_thread(self._read, position)
            if expected is not None and Counter(call.model for call in calls) >= expected:
                return calls
            if monotonic() >= end:
                return calls
            await asyncio.sleep(_POLL_SECONDS)


class DifyMeasurement(BaseModel):
    """阶段 36 同格式观察行，附网关证据定位和覆盖情况。"""

    case_id: str
    tier: Tier = "S"
    fault_mode: FaultMode
    observation: TurnObservation
    synthetic: bool | None = None
    classifier_class: str | None = None
    workflow_run_ids: tuple[str, ...] = ()
    gateway_request_ids: tuple[str, ...] = ()
    missing_usage: tuple[int, ...] = ()


class _ChatClient(Protocol):
    async def chat(self, request: DifyRequest) -> DifyTurn: ...


def _outputs(node: DifyNode) -> Mapping[str, Any]:
    if node.status == "succeeded" and not node.outputs_truncated and node.outputs is not None:
        return node.outputs
    return {}


def _class_id(nodes: Sequence[DifyNode]) -> str | None:
    for node in nodes:
        if node.node_type == "question-classifier":
            outputs = _outputs(node)
            for key in ("class_id", "class_name"):
                value = outputs.get(key)
                if isinstance(value, str) and (value in _INTENTS or value == "unclassified"):
                    return value
    return None


def _retrieval(
    turn: DifyTurn,
    catalog: DocumentCatalog,
) -> tuple[tuple[str, ...] | None, tuple[str, ...]]:
    nodes = [node for node in turn.nodes if node.node_type == "knowledge-retrieval"]
    ids: list[str] = []
    contexts: list[str] = []
    complete = bool(turn.workflow_status)
    for node in nodes:
        values = _outputs(node).get("result")
        if not isinstance(values, list):
            complete = False
            continue
        for item in values:
            if not isinstance(item, dict):
                complete = False
                continue
            identifier = catalog.identify(item)
            if identifier is not None:
                ids.append(identifier)
            else:
                complete = False
            if isinstance(content := item.get("content"), str) and content:
                contexts.append(content)
    return (tuple(ranked_documents(ids)) if complete else None), tuple(contexts)


def _tool_arguments(value: Mapping[str, Any]) -> ToolArgumentSummary:
    return ToolArgumentSummary(
        has_contract_id=value.get("has_contract_id", bool(value.get("contract_id"))),
        start_period=value.get("start_period"),
        end_period=value.get("end_period"),
    )


def _tool_timings(
    items: Sequence[Mapping[str, Any]], nodes: Sequence[DifyNode]
) -> Sequence[float | None]:
    auth = [node.latency_ms for node in nodes if node.node_id == "mock_authorize"]
    reads = [node.latency_ms for node in nodes if node.node_id == "mock_get"]
    dispatched = [item.get("business_dispatched") is True for item in items]
    # 画布按迭代串行完成这些节点，各工具均执行一次鉴权。
    if len(auth) != len(items) or len(reads) != sum(dispatched):
        return [None] * len(items)
    observed = iter(reads)
    return [ms + (next(observed) if sent else 0) for ms, sent in zip(auth, dispatched, strict=True)]


def _to_tool_trace(item: Mapping[str, Any], http_ms: float | None) -> ToolTrace:
    arguments = item.get("arguments")
    reason = item.get("reason")
    return ToolTrace.model_validate(
        {
            **item,
            "arguments": _tool_arguments(arguments if isinstance(arguments, dict) else {}),
            "reason": "upstream_error" if reason == "transport_error" else reason,
            "cached": False,  # 当前 Dify 画布无业务结果缓存。
            "elapsed_ms": item.get("elapsed_ms", http_ms),
            "total": item.get("total"),
            "returned_count": item.get("returned_count"),
        }
    )


def _tools(turn: DifyTurn) -> list[ToolTrace] | None:
    evidence = [node for node in turn.nodes if node.node_id == "tool_evidence"]
    if not evidence:
        return (
            []
            if turn.workflow_status
            and not any(node.node_type == "http-request" for node in turn.nodes)
            else None
        )
    calls: list[ToolTrace] = []
    for node in evidence:
        values = _outputs(node).get("tool_calls")
        if not isinstance(values, list) or not all(isinstance(item, dict) for item in values):
            return None
        try:
            calls.extend(
                _to_tool_trace(item, elapsed)
                for item, elapsed in zip(values, _tool_timings(values, turn.nodes), strict=True)
            )
        except ValidationError:
            return None
    return calls


def _steps(nodes: Sequence[DifyNode], tools: Sequence[ToolTrace]) -> list[Step]:
    steps = [tool_trace_step(tool) for tool in tools]
    for node in nodes:
        name = _NODE_STEPS.get(node.node_id)
        if node.node_type == "knowledge-retrieval":
            name = "retrieve"
        elif node.node_type == "llm" and node.node_id.startswith("generate"):
            name = "generate"
        if name is not None:
            steps.append(Step(name=name, ms=node.latency_ms, note=node.status))
    return steps


def _trace_question(turn: DifyTurn, case: CopilotCase) -> str | None:
    if case.expected_outcome != "redacted":
        return None
    for node in turn.nodes:
        if node.node_type == "start":
            value = _outputs(node).get("sys.query", (node.inputs or {}).get("sys.query"))
            if isinstance(value, str):
                return value
    return None


def observe_turn(turn: DifyTurn, case: CopilotCase, catalog: DocumentCatalog) -> TurnObservation:
    """读取本轮证据。未披露的检索、工具和用量保留空值。"""
    docs, contexts = _retrieval(turn, catalog)
    cites = tuple(identifier for identifier in catalog.by_id if identifier in turn.answer)
    as_of = case.as_of or AS_OF
    expired = (
        tuple(sorted(doc for doc in set(docs).union(cites) if catalog.by_id[doc].expired(as_of)))
        if docs is not None
        else None
    )
    tools = _tools(turn)
    return TurnObservation(
        answer=turn.answer,
        intent=_INTENTS.get(_class_id(turn.nodes) or ""),
        retrieved_docs=docs,
        citation_docs=cites,
        contexts=contexts,
        dropped_or_expired_docs=expired,
        tool_calls=tools,
        steps=_steps(turn.nodes, tools or ()),
        latency_ms=turn.latency_ms,
        first_token_ms=turn.first_token_ms,
        degraded=any(tool.status == "failed" for tool in tools or ()),
        trace_question=_trace_question(turn, case),
    )


@dataclass(frozen=True)
class _RecordedTurn:
    response: DifyTurn
    calls: list[GatewayCall]
    complete_usage: bool


class DifyReplay:
    """经 Dify API 依次重放历史，并按网关证据记账。"""

    def __init__(
        self,
        client: _ChatClient,
        journal: GatewayJournal,
        ledger: BudgetLedger,
        catalog: DocumentCatalog,
        *,
        small_model: str = "small",
        large_model: str = "deepseek-v4-pro",
    ) -> None:
        self._client = client
        self._journal = journal
        self._ledger = ledger
        self._catalog = catalog
        self._small = small_model
        self._large = large_model

    async def _request(self, request: DifyRequest) -> _RecordedTurn:
        self._ledger.check()
        offset = self._journal.position()
        try:
            turn = await self._client.chat(request)
        except DependencyUnavailableError:
            self._charge(await self._journal.collect(offset, None))
            raise
        expected = Counter(
            self._small if node.node_id in _SMALL_NODES else self._large
            for node in turn.nodes
            if node.node_type in {"question-classifier", "llm"}
        )
        calls = await self._journal.collect(offset, expected if turn.workflow_status else None)
        self._charge(calls)
        actual = Counter(call.model for call in calls)
        complete = (
            bool(turn.workflow_status)
            and any(node.node_id == "intent" for node in turn.nodes)
            and actual >= expected
            and all(model in {self._small, self._large} for model in actual)
        )
        return _RecordedTurn(turn, calls, complete)

    def _charge(self, calls: Sequence[GatewayCall]) -> None:
        amount = self._cost(calls)
        if amount:
            self._ledger.add(amount)

    def _cost(self, calls: Sequence[GatewayCall]) -> float:
        return sum(
            cost_cny(call.prompt_tokens, call.completion_tokens, model=call.model)
            for call in calls
            if call.model == self._large
        )

    async def observe(self, case: CopilotCase, fault_mode: FaultMode) -> DifyMeasurement:
        """回放一个用例，最后一轮的指标与全对话的费用分开取证。"""
        user = f"copilot-eval-{uuid4().hex}"
        inputs = {
            "channel": case.channel,
            "agent_id": case.agent_id or "",
            "customer_id": case.customer_id or "",
            "as_of": (case.as_of or AS_OF).isoformat(),
            "mock_fault": "",
        }
        conversation_id = None
        replies = []
        for question in case.history:
            reply = await self._request(
                DifyRequest(
                    query=question,
                    user=user,
                    conversation_id=conversation_id,
                    inputs=inputs,
                )
            )
            if not reply.complete_usage:
                raise DependencyUnavailableError("Dify 历史轮缺少网关用量证据，回放已停止")
            replies.append(reply)
            conversation_id = reply.response.conversation_id
        final = await self._request(
            DifyRequest(
                query=case.question,
                user=user,
                conversation_id=conversation_id,
                inputs={**inputs, "mock_fault": case.fault or ""},
            )
        )
        replies.append(final)
        return self._measurement(case, fault_mode, replies, final)

    def _measurement(
        self,
        case: CopilotCase,
        fault_mode: FaultMode,
        replies: Sequence[_RecordedTurn],
        final: _RecordedTurn,
    ) -> DifyMeasurement:
        calls = [call for reply in replies for call in reply.calls]
        missing = tuple(index for index, reply in enumerate(replies, 1) if not reply.complete_usage)
        observation = observe_turn(final.response, case, self._catalog)
        if not missing:
            observation = observation.model_copy(
                update={
                    "prompt_tokens": sum(call.prompt_tokens for call in calls),
                    "completion_tokens": sum(call.completion_tokens for call in calls),
                    "cost_cny": self._cost(calls),
                }
            )
        return DifyMeasurement(
            case_id=case.id,
            fault_mode=fault_mode,
            observation=observation,
            synthetic=case.synthetic,
            classifier_class=_class_id(final.response.nodes),
            workflow_run_ids=tuple(
                run for reply in replies if (run := reply.response.workflow_run_id) is not None
            ),
            gateway_request_ids=tuple(call.request_id for call in calls),
            missing_usage=missing,
        )


class _ToolSignature(BaseModel):
    tool_name: ToolName
    arguments: ToolArgumentSummary
    status: ToolStatus
    reason: ToolReason | None
    total: int | None
    returned_count: int | None


type _LayerValue = str | list[str] | list[_ToolSignature] | None


class LayerDifference(BaseModel):
    state: Literal["same", "different", "unmeasured"]
    langgraph: _LayerValue
    dify: _LayerValue


def _tool_signatures(observation: TurnObservation) -> list[_ToolSignature] | None:
    if observation.tool_calls is None:
        return None
    return sorted(
        (_ToolSignature.model_validate(call.model_dump()) for call in observation.tool_calls),
        key=lambda call: call.model_dump_json(),
    )


def compare_observations(
    langgraph: TurnObservation,
    dify: TurnObservation,
    *,
    classifier_class: str | None = None,
) -> dict[str, LayerDifference]:
    """按意图、检索排序、工具调用与回答文字逐层对照。"""
    result = {}
    pairs: dict[str, tuple[_LayerValue, _LayerValue]] = {
        "intent": (langgraph.intent, dify.intent or classifier_class),
        "retrieval": (
            None
            if langgraph.retrieved_docs is None
            else ranked_documents(langgraph.retrieved_docs),
            None if dify.retrieved_docs is None else ranked_documents(dify.retrieved_docs),
        ),
        "tools": (_tool_signatures(langgraph), _tool_signatures(dify)),
        "answer": (
            langgraph.answer.replace("\r\n", "\n").strip(),
            dify.answer.replace("\r\n", "\n").strip(),
        ),
    }
    for layer, (left, right) in pairs.items():
        state: Literal["same", "different", "unmeasured"]
        if left is None or right is None:
            state = "unmeasured"
        else:
            state = "same" if left == right else "different"
        result[layer] = LayerDifference(state=state, langgraph=left, dify=right)
    return result
