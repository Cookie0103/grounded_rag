import json

import pytest

from app.providers.fakes import FakeChatModel
from eval import judge as judge_module
from eval.attribution import (
    GENERATION,
    INSUFFICIENT,
    RETRIEVAL_MISS,
    UNKNOWN,
    Attribution,
    attribute_errors,
    cause_counts,
)
from eval.dataset import Nugget, Question
from eval.evaluate import evaluate
from eval.judge import ChatPromptRunner, Judge
from eval.report import render_report
from eval.systems import SystemAnswer

NUGGETS = (Nugget("x", "vital"), Nugget("y", "okay"))
PERFECT_VERDICT = json.dumps({"nuggets": ["support", "support"], "behavior": "answered"})
WRONG_VERDICT = json.dumps({"nuggets": ["not_support", "not_support"], "behavior": "answered"})
REFUSED = json.dumps({"nuggets": [], "behavior": "refused"})


@pytest.fixture(autouse=True)
def _no_corpus_files(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(judge_module, "gold_document_text", lambda document_id: document_id)


def _answer(qid: str, docs: tuple[str, ...], **fields: object) -> SystemAnswer:
    base: dict[str, object] = {
        "answer": "答",
        "route": None,
        "contexts": ("上下文",),
        "latency_ms": 5.0,
    }
    return SystemAnswer(qid, retrieved_docs=docs, **{**base, **fields})  # type: ignore[arg-type]


def _judge(*responses: str) -> Judge:
    return Judge(ChatPromptRunner(FakeChatModel(responses=list(responses))))


async def test_attribution_separates_retrieval_context_and_generation_errors() -> None:
    questions = [Question(f"q{i}", "问", ("a",), nuggets=NUGGETS) for i in range(5)]
    answers = [
        _answer("q0", ("a",)),  # 满分，不归因
        _answer("q1", ("z",)),  # 没检索到
        _answer("q2", ("a",)),  # 检索到，上下文不够
        _answer("q3", ("a",)),  # 上下文够，回答错
        _answer("q4", ("a",)),  # 评审坏了
    ]
    verdicts = _judge(PERFECT_VERDICT, *([WRONG_VERDICT] * 4))
    result = await evaluate("s", questions, answers, verdicts)
    sufficiency = _judge('{"sufficient": false}', '{"sufficient": true}', "不是 JSON")

    attributions = await attribute_errors(result.scored, answers, sufficiency)

    assert [(a.question_id, a.cause) for a in attributions] == [
        ("q1", RETRIEVAL_MISS),
        ("q2", INSUFFICIENT),
        ("q3", GENERATION),
        ("q4", UNKNOWN),
    ]
    assert cause_counts(attributions)[RETRIEVAL_MISS] == 1


async def test_report_contains_every_section() -> None:
    questions = [
        Question("q1", "问", ("a",), nuggets=NUGGETS, expected_route="SINGLE"),
        Question("u1", "问", (), type="unanswerable", unanswerable_category="injection"),
        Question("q2", "问", ("b",), nuggets=NUGGETS),
    ]
    answers = [
        _answer("q1", ("a",), route="SINGLE"),
        _answer("u1", (), answer="拒绝"),
        _answer("q2", (), answer=None, error="boom"),
    ]
    result = await evaluate("演示系统", questions, answers, _judge(PERFECT_VERDICT, REFUSED))

    report = render_report(result, [])

    assert report.startswith("# 评测报告：演示系统")
    for text in (
        "## 检索",
        "**全部**",
        "题型=fact_single",
        "### 不可回答题（按类别）",
        "injection",
    ):
        assert text in report
    assert "路由准确率：100.0%" in report
    assert "系统 `q2`：boom" in report


async def test_report_without_a_judge_says_so_and_lists_attribution() -> None:
    questions = [Question("q1", "问", ("a",), nuggets=NUGGETS)]
    result = await evaluate("s", questions, [_answer("q1", ("a",), answer=None)], None)

    report = render_report(result)

    assert "没有评审结果" in report
    assert "错误归因" not in report
    assert "错误归因" in render_report(result, [Attribution("q1", RETRIEVAL_MISS)])
