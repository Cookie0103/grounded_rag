"""把被测系统的回答和评审的标签汇总成评测结果。"""

import json
import logging
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from app.core.config import FINAL_TOP_K
from eval.dataset import Question
from eval.judge import Judge
from eval.metrics import hit_groups_at_k, mean, reciprocal_rank
from eval.scoring import JudgeVerdict, ScoredQuestion, score_question
from eval.systems import SystemAnswer

ABSTAIN_ROUTES = ("CLARIFY", "REFUSE")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievalStats:
    questions: int
    recall_at_5: float
    mrr: float


@dataclass
class EvalResult:
    system_name: str
    questions: list[Question]
    answers: list[SystemAnswer]
    scored: list[ScoredQuestion] = field(default_factory=list)
    judge_errors: dict[str, str] = field(default_factory=dict)
    system_errors: dict[str, str] = field(default_factory=dict)

    def retrieval_by(self, key: Callable[[Question], str]) -> dict[str, RetrievalStats]:
        return retrieval_breakdown(self.questions, self.answers, key)


def retrieval_stats(pairs: Sequence[tuple[Question, SystemAnswer]]) -> RetrievalStats:
    """只统计有金标文档的可回答题。"""
    usable = [(q, a) for q, a in pairs if q.answerable and q.gold_docs and a.error is None]
    return RetrievalStats(
        len(usable),
        mean(
            [
                float(hit_groups_at_k(q.required_groups, a.retrieved_docs, FINAL_TOP_K))
                for q, a in usable
            ]
        ),
        mean([reciprocal_rank(q.all_gold_docs, a.retrieved_docs) for q, a in usable]),
    )


def retrieval_breakdown(
    questions: Sequence[Question],
    answers: Sequence[SystemAnswer],
    key: Callable[[Question], str],
) -> dict[str, RetrievalStats]:
    groups: dict[str, list[tuple[Question, SystemAnswer]]] = defaultdict(list)
    for question, answer in zip(questions, answers, strict=True):
        groups[key(question)].append((question, answer))
    return {name: retrieval_stats(pairs) for name, pairs in sorted(groups.items())}


def route_accuracy(questions: Sequence[Question], answers: Sequence[SystemAnswer]) -> float | None:
    """实际路由等于期望路由的比例；没有路由信息的系统返回 None。"""
    pairs = [
        (q, a) for q, a in zip(questions, answers, strict=True) if q.expected_route and a.route
    ]
    if not pairs:
        return None
    return mean([float(q.expected_route == a.route) for q, a in pairs])


def latency_p95_ms(answers: Sequence[SystemAnswer]) -> float:
    values = [a.latency_ms for a in answers if a.error is None]
    return float(np.percentile(values, 95)) if values else 0.0


def cost_per_question(answers: Sequence[SystemAnswer]) -> float:
    return mean([a.cost_cny for a in answers])


async def evaluate(
    system_name: str,
    questions: Sequence[Question],
    answers: Sequence[SystemAnswer],
    judge: Judge | None,
    *,
    verdict_cache: Path | None = None,
    template_name: str = "judge_v1.md",
    include_contexts: bool = False,
) -> EvalResult:
    """评审给每个作答的题打标签（已缓存的不再问），再由 scoring 换算成分数。"""
    result = EvalResult(system_name, list(questions), list(answers))
    result.system_errors = {a.question_id: a.error for a in answers if a.error}
    if judge is None:
        return result
    cached = load_verdicts(verdict_cache)
    for question, answer in zip(questions, answers, strict=True):
        if answer.answer is None:
            continue
        verdict = cached.get(question.id)
        if verdict is None:
            try:
                if template_name == "judge_v1.md" and not include_contexts:
                    verdict = await judge.judge(question, answer.answer)
                else:
                    verdict = await judge.judge(
                        question,
                        answer.answer,
                        contexts=answer.contexts if include_contexts else (),
                        template_name=template_name,
                    )
            except Exception as error:  # noqa: BLE001  一道题评审失败不能让整轮评测中断
                result.judge_errors[question.id] = f"{type(error).__name__}: {error}"
                logger.error("评审失败 %s：%s", question.id, type(error).__name__)
                continue
            _append_verdict(verdict_cache, question.id, verdict)
            logger.info("评审完成 %s", question.id)
        result.scored.append(ScoredQuestion(question, verdict, score_question(question, verdict)))
    return result


def load_verdicts(path: Path | None) -> dict[str, JudgeVerdict]:
    """读取已有标签，不触发评审调用。"""
    if path is None or not path.exists():
        return {}
    verdicts: dict[str, JudgeVerdict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            data = json.loads(line)
            verdicts[data["question_id"]] = JudgeVerdict(
                nuggets=tuple(data["nuggets"]),
                contradiction=data["contradiction"],
                behavior=data["behavior"],
                corrects_premise=data["corrects_premise"],
                covers_interpretations=data["covers_interpretations"],
            )
    return verdicts


def _append_verdict(path: Path | None, question_id: str, verdict: JudgeVerdict) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "question_id": question_id,
        "nuggets": list(verdict.nuggets),
        "contradiction": verdict.contradiction,
        "behavior": verdict.behavior,
        "corrects_premise": verdict.corrects_premise,
        "covers_interpretations": verdict.covers_interpretations,
    }
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
