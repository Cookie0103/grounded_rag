"""住宅贷款坐席与客户的双泳道 LangGraph。"""

import time
import unicodedata
from collections.abc import AsyncIterator
from datetime import date
from typing import Literal, Self, cast

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from app.core.config import MIN_INTENT_CONFIDENCE
from app.core.errors import DependencyUnavailableError
from app.orchestration import prompts
from app.orchestration.context import assemble, resolve_citations
from app.orchestration.copilot_tools import ToolBranch, ToolOutcome
from app.orchestration.copilot_trace import ModelUsage, model_messages, record
from app.orchestration.guard import check_input
from app.orchestration.jsonutil import as_bool, parse_object
from app.orchestration.models import (
    REFUSE,
    AnswerDelta,
    Channel,
    ChatRequest,
    ChatResponse,
    ChatStreamItem,
    Citation,
    Intent,
    Step,
    StepDetails,
)
from app.orchestration.output_guard import validate_output
from app.orchestration.pii import redact_pii
from app.providers.base import ChatDelta, ChatMessage, ChatModel, Completion, StreamingChatModel
from app.retrieval.retriever import RetrievalResult, Retriever
from app.tools.middleware import ToolRunner

GREETINGS = frozenset(
    {
        "おはよう",
        "おはようございます",
        "こんにちは",
        "こんばんは",
        "ありがとう",
        "ありがとうございます",
        "ありがとうございました",
        "どうもありがとう",
        "さようなら",
        "はじめまして",
        "よろしくお願いします",
    }
)
REPHRASE_TEXT = "ご質問の内容を確認するため、具体的な手続きや条件を添えてお尋ねください。"
Failure = Literal[
    "guard",
    "denied",
    "failed",
    "empty_policy",
    "retrieval_unavailable",
    "evidence",
    "generation",
    "output_guard",
]
AfterAgentIntent = Literal["direct", "escalate", "retrieve", "tool_branch"]


class _IntentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Intent
    secondary_intent: Intent | None = None

    @model_validator(mode="after")
    def check_combination(self) -> Self:
        """当前只允许查数与规程的混合意图。"""
        if self.secondary_intent is not None and {self.intent, self.secondary_intent} != {
            "lookup",
            "policy",
        }:
            raise ValueError("仅支持查数与规程的混合意图")
        return self


class _State(ToolOutcome, total=False):
    request: ChatRequest
    stream_tokens: bool
    previous_intent: Intent | None
    previous_policy_question: str | None
    intent: Intent
    secondary_intent: Intent | None
    conservative: bool
    standalone_question: str
    retrieved: RetrievalResult
    policy_context: str
    potential_citations: list[Citation]
    citations: list[Citation]
    answer: str
    abstained: bool
    failure: Failure


class CopilotGraph:
    def __init__(
        self,
        small: ChatModel,
        large: ChatModel,
        retriever: Retriever,
        tools: ToolRunner,
        *,
        strict: bool = False,
    ) -> None:
        self._small = small
        self._large = large
        self._retriever = retriever
        self._strict = strict
        self.agent_graph = self._build("agent", tools)
        self.customer_graph = self._build("customer", tools)

    async def answer(
        self,
        request: ChatRequest,
        *,
        previous_intent: Intent | None = None,
        previous_policy_question: str | None = None,
    ) -> ChatResponse:
        """运行对应泳道并返回整轮响应。"""
        async for event in self.stream(
            request,
            previous_intent=previous_intent,
            previous_policy_question=previous_policy_question,
        ):
            if isinstance(event, ChatResponse):
                return event
        raise RuntimeError("双泳道图没有产出最终响应")

    async def stream(
        self,
        request: ChatRequest,
        *,
        previous_intent: Intent | None = None,
        previous_policy_question: str | None = None,
        stream_tokens: bool = False,
    ) -> AsyncIterator[ChatStreamItem]:
        """逐节点发送步骤，再发送包含本轮证据摘要的响应。"""
        graph = self.agent_graph if request.channel == "agent" else self.customer_graph
        final: _State = {
            "request": request,
            "stream_tokens": stream_tokens,
            "previous_intent": previous_intent,
            "previous_policy_question": previous_policy_question,
        }
        steps: list[Step] = []
        async for namespace, mode, result in graph.astream(
            final, stream_mode=["custom", "values"], subgraphs=True
        ):
            if mode == "custom" and isinstance(result, Step):
                steps.append(result)
                yield result
            elif mode == "custom" and isinstance(result, AnswerDelta):
                yield result
            elif mode == "values" and not namespace:
                final = cast(_State, result)
        yield _response(final, steps)

    def _build(
        self, channel: Channel, tools: ToolRunner
    ) -> CompiledStateGraph[_State, None, _State, _State]:
        builder: StateGraph[_State, None, _State, _State] = StateGraph(_State)
        builder.add_node("guard", _guard)
        builder.add_node("intent", self._intent)
        builder.add_node("retrieve", self._retrieve)
        builder.add_node("join", _join)
        builder.add_node("generate", self._generate)
        builder.add_node("direct", _direct)
        builder.add_node("escalate", _escalate)
        builder.add_node("degrade", _degrade)
        builder.add_edge(START, "guard")
        builder.add_conditional_edges("guard", _after_guard)
        if channel == "agent":
            branch = ToolBranch(self._small, tools).build()
            builder.add_node("tool_branch", branch)
            builder.add_edge("tool_branch", "join")
            builder.add_conditional_edges("intent", _after_agent_intent)
        else:
            builder.add_node("handoff", _handoff)
            builder.add_edge("handoff", END)
            builder.add_conditional_edges("intent", _after_customer_intent)
        builder.add_edge("retrieve", "join")
        builder.add_edge("direct", END)
        builder.add_edge("escalate", END)
        builder.add_edge("degrade", END)
        self._connect_generation(builder)
        return builder.compile()

    def _connect_generation(self, builder: StateGraph[_State, None, _State, _State]) -> None:
        if self._strict:
            builder.add_node("grade", self._grade)
            builder.add_node("verify", self._verify)
            builder.add_conditional_edges("join", _before_grade)
            builder.add_conditional_edges("grade", _before_generate)
            builder.add_conditional_edges("generate", _before_verify)
            builder.add_conditional_edges("verify", _after_verify)
        else:
            builder.add_conditional_edges("join", _before_generate)
            builder.add_conditional_edges("generate", _after_verify)

    async def _intent(self, state: _State) -> _State:
        started = time.perf_counter()
        question = state["request"].question
        if unicodedata.normalize("NFKC", question).strip().rstrip("!?。〜~ ") in GREETINGS:
            record("intent", started, "规则识别为闲聊")
            return {"intent": "smalltalk"}
        payload: dict[str, object] = {
            "question": question,
            "previous_intent": state["previous_intent"],
        }
        try:
            completion = await self._small.complete(
                model_messages("intent_v1", payload), json_mode=True, logprobs=True
            )
        except DependencyUnavailableError:
            record("intent", started, "分类模型不可用，按规程处理")
            return {"intent": "policy", "conservative": True}
        usage = [ModelUsage.from_completion(completion)]
        inferred = _parse_intent(completion)
        if inferred is None:
            record("intent", started, "分类输出不合法或置信度不足，按规程处理")
            return {"intent": "policy", "conservative": True, "usage": usage}
        note = (
            f"{inferred.intent} + {inferred.secondary_intent}"
            if inferred.secondary_intent
            else inferred.intent
        )
        if completion.confidence is not None:
            note += f"，置信度 {completion.confidence:.3f}"
        record("intent", started, note)
        return {
            "intent": inferred.intent,
            "secondary_intent": inferred.secondary_intent,
            "usage": usage,
        }

    async def _retrieve(self, state: _State) -> _State:
        request = state["request"]
        rewritten, usage = await self._standalone(state)
        question = rewritten or request.question
        started = time.perf_counter()
        update: _State = {"usage": usage}
        if rewritten:
            update["standalone_question"] = rewritten
        try:
            retrieved = await self._retriever.retrieve(
                question, filters=request.filter, rerank=request.rerank
            )
        except DependencyUnavailableError:
            record("retrieve", started, "规程检索不可用")
            return {**update, "failure": "retrieval_unavailable"}
        citations, policy_context = assemble(retrieved.parents)
        record(
            "retrieve",
            started,
            f"{len(retrieved.parents)} 个父块",
            StepDetails(retrievals=[retrieved], parents=retrieved.parents),
        )
        return {
            **update,
            "retrieved": retrieved,
            "policy_context": policy_context,
            "potential_citations": citations,
        }

    async def _standalone(self, state: _State) -> tuple[str | None, list[ModelUsage]]:
        previous = state.get("previous_policy_question")
        if state.get("intent") != "policy" or not previous:
            return None, []
        started = time.perf_counter()
        question = state["request"].question
        try:
            completion = await self._small.complete(
                model_messages(
                    "standalone_v2", {"previous_question": previous, "question": question}
                ),
                json_mode=True,
            )
        except DependencyUnavailableError:
            record("standalone", started, "独立化模型不可用，沿用原问")
            return None, []
        rewrite = (parse_object(completion.text) or {}).get("question")
        rewrite = redact_pii(rewrite.strip()) if isinstance(rewrite, str) else ""
        standalone = rewrite if rewrite != question and check_input(rewrite) is None else None
        record("standalone", started, "已独立化" if standalone else "沿用原问")
        return standalone, [ModelUsage.from_completion(completion)]

    async def _generate(self, state: _State) -> _State:
        started = time.perf_counter()
        policy_context = state.get("policy_context", "")
        question = state.get("standalone_question") or state["request"].question
        payload: dict[str, object] = {"question": question}
        evidence = [run.model_evidence() for run in state.get("tool_runs", [])]
        if evidence:
            payload["tools"] = evidence
            payload["question"] = state["request"].question
        if policy_context:
            payload["policies"] = policy_context
        kind = "mixed" if evidence and policy_context else "lookup" if evidence else "policy"
        try:
            completion = await self._complete_generation(
                model_messages(f"generate_{kind}_v1", payload), state.get("stream_tokens", False)
            )
        except DependencyUnavailableError:
            record("generate", started, "生成模型不可用")
            return {"failure": "generation"}
        raw = completion.text if state.get("stream_tokens") else completion.text.strip()
        citations = state.get("potential_citations", [])
        record(
            "generate",
            started,
            kind,
            StepDetails(context=policy_context or None),
        )
        update: _State = {"usage": [ModelUsage.from_completion(completion)]}
        if not raw.strip():
            return {**update, "failure": "evidence"}
        if not _validate_generation(raw, state, evidence):
            return {**update, "failure": "output_guard"}
        answer, used = resolve_citations(raw, citations)
        return {**update, "answer": answer, "citations": used}

    async def _complete_generation(
        self, messages: list[ChatMessage], stream_tokens: bool
    ) -> Completion:
        if not stream_tokens or not isinstance(self._large, StreamingChatModel):
            return await self._large.complete(messages)
        async for item in self._large.stream(messages):
            if isinstance(item, ChatDelta):
                get_stream_writer()(AnswerDelta(text=item.text))
            else:
                return item
        raise DependencyUnavailableError("模型流式响应提前结束")

    async def _grade(self, state: _State) -> _State:
        started = time.perf_counter()
        prompt = prompts.render(
            "grade_v1",
            question=state.get("standalone_question") or state["request"].question,
            contexts=_strict_context(state),
        )
        try:
            completion = await self._large.complete(
                [ChatMessage(role="user", content=prompt)], json_mode=True
            )
        except DependencyUnavailableError:
            record("grade", started, "证据评分不可用")
            return {"failure": "generation"}
        data = parse_object(completion.text) or {}
        sufficient = as_bool(data.get("sufficient"), True)
        record(
            "grade", started, "足够" if sufficient else "不足", StepDetails(sufficient=sufficient)
        )
        update: _State = {"usage": [ModelUsage.from_completion(completion)]}
        return update if sufficient else {**update, "failure": "evidence"}

    async def _verify(self, state: _State) -> _State:
        started = time.perf_counter()
        prompt = prompts.render(
            "verify_v1", contexts=_strict_context(state), answer=state["answer"]
        )
        try:
            completion = await self._large.complete(
                [ChatMessage(role="user", content=prompt)], json_mode=True
            )
        except DependencyUnavailableError:
            record("verify", started, "忠实度校验不可用")
            return {"failure": "generation"}
        faithful = as_bool((parse_object(completion.text) or {}).get("faithful"), True)
        record("verify", started, "通过" if faithful else "不通过")
        update: _State = {"usage": [ModelUsage.from_completion(completion)]}
        return update if faithful else {**update, "failure": "evidence"}


def _parse_intent(completion: Completion) -> _IntentResult | None:
    if completion.confidence is not None and completion.confidence < MIN_INTENT_CONFIDENCE:
        return None
    try:
        return _IntentResult.model_validate(parse_object(completion.text))
    except ValidationError:
        return None


def _guard(state: _State) -> _State:
    started = time.perf_counter()
    reason = check_input(state["request"].question)
    record("guard", started, reason or "通过")
    return {"failure": "guard"} if reason else {}


def _after_guard(state: _State) -> Literal["degrade", "intent"]:
    return "degrade" if state.get("failure") else "intent"


def _after_customer_intent(state: _State) -> Literal["direct", "escalate", "handoff", "retrieve"]:
    if "lookup" in (state["intent"], state.get("secondary_intent")):
        return "handoff"
    return _non_lookup_destination(state["intent"])


def _non_lookup_destination(intent: Intent) -> Literal["direct", "escalate", "retrieve"]:
    if intent == "smalltalk":
        return "direct"
    if intent == "complaint":
        return "escalate"
    return "retrieve"


def _after_agent_intent(
    state: _State,
) -> list[AfterAgentIntent]:
    if state.get("secondary_intent") is not None:
        return ["retrieve", "tool_branch"]
    if state["intent"] == "lookup":
        return ["tool_branch"]
    return [_non_lookup_destination(state["intent"])]


def _join(state: _State) -> _State:
    tool_status = state.get("tool_status")
    intents = (state["intent"], state.get("secondary_intent"))
    if "lookup" in intents and tool_status != "ok":
        return {"failure": "denied" if tool_status == "denied" else "failed"}
    if not state.get("failure") and "policy" in intents and not state.get("policy_context"):
        return {"failure": "empty_policy"}
    return {}


def _before_grade(state: _State) -> Literal["degrade", "grade"]:
    return "degrade" if state.get("failure") else "grade"


def _before_generate(state: _State) -> Literal["degrade", "generate"]:
    return "degrade" if state.get("failure") else "generate"


def _before_verify(state: _State) -> Literal["degrade", "verify"]:
    return "degrade" if state.get("failure") else "verify"


def _after_verify(state: _State) -> Literal["degrade", "__end__"]:
    return "degrade" if state.get("failure") else "__end__"


def _strict_context(state: _State) -> str:
    parts = [state.get("policy_context", "")]
    for run in state.get("tool_runs", []):
        parts.append(run.result.model_dump_json(include={"data", "total", "synthetic"}))
    return "\n\n".join(filter(None, parts))


def _validate_generation(raw: str, state: _State, evidence: list[dict[str, object]]) -> bool:
    started = time.perf_counter()
    request_filter = state["request"].filter
    as_of = request_filter.as_of if request_filter is not None else date.today()
    policy_context = state.get("policy_context", "")
    outcome = validate_output(
        raw,
        tool_evidence=evidence,
        policy_texts=(policy_context,) if policy_context else (),
        allowed_citations=state.get("potential_citations", []),
        active_document_ids=_active_documents(state.get("retrieved"), as_of),
        require_citations=bool(policy_context),
    )
    masked = redact_pii(raw)
    reasons = outcome.reasons if raw == masked else (*outcome.reasons, "personal_information")
    if reasons:
        record("output_guard", started, ",".join(reasons), StepDetails(output=masked))
        return False
    record("output_guard", started, "通过")
    return outcome.passed


def _active_documents(retrieved: RetrievalResult | None, as_of: date) -> set[str]:
    valid: set[str] = set()
    if retrieved is not None:
        for candidate in retrieved.candidates:
            policy = candidate.chunk.policy
            if (
                policy is not None
                and policy.status in {"online", "offline"}
                and policy.effective_from <= as_of
                and (policy.effective_to is None or as_of < policy.effective_to)
            ):
                valid.add(candidate.chunk.document_id)
    return valid


def _direct(state: _State) -> _State:
    return _fixed("direct")


def _escalate(state: _State) -> _State:
    return _fixed("escalate")


def _handoff(state: _State) -> _State:
    return {**_fixed("handoff"), "abstained": True}


def _fixed(node: str) -> _State:
    started = time.perf_counter()
    answer = prompts.render(f"{node}_v2" if node == "direct" else f"{node}_v1").strip()
    record(node, started)
    return {"answer": answer}


def _degrade(state: _State) -> _State:
    started = time.perf_counter()
    failure = state["failure"]
    filename = {
        "guard": "degrade_guard_v1",
        "denied": "degrade_denied_v1",
        "failed": "degrade_tool_v1",
        "empty_policy": "degrade_policy_v1",
        "retrieval_unavailable": "degrade_service_v1",
        "evidence": "degrade_policy_v1",
        "generation": "degrade_service_v1",
        "output_guard": "degrade_output_v1",
    }[failure]
    answer = prompts.render(filename).strip()
    record("degrade", started, failure)
    return {"answer": answer, "citations": []}


def _response(state: _State, steps: list[Step]) -> ChatResponse:
    intent = state.get("intent")
    usage = state.get("usage", [])
    retrieved = state.get("retrieved")
    parents = retrieved.parents if retrieved else []
    candidates = retrieved.candidates if retrieved else []
    answer = state["answer"]
    failure = state.get("failure")
    citations = state.get("citations", [])
    if state.get("conservative") and not failure:
        answer = f"{answer}\n\n{REPHRASE_TEXT}"
    return ChatResponse(
        answer=answer,
        route=intent or REFUSE,
        intent=intent,
        secondary_intent=state.get("secondary_intent"),
        citations=citations,
        steps=steps,
        tool_calls=[run.trace for run in state.get("tool_runs", [])],
        retrieved_docs=list(dict.fromkeys(candidate.chunk.document_id for candidate in candidates)),
        contexts=[parent.text for parent in parents],
        prompt_tokens=sum(item.prompt_tokens for item in usage),
        completion_tokens=sum(item.completion_tokens for item in usage),
        synthetic=_uses_synthetic_evidence(state, citations),
        cost_cny=sum(item.cost_cny for item in usage),
        abstained=bool(failure) or state.get("abstained", False),
        degraded=failure in ("denied", "failed", "retrieval_unavailable", "generation")
        or bool(retrieved and retrieved.degraded),
        standalone_question=state.get("standalone_question"),
    )


def _uses_synthetic_evidence(state: _State, citations: list[Citation]) -> bool:
    if any(run.result.synthetic for run in state.get("tool_runs", [])):
        return True
    result = state.get("retrieved")
    cited_docs = {citation.document_id for citation in citations}
    return result is not None and any(
        item.chunk.document_id in cited_docs
        and item.chunk.policy is not None
        and item.chunk.policy.synthetic
        for item in result.candidates
    )
