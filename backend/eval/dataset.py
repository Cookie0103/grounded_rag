"""评测题的读取和校验。

字段含义见 harness/build/phase-03-evaluation.md
和 harness/archive/2026-10-16/notes-evaluation.md §7.1。
"""

import json
from collections import Counter
from collections.abc import Callable, Collection
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TYPES = ("fact_single", "summary", "reasoning", "version", "unanswerable")
UNANSWERABLE_CATEGORIES = (
    "out_of_database",
    "false_premise",
    "underspecified",
    "out_of_scope",
    "injection",
)
ROUTES = ("DIRECT", "SINGLE", "MULTI", "CLARIFY", "REFUSE")
EDITIONS = ("self_host", "cloud")
LEXICAL = ("similar", "distant")
PERSONAS = ("novice", "expert")
IMPORTANCE = ("vital", "okay")
# 题型配额（100 题）；开发集和测试集按 7:3 分，所以单独看开发集时按比例缩小
QUOTAS = {
    "fact_single": 35,
    "summary": 15,
    "reasoning": 20,
    "version": 10,
    "unanswerable": 20,
}
UNANSWERABLE_QUOTAS = {
    "out_of_database": 6,
    "false_premise": 4,
    "underspecified": 5,
    "out_of_scope": 3,
    "injection": 2,
}
# 题干里出现这些说法，说明问题依赖「上下文」，离开原文就看不懂
LEAK_PHRASES = ("根据文档", "文档中", "上下文", "上文", "本文", "这篇文章", "该文档")
MIN_NUGGETS, MAX_NUGGETS = 2, 4
MIN_REASONING_DOCS = 2

Report = Callable[[str], None]


@dataclass(frozen=True)
class Nugget:
    text: str
    importance: str  # vital / okay


@dataclass(frozen=True)
class Question:
    id: str
    question: str
    gold_docs: tuple[str, ...]
    edition: str | None = None  # self_host / cloud / None
    lexical: str = "similar"  # 用词是否贴近原文：similar / distant
    type: str = "fact_single"
    unanswerable_category: str | None = None
    expected_route: str | None = None
    nuggets: tuple[Nugget, ...] = ()
    persona: str = "novice"
    phrasing: str = "natural_short"
    premise: str = "direct"
    split: str = "dev"

    @property
    def answerable(self) -> bool:
        return self.unanswerable_category is None


def load_questions(path: Path) -> list[Question]:
    questions: list[Question] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            questions.append(_parse(json.loads(line)))
        except (json.JSONDecodeError, KeyError, TypeError) as error:
            raise ValueError(f"{path}:{number} 不是合法的题目：{error!r}") from error
    return questions


def _parse(item: dict[str, Any]) -> Question:
    nuggets = tuple(
        Nugget(str(raw["text"]), str(raw["importance"])) for raw in item.get("nuggets", [])
    )
    category = item.get("unanswerable_category")
    return Question(
        id=str(item["id"]),
        question=str(item["question"]),
        gold_docs=tuple(item["gold_docs"]),
        edition=item.get("edition"),
        lexical=str(item.get("lexical", "similar")),
        type=str(item.get("type", "unanswerable" if category else "fact_single")),
        unanswerable_category=str(category) if category else None,
        expected_route=item.get("expected_route"),
        nuggets=nuggets,
        persona=str(item.get("persona", "novice")),
        phrasing=str(item.get("phrasing", "natural_short")),
        premise=str(item.get("premise", "direct")),
        split=str(item.get("split", "dev")),
    )


@dataclass(frozen=True)
class Issue:
    question_id: str
    message: str
    is_error: bool = True  # False 表示只是提醒


def validate_questions(
    questions: list[Question], known_documents: Collection[str] | None = None
) -> list[Issue]:
    """检查题目的格式和内容。known_documents 给了就同时检查金标文档是否真的在语料里。"""
    issues: list[Issue] = []
    seen: set[str] = set()
    for question in questions:
        if question.id in seen:
            issues.append(Issue(question.id, "id 重复"))
        seen.add(question.id)
        issues += _validate_one(question, known_documents)
    return issues


def _validate_one(question: Question, known_documents: Collection[str] | None) -> list[Issue]:
    issues: list[Issue] = []

    def error(message: str) -> None:
        issues.append(Issue(question.id, message))

    def warn(message: str) -> None:
        issues.append(Issue(question.id, message, is_error=False))

    _check_choices(question, error)
    if not question.question.strip():
        error("题干为空")
    if known_documents is not None:
        missing = [doc for doc in question.gold_docs if doc not in known_documents]
        if missing:
            error(f"金标文档不在语料里：{', '.join(missing)}")
    if question.answerable:
        _check_answerable(question, error)
    else:
        _check_unanswerable(question, error)
    leaked = [phrase for phrase in LEAK_PHRASES if phrase in question.question]
    if leaked:
        warn(f"题干里有「{'、'.join(leaked)}」，离开原文可能看不懂")
    return issues


def _check_choices(question: Question, error: Report) -> None:
    choices = [
        ("type", question.type, TYPES),
        ("lexical", question.lexical, LEXICAL),
        ("persona", question.persona, PERSONAS),
    ]
    for name, value, allowed in choices:
        if value not in allowed:
            error(f"{name}={value!r} 不在 {list(allowed)} 里")
    if question.edition is not None and question.edition not in EDITIONS:
        error(f"edition={question.edition!r} 不在 {list(EDITIONS)} 里")
    if question.expected_route is not None and question.expected_route not in ROUTES:
        error(f"expected_route={question.expected_route!r} 不在 {list(ROUTES)} 里")


def _check_answerable(question: Question, error: Report) -> None:
    if question.type == "unanswerable":
        error("type 是 unanswerable，但没有 unanswerable_category")
    if not question.gold_docs:
        error("可回答题必须有金标文档")
    if question.type == "reasoning" and len(question.gold_docs) < MIN_REASONING_DOCS:
        error("跨篇推理题至少要 2 篇金标文档")
    if question.type == "version" and question.edition is None:
        error("版本差异题必须写明 edition")
    if not MIN_NUGGETS <= len(question.nuggets) <= MAX_NUGGETS:
        error(f"关键点要 {MIN_NUGGETS}～{MAX_NUGGETS} 条，现在是 {len(question.nuggets)} 条")
    if question.nuggets and not any(n.importance == "vital" for n in question.nuggets):
        error("至少要有一条 vital 关键点")
    for nugget in question.nuggets:
        if nugget.importance not in IMPORTANCE or not nugget.text.strip():
            error(f"关键点不合法：{nugget}")


def _check_unanswerable(question: Question, error: Report) -> None:
    if question.unanswerable_category not in UNANSWERABLE_CATEGORIES:
        error(f"unanswerable_category={question.unanswerable_category!r} 不合法")
    if question.type != "unanswerable":
        error("有 unanswerable_category 的题 type 必须是 unanswerable")
    if question.nuggets:
        error("不可回答题不需要关键点")


def quota_report(questions: list[Question]) -> list[str]:
    """各题型的数量与 100 题配额（按题数比例缩放）的对比；只是提醒，不算错误。"""
    total = len(questions) or 1
    scale = total / sum(QUOTAS.values())
    counts = Counter(question.type for question in questions)
    lines = [f"共 {len(questions)} 题"]
    for name, quota in QUOTAS.items():
        lines.append(f"- {name}：{counts.get(name, 0)}（按比例应有约 {quota * scale:.1f}）")
    categories = Counter(q.unanswerable_category for q in questions if q.unanswerable_category)
    for name, quota in UNANSWERABLE_QUOTAS.items():
        lines.append(f"  - {name}：{categories.get(name, 0)}（按比例约 {quota * scale:.1f}）")
    return lines
