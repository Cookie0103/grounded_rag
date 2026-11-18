"""问答服务负责会话顺序、资源生命周期和追踪。"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from hashlib import sha256
from typing import Protocol, cast
from weakref import WeakValueDictionary

from sqlalchemy.exc import SQLAlchemyError

from app.core.records import TraceRecord
from app.core.trace import NO_TRACE, new_trace_id, trace_id_var
from app.db.conversation import Conversation
from app.orchestration.models import INTENTS, ChatRequest, ChatResponse, Intent, Step
from app.orchestration.observe import TraceStore
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
    ) -> AsyncIterator[Step | ChatResponse]: ...


class ChatAccess(Protocol):
    async def answer(self, request: ChatRequest) -> ChatResponse: ...

    def stream(self, request: ChatRequest) -> AsyncIterator[Step | ChatResponse]: ...

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

    async def stream(self, request: ChatRequest) -> AsyncIterator[Step | ChatResponse]:
        if request.channel == "customer":
            request = request.model_copy(update={"agent_id": None, "customer_id": None})
        trace_id = trace_id_var.get()
        if trace_id == NO_TRACE:
            trace_id = new_trace_id()
        thread_id = _thread_id(request)
        with self._cloud.observe(request.question, trace_id, session_id=thread_id) as run:
            steps: list[Step] = []
            response: ChatResponse | None = None
            try:
                async with asyncio.timeout(CHAT_TIMEOUT_SECONDS):
                    async for item in self._turn(request, thread_id):
                        if isinstance(item, ChatResponse):
                            response = item
                        else:
                            steps.append(item)
                            run.step(item)
                            yield item
            except TimeoutError:
                response = ChatResponse(
                    answer=TIMEOUT_ANSWER,
                    route="timeout",
                    degraded=True,
                    abstained=True,
                    steps=steps,
                )
            if response is None:
                raise RuntimeError("问答图没有产出最终响应")
            checked = postprocess(response.answer)
            if checked.notes:
                step = Step(name="postprocess", ms=0.0, note="、".join(checked.notes))
                response = response.model_copy(
                    update={"answer": checked.answer, "steps": [*response.steps, step]}
                )
                if checked.blocked:
                    response = response.model_copy(
                        update={"answer": SAFE_ANSWER, "citations": [], "abstained": True}
                    )
                run.step(step)
                yield step
            record = self._trace_record(request, response, trace_id, thread_id)
            await self._save_trace(record)
            run.finish(record)
        yield response

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
        self, request: ChatRequest, thread_id: str | None
    ) -> AsyncIterator[Step | ChatResponse]:
        if thread_id is None:
            async for item in self._graph.stream(request):
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
                previous_policy_question=conversation.previous_policy_question,
            ):
                if isinstance(item, ChatResponse) and item.intent is not None:
                    previous_policy_question = conversation.previous_policy_question
                    intents = {item.intent, item.secondary_intent}
                    customer_handoff = request.channel == "customer" and "lookup" in intents
                    if "policy" in intents and not customer_handoff:
                        previous_policy_question = item.standalone_question or request.question
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
