"""评测样例与 Dify 轨迹及网关用量的对齐。"""

import json
from datetime import date
from pathlib import Path
from zipfile import ZipFile

import pytest

from app.providers.budget import BudgetLedger
from app.providers.deepseek import cost_cny
from app.providers.dify import DifyNode, DifyRequest, DifyTurn
from eval.copilot_cases import CopilotCase
from eval.copilot_observations import TurnObservation, score_observation
from eval.dify_replay import (
    DifyReplay,
    DocumentCatalog,
    GatewayJournal,
    compare_observations,
    observe_turn,
)

_DOC_ID = "public/example@aef7761b1a01641e"
_TODAY = date(2026, 11, 18)


def _case(**fields: object) -> CopilotCase:
    return CopilotCase.model_validate(
        {
            "id": "case",
            "category": "lookup",
            "question": "返済予定は？",
            "synthetic": True,
            **fields,
        }
    )


def _node(
    node_id: str,
    kind: str,
    outputs: dict[str, object],
    *,
    ms: float = 50,
) -> DifyNode:
    return DifyNode(
        node_id=node_id,
        node_type=kind,
        outputs=outputs,
        status="succeeded",
        elapsed_time=ms / 1000,
    )


def _turn(nodes: list[DifyNode], *, answer: str = "毎月の返済をご確認ください。") -> DifyTurn:
    return DifyTurn(
        answer=answer,
        conversation_id="conversation",
        first_token_ms=200,
        latency_ms=900,
        nodes=nodes,
        workflow_status="succeeded",
        workflow_run_id="run",
        metadata={},
    )


def _catalog(path: Path) -> DocumentCatalog:
    with ZipFile(path, "w") as pack:
        pack.writestr(
            "index.jsonl",
            json.dumps(
                {
                    "document_id": _DOC_ID,
                    "source_id": "public/example",
                    "file": "public--example.md",
                    "status": "offline",
                    "effective_from": "2025-11-01",
                    "effective_to": "2026-11-01",
                }
            ),
        )
    return DocumentCatalog.from_question_pack(path)


def test_extracts_real_node_evidence_and_uses_stable_version_id(tmp_path: Path) -> None:
    case = _case(expected_intent="lookup", expected_claims=["500円"])
    trace = _turn(
        [
            _node("intent", "question-classifier", {"class_id": "lookup_policy"}),
            _node(
                "retrieve_mixed",
                "knowledge-retrieval",
                {
                    "result": [
                        {"metadata": {"document_name": "public--example.md"}, "content": "返済"}
                    ]
                },
            ),
            _node("http_repayment_schedule", "http-request", {"status_code": 200}, ms=85),
            _node(
                "tool_evidence",
                "code",
                {
                    "tool_calls": [
                        {
                            "tool_name": "query_repayment_schedule",
                            "status": "ok",
                            "arguments": {"contract_id": "synthetic", "start_period": 2},
                            "elapsed_ms": 85,
                            "cached": False,
                            "total": 420,
                            "returned_count": 5,
                        }
                    ]
                },
            ),
            _node("generate_mixed", "llm", {"text": "毎月500円。"}),
        ],
        answer=f"毎月500円。文書 ID {_DOC_ID}",
    )

    observation = observe_turn(trace, case, _catalog(tmp_path / "pack.zip"))
    assert observation.intent == "lookup"
    assert observation.retrieved_docs == observation.citation_docs == (_DOC_ID,)
    assert observation.dropped_or_expired_docs == (_DOC_ID,)
    assert observation.contexts == ("返済",)
    assert observation.tool_calls is not None
    tool = observation.tool_calls[0]
    assert tool.arguments.has_contract_id
    assert tool.arguments.start_period == 2
    assert tool.total == 420
    assert tool.returned_count == 5
    assert score_observation(case, observation, system="Dify V3").tool_ms == 85


def test_unknown_document_and_missing_tool_details_remain_unmeasured(tmp_path: Path) -> None:
    result = observe_turn(
        _turn(
            [
                _node("retrieve_policy", "knowledge-retrieval", {"result": [{"title": "unknown"}]}),
                _node("http_repayment_schedule", "http-request", {"status_code": 200}),
            ],
        ),
        _case(),
        _catalog(tmp_path / "pack.zip"),
    )
    assert result.intent is None
    assert result.retrieved_docs is None
    assert result.tool_calls is None
    assert result.cost_cny is None


def test_serial_tool_attempts_keep_denial_and_measure_dispatched_http(tmp_path: Path) -> None:
    result = observe_turn(
        _turn(
            [
                _node("mock_authorize", "http-request", {"status_code": 200}, ms=11),
                _node("mock_get", "http-request", {"status_code": 0}, ms=2000),
                _node("mock_authorize", "http-request", {"status_code": 403}, ms=17),
                _node(
                    "tool_evidence",
                    "code",
                    {
                        "tool_calls": [
                            {
                                "tool_name": "query_loan_contracts",
                                "arguments": {},
                                "status": "failed",
                                "reason": "transport_error",
                                "business_dispatched": True,
                            },
                            {
                                "tool_name": "query_repayment_schedule",
                                "arguments": {"has_contract_id": True},
                                "status": "denied",
                                "reason": "not_authorized",
                                "business_dispatched": False,
                            },
                        ]
                    },
                ),
            ],
        ),
        _case(),
        _catalog(tmp_path / "pack.zip"),
    )
    assert result.tool_calls is not None
    failed, denied = result.tool_calls
    assert (failed.status, failed.reason, failed.elapsed_ms) == ("failed", "upstream_error", 2011)
    assert (denied.status, denied.reason, denied.elapsed_ms) == ("denied", "not_authorized", 17)
    assert result.degraded


class _GatewayChat:
    def __init__(self, journal: Path, *, emit_paid_usage: bool = True) -> None:
        self.journal = journal
        self.requests: list[DifyRequest] = []
        self.emit_paid_usage = emit_paid_usage

    async def chat(self, request: DifyRequest) -> DifyTurn:
        self.requests.append(request)
        index = len(self.requests)
        nodes = [_node("intent", "question-classifier", {"class_id": "lookup"})]
        self._log(f"classifier-{index}", "small", 18, 5)
        if index == 2 or not self.emit_paid_usage:
            nodes.append(_node("generate_lookup", "llm", {"text": "返済予定です。"}))
            if self.emit_paid_usage:
                self._log(f"generation-{index}", "deepseek-v4-pro", 60, 10)
        return _turn(nodes)

    def _log(self, identifier: str, model: str, prompt: int, completion: int) -> None:
        with self.journal.open("a", encoding="utf-8") as file:
            file.write(
                json.dumps(
                    {
                        "request_id": identifier,
                        "model": model,
                        "prompt_tokens": prompt,
                        "completion_tokens": completion,
                    }
                )
                + "\n"
            )


@pytest.mark.asyncio
async def test_history_keeps_dify_conversation_and_paid_cost_uses_real_tokens(
    tmp_path: Path,
) -> None:
    journal_path = tmp_path / "usage.jsonl"
    usage = GatewayJournal(journal_path, wait_seconds=0)
    ledger = BudgetLedger(tmp_path / "budget", 10, today=lambda: _TODAY)
    client = _GatewayChat(journal_path)
    replay = DifyReplay(client, usage, ledger, _catalog(tmp_path / "pack.zip"))
    case = _case(
        channel="agent", agent_id="A-1", customer_id="C-1", history=["こんにちは"], fault="5xx"
    )

    entry = await replay.observe(case, "explicit")

    prior, final = client.requests
    assert prior.user == final.user
    assert prior.conversation_id is None
    assert final.conversation_id == "conversation"
    assert prior.inputs["mock_fault"] == ""
    assert final.inputs["mock_fault"] == "5xx"
    assert entry.observation.prompt_tokens == 96
    assert entry.observation.completion_tokens == 20
    assert not entry.missing_usage
    expected = cost_cny(60, 10, model="deepseek-v4-pro")
    assert entry.observation.cost_cny == pytest.approx(expected)
    assert ledger.spent() == pytest.approx(expected)


@pytest.mark.asyncio
async def test_missing_gateway_usage_does_not_turn_into_zero_cost(tmp_path: Path) -> None:
    journal = tmp_path / "usage.jsonl"
    ledger = BudgetLedger(tmp_path / "budget", 10, today=lambda: _TODAY)
    replay = DifyReplay(
        _GatewayChat(journal, emit_paid_usage=False),
        GatewayJournal(journal, wait_seconds=0),
        ledger,
        _catalog(tmp_path / "pack.zip"),
    )

    entry = await replay.observe(_case(), "none")

    assert entry.observation.cost_cny is None
    assert entry.observation.prompt_tokens is None
    assert entry.missing_usage


def test_differences_distinguish_unobservable_layer_from_mismatch() -> None:
    left = TurnObservation(
        answer="ご案内します。", intent="lookup", retrieved_docs=(), tool_calls=[]
    )
    right = TurnObservation(answer="  ご案内します。\n", intent="policy", tool_calls=[])

    result = compare_observations(left, right)

    assert result["intent"].state == "different"
    assert result["retrieval"].state == "unmeasured"
    assert result["tools"].state == result["answer"].state == "same"
