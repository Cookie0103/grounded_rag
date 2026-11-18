from collections.abc import AsyncIterator

from app.db.conversation import Conversation
from app.orchestration.copilot_service import CopilotService
from app.orchestration.models import ChatRequest, ChatResponse, Intent, Step
from app.orchestration.observe import InMemoryTraceStore


class MemoryConversationStore:
    def __init__(self) -> None:
        self.stored: dict[str, Conversation] = {}

    async def get(self, thread_id: str) -> Conversation:
        return self.stored.get(thread_id, Conversation())

    async def save(self, thread_id: str, conversation: Conversation) -> None:
        self.stored[thread_id] = conversation


class RecordingGraph:
    def __init__(self) -> None:
        self.calls: list[tuple[ChatRequest, Intent | None, str | None]] = []

    async def stream(
        self,
        request: ChatRequest,
        *,
        previous_intent: Intent | None = None,
        previous_policy_question: str | None = None,
    ) -> AsyncIterator[Step | ChatResponse]:
        self.calls.append((request, previous_intent, previous_policy_question))
        yield Step(name="intent", ms=1, note="policy")
        yield ChatResponse(answer="規程を確認します。", route="policy", intent="policy")


async def test_session_progress_is_saved_with_channel_and_workbench_identity_isolation() -> None:
    conversations = MemoryConversationStore()
    graph = RecordingGraph()
    service = CopilotService(graph, conversations)
    workbench = ChatRequest(
        question="申込条件を教えてください。",
        channel="agent",
        session_id="synthetic-session",
        agent_id="A001",
        customer_id="C0001",
    )
    await service.answer(workbench)
    await service.answer(workbench.model_copy(update={"question": "必要な書類も教えてください。"}))
    await service.answer(workbench.model_copy(update={"customer_id": "C0002"}))
    await service.answer(workbench.model_copy(update={"channel": "customer"}))

    assert [call[1] for call in graph.calls] == [None, "policy", None, None]
    assert graph.calls[1][2] == workbench.question
    assert graph.calls[3][0].agent_id is graph.calls[3][0].customer_id is None
    assert len(conversations.stored) == 3
    assert all("synthetic-session" not in key for key in conversations.stored)


async def test_stream_records_observed_intent_without_workbench_identifiers() -> None:
    conversations = MemoryConversationStore()
    traces = InMemoryTraceStore()
    service = CopilotService(RecordingGraph(), conversations, traces=traces)
    request = ChatRequest(
        question="規程について確認します。", channel="agent", agent_id="A001", customer_id="C0001"
    )
    events = [item async for item in service.stream(request)]

    assert [type(item) for item in events] == [Step, ChatResponse]
    trace = next(iter(traces.records.values()))
    assert trace.route == "policy"
    assert trace.question == request.question
    encoded = trace.model_dump_json()
    assert "A001" not in encoded
    assert "C0001" not in encoded
    assert not conversations.stored
