"""把评测结果渲染成 Markdown 报告。"""

from collections.abc import Callable

from eval.attribution import Attribution, cause_counts
from eval.dataset import Question
from eval.evaluate import (
    EvalResult,
    RetrievalStats,
    cost_per_question,
    latency_p95_ms,
    route_accuracy,
)
from eval.scoring import TrustSummary, breakdown, summarize

GROUPS: list[tuple[str, Callable[[Question], str]]] = [
    ("题型", lambda q: q.type),
    ("用词", lambda q: q.lexical),
    ("版本", lambda q: q.edition or "未指定"),
    ("提问人", lambda q: q.persona),
]


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _trust_row(name: str, s: TrustSummary) -> str:
    return (
        f"| {name} | {s.count} | {s.trust:+.3f}（{s.ci_low:+.2f}～{s.ci_high:+.2f}） | "
        f"{_pct(s.strict_success)} | {_pct(s.accuracy)} | {_pct(s.hallucination)} | "
        f"{_pct(s.missing)} | "
        f"{_pct(s.v_strict)} | {_pct(s.a_strict)} | {_pct(s.unanswerable_acceptable)} |"
    )


TRUST_HEADER = [
    "| 分组 | 题数 | 可信得分（95% 区间） | 严格成功率 | 宽松正确率（含部分） | 答错率 "
    "| 未作答率 | V_strict | A_strict | 不可回答题可接受率 |",
    "|---|---|---|---|---|---|---|---|---|---|",
]


def _retrieval_row(name: str, s: RetrievalStats) -> str:
    return f"| {name} | {s.questions} | {_pct(s.recall_at_5)} | {s.mrr:.3f} |"


def render_report(result: EvalResult, attributions: list[Attribution] | None = None) -> str:
    lines = [f"# 评测报告：{result.system_name}", "", f"题数：{len(result.questions)}", ""]
    lines += _retrieval_section(result)
    if result.scored:
        lines += _trust_section(result)
    else:
        lines += ["## 回答质量", "", "没有评审结果（没有开评审，或系统没有生成回答）。", ""]
    if attributions:
        lines += _attribution_section(attributions)
    lines += _operations_section(result)
    lines += _error_section(result)
    return "\n".join(lines) + "\n"


def _retrieval_section(result: EvalResult) -> list[str]:
    lines = ["## 检索（只统计有金标文档的可回答题）", ""]
    lines += ["| 分组 | 题数 | Recall@5（文档级） | MRR |", "|---|---|---|---|"]
    for name, key in GROUPS:
        for group, stats in result.retrieval_by(key).items():
            lines.append(_retrieval_row(f"{name}={group}", stats))
    all_stats = result.retrieval_by(lambda _: "全部")["全部"] if result.questions else None
    if all_stats:
        lines.insert(4, _retrieval_row("**全部**", all_stats))
    return [*lines, ""]


def _trust_section(result: EvalResult) -> list[str]:
    lines = ["## 回答质量", "", *TRUST_HEADER, _trust_row("**全部**", summarize(result.scored))]
    for name, key in GROUPS:
        for group, summary in breakdown(result.scored, key).items():
            lines.append(_trust_row(f"{name}={group}", summary))
    unanswerable = [item for item in result.scored if not item.question.answerable]
    if unanswerable:
        lines += ["", "### 不可回答题（按类别）", "", *TRUST_HEADER]
        categories = breakdown(unanswerable, lambda q: q.unanswerable_category or "")
        lines += [_trust_row(name, summary) for name, summary in categories.items()]
    return [*lines, ""]


def _attribution_section(attributions: list[Attribution]) -> list[str]:
    lines = ["## 错误归因（没拿满分的可回答题）", "", "| 原因 | 题数 |", "|---|---|"]
    lines += [
        f"| {cause} | {count} |" for cause, count in sorted(cause_counts(attributions).items())
    ]
    return [*lines, ""]


def _operations_section(result: EvalResult) -> list[str]:
    lines = ["## 运行指标", ""]
    accuracy = route_accuracy(result.questions, result.answers)
    lines.append(f"- 路由准确率：{'无路由信息' if accuracy is None else _pct(accuracy)}")
    lines.append(f"- P95 延迟：{latency_p95_ms(result.answers):.0f} 毫秒")
    lines.append(f"- 每题平均成本：¥{cost_per_question(result.answers):.4f}")
    return [*lines, ""]


def _error_section(result: EvalResult) -> list[str]:
    if not result.system_errors and not result.judge_errors:
        return []
    lines = ["## 出错的题（没有计入上面的指标）", ""]
    lines += [f"- 系统 `{qid}`：{message}" for qid, message in result.system_errors.items()]
    lines += [f"- 评审 `{qid}`：{message}" for qid, message in result.judge_errors.items()]
    return [*lines, ""]
