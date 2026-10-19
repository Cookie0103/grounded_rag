import asyncio
from typing import Any

import pytest

from app.core.cache import TtlCache
from app.core.errors import BudgetExceededError, ConfigError, DependencyUnavailableError
from app.orchestration import prompts
from app.orchestration.models import ChatRequest, ChatResponse, Step
from app.orchestration.pipeline import ChatPipeline
from app.orchestration.service import DEGRADED_NOTICE, ChatService
from app.providers.base import ChatMessage, Completion
from app.retrieval.retriever import RetrievalResult

from .test_pipeline import GRADE_OK, ROUTE_SINGLE, VERIFY_OK, ScriptedChat, StubRetriever, _json


def _chat(**overrides: str | list[str]) -> ScriptedChat:
    replies: dict[str, str | list[str]] = {
        "router": ROUTE_SINGLE,
        "rewrite": _json(query="改写"),
        "grade": GRADE_OK,
        "generate": "回答 [1]",
        "verify": VERIFY_OK,
    }
    return ScriptedChat(**{**replies, **overrides})


class BrokenChat:
    def __init__(self, error: Exception) -> None:
        self._error = error

    async def complete(self, messages: list[ChatMessage], *, json_mode: bool = False) -> Completion:
        raise self._error


class SlowChat(ScriptedChat):
    async def complete(self, messages: list[ChatMessage], *, json_mode: bool = False) -> Completion:
        await asyncio.sleep(5)
        return await super().complete(messages, json_mode=json_mode)


class DegradedRetriever(StubRetriever):
    async def retrieve(self, query: str, **kwargs: Any) -> RetrievalResult:
        result = await super().retrieve(query)
        return RetrievalResult(result.query, result.candidates, result.parents, degraded=True)


def _service(chat: Any, retriever: StubRetriever | None = None, **kw: Any) -> ChatService:
    retriever = retriever or StubRetriever()
    pipeline = ChatPipeline(chat, retriever)
    return ChatService(pipeline, retriever, answer_cache=TtlCache(10, 60), **kw)


async def test_pipeline_stream_yields_each_step_then_the_response() -> None:
    pipeline = ChatPipeline(_chat(), StubRetriever())

    items = [item async for item in pipeline.stream(ChatRequest(question="怎么上传"))]

    steps, response = items[:-1], items[-1]
    assert all(isinstance(step, Step) for step in steps)
    assert [step.name for step in steps if isinstance(step, Step)] == [
        "guard",
        "route",
        "rewrite",
        "retrieve",
        "grade",
        "generate",
        "verify",
    ]
    assert isinstance(response, ChatResponse)
    assert len(response.steps) == len(steps)


async def test_second_identical_question_is_served_from_the_answer_cache() -> None:
    chat, retriever = _chat(), StubRetriever()
    service = _service(chat, retriever)

    first = await service.answer(ChatRequest(question="怎么上传"))
    calls_after_first = len(chat.kinds)
    second = await service.answer(ChatRequest(question=" 怎么上传 "))

    assert not first.cached
    assert second.cached
    assert second.answer == first.answer
    assert len(chat.kinds) == calls_after_first  # 没有再调模型
    assert len(retriever.queries) == 1
    assert [step.name for step in second.steps] == ["answer_cache"]
    assert second.cost_cny == 0


async def test_cache_key_includes_edition_and_sessions_are_never_cached() -> None:
    service = _service(_chat())

    await service.answer(ChatRequest(question="问", edition="cloud"))
    other = await service.answer(ChatRequest(question="问", edition="self_host"))
    await service.answer(ChatRequest(question="问", session_id="s"))
    again = await service.answer(ChatRequest(question="问", session_id="s"))

    assert not other.cached
    assert not again.cached


async def test_abstained_answers_are_not_cached() -> None:
    chat = _chat(grade=_json(sufficient=False, missing="x"), retry_query=_json(query="再"))
    service = _service(chat)

    first = await service.answer(ChatRequest(question="问"))
    second = await service.answer(ChatRequest(question="问"))

    assert first.abstained
    assert not second.cached


@pytest.mark.parametrize(
    "error", [DependencyUnavailableError("DeepSeek 不可用"), BudgetExceededError("今天用完了")]
)
async def test_generation_outage_degrades_to_retrieved_snippets(error: Exception) -> None:
    service = _service(BrokenChat(error))

    response = await service.answer(ChatRequest(question="怎么上传"))

    assert response.degraded
    assert response.answer.startswith(DEGRADED_NOTICE)
    assert "doc-a 的正文" in response.answer
    assert [c.document_id for c in response.citations] == ["doc-a"]
    assert response.retrieved_docs == ["doc-a"]
    assert not response.abstained
    fallback = next(s for s in response.steps if s.name == "fallback_retrieve")
    assert fallback.name == "fallback_retrieve"
    assert fallback.details is not None
    assert fallback.details.retrievals[0].query == "怎么上传"
    assert fallback.details.context is None  # 这次没有生成调用


async def test_timeout_degrades_too() -> None:
    service = _service(SlowChat(router=ROUTE_SINGLE), timeout_seconds=0.05)

    response = await service.answer(ChatRequest(question="怎么上传"))

    assert response.degraded


async def test_generation_failure_keeps_completed_retrieval_steps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chat = _chat()
    original = chat.complete

    async def fail_generation(
        messages: list[ChatMessage], *, json_mode: bool = False
    ) -> Completion:
        if "只能**根据下面编号" in messages[-1].content:
            raise DependencyUnavailableError("生成失败")
        return await original(messages, json_mode=json_mode)

    monkeypatch.setattr(chat, "complete", fail_generation)

    response = await _service(chat).answer(ChatRequest(question="怎么上传"))

    assert response.degraded
    assert [step.name for step in response.steps] == [
        "guard",
        "route",
        "rewrite",
        "retrieve",
        "grade",
        "pipeline_error",
        "fallback_retrieve",
        "postprocess",
    ]
    retrieval = response.steps[3].details
    assert retrieval is not None
    assert retrieval.retrievals[0].query == "改写"


async def test_config_errors_are_not_hidden_by_degradation() -> None:
    service = _service(BrokenChat(ConfigError("没有密钥")))

    with pytest.raises(ConfigError):
        await service.answer(ChatRequest(question="怎么上传"))


async def test_service_stream_forwards_steps_and_ends_with_the_response() -> None:
    service = _service(_chat())

    items = [item async for item in service.stream(ChatRequest(question="怎么上传"))]

    assert isinstance(items[-1], ChatResponse)
    assert len(items) > 3


async def test_retrieval_degradation_is_reported_and_not_cached() -> None:
    service = _service(_chat(), DegradedRetriever())

    first = await service.answer(ChatRequest(question="怎么上传"))
    second = await service.answer(ChatRequest(question="怎么上传"))

    assert first.degraded
    assert not first.abstained
    assert not second.cached


def test_prompt_version_is_a_short_stable_hash() -> None:
    assert prompts.version() == prompts.version()
    assert len(prompts.version()) == 8
