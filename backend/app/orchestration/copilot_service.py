"""问答服务负责会话顺序、资源生命周期和追踪。"""

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from hashlib import sha256
from typing import Protocol, cast
from weakref import WeakValueDictionary

from sqlalchemy.exc import SQLAlchemyError

from app.core.records import TraceRecord
from app.core.trace import NO_TRACE, new_trace_id, trace_id_var
from app.db.conversation import Conversation
from app.orchestration.models import (
    INTENTS,
    AnswerDelta,
    AnswerRetraction,
    ChatRequest,
    ChatResponse,
    ChatStreamItem,
    Intent,
    Step,
    StepDetails,
)
from app.orchestration.observe import TraceStore
from app.orchestration.pii import redact_pii
from app.orchestration.postprocess import postprocess
from app.providers.cloud_trace import CloudTracer

logger = logging.getLogger(__name__)
CHAT_TIMEOUT_SECONDS = 90.0
TIMEOUT_ANSWER = "応答に時間がかかっています。担当者にお問い合わせください。"
SAFE_ANSWER = "回答を確認できませんでした。担当者にお問い合わせください。"


class ConversationStore(Protocol):
    async def get(self, thread_id: str) -> Conversation: ...

    async def save(self, thread_id: str, conversation: Conversation) -> None: ...


class CopilotFlow(Protocol):
    def stream(
        self,
        request: ChatRequest,
        *,
        previous_intent: Intent | None = None,
        previous_policy_question: str | None = None,
        stream_tokens: bool = False,
    ) -> AsyncIterator[ChatStreamItem]: ...


class ChatAccess(Protocol):
    async def answer(self, request: ChatRequest) -> ChatResponse: ...

    def stream(
        self, request: ChatRequest, *, stream_tokens: bool = False
    ) -> AsyncIterator[ChatStreamItem]: ...

    async def close(self) -> None: ...


class CopilotService:
    def __init__(
        self,
        graph: CopilotFlow,
        conversations: ConversationStore,
        *,
        traces: TraceStore | None = None,
        cloud: CloudTracer | None = None,
        resources: AsyncExitStack | None = None,
    ) -> None:
        self._graph = graph
        self._conversations = conversations
        self._traces = traces
        self._cloud = cloud or CloudTracer()
        self._resources = resources or AsyncExitStack()
        self._locks: WeakValueDictionary[str, asyncio.Lock] = WeakValueDictionary()

    async def answer(self, request: ChatRequest) -> ChatResponse:
        async for item in self.stream(request):
            if isinstance(item, ChatResponse):
                return item
        raise RuntimeError("问答图没有产出最终响应")

    async def stream(
        self, request: ChatRequest, *, stream_tokens: bool = False
    ) -> AsyncIterator[ChatStreamItem]:
        started = time.perf_counter()
        request = _prepared_request(request)
        current_trace = trace_id_var.get()
        trace_id = new_trace_id() if current_trace == NO_TRACE else current_trace
        thread_id = _thread_id(request)
        visible: list[str] = []
        first_token_ms: float | None = None
        with self._cloud.observe(request.question, trace_id, session_id=thread_id) as run:
            response: ChatResponse | None = None
            async for item in self._timed_turn(request, thread_id, stream_tokens):
                if isinstance(item, ChatResponse):
                    response = item
                    continue
                if isinstance(item, Step):
                    run.step(item)
                elif isinstance(item, AnswerDelta):
                    if first_token_ms is None:
                        first_token_ms = _elapsed_ms(started)
                    visible.append(item.text)
                yield item
            if response is None:
                raise RuntimeError("问答图没有产出最终响应")
            response, postprocess_step = _postprocess(response)
            if postprocess_step is not None:
                run.step(postprocess_step)
                yield postprocess_step
            if stream_tokens and (adjustment := _adjust_visible(response, visible)) is not None:
                if first_token_ms is None:
                    first_token_ms = _elapsed_ms(started)
                yield adjustment
            response, timing_step = _with_timing(response, first_token_ms, _elapsed_ms(started))
            run.step(timing_step)
            record = self._trace_record(request, response, trace_id, thread_id)
            await self._save_trace(record)
            run.finish(record)
        yield response

    async def _timed_turn(
        self, request: ChatRequest, thread_id: str | None, stream_tokens: bool
    ) -> AsyncIterator[ChatStreamItem]:
        steps: list[Step] = []
        try:
            async with asyncio.timeout(CHAT_TIMEOUT_SECONDS):
                async for item in self._turn(request, thread_id, stream_tokens):
                    if isinstance(item, Step):
                        steps.append(item)
                    yield item
        except TimeoutError:
            yield ChatResponse(
                answer=TIMEOUT_ANSWER, route="timeout", degraded=True, abstained=True, steps=steps
            )

    async def _save_trace(self, record: TraceRecord) -> None:
        if self._traces is not None:
            try:
                await self._traces.save(record)
            except (SQLAlchemyError, OSError) as error:
                logger.warning("trace 保存失败：%s", type(error).__name__)

    async def close(self) -> None:
        try:
            await self._cloud.close()
        finally:
            await self._resources.aclose()

    async def _turn(
        self, request: ChatRequest, thread_id: str | None, stream_tokens: bool
    ) -> AsyncIterator[ChatStreamItem]:
        if thread_id is None:
            async for item in self._graph.stream(request, stream_tokens=stream_tokens):
                yield item
            return

        lock = self._locks.get(thread_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[thread_id] = lock
        async with lock:
            conversation = await self._conversations.get(thread_id)
            previous_intent = (
                cast(Intent, conversation.previous_intent)
                if conversation.previous_intent in INTENTS
                else None
            )
            async for item in self._graph.stream(
                request,
                previous_intent=previous_intent,
                previous_policy_question=redact_pii(conversation.previous_policy_question)
                if conversation.previous_policy_question
                else None,
                stream_tokens=stream_tokens,
            ):
                if isinstance(item, ChatResponse) and item.intent is not None:
                    previous_policy_question = conversation.previous_policy_question
                    intents = {item.intent, item.secondary_intent}
                    customer_handoff = request.channel == "customer" and "lookup" in intents
                    if "policy" in intents and not customer_handoff:
                        previous_policy_question = redact_pii(
                            item.standalone_question or request.question
                        )
                    await self._conversations.save(
                        thread_id, Conversation(item.intent, previous_policy_question)
                    )
                yield item

    @staticmethod
    def _trace_record(
        request: ChatRequest, response: ChatResponse, trace_id: str, thread_id: str | None
    ) -> TraceRecord:
        return TraceRecord(
            trace_id=trace_id,
            question=request.question,
            route=response.route,
            session_id=thread_id,
            answer=response.answer,
            abstained=response.abstained,
            degraded=response.degraded,
            cost_cny=response.cost_cny,
            steps=[step.model_dump(mode="json") for step in response.steps],
            retrieved_docs=response.retrieved_docs,
            citations=[citation.model_dump() for citation in response.citations],
        )


def _thread_id(request: ChatRequest) -> str | None:
    """对会话加泳道和工作台作用域后再做散列，避免会话 ID 或身份写入追踪。"""
    if request.session_id is None:
        return None
    if request.channel == "agent" and not (request.agent_id and request.customer_id):
        return None
    key = json.dumps((request.channel, request.agent_id, request.customer_id, request.session_id))
    return sha256(key.encode()).hexdigest()


def _prepared_request(request: ChatRequest) -> ChatRequest:
    fields: dict[str, object] = {"question": redact_pii(request.question)}
    if request.channel == "customer":
        fields.update(agent_id=None, customer_id=None)
    return request.model_copy(update=fields)


def _elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000


def _postprocess(response: ChatResponse) -> tuple[ChatResponse, Step | None]:
    checked = postprocess(response.answer)
    if not checked.notes:
        return response, None
    step = Step(name="postprocess", ms=0.0, note="、".join(checked.notes))
    updates: dict[str, object] = {"answer": checked.answer, "steps": [*response.steps, step]}
    if checked.blocked:
        updates.update(answer=SAFE_ANSWER, citations=[], abstained=True)
    return response.model_copy(update=updates), step


def _adjust_visible(
    response: ChatResponse, fragments: list[str]
) -> AnswerDelta | AnswerRetraction | None:
    visible = "".join(fragments)
    if visible == response.answer:
        return None
    if response.answer.startswith(visible):
        return AnswerDelta(text=response.answer[len(visible) :])
    reasons = next(
        (
            tuple(step.note.split(","))
            for step in reversed(response.steps)
            if step.name == "output_guard" and step.details and step.details.output is not None
        ),
        ("answer_replaced",),
    )
    return AnswerRetraction(replacement=response.answer, reasons=reasons)


def _with_timing(
    response: ChatResponse, first_token_ms: float | None, total_ms: float
) -> tuple[ChatResponse, Step]:
    timing = Step(
        name="latency",
        ms=total_ms,
        details=StepDetails(first_token_ms=first_token_ms, total_ms=total_ms),
    )
    return response.model_copy(
        update={
            "first_token_ms": first_token_ms,
            "total_ms": total_ms,
            "steps": [*response.steps, timing],
        },
    ), timing
