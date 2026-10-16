"""被测系统：给一道题，返回回答（或只返回检索结果）、路由、耗时、成本。"""

import time
from dataclasses import asdict, dataclass
from typing import Any, Protocol

from app.core.config import EDITION_FILTERS, FINAL_TOP_K
from app.retrieval.retriever import Retriever
from eval.dataset import Question
from eval.metrics import ranked_documents


@dataclass(frozen=True)
class SystemAnswer:
    question_id: str
    answer: str | None  # 只检索的系统没有回答
    route: str | None
    retrieved_docs: tuple[str, ...]  # 文档 ID，按名次，去重
    contexts: tuple[str, ...]  # 交给大模型的上下文（父块文本）
    latency_ms: float
    cost_cny: float = 0.0
    error: str | None = None

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_json(data: dict[str, Any]) -> "SystemAnswer":
        return SystemAnswer(
            question_id=data["question_id"],
            answer=data["answer"],
            route=data["route"],
            retrieved_docs=tuple(data["retrieved_docs"]),
            contexts=tuple(data["contexts"]),
            latency_ms=data["latency_ms"],
            cost_cny=data.get("cost_cny", 0.0),
            error=data.get("error"),
        )


class System(Protocol):
    name: str

    async def answer(self, question: Question) -> SystemAnswer: ...


class RetrievalOnlySystem:
    """只做检索，不生成回答：用来出检索指标（Recall@5），不需要大模型。"""

    name = "只检索"

    def __init__(
        self, retriever: Retriever, *, top_k: int = FINAL_TOP_K, rerank: bool = True
    ) -> None:
        self._retriever = retriever
        self._top_k = top_k
        self._rerank = rerank

    async def answer(self, question: Question) -> SystemAnswer:
        editions = EDITION_FILTERS[question.edition] if question.edition else None
        started = time.perf_counter()
        result = await self._retriever.retrieve(
            question.question, top_k=self._top_k, editions=editions, rerank=self._rerank
        )
        return SystemAnswer(
            question_id=question.id,
            answer=None,
            route=None,
            retrieved_docs=tuple(
                ranked_documents([c.chunk.document_id for c in result.candidates])
            ),
            contexts=tuple(parent.text for parent in result.parents),
            latency_ms=(time.perf_counter() - started) * 1000,
        )
