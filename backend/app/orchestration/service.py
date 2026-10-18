"""问答服务：在编排之上加整次问答的超时、完整回答缓存和降级（生成不可用时只返回检索片段）。"""

import asyncio
import logging
from collections.abc import AsyncIterator

from sqlalchemy.exc import SQLAlchemyError

from app.core.cache import TtlCache
from app.core.config import EDITION_FILTERS
from app.core.errors import BudgetExceededError, DependencyUnavailableError
from app.core.records import TraceRecord
from app.core.trace import NO_TRACE, new_trace_id, trace_id_var
from app.orchestration import prompts
from app.orchestration.models import (
    ABSTAIN_TEXT,
    ChatRequest,
    ChatResponse,
    Citation,
    Step,
    StepDetails,
)
from app.orchestration.observe import InterventionStore, TraceStore
from app.orchestration.pipeline import ChatPipeline
from app.orchestration.postprocess import postprocess
from app.retrieval.retriever import Retriever

logger = logging.getLogger(__name__)
CHAT_TIMEOUT_SECONDS = 90.0
FALLBACK_TOP_K = 3
SNIPPET_CHARS = 300
DEGRADED_NOTICE = "生成服务暂时不可用，下面是检索到的相关文档片段：\n\n"
type AnswerKey = tuple[str, str | None, str]


class ChatService:
    def __init__(
        self,
        pipeline: ChatPipeline,
        retriever: Retriever,
        *,
        answer_cache: TtlCache[AnswerKey, ChatResponse],
        timeout_seconds: float = CHAT_TIMEOUT_SECONDS,
        traces: TraceStore | None = None,
        interventions: InterventionStore | None = None,
    ) -> None:
        self._traces = traces
        self._interventions = interventions
        self._pipeline = pipeline
        self._retriever = retriever
        self._cache = answer_cache
        self._timeout = timeout_seconds

    async def answer(self, request: ChatRequest) -> ChatResponse:
        response: ChatResponse | None = None
        async for item in self.stream(request):
            if isinstance(item, ChatResponse):
                response = item
        if response is None:
            raise RuntimeError("stream 没有产出 ChatResponse")
        return response

    async def stream(self, request: ChatRequest) -> AsyncIterator[Step | ChatResponse]:
        async for item in self._run(request):
            if isinstance(item, ChatResponse):
                await self._record(request, item)
            yield item

    async def _record(self, request: ChatRequest, response: ChatResponse) -> None:
        """保存 trace；保存失败只记日志，不影响回答。"""
        if self._traces is None:
            return
        trace_id = trace_id_var.get()
        record = TraceRecord(
            trace_id=new_trace_id() if trace_id == NO_TRACE else trace_id,
            question=request.question,
            route=response.route,
            edition=request.edition,
            session_id=request.session_id,
            answer=response.answer,
            abstained=response.abstained,
            degraded=response.degraded,
            cached=response.cached,
            cost_cny=response.cost_cny,
            steps=[step.model_dump() for step in response.steps],
            retrieved_docs=response.retrieved_docs,
            citations=[citation.model_dump() for citation in response.citations],
        )
        try:
            await self._traces.save(record)
        except (SQLAlchemyError, OSError) as error:
            logger.warning("trace 保存失败：%r", error)

    async def _intervention(self, request: ChatRequest) -> ChatResponse | None:
        if self._interventions is None:
            return None
        try:
            answer = await self._interventions.get(request.question)
        except (SQLAlchemyError, OSError) as error:
            logger.warning("干预库不可用，按正常流程回答：%r", error)
            return None
        if answer is None:
            return None
        return ChatResponse(
            answer=answer,
            route="INTERVENED",
            steps=[Step(name="intervention", ms=0.0, note="命中干预库")],
        )

    async def _run(self, request: ChatRequest) -> AsyncIterator[Step | ChatResponse]:
        intervened = await self._intervention(request)
        if intervened is not None:
            yield intervened
            return
        key = (request.question.strip(), request.edition, prompts.version())
        cacheable = not request.session_id  # 有会话的回答依赖历史，不缓存
        if cacheable and (cached := self._cache.get(key)) is not None:
            yield cached.model_copy(update={"cached": True})
            return
        final: ChatResponse | None = None
        steps: list[Step] = []
        try:
            async with asyncio.timeout(self._timeout):
                async for item in self._pipeline.stream(request):
                    if isinstance(item, ChatResponse):
                        final = item
                    else:
                        steps.append(item)
                        yield item
        except (DependencyUnavailableError, BudgetExceededError, TimeoutError) as error:
            logger.warning("生成不可用，降级为检索片段：%r", error)
            final = await self._fallback(request)
            final = final.model_copy(update={"steps": [*steps, *final.steps]})
        if final is None:
            raise RuntimeError("编排没有产出 ChatResponse")
        final = self._postprocess(final)
        if cacheable and not final.degraded and not final.abstained:
            self._cache.put(key, final)
        yield final

    @staticmethod
    def _postprocess(response: ChatResponse) -> ChatResponse:
        result = postprocess(response.answer)
        if result.blocked:
            return response.model_copy(
                update={"answer": ABSTAIN_TEXT, "abstained": True, "citations": []}
            )
        if not result.notes:
            return response
        step = Step(name="postprocess", ms=0.0, note="；".join(result.notes))
        return response.model_copy(
            update={"answer": result.answer, "steps": [*response.steps, step]}
        )

    async def _fallback(self, request: ChatRequest) -> ChatResponse:
        editions = EDITION_FILTERS.get(request.edition or "")
        result = await self._retriever.retrieve(
            request.question, top_k=FALLBACK_TOP_K, editions=editions, rerank=False
        )
        citations: list[Citation] = []
        blocks: list[str] = []
        for index, parent in enumerate(result.parents, start=1):
            citations.append(
                Citation(
                    index=index, document_id=parent.document_id, heading_path=parent.heading_path
                )
            )
            snippet = parent.text[:SNIPPET_CHARS]
            blocks.append(f"[{index}] {parent.document_id}｜{parent.heading_path}\n{snippet}")
        return ChatResponse(
            answer=DEGRADED_NOTICE + "\n\n".join(blocks),
            route="SINGLE",
            citations=citations,
            retrieved_docs=list(dict.fromkeys(c.chunk.document_id for c in result.candidates)),
            contexts=[parent.text for parent in result.parents],
            steps=[
                Step(
                    name="fallback_retrieve",
                    ms=result.timings_ms.get("total", 0.0),
                    details=StepDetails(retrievals=[result]),
                )
            ],
            degraded=True,
            abstained=not blocks,
        )
