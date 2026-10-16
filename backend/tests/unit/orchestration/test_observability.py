from typing import Any

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core.cache import TtlCache
from app.core.records import FeedbackIn, TraceRecord
from app.core.text import question_key
from app.core.trace import trace_id_var
from app.orchestration.models import ABSTAIN_TEXT, ChatRequest
from app.orchestration.observe import InMemoryInterventionStore, InMemoryTraceStore
from app.orchestration.pipeline import ChatPipeline
from app.orchestration.postprocess import (
    MASK_TEXT,
    collapse_repeats,
    postprocess,
)
from app.orchestration.service import ChatService

from .test_pipeline import GRADE_OK, ROUTE_SINGLE, VERIFY_OK, ScriptedChat, StubRetriever, _json


def _chat(generate: str = "默认最多 5 个 [1]") -> ScriptedChat:
    return ScriptedChat(
        router=ROUTE_SINGLE,
        rewrite=_json(query="改写"),
        grade=GRADE_OK,
        generate=generate,
        verify=VERIFY_OK,
    )


def _service(chat: ScriptedChat, **kw: Any) -> ChatService:
    retriever = StubRetriever()
    return ChatService(
        ChatPipeline(chat, retriever), retriever, answer_cache=TtlCache(10, 60), **kw
    )


# ------------------------------------------------------------------ 后处理


def test_api_keys_and_bearer_tokens_are_masked() -> None:
    result = postprocess("密钥是 sk-abcdefghijklmnop1234，头是 Bearer abcdefghijklmnop12.34")

    assert result.answer == f"密钥是 {MASK_TEXT}，头是 {MASK_TEXT}"
    assert result.notes == ["遮蔽了疑似密钥"] * 2


def test_blocked_terms_block_the_whole_answer() -> None:
    result = postprocess("这里有违禁词甲", blocked_terms=("违禁词甲",))

    assert result.blocked
    assert postprocess("正常内容", blocked_terms=("违禁词甲", "")).blocked is False


def test_sentences_repeated_more_than_twice_are_collapsed_but_short_ones_kept() -> None:
    text = "请检查配置。请检查配置。请检查配置。请检查配置。是。是。是。其他说明。"

    assert collapse_repeats(text) == "请检查配置。请检查配置。是。是。是。其他说明。"


def test_normal_answers_are_untouched() -> None:
    result = postprocess("默认最多 5 个 [1]。需要修改请设置 UPLOAD_FILE_BATCH_LIMIT。")

    assert result.notes == []
    assert result.answer.startswith("默认最多")


async def test_service_masks_secrets_and_records_a_postprocess_step() -> None:
    service = _service(_chat("用这个 sk-abcdefghijklmnop1234 [1]"))

    response = await service.answer(ChatRequest(question="问"))

    assert MASK_TEXT in response.answer
    assert "sk-abc" not in response.answer
    assert response.steps[-1].name == "postprocess"


async def test_service_replaces_blocked_answers_with_an_abstention(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.orchestration.postprocess.BLOCKED_TERMS", ("默认",))

    response = await _service(_chat()).answer(ChatRequest(question="问"))

    assert (response.answer, response.abstained, response.citations) == (ABSTAIN_TEXT, True, [])


# ------------------------------------------------------------------ trace


async def test_every_answer_is_saved_with_the_request_trace_id() -> None:
    traces = InMemoryTraceStore()
    service = _service(_chat(), traces=traces)
    token = trace_id_var.set("trace-1")
    try:
        await service.answer(ChatRequest(question="问", edition="cloud", session_id="s"))
        await service.answer(ChatRequest(question="问", edition="cloud"))  # 第二次：缓存命中
    finally:
        trace_id_var.reset(token)

    record = traces.records["trace-1"]
    assert (record.question, record.route, record.edition, record.session_id) == (
        "问",
        "SINGLE",
        "cloud",
        "s",
    )
    assert record.retrieved_docs == ["doc-a"]
    assert record.citations[0]["document_id"] == "doc-a"
    assert [step["name"] for step in record.steps][:2] == ["guard", "route"]


async def test_requests_without_a_trace_id_get_a_fresh_one_each() -> None:
    traces = InMemoryTraceStore()
    service = _service(_chat(), traces=traces)

    await service.answer(ChatRequest(question="问一"))
    await service.answer(ChatRequest(question="问二"))

    assert len(traces.records) == 2


async def test_failing_trace_store_does_not_break_the_answer() -> None:
    class Broken(InMemoryTraceStore):
        async def save(self, record: TraceRecord) -> None:
            raise SQLAlchemyError("down")

    response = await _service(_chat(), traces=Broken()).answer(ChatRequest(question="问"))

    assert response.answer.startswith("默认最多")


# ------------------------------------------------------------------ 干预库


async def test_intervention_answers_before_cache_and_pipeline() -> None:
    chat, interventions, traces = _chat(), InMemoryInterventionStore(), InMemoryTraceStore()
    await interventions.set("知识库最多传几个文件？", "标准答案：5 个")
    service = _service(chat, interventions=interventions, traces=traces)

    response = await service.answer(ChatRequest(question=" 知识库 最多传几个文件 "))

    assert (response.answer, response.route) == ("标准答案：5 个", "INTERVENED")
    assert response.cost_cny == 0
    assert chat.kinds == []
    assert [step.name for step in response.steps] == ["intervention"]
    assert next(iter(traces.records.values())).route == "INTERVENED"


async def test_intervention_store_errors_fall_back_to_the_normal_flow() -> None:
    class Broken(InMemoryInterventionStore):
        async def get(self, question: str) -> str | None:
            raise OSError("down")

    response = await _service(_chat(), interventions=Broken()).answer(ChatRequest(question="问"))

    assert response.route == "SINGLE"


async def test_in_memory_intervention_store_contract() -> None:
    store = InMemoryInterventionStore()
    assert await store.get("问") is None

    await store.set("怎么上传？", "答案一")
    await store.set("怎么 上传", "答案二")  # 归一化后是同一个问题，覆盖

    assert await store.list_all() == [("怎么 上传", "答案二")]
    assert await store.get("怎么上传!") == "答案二"
    assert await store.remove("怎么上传")
    assert not await store.remove("怎么上传")


def test_question_key_ignores_case_spaces_and_punctuation() -> None:
    assert question_key("怎么上传？ API Key") == question_key("怎么上传，api key!")
    assert question_key("A") != question_key("B")


# ------------------------------------------------------------------ 坏例


async def test_bad_cases_pick_bad_feedback_then_abstained_then_degraded() -> None:
    traces = InMemoryTraceStore()

    def record(trace_id: str, **kw: Any) -> TraceRecord:
        return TraceRecord(
            trace_id=trace_id, question=f"问{trace_id}", route="SINGLE", answer="答", **kw
        )

    for item in (
        record("ok"),
        record("bad"),
        record("abs", abstained=True),
        record("deg", degraded=True),
        record("both", abstained=True),
    ):
        await traces.save(item)
    await traces.add_feedback(FeedbackIn(trace_id="bad", rating="bad"))
    await traces.add_feedback(FeedbackIn(trace_id="ok", rating="good"))
    await traces.add_feedback(FeedbackIn(trace_id="both", rating="bad"))

    cases = {case.trace_id: case.reason for case in await traces.bad_cases()}

    assert cases == {
        "bad": "bad_feedback",
        "abs": "abstained",
        "deg": "degraded",
        "both": "bad_feedback",
    }
