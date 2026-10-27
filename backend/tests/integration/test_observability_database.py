from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.records import FeedbackIn, TraceRecord
from app.db.observability import PostgresInterventionStore, PostgresTraceStore
from app.orchestration.models import Step, StepDetails
from app.retrieval.retriever import Candidate, ChunkInfo, ParentContext, RetrievalResult

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
async def _clean(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.execute(text("TRUNCATE traces, feedback, interventions"))


def _record(trace_id: str, **kw: object) -> TraceRecord:
    return TraceRecord(
        trace_id=trace_id,
        question=f"问{trace_id}",
        route="SINGLE",
        answer="答",
        **kw,
    )


async def test_trace_round_trip_keeps_json_fields(engine: AsyncEngine) -> None:
    store = PostgresTraceStore(engine)
    retrieval = RetrievalResult(
        "版本限制",
        [Candidate(1, ChunkInfo("c1", "a", "p1", "标题", "子块正文", "cloud"), rrf_score=0.1)],
        [ParentContext("p1", "a", "标题", "父块正文")],
    )
    record = _record(
        "t1",
        edition="cloud",
        cost_cny=0.02,
        steps=[
            step.model_dump(mode="json")
            for step in (
                Step(name="retrieve", ms=1.5, details=StepDetails(retrievals=[retrieval])),
                Step(
                    name="grade", ms=1, details=StepDetails(sufficient=False, missing="缺少默认值")
                ),
                Step(name="generate", ms=2, details=StepDetails(context="[1] 原样\n上下文")),
            )
        ],
        retrieved_docs=["a", "b"],
        citations=[{"index": 1, "document_id": "a", "heading_path": "标题"}],
    )

    await store.save(record)
    loaded = await store.get("t1")

    assert loaded is not None
    assert loaded.created_at is not None
    assert loaded.model_copy(update={"created_at": None}) == record
    assert await store.get("missing") is None


async def test_saving_the_same_trace_twice_keeps_the_first(engine: AsyncEngine) -> None:
    store = PostgresTraceStore(engine)

    await store.save(_record("t1"))
    await store.save(_record("t1", abstained=True))

    loaded = await store.get("t1")
    assert loaded is not None
    assert not loaded.abstained


async def test_bad_cases_match_the_in_memory_semantics_and_respect_since(
    engine: AsyncEngine,
) -> None:
    store = PostgresTraceStore(engine)
    for item in (
        _record("ok"),
        _record("bad"),
        _record("abs", abstained=True),
        _record("deg", degraded=True),
        _record("both", abstained=True),
    ):
        await store.save(item)
    await store.add_feedback(FeedbackIn(trace_id="bad", rating="bad", comment="错"))
    await store.add_feedback(FeedbackIn(trace_id="ok", rating="good"))
    await store.add_feedback(FeedbackIn(trace_id="both", rating="bad"))

    cases = {case.trace_id: case.reason for case in await store.bad_cases()}

    assert cases == {
        "bad": "bad_feedback",
        "abs": "abstained",
        "deg": "degraded",
        "both": "bad_feedback",
    }
    assert await store.bad_cases(since=datetime.now(UTC) + timedelta(days=1)) == []


async def test_feedback_rating_is_constrained(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        with pytest.raises(IntegrityError):
            await connection.execute(
                text("INSERT INTO feedback (trace_id, rating) VALUES ('t', 'meh')")
            )


async def test_intervention_store_normalizes_questions_and_overwrites(engine: AsyncEngine) -> None:
    store = PostgresInterventionStore(engine)
    assert await store.get("问") is None

    await store.set("怎么上传？", "答案一")
    await store.set("怎么 上传", "答案二")

    assert await store.list_all() == [("怎么 上传", "答案二")]
    assert await store.get("怎么上传!") == "答案二"
    assert await store.remove("怎么上传")
    assert not await store.remove("怎么上传")
    assert await store.list_all() == []
