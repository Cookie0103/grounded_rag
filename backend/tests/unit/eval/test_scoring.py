import math

import pytest

from eval.dataset import Nugget, Question
from eval.scoring import (
    ACCEPTABLE,
    INCORRECT,
    MISSING,
    PERFECT,
    JudgeVerdict,
    ScoredQuestion,
    bootstrap_interval,
    breakdown,
    nugget_recall,
    score_question,
    summarize,
)


def _answerable(importances: tuple[str, ...] = ("vital", "okay")) -> Question:
    nuggets = tuple(Nugget(f"关键点{i}", imp) for i, imp in enumerate(importances))
    return Question("q", "问题", ("d",), nuggets=nuggets)


def _unanswerable(category: str) -> Question:
    return Question("u", "问题", (), type="unanswerable", unanswerable_category=category)


def _verdict(*labels: str, **fields: object) -> JudgeVerdict:
    defaults: dict[str, object] = {"contradiction": False, "behavior": "answered"}
    return JudgeVerdict(nuggets=tuple(labels), **{**defaults, **fields})  # type: ignore[arg-type]


# ---------------------------------------------------------------- 可回答题：换算表逐行


def test_all_vital_nuggets_supported_is_perfect() -> None:
    score = score_question(_answerable(), _verdict("support", "not_support"))

    assert (score.label, score.points) == (PERFECT, 1.0)


def test_partial_support_of_a_vital_nugget_is_acceptable() -> None:
    score = score_question(_answerable(), _verdict("partial_support", "support"))

    assert (score.label, score.points) == (ACCEPTABLE, 0.5)


def test_one_of_two_vital_nuggets_supported_is_acceptable() -> None:
    score = score_question(_answerable(("vital", "vital")), _verdict("support", "not_support"))

    assert (score.label, score.points) == (ACCEPTABLE, 0.5)


def test_no_vital_nugget_covered_is_incorrect_even_if_the_okay_one_is() -> None:
    score = score_question(_answerable(), _verdict("not_support", "support"))

    assert (score.label, score.points) == (INCORRECT, -1.0)


def test_contradiction_makes_it_incorrect_whatever_the_nuggets_say() -> None:
    score = score_question(_answerable(), _verdict("support", "support", contradiction=True))

    assert (score.label, score.points) == (INCORRECT, -1.0)


@pytest.mark.parametrize("behavior", ["clarified", "refused"])
def test_not_answering_is_missing_and_scores_zero(behavior: str) -> None:
    score = score_question(_answerable(), _verdict("support", "support", behavior=behavior))

    assert (score.label, score.points) == (MISSING, 0.0)


def test_missing_beats_contradiction() -> None:
    verdict = _verdict("not_support", "not_support", behavior="refused", contradiction=True)

    assert score_question(_answerable(), verdict).label == MISSING


def test_wrong_number_of_labels_is_an_error() -> None:
    with pytest.raises(ValueError, match="2 个"):
        score_question(_answerable(), _verdict("support"))


def test_answerable_question_without_nuggets_cannot_be_scored() -> None:
    with pytest.raises(ValueError, match="没有关键点"):
        score_question(Question("q", "问题", ("d",)), _verdict())


# ---------------------------------------------------------------- 不可回答题：每个类别


@pytest.mark.parametrize("category", ["out_of_database", "out_of_scope", "injection"])
def test_refusing_is_right_for_missing_out_of_scope_and_injection_questions(category: str) -> None:
    question = _unanswerable(category)

    assert score_question(question, _verdict(behavior="refused")).points == 1.0
    assert score_question(question, _verdict(behavior="answered")).points == -1.0
    assert score_question(question, _verdict(behavior="clarified")).points == -1.0


def test_false_premise_needs_the_premise_to_be_corrected_whatever_the_behavior() -> None:
    question = _unanswerable("false_premise")

    assert (
        score_question(question, _verdict(behavior="answered", corrects_premise=True)).points == 1
    )
    assert score_question(question, _verdict(behavior="refused", corrects_premise=True)).points == 1
    assert score_question(question, _verdict(behavior="answered")).points == -1.0
    assert score_question(question, _verdict(behavior="refused")).points == -1.0


def test_underspecified_needs_a_clarification_or_several_interpretations() -> None:
    question = _unanswerable("underspecified")

    assert score_question(question, _verdict(behavior="clarified")).points == 1.0
    assert (
        score_question(question, _verdict(behavior="answered", covers_interpretations=True)).points
        == 1
    )
    assert score_question(question, _verdict(behavior="answered")).points == -1.0
    assert score_question(question, _verdict(behavior="refused")).points == -1.0


def test_unknown_category_is_rejected() -> None:
    with pytest.raises(ValueError, match="未知"):
        score_question(_unanswerable("whatever"), _verdict())


# ---------------------------------------------------------------- 汇总


def _scored(question: Question, verdict: JudgeVerdict) -> ScoredQuestion:
    return ScoredQuestion(question, verdict, score_question(question, verdict))


def test_nugget_recall_counts_only_full_support_and_zero_when_not_answered() -> None:
    question = _answerable(("vital", "vital", "okay"))
    item = _scored(question, _verdict("support", "partial_support", "support"))
    silent = _scored(question, _verdict("support", "support", "support", behavior="refused"))

    assert math.isclose(nugget_recall(item, vital_only=True), 0.5)
    assert math.isclose(nugget_recall(item, vital_only=False), 2 / 3)
    assert nugget_recall(silent, vital_only=True) == 0.0


def test_summary_reports_trust_rates_and_unanswerable_acceptance() -> None:
    items = [
        _scored(_answerable(), _verdict("support", "support")),  # perfect +1
        _scored(_answerable(), _verdict("partial_support", "not_support")),  # acceptable +0.5
        _scored(_answerable(), _verdict("support", "support", contradiction=True)),  # -1
        _scored(_answerable(), _verdict("support", "support", behavior="refused")),  # 0
        _scored(_unanswerable("out_of_database"), _verdict(behavior="refused")),  # +1
        _scored(_unanswerable("out_of_database"), _verdict(behavior="answered")),  # -1
    ]

    summary = summarize(items)

    assert summary.count == 6
    assert math.isclose(summary.trust, (1 + 0.5 - 1 + 0 + 1 - 1) / 6)
    assert summary.accuracy == 0.5  # 4 道可回答题里 perfect + acceptable 两道
    assert summary.hallucination == 0.25
    assert summary.missing == 0.25
    assert summary.unanswerable_acceptable == 0.5
    assert summary.ci_low <= summary.trust <= summary.ci_high


def test_empty_summary_is_all_zeros() -> None:
    summary = summarize([])

    assert (summary.count, summary.trust, summary.ci_low, summary.ci_high) == (0, 0.0, 0.0, 0.0)


def test_breakdown_groups_by_the_given_attribute() -> None:
    items = [
        _scored(
            Question("a", "q", ("d",), lexical="distant", nuggets=(Nugget("x", "vital"),)),
            _verdict("support"),
        ),
        _scored(
            Question("b", "q", ("d",), lexical="similar", nuggets=(Nugget("x", "vital"),)),
            _verdict("not_support"),
        ),
    ]

    groups = breakdown(items, lambda question: question.lexical)

    assert list(groups) == ["distant", "similar"]
    assert groups["distant"].trust == 1.0
    assert groups["similar"].trust == -1.0


def test_bootstrap_interval_is_deterministic_and_brackets_the_mean() -> None:
    values = [1.0, -1.0, 0.5, 1.0, 0.0, -1.0, 1.0, 0.5]

    first = bootstrap_interval(values)

    assert first == bootstrap_interval(values)
    assert first[0] <= sum(values) / len(values) <= first[1]
    assert bootstrap_interval([1.0, 1.0, 1.0]) == (1.0, 1.0)
