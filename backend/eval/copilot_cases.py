"""日文 Copilot 评测用例的 JSONL 契约与校验。"""

import json
from collections import Counter
from collections.abc import Collection, Sequence
from datetime import date
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.orchestration.models import INTENTS, Channel, Intent
from app.tools.definitions import TOOL_DEFINITIONS
from eval.dataset import IMPORTANCE, MAX_NUGGETS, MIN_NUGGETS, Issue, Nugget

type CaseCategory = Literal["intent", "policy", "lookup", "lane", "guard"]
type CaseSplit = Literal["dev", "holdout", "test"]
type CaseOutcome = Literal["answer", "handoff", "denied", "degraded", "blocked", "redacted"]
type CaseFault = Literal["timeout", "5xx"]
type GuardKind = Literal["pii", "injection", "unsupported_number", "promise"]
type ValidationScope = Literal["rows", "synthetic", "policy-dev", "policy-test", "all"]
type _Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

_COUNT_TOLERANCE = 0.20
_MULTI_TURN_HISTORY = 2
_SYNTHETIC_COUNTS: dict[CaseCategory, int] = {"intent": 160, "lookup": 40, "lane": 20, "guard": 20}


class CopilotCase(BaseModel):
    """一条主评测请求及其可判定的期望。"""

    id: _Text
    category: CaseCategory
    question: _Text
    synthetic: Annotated[bool, Field(strict=True)]
    split: CaseSplit = "dev"
    channel: Channel = "customer"
    agent_id: _Text | None = None
    customer_id: _Text | None = None
    history: tuple[_Text, ...] = ()
    expected_intent: Intent | None = None
    expected_outcome: CaseOutcome | None = None
    expected_tools: tuple[_Text, ...] = ()
    expected_claims: tuple[_Text, ...] = ()
    as_of: date | None = None
    gold_docs: tuple[_Text, ...] = ()
    gold_doc_groups: tuple[tuple[_Text, ...], ...] = ()
    nuggets: tuple[Nugget, ...] = ()
    unanswerable_category: _Text | None = None
    version_trap: bool = False
    fault: CaseFault | None = None
    large_response: bool = False
    guard_kind: GuardKind | None = None

    @property
    def answerable(self) -> bool:
        """规程题可以按提供的证据作答。"""
        return self.unanswerable_category is None

    @property
    def required_groups(self) -> tuple[tuple[str, ...], ...]:
        """每组至少需要一篇命中，单独登记的文档各为一组。"""
        return self.gold_doc_groups or tuple((document,) for document in self.gold_docs)


def load_cases(path: Path) -> list[CopilotCase]:
    """读取评测 JSONL，并兼容作者的既有规程题字段。"""
    cases: list[CopilotCase] = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise ValueError("一行必须为一个对象")
                if "category" not in item:
                    item["category"] = "policy"
                    item.setdefault("synthetic", False)
                if item.get("type") == "version":
                    item.setdefault("version_trap", True)
                cases.append(CopilotCase.model_validate(item))
            except ValueError as error:
                raise ValueError(f"{path}:{number} 用例格式有误：{error}") from error
    return cases


def _check_policy(case: CopilotCase) -> list[str]:
    if not case.answerable:
        if case.gold_docs or case.gold_doc_groups or case.nuggets:
            return ["不可回答题的金标文档与关键点应为空"]
        return []
    errors: list[str] = []
    if not case.required_groups or any(not group for group in case.required_groups):
        errors.append("可回答规程题需要金标文档，每个等价组至少一篇")
    if not MIN_NUGGETS <= len(case.nuggets) <= MAX_NUGGETS:
        errors.append(f"规程关键点数量应为 {MIN_NUGGETS}～{MAX_NUGGETS}")
    if not any(nugget.importance == "vital" for nugget in case.nuggets):
        errors.append("至少需要一项 vital 规程关键点")
    if any(
        nugget.importance not in IMPORTANCE or not nugget.text.strip() for nugget in case.nuggets
    ):
        errors.append("规程关键点须有非空文本和合法 importance")
    return errors


def _check_lookup(case: CopilotCase) -> list[str]:
    errors: list[str] = []
    if case.channel != "agent" or not case.agent_id or not case.customer_id:
        errors.append("查数题需要坐席泳道、agent_id 和 customer_id")
    if case.expected_intent != "lookup" or not case.expected_tools:
        errors.append("查数题需要 lookup 意图和期望工具")
    if case.expected_outcome not in {"answer", "denied", "degraded"}:
        errors.append("查数题需要 answer、denied 或 degraded 行为")
    if bool(case.expected_claims) != (case.expected_outcome == "answer"):
        errors.append("成功查数题需要金标数字，其他查数题应留空")
    if bool(case.fault) != (case.expected_outcome == "degraded"):
        errors.append("故障注入与 degraded 行为必须同时填写")
    if case.large_response and (
        case.expected_outcome != "answer" or "query_repayment_schedule" not in case.expected_tools
    ):
        errors.append("大返回题需要成功查询还款表")
    return errors


def _check_lane(case: CopilotCase) -> list[str]:
    errors: list[str] = []
    if case.channel != "customer" or case.expected_tools or case.expected_claims:
        errors.append("客户泳道边界题不应声明业务工具或客户数字")
    if (case.expected_intent, case.expected_outcome) not in {
        ("lookup", "handoff"),
        ("policy", "answer"),
    }:
        errors.append("客户泳道题应为规程作答或查数转人工")
    if case.expected_outcome == "answer" and not case.nuggets:
        errors.append("泳道规程题需要作答关键点")
    return errors


def _check_category(case: CopilotCase) -> list[str]:
    match case.category:
        case "policy":
            return _check_policy(case)
        case "lookup":
            return _check_lookup(case)
        case "lane":
            return _check_lane(case)
        case "intent":
            return ["意图题需要 expected_intent"] if case.expected_intent is None else []
        case "guard":
            if case.expected_outcome not in {"blocked", "redacted"}:
                return ["护栏题需要 blocked 或 redacted 行为"]
            return []


def _check_fields(case: CopilotCase, known_documents: Collection[str] | None) -> list[str]:
    errors: list[str] = []
    if case.category != "policy" and (not case.synthetic or case.split == "test"):
        errors.append("意图、查数、泳道与护栏用例须为合成开发集或保留集")
    if case.version_trap and case.as_of is None:
        errors.append("版本陷阱题须指定 as_of 日期")
    if case.category != "lookup" and (case.fault or case.large_response):
        errors.append("只有查数题可以登记故障注入或大返回")
    if case.guard_kind is not None:
        outcome = "redacted" if case.guard_kind == "pii" else "blocked"
        if case.category != "guard" or case.expected_outcome != outcome:
            errors.append("护栏类别须与护栏题的期望行为匹配")
    unknown_tools = set(case.expected_tools).difference(TOOL_DEFINITIONS)
    if unknown_tools:
        errors.append(f"工具未注册：{', '.join(sorted(unknown_tools))}")
    if known_documents is not None:
        named_documents = set(case.gold_docs).union(*case.required_groups)
        missing = named_documents.difference(known_documents)
        if missing:
            errors.append(f"金标文档不在语料里：{', '.join(sorted(missing))}")
    return [*errors, *_check_category(case)]


def _check_count(label: str, actual: int, target: int) -> list[Issue]:
    if abs(actual - target) > target * _COUNT_TOLERANCE:
        return [Issue(label, f"实际 {actual} 条，目标约 {target} 条（容许偏差 20%）")]
    return []


def _check_synthetic_counts(cases: Sequence[CopilotCase]) -> list[Issue]:
    totals = Counter(case.category for case in cases)
    intents = [case for case in cases if case.category == "intent"]
    lookup = [case for case in cases if case.category == "lookup"]
    lane = [case for case in cases if case.category == "lane"]
    issues = [
        issue
        for category, target in _SYNTHETIC_COUNTS.items()
        for issue in _check_count(category, totals[category], target)
    ]
    intent_counts: Counter[str | None] = Counter(case.expected_intent for case in intents)
    checks = [
        *((intent, intent_counts[intent], 40) for intent in INTENTS),
        ("第三轮及以后", sum(len(case.history) >= _MULTI_TURN_HISTORY for case in intents), 40),
        ("查数故障", sum(case.fault is not None for case in lookup), 8),
        ("查数越权", sum(case.expected_outcome == "denied" for case in lookup), 6),
        ("查数大返回", sum(case.large_response for case in lookup), 4),
        ("客户规程", sum(case.expected_intent == "policy" for case in lane), 12),
        ("客户转人工", sum(case.expected_intent == "lookup" for case in lane), 8),
    ]
    for label, actual, target in checks:
        issues.extend(_check_count(label, actual, target))
    for category in _SYNTHETIC_COUNTS:
        for split in ("dev", "holdout"):
            if not any(case.category == category and case.split == split for case in cases):
                issues.append(Issue(category, f"缺少 {split} 用例"))
    return issues


def _check_policy_counts(cases: Sequence[CopilotCase], scope: ValidationScope) -> list[Issue]:
    policy = [case for case in cases if case.category == "policy"]
    issues: list[Issue] = []
    if scope in {"policy-dev", "all"}:
        issues.extend(_check_count("规程开发集", sum(case.split == "dev" for case in policy), 40))
    if scope in {"policy-test", "all"}:
        issues.extend(_check_count("规程测试集", sum(case.split == "test" for case in policy), 20))
    if scope == "all":
        issues.extend(_check_count("规程版本陷阱", sum(case.version_trap for case in policy), 12))
        issues.extend(_check_count("不可回答规程", sum(not case.answerable for case in policy), 8))
    return issues


def validate_cases(
    cases: Sequence[CopilotCase],
    *,
    scope: ValidationScope = "rows",
    known_documents: Collection[str] | None = None,
) -> list[Issue]:
    """检查字段、重复 ID，以及指定评测集的数量和覆盖。"""
    seen: set[str] = set()
    issues: list[Issue] = []
    for case in cases:
        if case.id in seen:
            issues.append(Issue(case.id, "id 重复"))
        seen.add(case.id)
        issues.extend(Issue(case.id, error) for error in _check_fields(case, known_documents))
    if scope in {"synthetic", "all"}:
        issues.extend(_check_synthetic_counts(cases))
    if scope in {"policy-dev", "policy-test", "all"}:
        issues.extend(_check_policy_counts(cases, scope))
    return issues
