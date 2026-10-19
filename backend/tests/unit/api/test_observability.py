import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.api.services import get_services
from app.core.records import TraceRecord
from app.orchestration.factory import Services
from app.orchestration.observe import InMemoryTraceStore


class _Unused:
    pass


@pytest.fixture
def traces(app: FastAPI) -> InMemoryTraceStore:
    store = InMemoryTraceStore()
    services = Services(retriever=_Unused(), chat=_Unused(), traces=store)  # type: ignore[arg-type]
    app.dependency_overrides[get_services] = lambda: services
    return store


async def _seed(store: InMemoryTraceStore) -> None:
    await store.save(
        TraceRecord(
            trace_id="t1",
            question="问",
            route="SINGLE",
            answer="答",
            steps=[{"name": "guard", "ms": 0.1, "note": ""}],
            retrieved_docs=["d"],
        )
    )


async def test_trace_can_be_fetched_by_id(client: AsyncClient, traces: InMemoryTraceStore) -> None:
    await _seed(traces)

    response = await client.get("/traces/t1")

    body = response.json()
    assert response.status_code == 200
    assert (body["trace_id"], body["question"], body["route"]) == ("t1", "问", "SINGLE")
    assert body["steps"][0]["name"] == "guard"
    assert body["retrieved_docs"] == ["d"]


async def test_unknown_trace_is_a_unified_404(
    client: AsyncClient, traces: InMemoryTraceStore
) -> None:
    response = await client.get("/traces/nope")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TRACE_NOT_FOUND"


async def test_feedback_is_stored_for_an_existing_trace(
    client: AsyncClient, traces: InMemoryTraceStore
) -> None:
    await _seed(traces)

    response = await client.post(
        "/feedback", json={"trace_id": "t1", "rating": "bad", "comment": "答非所问"}
    )

    assert response.json() == {"status": "ok"}
    assert [(f.trace_id, f.rating, f.comment) for f in traces.feedback] == [
        ("t1", "bad", "答非所问")
    ]


async def test_feedback_for_an_unknown_trace_is_404_and_not_stored(
    client: AsyncClient, traces: InMemoryTraceStore
) -> None:
    response = await client.post("/feedback", json={"trace_id": "nope", "rating": "good"})

    assert response.status_code == 404
    assert traces.feedback == []


@pytest.mark.parametrize(
    "body",
    [{"trace_id": "t1", "rating": "meh"}, {"rating": "good"}, {"trace_id": "t1"}],
)
async def test_invalid_feedback_is_rejected(
    client: AsyncClient, traces: InMemoryTraceStore, body: dict[str, str]
) -> None:
    await _seed(traces)

    response = await client.post("/feedback", json=body)

    assert response.status_code == 422
    assert traces.feedback == []


async def test_endpoints_need_a_trace_store(app: FastAPI, client: AsyncClient) -> None:
    services = Services(retriever=_Unused(), chat=_Unused())  # type: ignore[arg-type]
    app.dependency_overrides[get_services] = lambda: services

    response = await client.get("/traces/t1")

    assert response.status_code == 503
