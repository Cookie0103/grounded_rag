import asyncio
import json
from collections.abc import Mapping, Sequence
from datetime import date

import pytest

from app.core.config import DEFAULT_POLICY_RERANK, FINAL_TOP_K
from app.core.policy import PolicyMetadata
from app.db.policy_filter import MetaFilter
from app.orchestration.copilot import CopilotGraph
from app.orchestration.models import AnswerDelta, Channel, ChatRequest, ChatResponse, Step
from app.providers.base import Completion, FunctionCall
from app.providers.fakes import FakeChatModel
from app.providers.mock_core import MockCoreReply, MockCoreRequest
from app.retrieval.retriever import HYBRID, Candidate, ChunkInfo, ParentContext, RetrievalResult
from app.tools.cache import MemoryToolCache
from app.tools.middleware import ToolRunner

QUESTION = "次回の返済額と繰上返済の手続きについて教えてください。"
CONTRACT_ID = "L0001"
POLICY = "繰上返済はインターネットからお申し込みいただけます。"
DELINQUENCY_DATA = {"days_overdue": 4, "amount_yen": 123_456, "late_fee_yen": 10}
CONTRACT_DATA = {
    "contracts": [
        {
            "contract_id": CONTRACT_ID,
            "product": "住宅ローン",
            "principal_yen": 5_000_000,
            "disbursed_on": "2024-04-01",
            "status": "active",
        }
    ]
}
SCHEDULE_DATA = {
    "next_payment_date": "2026-12-01",
    "next_payment_yen": 123_456,
    "outstanding_principal_yen": 1_000_000,
    "remaining_installments": 40,
    "schedule": [],
}


class StubRetriever:
    def __init__(self, started: asyncio.Event | None = None) -> None:
        self.calls: list[tuple[str, MetaFilter | None, bool]] = []
        self.started = started

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = FINAL_TOP_K,
        editions: Sequence[str] | None = None,
        filters: MetaFilter | None = None,
        rerank: bool = DEFAULT_POLICY_RERANK,
        mode: str = HYBRID,
    ) -> RetrievalResult:
        self.calls.append((query, filters, rerank))
        if self.started is not None:
            await self.started.wait()
        parent = ParentContext("p1", "policy-a", "申込方法", POLICY)
        policy = PolicyMetadata(
            source="internal",
            synthetic=True,
            product_line="home_loan",
            policy_type="手続",
            policy_id="POL-TEST",
            effective_from=date(2020, 1, 1),
            status="online",
            corpus_tier="S",
            based_on=("public-fixture",),
        )
        candidate = Candidate(
            1, ChunkInfo("c1", "policy-a", "p1", "申込方法", POLICY, policy=policy)
        )
        return RetrievalResult(query, [candidate], [parent])


class StubCore:
    def __init__(
        self,
        replies: dict[str, MockCoreReply] | None = None,
        *,
        parallel: bool = False,
        wait_for: asyncio.Event | None = None,
    ) -> None:
        self.replies = replies or {}
        self.calls: list[tuple[str, MockCoreRequest]] = []
        self.started = asyncio.Event()
        self.overlapping = asyncio.Event()
        self.parallel = parallel
        self.wait_for = wait_for

    async def get(
        self, path: str, request: MockCoreRequest, *, timeout_seconds: float
    ) -> MockCoreReply:
        self.calls.append((path, request))
        if path == "/authorization":
            return MockCoreReply(status="ok", body={"authorized": True})
        self.started.set()
        if self.wait_for is not None:
            await self.wait_for.wait()
        if self.parallel:
            if sum(name != "/authorization" for name, _ in self.calls) == 2:
                self.overlapping.set()
            await self.overlapping.wait()
        return self.replies[path]


def _ok(data: Mapping[str, object]) -> MockCoreReply:
    return MockCoreReply(status="ok", body={"synthetic": True, "data": data, "total": None})


def _completion(
    text: str = "", *calls: FunctionCall, confidence: float | None = None
) -> Completion:
    return Completion(
        text=text,
        model="fake",
        prompt_tokens=12,
        completion_tokens=4,
        cost_cny=0.002,
        tool_calls=list(calls),
        confidence=confidence,
    )


def _agent(question: str = QUESTION) -> ChatRequest:
    return ChatRequest(question=question, channel="agent", agent_id="A001", customer_id="C0001")


def _runner(core: StubCore) -> ToolRunner:
    return ToolRunner(core, MemoryToolCache(), timeout_seconds=0.5)


@pytest.mark.parametrize(
    ("intent", "node", "message"),
    [
        ("smalltalk", "direct", "住宅ローン"),
        ("complaint", "escalate", "責任者"),
        ("lookup", "handoff", "担当者"),
        ("policy", "output_guard", POLICY),
    ],
)
async def test_customer_intents_use_separate_lanes(intent: str, node: str, message: str) -> None:
    small = FakeChatModel([_completion(json.dumps({"intent": intent}))])
    large = FakeChatModel([_completion(f"{POLICY} [1]")])
    retriever, core = StubRetriever(), StubCore()
    graph = CopilotGraph(small, large, retriever, _runner(core))

    response = await graph.answer(ChatRequest(question=QUESTION, agent_id="A001", customer_id="C1"))

    assert response.intent == intent
    assert message in response.answer
    assert response.steps[-1].name == node
    assert len(large.calls) == len(retriever.calls) == int(intent == "policy")
    assert all("tool" not in name for name in graph.customer_graph.get_graph(xray=True).nodes)
    assert not core.calls
    if intent == "lookup":
        assert not any(char.isnumeric() for char in response.answer)
    if intent == "policy":
        assert [citation.document_id for citation in response.citations] == ["policy-a"]


async def test_customer_mixed_intent_hands_off_without_retrieving_or_offering_tools() -> None:
    small = FakeChatModel([_completion('{"intent":"policy","secondary_intent":"lookup"}')])
    retriever, core = StubRetriever(), StubCore()
    graph = CopilotGraph(small, FakeChatModel([]), retriever, _runner(core))

    response = await graph.answer(ChatRequest(question=QUESTION, agent_id="A001", customer_id="C1"))

    assert response.secondary_intent == "lookup"
    assert response.steps[-1].name == "handoff"
    assert response.abstained
    assert not any(char.isnumeric() for char in response.answer)
    assert small.offered_tools == [None]
    assert not retriever.calls
    assert not core.calls


@pytest.mark.parametrize(
    ("channel", "question"),
    [
        ("customer", "病気で来月の住宅ローンの返済が難しく、相談したいです。"),
        ("customer", "月々の支払いが滞ってしまいました。どうすればいいですか。"),
        ("agent", "延滞した住宅ローンについてお客さまが相談したいそうです。"),
        ("agent", "お客さまが返済条件の変更について相談を希望しています。"),
        ("customer", "家のローンが今月は払えないです。助けてください。"),
        ("customer", "今月は住宅ローンの返済ができません。相談したいです。"),
    ],
)
async def test_repayment_consultation_stops_before_intent_and_tools(
    channel: Channel, question: str
) -> None:
    small, large = FakeChatModel([]), FakeChatModel([])
    retriever, core = StubRetriever(), StubCore()
    graph = CopilotGraph(small, large, retriever, _runner(core))
    request = ChatRequest(question=question, channel=channel, agent_id="A001", customer_id="C0001")

    response = await graph.answer(request)

    assert [step.name for step in response.steps] == ["guard", "repayment_support"]
    assert "専門窓口" in response.answer
    assert "責任者" not in response.answer
    assert not any(character.isnumeric() for character in response.answer)
    assert response.abstained
    assert not small.calls
    assert not large.calls
    assert not retriever.calls
    assert not core.calls


@pytest.mark.parametrize(
    ("intent", "question", "destination"),
    [
        ("complaint", "返済の説明が難しかったです。案内について責任者と話したい。", "escalate"),
        ("policy", "繰上返済で毎月の返済額を減らす一般的な仕組みを教えて。", "retrieve"),
        ("policy", "毎月の返済日を変更する手順はどこにありますか。", "retrieve"),
        ("policy", "返済条件の変更の一般的な手順を知りたいです。", "retrieve"),
        ("policy", "延滞した場合の遅延損害金の一般的な扱いを教えてください。", "retrieve"),
        ("lookup", "私の契約に延滞の記録があるか確認してください。", "handoff"),
        ("policy", "住宅ローン控除の申告に必要な書類はどこで確認できますか。", "retrieve"),
        ("policy", "アプリで繰上返済できません。操作手順を教えてください。", "retrieve"),
        (
            "policy",
            "住民税を滞納しています。住宅ローン控除の対象になるか税理士に相談した方がよいですか。",
            "retrieve",
        ),
        (
            "complaint",
            "延滞の相談を断った担当者の対応に苦情があります。責任者に取り次いでください。",
            "escalate",
        ),
    ],
)
async def test_other_repayment_questions_keep_their_route(
    intent: str, question: str, destination: str
) -> None:
    small = FakeChatModel([_completion(json.dumps({"intent": intent}))])
    large = FakeChatModel([_completion(f"{POLICY} [1]")])
    core = StubCore()
    graph = CopilotGraph(small, large, StubRetriever(), _runner(core))

    response = await graph.answer(ChatRequest(question=question))

    assert response.intent == intent
    assert destination in {step.name for step in response.steps}
    assert "専門窓口" not in response.answer
    assert not core.calls


@pytest.mark.parametrize(
    ("channel", "question"),
    [
        ("customer", "私の住宅ローン控除は適用されるか判断してください。"),
        ("agent", "お客さまの住宅ローン減税の金額を試算してほしいと相談されました。"),
        ("customer", "家のローンがあるのですが、自分は控除でいくら戻りますか。"),
        ("customer", "住宅ローン控除って、いくら戻るんですか。"),
    ],
)
async def test_personal_tax_referral_skips_retrieval_and_models(
    channel: Channel, question: str
) -> None:
    small, large = FakeChatModel([]), FakeChatModel([])
    retriever, core = StubRetriever(), StubCore()
    graph = CopilotGraph(small, large, retriever, _runner(core))

    response = await graph.answer(ChatRequest(question=question, channel=channel))

    assert [step.name for step in response.steps] == ["guard", "tax_referral"]
    assert "税務署" in response.answer
    assert response.abstained
    assert not small.calls
    assert not large.calls
    assert not retriever.calls
    assert not core.calls


@pytest.mark.parametrize(
    "question",
    [
        "住宅ローン控除用の残高証明書はいつ届きますか。",
        "私の住宅ローン減税用の年末残高証明書を再発行してもらえますか。",
        "住宅ローン控除の対象となる一般的な条件は何ですか。",
        "私が住宅ローン控除の対象となった年の証明書はいつ届きますか。",
    ],
)
async def test_general_tax_policy_uses_original_retrieval(question: str) -> None:
    small = FakeChatModel([_completion('{"intent":"policy"}')])
    graph = CopilotGraph(
        small,
        FakeChatModel([_completion(f"{POLICY} [1]")]),
        StubRetriever(),
        _runner(StubCore()),
    )

    response = await graph.answer(ChatRequest(question=question))

    assert not response.abstained
    assert "retrieve" in {step.name for step in response.steps}
    assert "税務署" not in response.answer
    assert response.citations


async def test_tax_referral_replaces_answer_when_citations_are_rejected() -> None:
    small = FakeChatModel([_completion('{"intent":"policy"}')])
    graph = CopilotGraph(
        small,
        FakeChatModel([["住宅ローン控除は確認できません。"]]),
        StubRetriever(),
        _runner(StubCore()),
    )
    question = "住宅ローン控除の適用可否について相談したいです。"

    events = [
        item async for item in graph.stream(ChatRequest(question=question), stream_tokens=True)
    ]

    result = events[-1]
    assert isinstance(result, ChatResponse)
    assert result.abstained
    assert any(
        step.name == "output_guard" and step.note == "missing_citation" for step in result.steps
    )
    assert "税務署" in result.answer
    assert not result.citations


async def test_personal_tax_followup_stops_after_standalone_question() -> None:
    rewrite = "私の場合に住宅ローン控除の対象となるか判断してください。"
    small = FakeChatModel(
        [_completion('{"intent":"policy"}'), _completion(json.dumps({"question": rewrite}))]
    )
    large = FakeChatModel([])
    retriever = StubRetriever()
    graph = CopilotGraph(small, large, retriever, _runner(StubCore()))

    response = await graph.answer(
        ChatRequest(question="この場合はどうですか。"),
        previous_policy_question="住宅ローン控除の一般の要件を教えてください。",
    )

    assert response.abstained
    assert "税務署" in response.answer
    assert not retriever.calls
    assert not large.calls


@pytest.mark.parametrize(
    "output",
    [
        _completion("意図を分類できません"),
        _completion('{"intent":"lookup","secondary_intent":"complaint"}'),
        _completion('{"intent":"lookup"}', confidence=0.01),
    ],
)
async def test_invalid_or_low_confidence_intent_uses_conservative_policy(
    output: Completion,
) -> None:
    core, retriever = StubCore(), StubRetriever()
    graph = CopilotGraph(
        FakeChatModel([output]),
        FakeChatModel([_completion(POLICY + " [1]")]),
        retriever,
        _runner(core),
    )

    response = await graph.answer(_agent())

    assert response.intent == "policy"
    assert "お尋ね" in response.answer
    assert len(retriever.calls) == 1
    assert not core.calls


async def test_classifier_sees_only_current_question_and_previous_intent() -> None:
    previous = "繰上返済に関する以前の質問。"
    current = "その場合はどうなりますか。"
    standalone = "繰上返済の申込方法を教えてください。"
    small = FakeChatModel(
        [_completion('{"intent":"policy"}'), _completion(json.dumps({"question": standalone}))]
    )
    filters = MetaFilter(as_of=date(2026, 11, 18))
    retriever = StubRetriever()
    graph = CopilotGraph(
        small, FakeChatModel([_completion(f"{POLICY} [1]")]), retriever, _runner(StubCore())
    )

    response = await graph.answer(
        ChatRequest(question=current, filter=filters, rerank=True),
        previous_intent="policy",
        previous_policy_question=previous,
    )

    assert json.loads(small.calls[0][-1].content) == {
        "question": current,
        "previous_intent": "policy",
    }
    assert all(previous not in message.content for message in small.calls[0])
    assert previous in small.calls[1][-1].content
    assert retriever.calls == [(standalone, filters, True)]
    assert response.standalone_question == standalone


async def test_rule_greeting_needs_no_model() -> None:
    small, large = FakeChatModel([]), FakeChatModel([])
    graph = CopilotGraph(small, large, StubRetriever(), _runner(StubCore()))

    response = await graph.answer(ChatRequest(question="こんにちは！"))

    assert response.intent == "smalltalk"
    assert response.steps[-1].name == "direct"
    assert not small.calls
    assert not large.calls


async def test_tools_execute_in_parallel_and_are_traced_without_raw_data() -> None:
    core = StubCore(
        {"/delinquency": _ok(DELINQUENCY_DATA), "/benefits": _ok({"benefits": []})}, parallel=True
    )
    small = FakeChatModel(
        [
            _completion('{"intent":"lookup"}'),
            _completion(
                "",
                FunctionCall(name="query_delinquency", arguments="{}"),
                FunctionCall(name="query_benefits", arguments="{}"),
            ),
        ]
    )
    large = FakeChatModel([_completion("延滞額は123,456円です。")])
    graph = CopilotGraph(small, large, StubRetriever(), _runner(core))

    response = await graph.answer(_agent("延滞額と優遇状況を確認してください。"))

    assert core.overlapping.is_set()
    assert response.answer == "延滞額は123,456円です。"
    assert [trace.tool_name for trace in response.tool_calls] == [
        "query_delinquency",
        "query_benefits",
    ]
    assert all(trace.status == "ok" for trace in response.tool_calls)
    assert "123456" not in "".join(step.model_dump_json() for step in response.steps)
    assert "C0001" not in "".join(msg.content for call in small.calls for msg in call)
    assert "123456" in large.calls[0][-1].content
    assert (response.prompt_tokens, response.completion_tokens) == (36, 12)
    assert response.cost_cny == pytest.approx(0.006)


async def test_mixed_branches_overlap_and_generate_once_after_two_rounds() -> None:
    core = StubCore(
        {"/loan-contracts": _ok(CONTRACT_DATA), "/repayment-schedule": _ok(SCHEDULE_DATA)}
    )
    retriever = StubRetriever(started=core.started)
    small = FakeChatModel(
        [
            _completion('{"intent":"policy","secondary_intent":"lookup"}'),
            _completion("", FunctionCall(name="query_loan_contracts", arguments="{}")),
            _completion(
                "",
                FunctionCall(name="query_repayment_schedule", arguments='{"contract_id":"L0001"}'),
            ),
        ]
    )
    large = FakeChatModel([_completion(f"次回返済額は123,456円です。{POLICY} [1]")])
    graph = CopilotGraph(small, large, retriever, _runner(core))

    async with asyncio.timeout(2):
        events = [item async for item in graph.stream(_agent())]

    response = events[-1]
    assert isinstance(response, ChatResponse)
    assert response.secondary_intent == "lookup"
    assert response.steps == [item for item in events if isinstance(item, Step)]
    assert [(trace.tool_name, trace.status) for trace in response.tool_calls] == [
        ("query_loan_contracts", "ok"),
        ("query_repayment_schedule", "ok"),
    ]
    assert len(small.calls) == 3
    assert len(large.calls) == 1
    assert CONTRACT_ID in small.calls[2][-1].content
    assert "123456" in large.calls[0][-1].content
    assert POLICY in large.calls[0][-1].content
    assert len(response.citations) == 1
    assert response.retrieved_docs == ["policy-a"]


@pytest.mark.parametrize(("failure", "word"), [("timeout", "業務システム"), ("denied", "権限")])
async def test_failed_or_denied_tool_hides_partial_results(failure: str, word: str) -> None:
    failure_reply = MockCoreReply(status="timeout" if failure == "timeout" else "denied")
    core = StubCore({"/delinquency": _ok(DELINQUENCY_DATA), "/benefits": failure_reply})
    small = FakeChatModel(
        [
            _completion('{"intent":"lookup","secondary_intent":"policy"}'),
            _completion(
                "",
                FunctionCall(name="query_delinquency", arguments="{}"),
                FunctionCall(name="query_benefits", arguments="{}"),
            ),
        ]
    )
    large, retriever = FakeChatModel([]), StubRetriever()
    graph = CopilotGraph(small, large, retriever, _runner(core))

    response = await graph.answer(_agent())

    assert response.abstained
    assert response.degraded
    assert word in response.answer
    assert not any(char.isnumeric() for char in response.answer)
    assert not large.calls
    assert not response.citations
    assert len(retriever.calls) == 1
    assert {trace.status for trace in response.tool_calls} == {
        "ok",
        "failed" if failure == "timeout" else "denied",
    }


@pytest.mark.parametrize(
    ("call", "invalid_trace"),
    [
        (FunctionCall(name="unknown_tool", arguments="{}"), None),
        (FunctionCall(name="query_delinquency", arguments="{坏}"), "invalid_arguments"),
        (
            FunctionCall(name="query_delinquency", arguments='{"customer_id":"C9999"}'),
            "invalid_arguments",
        ),
    ],
)
async def test_unregistered_tools_or_invalid_arguments_never_reach_core(
    call: FunctionCall, invalid_trace: str | None
) -> None:
    core = StubCore()
    small = FakeChatModel([_completion('{"intent":"lookup"}'), _completion("", call)])
    graph = CopilotGraph(small, FakeChatModel([]), StubRetriever(), _runner(core))

    response = await graph.answer(_agent())

    offered = small.offered_tools[1]
    assert offered is not None
    assert {tool.name for tool in offered} == {
        "query_loan_contracts",
        "query_repayment_schedule",
        "query_delinquency",
        "query_rate_terms",
        "query_benefits",
    }
    assert not core.calls
    assert response.degraded
    assert [trace.reason for trace in response.tool_calls] == (
        [invalid_trace] if invalid_trace else []
    )


async def test_policy_with_any_unknown_citations_abstains() -> None:
    small = FakeChatModel([_completion('{"intent":"policy"}')])
    large = FakeChatModel([_completion(f"{POLICY} [1] [9]")])
    graph = CopilotGraph(small, large, StubRetriever(), _runner(StubCore()))

    response = await graph.answer(ChatRequest(question=QUESTION))

    assert response.abstained
    assert POLICY not in response.answer
    assert not response.citations
    assert (
        next(step.note for step in response.steps if step.name == "output_guard")
        == "invalid_citation"
    )


async def test_streamed_unsupported_amount_is_captured_for_retraction() -> None:
    small = FakeChatModel([_completion('{"intent":"policy"}')])
    large = FakeChatModel([["手数料は", "1,234円です。 [1]"]])
    graph = CopilotGraph(small, large, StubRetriever(), _runner(StubCore()))

    events = [
        item async for item in graph.stream(ChatRequest(question=QUESTION), stream_tokens=True)
    ]
    assert [item.text for item in events if isinstance(item, AnswerDelta)] == [
        "手数料は",
        "1,234円です。 [1]",
    ]
    response = events[-1]
    assert isinstance(response, ChatResponse)
    assert response.abstained
    assert "1,234" not in response.answer
    blocked = next(step for step in response.steps if step.name == "output_guard")
    assert blocked.note == "unsupported_number"
    assert blocked.details is not None
    assert blocked.details.output == "手数料は1,234円です。 [1]"


async def test_strict_mode_runs_existing_grade_and_verify() -> None:
    small = FakeChatModel([_completion('{"intent":"policy"}')])
    large = FakeChatModel(
        [
            _completion('{"sufficient":true,"missing":""}'),
            _completion(f"{POLICY} [1]"),
            _completion('{"faithful":false,"unsupported":["例"]}'),
        ]
    )
    graph = CopilotGraph(small, large, StubRetriever(), _runner(StubCore()), strict=True)

    response = await graph.answer(ChatRequest(question=QUESTION))

    assert response.abstained
    assert not response.citations
    assert [step.name for step in response.steps][-5:] == [
        "grade",
        "generate",
        "output_guard",
        "verify",
        "degrade",
    ]
    assert "能不能回答用户的问题" in large.calls[0][-1].content
    assert "是否都能在「资料」里找到依据" in large.calls[2][-1].content
