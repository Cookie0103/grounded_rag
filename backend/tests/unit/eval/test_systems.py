from collections.abc import Sequence

import pytest

from app.providers.deepseek import cost_cny
from app.providers.fakes import FakeChatModel
from app.retrieval.retriever import (
    HYBRID,
    Candidate,
    ChunkInfo,
    ParentContext,
    RetrievalResult,
)
from eval.dataset import Question
from eval.systems import NaiveRagSystem, NoRetrievalSystem, RetrievalOnlySystem

QUESTION = Question("q1", "知识库最多上传几个文件", ("a",), edition="cloud")


class StubRetriever:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        editions: Sequence[str] | None = None,
        rerank: bool = True,
        mode: str = HYBRID,
    ) -> RetrievalResult:
        self.calls.append({"top_k": top_k, "editions": editions, "rerank": rerank, "mode": mode})
        chunks = [
            ChunkInfo(f"c{i}", doc, "p", "标题", "正文", "common") for i, doc in enumerate("aab")
        ]
        return RetrievalResult(
            query,
            [Candidate(rank=i, chunk=chunk) for i, chunk in enumerate(chunks, start=1)],
            [ParentContext("p", "a", "标题", "父块正文")],
        )


async def test_no_retrieval_baseline_asks_the_model_with_only_the_question() -> None:
    chat = FakeChatModel(responses=["最多 5 个"])

    answer = await NoRetrievalSystem(chat).answer(QUESTION)

    assert answer.answer == "最多 5 个"
    assert answer.retrieved_docs == ()
    assert answer.contexts == ()
    assert "知识库最多上传几个文件" in chat.calls[0][0].content
    assert answer.cost_cny == pytest.approx(cost_cny(*_tokens(chat)))


async def test_naive_rag_uses_vector_search_without_rerank() -> None:
    retriever, chat = StubRetriever(), FakeChatModel(responses=["答案"])

    answer = await NaiveRagSystem(retriever, chat).answer(QUESTION)

    assert retriever.calls == [
        {"top_k": 5, "editions": ("cloud", "common"), "rerank": False, "mode": "vector"}
    ]
    assert answer.answer == "答案"
    assert answer.retrieved_docs == ("a", "b")
    assert answer.contexts == ("父块正文",)
    prompt = chat.calls[0][0].content
    assert "父块正文" in prompt
    assert "知识库最多上传几个文件" in prompt
    assert answer.cost_cny > 0


async def test_retrieval_only_system_still_returns_no_answer() -> None:
    answer = await RetrievalOnlySystem(StubRetriever()).answer(QUESTION)

    assert answer.answer is None
    assert answer.retrieved_docs == ("a", "b")


def _tokens(chat: FakeChatModel) -> tuple[int, int]:
    prompt_chars = sum(len(m.content) for m in chat.calls[0])
    return prompt_chars // 2, len("最多 5 个") // 2
