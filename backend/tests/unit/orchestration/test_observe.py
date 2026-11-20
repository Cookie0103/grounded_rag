from typing import Any

from app.core.records import FeedbackIn, TraceRecord
from app.core.text import question_key
from app.orchestration.observe import InMemoryInterventionStore, InMemoryTraceStore


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
