from collections.abc import AsyncIterator

from app.db.conversation import Conversation
from app.orchestration.copilot_service import CopilotService
from app.orchestration.models import (
    AnswerDelta,
    AnswerRetraction,
    ChatRequest,
    ChatResponse,
    ChatStreamItem,
    Intent,
    Step,
    StepDetails,
)
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
        stream_tokens: bool = False,
    ) -> AsyncIterator[ChatStreamItem]:
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


async def test_redaction_precedes_graph_and_trace_recording() -> None:
    graph = RecordingGraph()
    traces = InMemoryTraceStore()
    service = CopilotService(graph, MemoryConversationStore(), traces=traces)
    contacts = "連絡先は090-1234-5678、メールは test@example.invalid です。"

    await service.answer(ChatRequest(question=contacts))

    masked = graph.calls[0][0].question
    assert "［電話番号］" in masked
    assert "［メールアドレス］" in masked
    assert "090-1234-5678" not in masked
    assert "test@example.invalid" not in masked
    assert next(iter(traces.records.values())).question == masked


async def test_stream_retracts_visible_unsafe_output_and_records_both_latency_values() -> None:
    class GuardedGraph(RecordingGraph):
        async def stream(
            self,
            request: ChatRequest,
            *,
            previous_intent: Intent | None = None,
            previous_policy_question: str | None = None,
            stream_tokens: bool = False,
        ) -> AsyncIterator[ChatStreamItem]:
            blocked = Step(
                name="output_guard",
                ms=1,
                note="unsupported_number",
                details=StepDetails(output="手数料は123円です。"),
            )
            if stream_tokens:
                yield AnswerDelta(text="手数料は123円です。")
            yield blocked
            yield ChatResponse(
                answer="回答を控えます。", route="policy", intent="policy", steps=[blocked]
            )

    traces = InMemoryTraceStore()
    service = CopilotService(GuardedGraph(), MemoryConversationStore(), traces=traces)
    events = [
        event
        async for event in service.stream(ChatRequest(question="手数料は？"), stream_tokens=True)
    ]
    assert events[2] == AnswerRetraction(
        replacement="回答を控えます。", reasons=("unsupported_number",)
    )
    result = events[-1]
    assert isinstance(result, ChatResponse)
    assert result.first_token_ms is not None
    assert result.total_ms is not None
    assert 0 <= result.first_token_ms <= result.total_ms
    record = next(iter(traces.records.values()))
    assert record.steps[0]["details"]["output"] == "手数料は123円です。"
    assert record.steps[-1]["details"]["first_token_ms"] == result.first_token_ms
    assert record.steps[-1]["details"]["total_ms"] == result.total_ms
