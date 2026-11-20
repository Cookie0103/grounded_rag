"""住宅贷款 Copilot 同题回放的评分、指标和 Markdown 报告。"""

from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field

from eval.metrics import hit_at_k, hit_groups_at_k, mean, ranked_documents
from eval.scoring import BOOTSTRAP_RESAMPLES, CONFIDENCE, bootstrap_interval

type Tier = Literal["S", "L"]
type FaultMode = Literal["none", "5%-timeout", "explicit"]
type GroupKey = tuple[str, Tier, FaultMode]
type Display = Literal["rate", "ms", "cny", "tokens", "multiple"]
type Measurement = Callable[["EvalRow"], bool | int | float | None]

TOP_K = 5
MULTI_TURN_HISTORY = 2
LATENCY_PERCENTILE = 95
MIN_LATENCY_SAMPLES = 100
MIN_CALIBRATION_SAMPLES = 20
MIN_CALIBRATION_AGREEMENT = 0.85
INTENT_TARGET = 0.90
TOP5_TARGET = 0.85
FIRST_TOKEN_TARGET_MS = 3000
TOOL_FAILURE_TARGET = 0.005
REGRESSION_TARGET = 0.95
FAULT_LABELS: dict[FaultMode, str] = {
    "none": "无注入",
    "5%-timeout": "注入 5% 超时",
    "explicit": "指定故障注入",
}
INTENT_LABELS = ("smalltalk", "complaint", "policy", "lookup")
ERROR_LABELS = {
    "intent": "意图错",
    "retrieval": "检索错",
    "generation": "生成错",
    "tool": "工具错",
    "guard": "护栏行为偏差",
    "other": "待归因（证据不足）",
}
METRIC_ERRORS = {
    "intent": "intent",
    "top5": "retrieval",
    "tool_failure": "tool",
    "degradation": "tool",
    "unauthorized": "tool",
    "grounding": "generation",
}


class EvalRow(BaseModel):
    """一个系统、语料档和故障条件下的一条用例结果。空值表示缺少测量证据。"""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    case_id: str
    category: str
    system: str = "LangGraph"
    tier: Tier = "S"
    fault_mode: FaultMode = "none"
    expected_intent: str | None = None
    intent: str | None = None
    prior_turns: int = Field(default=0, ge=0)
    expected_outcome: str | None = None
    passed: bool | None = None
    error_category: str | None = None
    policy_answerable: bool | None = None
    gold_docs: tuple[str, ...] = ()
    gold_doc_groups: tuple[tuple[str, ...], ...] = ()
    retrieved_docs: tuple[str, ...] | None = None
    expired_docs: tuple[str, ...] | None = None
    version_trap: bool = False
    latency_ms: float | None = Field(default=None, ge=0)
    first_token_ms: float | None = Field(default=None, ge=0)
    intent_ms: float | None = Field(default=None, ge=0)
    rewrite_ms: float | None = Field(default=None, ge=0)
    retrieval_ms: float | None = Field(default=None, ge=0)
    tool_ms: float | None = Field(default=None, ge=0)
    generation_ms: float | None = Field(default=None, ge=0)
    cost_cny: float | None = Field(default=None, ge=0)
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    tools_ok: int | None = Field(default=None, ge=0)
    tools_failed: int | None = Field(default=None, ge=0)
    tools_denied: int | None = Field(default=None, ge=0)
    degraded_correctly: bool | None = None
    grounded_numbers: bool | None = None
    unauthorized_blocked: bool | None = None
    offline_acceptable: bool | None = None
    citation_docs: tuple[str, ...] | None = None
    source: str | None = None


class RunMetadata(BaseModel):
    """报告中用于核对回放条件的运行信息。"""

    dataset: str | None = None
    commit: str | None = None
    config: dict[str, str] | str | None = None
    models: dict[str, str] | str | None = None
    corpus_version: str | None = None
    dataset_version: str | None = None
    started_at: str | None = None
    hardware: dict[str, str] | str | None = None
    warmup: int | None = Field(default=None, ge=0)
    concurrency: int | None = Field(default=None, ge=1)


class Calibration(BaseModel):
    """作者人工校准与评审模型逐条判断的一致数。"""

    matched: int = Field(ge=0)
    total: int = Field(gt=0)

    @property
    def is_reliable(self) -> bool:
        """按阶段约定判断这批评审标签能否用于报告。"""
        return (
            self.total >= MIN_CALIBRATION_SAMPLES
            and MIN_CALIBRATION_AGREEMENT <= self.matched / self.total <= 1
        )


@dataclass(frozen=True)
class Metric:
    n: int = 0
    value: float | None = None
    low: float | None = None
    high: float | None = None
    numerator: int | None = None


@dataclass(frozen=True)
class Indicator:
    label: str
    measure: Measurement
    display: Display = "rate"


def _intent_hit(row: EvalRow) -> bool | None:
    if row.category != "intent" or row.expected_intent is None or row.intent is None:
        return None
    return row.intent == row.expected_intent


def _multi_turn_hit(row: EvalRow) -> bool | None:
    return _intent_hit(row) if row.prior_turns >= MULTI_TURN_HISTORY else None


def _top5_hit(row: EvalRow) -> bool | None:
    if row.policy_answerable is not True or row.retrieved_docs is None:
        return None
    ranked = ranked_documents(row.retrieved_docs)
    if row.gold_doc_groups:
        return hit_groups_at_k(row.gold_doc_groups, ranked, TOP_K)
    return hit_at_k(row.gold_docs, ranked, TOP_K) if row.gold_docs else None


def _expired_hit(row: EvalRow) -> bool | None:
    if not row.version_trap:
        return None
    if row.retrieved_docs == () and row.citation_docs == ():
        return False
    if row.expired_docs is None:
        return None
    top = ranked_documents(row.retrieved_docs or ())[:TOP_K]
    if set(row.expired_docs).intersection([*top, *(row.citation_docs or ())]):
        return True
    return False if row.retrieved_docs is not None and row.citation_docs is not None else None


def _degradation(row: EvalRow) -> bool | None:
    return row.degraded_correctly if row.tools_failed else None


INDICATORS = {
    "intent": Indicator("意图分类准确率", _intent_hit),
    "multi_turn": Indicator("多轮意图准确率（第 3 轮起）", _multi_turn_hit),
    "top5": Indicator("规程召回 Top5 命中率", _top5_hit),
    "expired": Indicator("过期引用率", _expired_hit),
    "first_token": Indicator("首字延迟 P95", lambda row: row.first_token_ms, "ms"),
    "latency": Indicator("整段端到端延迟 P95", lambda row: row.latency_ms, "ms"),
    "intent_latency": Indicator("意图节点耗时 P95", lambda row: row.intent_ms, "ms"),
    "rewrite_latency": Indicator("追问改写节点耗时 P95", lambda row: row.rewrite_ms, "ms"),
    "retrieval_latency": Indicator("检索节点耗时 P95", lambda row: row.retrieval_ms, "ms"),
    "tool_latency": Indicator("工具节点耗时 P95", lambda row: row.tool_ms, "ms"),
    "generation_latency": Indicator("生成节点耗时 P95", lambda row: row.generation_ms, "ms"),
    "cost": Indicator("单会话平均 token 成本", lambda row: row.cost_cny, "cny"),
    "prompt_tokens": Indicator("单会话平均输入 token", lambda row: row.prompt_tokens, "tokens"),
    "completion_tokens": Indicator(
        "单会话平均输出 token", lambda row: row.completion_tokens, "tokens"
    ),
    "tool_failure": Indicator("工具调用失败率", lambda row: row.tools_failed),
    "degradation": Indicator("降级正确率", _degradation),
    "grounding": Indicator("数字溯源率", lambda row: row.grounded_numbers),
    "unauthorized": Indicator("越权拦截率", lambda row: row.unauthorized_blocked),
    "regression": Indicator("评测集回归通过率", lambda row: row.passed),
    "offline": Indicator("离线可采纳率", lambda row: row.offline_acceptable),
}


def _percentile_interval(samples: NDArray[np.float64]) -> tuple[float, float]:
    tail = (100 - CONFIDENCE) / 2
    low, high = np.percentile(samples, [tail, 100 - tail])
    return float(low), float(high)


def _resample_indices(n: int) -> NDArray[np.int64]:
    return np.random.default_rng(0).integers(n, size=(BOOTSTRAP_RESAMPLES, n))


def _mean_metric(values: Sequence[float], *, proportion: bool = False) -> Metric:
    if not values:
        return Metric()
    low, high = bootstrap_interval(values)
    return Metric(len(values), mean(values), low, high, int(sum(values)) if proportion else None)


def _p95_metric(values: Sequence[float]) -> Metric:
    if not values:
        return Metric()
    data = np.asarray(values, dtype=float)
    samples = np.percentile(data[_resample_indices(len(values))], LATENCY_PERCENTILE, axis=1)
    low, high = _percentile_interval(samples)
    return Metric(len(values), float(np.percentile(data, LATENCY_PERCENTILE)), low, high)


def _ratio_metric(pairs: Sequence[tuple[float, float]], *, count_calls: bool = False) -> Metric:
    if not pairs:
        return Metric()
    left, right = np.asarray(pairs, dtype=float).T
    denominator = float(right.sum())
    if not denominator:
        return Metric(n=len(pairs))
    indices = _resample_indices(len(pairs))
    denominators = right[indices].sum(axis=1)
    valid = denominators > 0
    ratios = left[indices[valid]].sum(axis=1) / denominators[valid]
    low, high = _percentile_interval(ratios) if ratios.size else (None, None)
    numerator = float(left.sum())
    return Metric(
        int(denominator) if count_calls else len(pairs),
        numerator / denominator,
        low,
        high,
        int(numerator) if count_calls else None,
    )


def _tool_observations(rows: Sequence[EvalRow]) -> list[tuple[int, int]]:
    counts = []
    for row in rows:
        ok, failed, denied = row.tools_ok, row.tools_failed, row.tools_denied
        if ok is not None and failed is not None and denied is not None:
            total = ok + failed + denied
            if total:
                counts.append((failed, total))
    return counts


def _measure(rows: Sequence[EvalRow], indicator: Indicator) -> Metric:
    values = [float(value) for row in rows if (value := indicator.measure(row)) is not None]
    if indicator.display == "ms":
        return _p95_metric(values)
    return _mean_metric(values, proportion=indicator.display == "rate")


def build_metrics(
    rows: Sequence[EvalRow], *, calibration: Calibration | None = None
) -> dict[str, Metric]:
    """计算同一系统、语料档和故障条件下的指标及观察分母。"""
    ordered = sorted(rows, key=lambda row: row.case_id)
    result = {key: _measure(ordered, indicator) for key, indicator in INDICATORS.items()}
    result["tool_failure"] = _ratio_metric(_tool_observations(ordered), count_calls=True)
    if calibration is None or not calibration.is_reliable:
        result["offline"] = Metric()
    return result


def _paired_values(
    base: Sequence[EvalRow], compared: Sequence[EvalRow], measure: Measurement
) -> list[tuple[float, float]]:
    lookup = {row.case_id: measure(row) for row in base}
    pairs = []
    for row in sorted(compared, key=lambda item: item.case_id):
        baseline, value = lookup.get(row.case_id), measure(row)
        if baseline is not None and value is not None:
            pairs.append((float(value), float(baseline)))
    return pairs


def paired_top5(s_rows: Sequence[EvalRow], l_rows: Sequence[EvalRow]) -> Metric:
    """在同题都有召回证据的样本内计算 L 减 S 的命中率差。"""
    return _mean_metric([left - right for left, right in _paired_values(s_rows, l_rows, _top5_hit)])


def _display(value: float, display: Display) -> str:
    match display:
        case "rate":
            return f"{value:.2%}"
        case "ms":
            return f"{value:,.2f} 毫秒"
        case "cny":
            return f"¥{value:.6f}"
        case "tokens":
            return f"{value:,.2f}"
        case "multiple":
            return f"{value:.2f} 倍"


def _number(metric: Metric, display: Display) -> str:
    return _display(metric.value, display) if metric.value is not None else "未测"


def _interval(metric: Metric, display: Display) -> str:
    if metric.low is None or metric.high is None:
        return "未测"
    return f"[{_display(metric.low, display)}, {_display(metric.high, display)}]"


def _escaped(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def _metadata_value(value: Mapping[str, str] | str | int | None) -> str:
    if isinstance(value, Mapping):
        fields = (f"{_escaped(key)}＝{_escaped(item)}" for key, item in sorted(value.items()))
        return "、".join(fields) or "未测"
    return "未测" if value is None else _escaped(str(value))


def _run_section(metadata: RunMetadata) -> list[str]:
    fields = {
        "题集": metadata.dataset,
        "题集版本": metadata.dataset_version,
        "代码提交": metadata.commit,
        "语料版本": metadata.corpus_version,
        "回放开始": metadata.started_at,
        "机器配置": metadata.hardware,
        "模型与版本": metadata.models,
        "回放配置": metadata.config,
        "预热次数": metadata.warmup,
        "并发度": metadata.concurrency,
    }
    return [
        "# 住宅贷款 Copilot 评测报告",
        "",
        "## 运行条件",
        "",
        "| 项目 | 记录 |",
        "|---|---|",
        *(f"| {key} | {_metadata_value(value)} |" for key, value in fields.items()),
        "",
        f"- 区间取 {CONFIDENCE}% bootstrap。按用例重采样 {BOOTSTRAP_RESAMPLES:,} 次，"
        "随机种子为 0。",
        "- 表中 n 为有测量证据的样本数。工具调用失败率以调用数为分母，含被鉴权拒绝的调用。",
        "- 整段和首字延迟按实测请求计数。节点可并行，步骤耗时单列。",
        "",
    ]


def _calibration_section(calibration: Calibration | None) -> list[str]:
    lines = ["## 评审校准", "", "离线可采纳率衡量评审模型判定回答可直接发送的比例。", ""]
    if calibration is None or calibration.matched > calibration.total:
        return [*lines, "作者抽检一致率为未测。", ""]
    matched = calibration.matched
    metric = _mean_metric([1.0] * matched + [0.0] * (calibration.total - matched))
    status = "采信" if calibration.is_reliable else "不采信"
    return [
        *lines,
        f"作者抽检一致率 {_number(metric, 'rate')}（{matched}/{calibration.total}），"
        f"95% 区间 {_interval(metric, 'rate')}。本次评审{status}。",
        f"采信要求为至少 {MIN_CALIBRATION_SAMPLES} 条校准标签且一致率至少 "
        f"{MIN_CALIBRATION_AGREEMENT:.0%}。",
        "",
    ]


def _tool_denials(rows: Sequence[EvalRow]) -> str:
    denials = [row.tools_denied for row in rows if row.tools_denied is not None]
    return f"{sum(denials)}（覆盖 {len(denials)} 条用例）" if denials else "未测"


def _confusion_section(rows: Sequence[EvalRow]) -> list[str]:
    pairs = Counter(
        (row.expected_intent, row.intent) for row in rows if _intent_hit(row) is not None
    )
    if not pairs:
        return ["意图混淆矩阵为未测。", ""]
    observed = sorted({label for pair in pairs for label in pair if label is not None})
    labels = tuple(dict.fromkeys((*INTENT_LABELS, *observed)))
    lines = [
        "| 金标 ↓ / 预测 → | " + " | ".join(map(_escaped, labels)) + " |",
        "|---|" + "---:|" * len(labels),
    ]
    for expected in labels:
        counts = " | ".join(str(pairs[expected, actual]) for actual in labels)
        lines.append(f"| {_escaped(expected)} | {counts} |")
    return [*lines, ""]


def _latency_section(metrics: Mapping[str, Metric]) -> list[str]:
    first, full = metrics["first_token"].n, metrics["latency"].n
    if min(first, full) >= MIN_LATENCY_SAMPLES:
        return []
    return [
        f"首字 {first} 条、整段 {full} 条，延迟统计未达到 {MIN_LATENCY_SAMPLES} 条的样本要求。",
        "",
    ]


def _targets(tier: Tier, fault_mode: FaultMode) -> dict[str, tuple[float, bool]]:
    targets = {
        "intent": (INTENT_TARGET, False),
        "expired": (0.0, True),
        "first_token": (FIRST_TOKEN_TARGET_MS, True),
        "grounding": (1.0, False),
        "unauthorized": (1.0, False),
        "regression": (REGRESSION_TARGET, False),
    }
    if tier == "S":
        targets["top5"] = TOP5_TARGET, False
    if fault_mode == "none":
        targets["tool_failure"] = TOOL_FAILURE_TARGET, True
    else:
        targets["degradation"] = 1.0, False
    return targets


def _latency_cause(row: EvalRow) -> str:
    stages = {
        "意图": row.intent_ms,
        "追问改写": row.rewrite_ms,
        "检索": row.retrieval_ms,
        "工具": row.tool_ms,
        "生成": row.generation_ms,
    }
    measured = [(duration, label) for label, duration in stages.items() if duration is not None]
    return f"{max(measured)[1]}节点耗时最高" if measured else ERROR_LABELS["other"]


def _recorded_cause(row: EvalRow) -> str:
    if row.error_category:
        return ERROR_LABELS.get(row.error_category, row.error_category)
    if (
        row.expected_intent is not None
        and row.intent is not None
        and row.intent != row.expected_intent
    ):
        return ERROR_LABELS["intent"]
    if _top5_hit(row) is False:
        return ERROR_LABELS["retrieval"]
    if row.tools_failed or row.unauthorized_blocked is False:
        return ERROR_LABELS["tool"]
    if row.grounded_numbers is False:
        return ERROR_LABELS["generation"]
    return ERROR_LABELS["other"]


def _cause(key: str, row: EvalRow) -> str:
    if key == "top5" and row.error_category == "intent":
        return ERROR_LABELS["intent"]
    if key in METRIC_ERRORS:
        return ERROR_LABELS[METRIC_ERRORS[key]]
    if key == "expired":
        top = ranked_documents(row.retrieved_docs or ())[:TOP_K]
        if set(top).intersection(row.expired_docs or ()):
            return ERROR_LABELS["retrieval"]
        return "输出引用使用失效版本"
    if key == "first_token":
        return _latency_cause(row)
    return _recorded_cause(row)


def _target_text(key: str, threshold: float, upper_bound: bool) -> str:
    return f"{'≤' if upper_bound else '≥'} {_display(threshold, INDICATORS[key].display)}"


def _missed_observation(key: str, row: EvalRow, threshold: float, upper_bound: bool) -> bool:
    measured = INDICATORS[key].measure(row)
    if measured is None:
        return False
    if upper_bound:
        return measured > (threshold if key == "first_token" else 0)
    return measured == 0


def _attribution_section(
    rows: Sequence[EvalRow],
    metrics: Mapping[str, Metric],
    targets: Mapping[str, tuple[float, bool]],
) -> list[str]:
    lines = []
    for key, (threshold, upper_bound) in targets.items():
        value = metrics[key].value
        if value is None or (value <= threshold if upper_bound else value >= threshold):
            continue
        counts = Counter(
            _cause(key, row)
            for row in rows
            if _missed_observation(key, row, threshold, upper_bound)
        )
        details = "、".join(
            f"{_escaped(cause)} {count} 条" for cause, count in sorted(counts.items())
        )
        target = _target_text(key, threshold, upper_bound)
        lines.append(f"| {INDICATORS[key].label} | {target} | {details or '待归因'} |")
    if not lines:
        return []
    return ["| 未达目标的指标 | 目标 | 相关用例归因 |", "|---|---|---|", *lines, ""]


def _metric_lines(
    metrics: Mapping[str, Metric], targets: Mapping[str, tuple[float, bool]]
) -> list[str]:
    lines = ["| 指标 | 实测 | 分子 / 分母或样本 n | 95% 区间 | 目标 |", "|---|---:|---:|---|---|"]
    for key, metric in metrics.items():
        indicator = INDICATORS[key]
        count = (
            f"{metric.numerator} / {metric.n}" if metric.numerator is not None else str(metric.n)
        )
        target = _target_text(key, *targets[key]) if key in targets else "—"
        value, interval = _number(metric, indicator.display), _interval(metric, indicator.display)
        lines.append(f"| {indicator.label} | {value} | {count} | {interval} | {target} |")
    return [*lines, ""]


def _group_section(
    key: GroupKey, rows: Sequence[EvalRow], calibration: Calibration | None
) -> list[str]:
    system, tier, fault_mode = key
    metrics = build_metrics(rows, calibration=calibration)
    targets = _targets(tier, fault_mode)
    return [
        f"### {_escaped(system)} / {tier} 档 / {FAULT_LABELS[fault_mode]}",
        "",
        f"共 {len(rows)} 条回放结果，鉴权拒绝调用数为 {_tool_denials(rows)}。",
        "",
        *_metric_lines(metrics, targets),
        *_latency_section(metrics),
        *_confusion_section(rows),
        *_attribution_section(rows, metrics, targets),
    ]


def _top5_pair_line(
    system: str,
    fault_mode: FaultMode,
    s_rows: Sequence[EvalRow],
    l_rows: Sequence[EvalRow],
    source: str,
) -> str:
    s_score, l_score = [_measure(rows, INDICATORS["top5"]) for rows in (s_rows, l_rows)]
    delta = paired_top5(s_rows, l_rows)
    if delta.low is None or delta.high is None or delta.value is None:
        estimate, interval = "未测", "未测"
    else:
        estimate = f"{delta.value * 100:.2f}"
        interval = f"[{delta.low * 100:.2f}, {delta.high * 100:.2f}]"
        if delta.low <= 0 <= delta.high:
            interval += "，区间含 0"
    return (
        f"| {_escaped(system)} | {FAULT_LABELS[fault_mode]} | {_escaped(source)} | "
        f"{_number(s_score, 'rate')}（n={s_score.n}） | "
        f"{_number(l_score, 'rate')}（n={l_score.n}） | "
        f"{estimate} | {delta.n} | {interval} |"
    )


def _pair_section(groups: Mapping[GroupKey, Sequence[EvalRow]]) -> list[str]:
    lines = [
        "## S 与 L 档规程召回对照",
        "",
        "差值为同一系统、同一故障条件下的 L 档减 S 档，仅配对两档均有观测的同题。",
        "",
        "| 系统 | 故障条件 | 来源 | S 档 Top5 | L 档 Top5 | "
        "配对差值（百分点） | 配对 n | 95% 区间 |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]
    for system, fault_mode in sorted({(system, fault) for system, _, fault in groups}):
        s_rows = groups.get((system, "S", fault_mode), ())
        l_rows = groups.get((system, "L", fault_mode), ())
        lines.append(_top5_pair_line(system, fault_mode, s_rows, l_rows, "全部"))
        sources = {
            row.source for row in (*s_rows, *l_rows) if row.source and _top5_hit(row) is not None
        }
        for source in sorted(sources):
            source_s = [row for row in s_rows if row.source == source]
            source_l = [row for row in l_rows if row.source == source]
            lines.append(_top5_pair_line(system, fault_mode, source_s, source_l, source))
    return [*lines, ""]


def _is_dify(system: str) -> bool:
    return system.casefold() in ("dify", "dify v3")


def _cost_section(groups: Mapping[GroupKey, Sequence[EvalRow]]) -> list[str]:
    baselines = {
        (tier, fault): rows for (system, tier, fault), rows in groups.items() if _is_dify(system)
    }
    lines = [
        "## 相对 Dify 的单会话成本",
        "",
        "Dify 为 1.00 倍。系统间倍数取同档、同故障条件、均有网关成本的同题平均值之比。",
        "",
        "| 系统 | 档位 | 故障条件 | 倍数 | n | 95% 区间 |",
        "|---|---|---|---:|---:|---|",
    ]
    for (system, tier, fault), rows in sorted(groups.items()):
        pairs = _paired_values(baselines.get((tier, fault), ()), rows, INDICATORS["cost"].measure)
        metric = _ratio_metric(pairs)
        lines.append(
            f"| {_escaped(system)} | {tier} | {FAULT_LABELS[fault]} | "
            f"{_number(metric, 'multiple')} | {metric.n} | {_interval(metric, 'multiple')} |"
        )
    return [*lines, ""]


def render_report(
    rows: Sequence[EvalRow], metadata: RunMetadata, *, calibration: Calibration | None = None
) -> str:
    """输出可由 LangGraph 与 Dify 共用的中文评测报告。"""
    groups: dict[GroupKey, list[EvalRow]] = defaultdict(list)
    for row in rows:
        groups[row.system, row.tier, row.fault_mode].append(row)
    for system in {row.system for row in rows} or {"LangGraph"}:
        for tier in ("S", "L"):
            for fault in ("none", "5%-timeout"):
                groups.setdefault((system, tier, fault), [])
    lines = [*_run_section(metadata), *_calibration_section(calibration), "## 技术指标", ""]
    for key, subset in sorted(groups.items()):
        lines.extend(_group_section(key, subset, calibration))
    lines.extend(_pair_section(groups))
    lines.extend(_cost_section(groups))
    lines.extend(
        [
            "## 未测的业务指标",
            "",
            "| 指标 | 实测 |",
            "|---|---|",
            "| 坐席采纳率 | 未测 |",
            "| AHT | 未测 |",
            "| 单次查询人工耗时的前后对比 | 未测 |",
            "| 客户自助办结率 | 未测 |",
            "| 月度结算成本 | 未测 |",
            "",
            "## 与参考方案的偏差",
            "",
            "- 真实运行的大模型通过外部 API 调用，网关原型使用本地 LiteLLM。",
            "- Langfuse 默认使用云端服务。",
            "- 业务系统使用模拟数据，故障注入条件下的失败率只反映该实验设置。",
            "- 双跑使用同一批用例回放，当前试验无真人坐席和真实流量。",
            "- 当前方案支持切换和双跑。灰度切流与回滚演练未测。",
            "",
        ]
    )
    return "\n".join(lines)
