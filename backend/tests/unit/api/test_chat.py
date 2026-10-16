import json
from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.api import main as main_module
from app.api.services import get_services
from app.core.config import Settings
from app.core.errors import DependencyUnavailableError
from app.core.resilience import TokenBucketLimiter
from app.orchestration.factory import Services
from app.orchestration.models import ChatRequest, ChatResponse, Citation, Step
from app.retrieval.retriever import RetrievalResult


class StubChat:
    def __init__(self, *, fail_after_steps: bool = False) -> None:
        self.requests: list[ChatRequest] = []
        self._fail = fail_after_steps

    async def answer(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        return self._response()

    async def stream(self, request: ChatRequest) -> AsyncIterator[Step | ChatResponse]:
        self.requests.append(request)
        yield Step(name="guard", ms=0.1, note="通过")
        yield Step(name="route", ms=0.2, note="SINGLE")
        if self._fail:
            raise DependencyUnavailableError("数据库不可用")
        yield self._response()

    @staticmethod
    def _response() -> ChatResponse:
        return ChatResponse(
            answer="默认最多 5 个 [1]",
            route="SINGLE",
            citations=[Citation(index=1, document_id="d", heading_path="标题")],
            retrieved_docs=["d"],
            contexts=["很长的上下文，不应该返回给调用方"],
            cost_cny=0.01,
        )


class StubRetriever:
    async def retrieve(self, query: str, **kwargs: object) -> RetrievalResult:
        return RetrievalResult(query, [], [])


@pytest.fixture
def chat(app: FastAPI) -> StubChat:
    stub = StubChat()
    services = Services(retriever=StubRetriever(), chat=stub)  # type: ignore[arg-type]
    app.dependency_overrides[get_services] = lambda: services
    return stub


async def test_chat_returns_answer_citations_steps_and_the_trace_id(
    client: AsyncClient, chat: StubChat
) -> None:
    response = await client.post(
        "/chat", json={"question": " 一次最多上传几个文件 ", "edition": "cloud"}
    )

    body = response.json()
    assert response.status_code == 200
    assert body["answer"] == "默认最多 5 个 [1]"
    assert body["citations"] == [{"index": 1, "document_id": "d", "heading_path": "标题"}]
    assert body["trace_id"] == response.headers["X-Trace-Id"]
    assert "contexts" not in body
    assert chat.requests == [ChatRequest(question="一次最多上传几个文件", edition="cloud")]


async def test_session_id_is_passed_through(client: AsyncClient, chat: StubChat) -> None:
    await client.post("/chat", json={"question": "问", "session_id": "abc"})

    assert chat.requests[0].session_id == "abc"


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"question": ""},
        {"question": "   "},
        {"question": "x" * 501},
        {"question": "问", "edition": "mars"},
        {"question": "问", "session_id": ""},
    ],
)
async def test_invalid_requests_get_a_unified_422(
    client: AsyncClient, chat: StubChat, body: dict[str, object]
) -> None:
    response = await client.post("/chat", json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def _events(text: str) -> list[tuple[str, dict[str, object]]]:
    events = []
    for block in text.strip().split("\n\n"):
        name, data = block.split("\n")
        events.append((name.removeprefix("event: "), json.loads(data.removeprefix("data: "))))
    return events


async def test_stream_sends_step_events_then_the_answer(
    client: AsyncClient, chat: StubChat
) -> None:
    response = await client.post("/chat", json={"question": "问", "stream": True})

    assert response.headers["content-type"].startswith("text/event-stream")
    events = _events(response.text)
    assert [name for name, _ in events] == ["step", "step", "answer"]
    assert events[0][1]["name"] == "guard"
    assert events[2][1]["answer"] == "默认最多 5 个 [1]"
    assert events[2][1]["trace_id"] == response.headers["X-Trace-Id"]


async def test_stream_reports_errors_as_an_error_event(app: FastAPI, client: AsyncClient) -> None:
    services = Services(retriever=StubRetriever(), chat=StubChat(fail_after_steps=True))  # type: ignore[arg-type]
    app.dependency_overrides[get_services] = lambda: services

    response = await client.post("/chat", json={"question": "问", "stream": True})

    events = _events(response.text)
    assert [name for name, _ in events] == ["step", "step", "error"]
    assert events[-1][1] == {"code": "DEPENDENCY_UNAVAILABLE", "message": "数据库不可用"}


async def test_rate_limit_returns_a_unified_429_per_client(
    app: FastAPI, client: AsyncClient, chat: StubChat
) -> None:
    app.state.limiter = TokenBucketLimiter(per_minute=2)

    codes = [(await client.post("/chat", json={"question": "问"})).status_code for _ in range(3)]
    blocked = await client.post("/chat", json={"question": "问"})

    assert codes == [200, 200, 429]
    assert blocked.json()["error"]["code"] == "RATE_LIMITED"
    assert blocked.json()["trace_id"] == blocked.headers["X-Trace-Id"]


async def test_service_is_built_lazily_once_when_not_prewarmed(
    app: FastAPI, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    built: list[int] = []

    async def fake_build(engine: object, settings: object) -> Services:
        built.append(1)
        return Services(retriever=StubRetriever(), chat=StubChat())  # type: ignore[arg-type]

    monkeypatch.setattr("app.api.services.build_services", fake_build)
    app.state.engine = object()

    await client.post("/chat", json={"question": "问"})
    await client.post("/chat", json={"question": "问"})

    assert built == [1]


async def test_prewarm_builds_the_services_at_startup(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    services = Services(retriever=StubRetriever(), chat=StubChat())  # type: ignore[arg-type]

    async def fake_build(engine: object, settings: object) -> Services:
        return services

    monkeypatch.setattr(main_module, "build_services", fake_build)
    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(_env_file=None, prewarm=True))

    async with main_module.lifespan(app):
        assert app.state.services is services


async def test_failed_prewarm_does_not_stop_the_server(
    app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def failing_build(engine: object, settings: object) -> Services:
        raise DependencyUnavailableError("db")

    monkeypatch.setattr(main_module, "build_services", failing_build)
    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(_env_file=None, prewarm=True))

    async with main_module.lifespan(app):
        assert app.state.services is None
