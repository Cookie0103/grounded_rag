"""问答服务：在编排之上加整次问答的超时、完整回答缓存和降级（生成不可用时只返回检索片段）。"""

import asyncio
import logging
from collections.abc import AsyncIterator

from app.core.cache import TtlCache
from app.core.config import EDITION_FILTERS
from app.core.errors import BudgetExceededError, DependencyUnavailableError
from app.orchestration import prompts
from app.orchestration.models import ChatRequest, ChatResponse, Citation, Step
from app.orchestration.pipeline import ChatPipeline
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
    ) -> None:
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
        key = (request.question.strip(), request.edition, prompts.version())
        cacheable = not request.session_id  # 有会话的回答依赖历史，不缓存
        if cacheable and (cached := self._cache.get(key)) is not None:
            yield cached.model_copy(update={"cached": True})
            return
        final: ChatResponse | None = None
        try:
            async with asyncio.timeout(self._timeout):
                async for item in self._pipeline.stream(request):
                    if isinstance(item, ChatResponse):
                        final = item
                    else:
                        yield item
        except (DependencyUnavailableError, BudgetExceededError, TimeoutError) as error:
            logger.warning("生成不可用，降级为检索片段：%r", error)
            final = await self._fallback(request)
        if final is None:
            raise RuntimeError("编排没有产出 ChatResponse")
        if cacheable and not final.degraded and not final.abstained:
            self._cache.put(key, final)
        yield final

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
            degraded=True,
            abstained=not blocks,
        )
