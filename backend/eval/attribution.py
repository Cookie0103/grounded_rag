"""错误归因：没拿到 100 分的可回答题，错在检索、上下文不充分，还是生成。"""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from app.core.config import FINAL_TOP_K
from eval.judge import Judge
from eval.metrics import hit_groups_at_k
from eval.scoring import PERFECT, ScoredQuestion
from eval.systems import SystemAnswer

RETRIEVAL_MISS = "retrieval_miss"  # 金标文档没进前 K
INSUFFICIENT = "insufficient_context"  # 金标文档进了，但上下文不足以推出答案
GENERATION = "generation_error"  # 上下文足够，回答仍然不对
UNKNOWN = "unknown"  # 评审判断失败，无法归因


@dataclass(frozen=True)
class Attribution:
    question_id: str
    cause: str


async def attribute_errors(
    scored: Sequence[ScoredQuestion], answers: Sequence[SystemAnswer], judge: Judge
) -> list[Attribution]:
    by_id = {answer.question_id: answer for answer in answers}
    results: list[Attribution] = []
    for item in scored:
        question = item.question
        if not question.answerable or item.score.label == PERFECT:
            continue
        answer = by_id[question.id]
        if not hit_groups_at_k(question.required_groups, answer.retrieved_docs, FINAL_TOP_K):
            results.append(Attribution(question.id, RETRIEVAL_MISS))
            continue
        try:
            enough = await judge.sufficient(question, answer.contexts)
        except Exception:  # noqa: BLE001  一道题归因失败不能让整份报告出不来
            results.append(Attribution(question.id, UNKNOWN))
            continue
        results.append(Attribution(question.id, GENERATION if enough else INSUFFICIENT))
    return results


def cause_counts(attributions: Sequence[Attribution]) -> dict[str, int]:
    return dict(Counter(item.cause for item in attributions))
