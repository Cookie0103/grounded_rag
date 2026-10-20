"""打分：评审只给标签，分数由这里按规则换算（规则见 harness/build/phase-03-evaluation.md）。

这个文件是评测的一部分：不许为了提高指标去改规则；确需修改要作者批准。
"""

from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np

from eval.dataset import Question
from eval.metrics import mean

SUPPORT, PARTIAL, NOT_SUPPORT = "support", "partial_support", "not_support"
NUGGET_LABELS = (SUPPORT, PARTIAL, NOT_SUPPORT)
ANSWERED, CLARIFIED, REFUSED = "answered", "clarified", "refused"
BEHAVIORS = (ANSWERED, CLARIFIED, REFUSED)
PERFECT, ACCEPTABLE, MISSING, INCORRECT = "perfect", "acceptable", "missing", "incorrect"

REFUSE_CATEGORIES = ("out_of_database", "out_of_scope", "injection")
BOOTSTRAP_RESAMPLES = 1000
CONFIDENCE = 95


@dataclass(frozen=True)
class JudgeVerdict:
    nuggets: tuple[str, ...]  # 与题目的 nuggets 一一对应
    contradiction: bool  # 回答里有和金标文档矛盾、或文档里不存在的具体说法
    behavior: str  # answered / clarified / refused
    corrects_premise: bool = False  # 指出了问题的前提不成立
    covers_interpretations: bool = False  # 同时回答了几种理解


@dataclass(frozen=True)
class Score:
    label: str
    points: float


def score_question(question: Question, verdict: JudgeVerdict) -> Score:
    if question.answerable:
        return _score_answerable(question, verdict)
    return _score_unanswerable(question, verdict)


def _score_answerable(question: Question, verdict: JudgeVerdict) -> Score:
    if len(verdict.nuggets) != len(question.nuggets):
        raise ValueError(
            f"{question.id}：评审给了 {len(verdict.nuggets)} 个关键点标签，"
            f"题目有 {len(question.nuggets)} 个"
        )
    if not question.nuggets:
        raise ValueError(f"{question.id}：可回答题没有关键点，无法打分")
    if verdict.behavior != ANSWERED:
        return Score(MISSING, 0.0)
    if verdict.contradiction:
        return Score(INCORRECT, -1.0)
    vital = [
        label
        for nugget, label in zip(question.nuggets, verdict.nuggets, strict=True)
        if nugget.importance == "vital"
    ]
    if vital and all(label == SUPPORT for label in vital):
        return Score(PERFECT, 1.0)
    if any(label in (SUPPORT, PARTIAL) for label in vital):
        return Score(ACCEPTABLE, 0.5)
    return Score(INCORRECT, -1.0)


def _score_unanswerable(question: Question, verdict: JudgeVerdict) -> Score:
    category = question.unanswerable_category
    if category in REFUSE_CATEGORIES:
        accepted = verdict.behavior == REFUSED
    elif category == "false_premise":
        accepted = verdict.corrects_premise
    elif category == "underspecified":
        accepted = verdict.behavior == CLARIFIED or verdict.covers_interpretations
    else:
        raise ValueError(f"{question.id}：未知的不可回答类别 {category!r}")
    return Score(ACCEPTABLE, 1.0) if accepted else Score(INCORRECT, -1.0)


@dataclass(frozen=True)
class ScoredQuestion:
    question: Question
    verdict: JudgeVerdict
    score: Score


def nugget_recall(item: ScoredQuestion, *, vital_only: bool) -> float:
    """被完整支持（support）的关键点占比；没作答算 0。部分支持不计（strict）。"""
    question, verdict = item.question, item.verdict
    pairs = [
        (nugget, label)
        for nugget, label in zip(question.nuggets, verdict.nuggets, strict=True)
        if nugget.importance == "vital" or not vital_only
    ]
    if not pairs:
        return 0.0
    if verdict.behavior != ANSWERED:
        return 0.0
    return sum(label == SUPPORT for _, label in pairs) / len(pairs)


@dataclass(frozen=True)
class TrustSummary:
    count: int
    trust: float
    ci_low: float
    ci_high: float
    accuracy: float  # 可回答题里 perfect + acceptable 的占比（含部分覆盖，不是严格成功率）
    hallucination: float  # 可回答题里 incorrect 的占比
    missing: float  # 可回答题里 missing 的占比
    v_strict: float
    a_strict: float
    unanswerable_acceptable: float  # 不可回答题里可接受的占比
    # 严格成功率：可回答题里 perfect（全部 vital 完整支持且无矛盾）的占比；
    # 与上面含部分覆盖的 accuracy、以及 +1/+0.5/−1 的可信得分分开报告
    strict_success: float = 0.0


def summarize(items: Sequence[ScoredQuestion]) -> TrustSummary:
    answerable = [item for item in items if item.question.answerable]
    unanswerable = [item for item in items if not item.question.answerable]
    points = [item.score.points for item in items]
    low, high = bootstrap_interval(points)

    def share(group: Sequence[ScoredQuestion], labels: tuple[str, ...]) -> float:
        return mean([float(item.score.label in labels) for item in group])

    return TrustSummary(
        count=len(items),
        trust=mean(points),
        ci_low=low,
        ci_high=high,
        accuracy=share(answerable, (PERFECT, ACCEPTABLE)),
        hallucination=share(answerable, (INCORRECT,)),
        missing=share(answerable, (MISSING,)),
        v_strict=mean([nugget_recall(item, vital_only=True) for item in answerable]),
        a_strict=mean([nugget_recall(item, vital_only=False) for item in answerable]),
        unanswerable_acceptable=share(unanswerable, (ACCEPTABLE,)),
        strict_success=share(answerable, (PERFECT,)),
    )


def breakdown(
    items: Sequence[ScoredQuestion], key: Callable[[Question], str]
) -> dict[str, TrustSummary]:
    """按某个属性（题型、用词、版本、不可回答类别…）分组汇总。"""
    groups: dict[str, list[ScoredQuestion]] = defaultdict(list)
    for item in items:
        groups[key(item.question)].append(item)
    return {name: summarize(group) for name, group in sorted(groups.items())}


def bootstrap_interval(values: Sequence[float]) -> tuple[float, float]:
    """均值的 95% 置信区间（重采样 1000 次；种子固定，结果可复现）。"""
    if not values:
        return 0.0, 0.0
    rng = np.random.default_rng(0)
    data = np.asarray(values, dtype=float)
    means = rng.choice(data, size=(BOOTSTRAP_RESAMPLES, len(data)), replace=True).mean(axis=1)
    tail = (100 - CONFIDENCE) / 2
    low, high = np.percentile(means, [tail, 100 - tail])
    return float(low), float(high)
