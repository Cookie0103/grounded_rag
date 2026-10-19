"""被测系统：给一道题，返回回答（或只返回检索结果）、路由、耗时、成本。"""

import time
from dataclasses import asdict, dataclass
from typing import Any, Protocol

from app.core.config import EDITION_FILTERS, FINAL_TOP_K
from app.orchestration.models import ChatRequest, Step, StepDetails
from app.orchestration.pipeline import ChatPipeline
from app.providers.base import ChatMessage, ChatModel, Completion
from app.providers.deepseek import cost_cny
from app.retrieval.retriever import VECTOR, Retriever
from eval.dataset import Question
from eval.judge import fill_template
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
    steps: tuple[Step, ...] = ()

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["steps"] = [step.model_dump(mode="json") for step in self.steps]
        return data

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
            steps=tuple(Step.model_validate(step) for step in data.get("steps", [])),
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
            steps=(
                Step(
                    name="retrieve",
                    ms=result.timings_ms.get("total", 0.0),
                    details=StepDetails(retrievals=[result]),
                ),
            ),
        )


def _completion_cost(completion: Completion) -> float:
    return cost_cny(completion.prompt_tokens, completion.completion_tokens)


class NoRetrievalSystem:
    """基线一：不检索，直接问模型。"""

    name = "无检索"

    def __init__(self, chat: ChatModel) -> None:
        self._chat = chat

    async def answer(self, question: Question) -> SystemAnswer:
        started = time.perf_counter()
        prompt = fill_template("baseline_no_retrieval_v1.md", question=question.question)
        completion = await self._chat.complete([ChatMessage(role="user", content=prompt)])
        return SystemAnswer(
            question_id=question.id,
            answer=completion.text,
            route=None,
            retrieved_docs=(),
            contexts=(),
            latency_ms=(time.perf_counter() - started) * 1000,
            cost_cny=_completion_cost(completion),
            steps=(
                Step(
                    name="generate",
                    ms=(time.perf_counter() - started) * 1000,
                    details=StepDetails(context="", output=completion.text),
                ),
            ),
        )


class NaiveRagSystem:
    """基线二：向量检索前 5 → 拼上下文 → 生成。不精排、不路由、不要求引用。"""

    name = "朴素 RAG"

    def __init__(
        self,
        retriever: Retriever,
        chat: ChatModel,
        *,
        top_k: int = FINAL_TOP_K,
        mode: str = VECTOR,
        rerank: bool = False,
        name: str | None = None,
    ) -> None:
        """mode / rerank 默认是朴素基线；改成混合 + 精排就是消融里的「+ 混合检索与精排」。"""
        self._retriever = retriever
        self._chat = chat
        self._top_k = top_k
        self._mode = mode
        self._rerank = rerank
        if name is not None:
            self.name = name

    async def answer(self, question: Question) -> SystemAnswer:
        editions = EDITION_FILTERS[question.edition] if question.edition else None
        started = time.perf_counter()
        result = await self._retriever.retrieve(
            question.question,
            top_k=self._top_k,
            editions=editions,
            rerank=self._rerank,
            mode=self._mode,
        )
        contexts = tuple(parent.text for parent in result.parents)
        context = "\n\n---\n\n".join(contexts)
        prompt = fill_template(
            "baseline_naive_rag_v1.md",
            question=question.question,
            contexts=context,
        )
        generated = time.perf_counter()
        completion = await self._chat.complete([ChatMessage(role="user", content=prompt)])
        return SystemAnswer(
            question_id=question.id,
            answer=completion.text,
            route=None,
            retrieved_docs=tuple(
                ranked_documents([c.chunk.document_id for c in result.candidates])
            ),
            contexts=contexts,
            latency_ms=(time.perf_counter() - started) * 1000,
            cost_cny=_completion_cost(completion),
            steps=(
                Step(
                    name="retrieve",
                    ms=(generated - started) * 1000,
                    details=StepDetails(retrievals=[result]),
                ),
                Step(
                    name="generate",
                    ms=(time.perf_counter() - generated) * 1000,
                    details=StepDetails(context=context, output=completion.text),
                ),
            ),
        )


class FullSystem:
    """完整系统：护栏、路由、改写 / 分解、证据评分、带引用生成、忠实度校验。"""

    name = "完整系统"

    def __init__(self, pipeline: ChatPipeline, *, name: str | None = None) -> None:
        self._pipeline = pipeline
        if name is not None:
            self.name = name

    async def answer(self, question: Question) -> SystemAnswer:
        started = time.perf_counter()
        response = await self._pipeline.answer(
            ChatRequest(question=question.question, edition=question.edition)
        )
        return SystemAnswer(
            question_id=question.id,
            answer=response.answer,
            route=response.route,
            retrieved_docs=tuple(response.retrieved_docs),
            contexts=tuple(response.contexts),
            latency_ms=(time.perf_counter() - started) * 1000,
            cost_cny=response.cost_cny,
            steps=tuple(response.steps),
        )
