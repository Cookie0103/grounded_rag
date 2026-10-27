import json
from pathlib import Path

import pytest

from app.providers.fakes import FakeChatModel
from eval import judge as judge_module
from eval.dataset import Nugget, Question
from eval.evaluate import (
    cost_per_question,
    evaluate,
    latency_p95_ms,
    retrieval_breakdown,
    retrieval_stats,
    route_accuracy,
)
from eval.judge import ChatPromptRunner, Judge
from eval.systems import SystemAnswer

NUGGETS = (Nugget("x", "vital"), Nugget("y", "okay"))
Q1 = Question("q1", "问", ("a",), nuggets=NUGGETS, lexical="distant")
Q2 = Question("q2", "问", ("b",), nuggets=NUGGETS, expected_route="SINGLE")
VERDICT = json.dumps({"nuggets": ["support", "support"], "behavior": "answered"})


@pytest.fixture(autouse=True)
def _no_corpus_files(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        judge_module, "gold_document_text", lambda document_id: f"文档 {document_id}"
    )


def _judge(*responses: str) -> tuple[Judge, FakeChatModel]:
    chat = FakeChatModel(responses=list(responses))
    return Judge(ChatPromptRunner(chat)), chat


def _answer(qid: str, docs: tuple[str, ...], **fields: object) -> SystemAnswer:
    base: dict[str, object] = {"answer": "答", "route": None, "contexts": (), "latency_ms": 10.0}
    return SystemAnswer(qid, retrieved_docs=docs, **{**base, **fields})  # type: ignore[arg-type]


def test_retrieval_stats_count_only_answerable_questions_with_gold_and_no_error() -> None:
    unanswerable = Question("u", "问", (), type="unanswerable", unanswerable_category="injection")
    pairs = [
        (Q1, _answer("q1", ("a",))),
        (Q2, _answer("q2", ("x", "b"))),
        (Q2, _answer("q2", (), error="boom", answer=None)),
        (unanswerable, _answer("u", ("a",))),
    ]

    stats = retrieval_stats(pairs)

    assert stats.questions == 2
    assert stats.recall_at_5 == 1.0
    assert stats.mrr == pytest.approx(0.75)


def test_retrieval_breakdown_groups_by_key() -> None:
    answers = [_answer("q1", ("a",)), _answer("q2", ("z",))]

    groups = retrieval_breakdown([Q1, Q2], answers, lambda q: q.lexical)

    assert groups["distant"].recall_at_5 == 1.0
    assert groups["similar"].recall_at_5 == 0.0


def test_route_accuracy_ignores_questions_without_route_information() -> None:
    assert route_accuracy([Q1, Q2], [_answer("q1", ()), _answer("q2", (), route="SINGLE")]) == 1.0
    assert route_accuracy([Q2], [_answer("q2", (), route="MULTI")]) == 0.0
    assert route_accuracy([Q2], [_answer("q2", ())]) is None


def test_latency_and_cost() -> None:
    answers = [_answer("a", (), latency_ms=float(ms), cost_cny=0.02) for ms in range(1, 101)]
    answers.append(_answer("b", (), latency_ms=99999.0, error="x", answer=None))

    assert latency_p95_ms(answers) == pytest.approx(95.05, abs=0.1)
    assert cost_per_question(answers) == pytest.approx(0.02 * 100 / 101)
    assert latency_p95_ms([]) == 0.0


async def test_evaluate_without_a_judge_only_records_system_errors() -> None:
    answers = [_answer("q1", ("a",)), _answer("q2", (), error="boom", answer=None)]

    result = await evaluate("s", [Q1, Q2], answers, None)

    assert result.scored == []
    assert result.system_errors == {"q2": "boom"}


async def test_evaluate_scores_answers_and_survives_a_failing_judge(tmp_path: Path) -> None:
    judge, _ = _judge(VERDICT, "垃圾", "还是垃圾")
    cache = tmp_path / "sub" / "verdicts.jsonl"

    result = await evaluate(
        "s", [Q1, Q2], [_answer("q1", ("a",)), _answer("q2", ("b",))], judge, verdict_cache=cache
    )

    assert [s.score.points for s in result.scored] == [1.0]
    assert list(result.judge_errors) == ["q2"]
    assert len(cache.read_text(encoding="utf-8").splitlines()) == 1


async def test_cached_verdicts_are_not_judged_again(tmp_path: Path) -> None:
    cache = tmp_path / "verdicts.jsonl"
    answers = [_answer("q1", ("a",))]
    first, _ = _judge(VERDICT)
    await evaluate("s", [Q1], answers, first, verdict_cache=cache)
    second, chat = _judge()

    result = await evaluate("s", [Q1], answers, second, verdict_cache=cache)

    assert chat.calls == []
    assert result.scored[0].score.points == 1.0


async def test_answers_that_are_none_are_skipped() -> None:
    judge, chat = _judge()

    result = await evaluate("s", [Q1], [_answer("q1", ("a",), answer=None)], judge)

    assert result.scored == []
    assert result.judge_errors == {}
    assert chat.calls == []


async def test_evaluate_passes_cached_contexts_only_when_requested() -> None:
    answer = _answer("q1", ("a",), contexts=("缓存的父块",))
    first, old_chat = _judge(VERDICT)
    await evaluate("s", [Q1], [answer], first)
    assert "缓存的父块" not in old_chat.calls[0][0].content
    second, new_chat = _judge(VERDICT)
    await evaluate("s", [Q1], [answer], second, template_name="judge_v2.md", include_contexts=True)
    assert "缓存的父块" in new_chat.calls[0][0].content
