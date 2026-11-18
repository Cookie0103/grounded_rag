"""串行回放 Dify V3 开发集，生成阶段 36 兼容的记录和逐题对照。"""

import argparse
import asyncio
import hashlib
import json
import platform
import re
import sys
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast
from urllib.parse import urlsplit

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel

from app.core.config import CACHE_DIR, REPO_ROOT, get_settings
from app.core.errors import DependencyUnavailableError
from app.providers.budget import BudgetLedger
from app.providers.dify import dify_connection
from eval.copilot_cases import CopilotCase, load_cases
from eval.copilot_report import (
    FAULT_LABELS,
    INDICATORS,
    LATENCY_PERCENTILE,
    Calibration,
    Display,
    EvalRow,
    FaultMode,
    Metric,
    RunMetadata,
    build_metrics,
    render_report,
)
from eval.dify_replay import (
    SYSTEM,
    DifyMeasurement,
    DifyReplay,
    DocumentCatalog,
    GatewayJournal,
    LayerDifference,
    compare_observations,
)
from eval.scoring import BOOTSTRAP_RESAMPLES, CONFIDENCE
from scripts.evaluate_copilot import DEFAULT_CASES, Measurement, _jobs, _review

DEFAULT_JOURNAL = CACHE_DIR / "litellm-usage" / "phase-37-gateway-usage.jsonl"
PROGRESS_INTERVAL = 20
_CASES_DENIED = (REPO_ROOT / "backend" / "eval" / "data", REPO_ROOT / "harness" / "archive")
_TEST_NAME = re.compile(r"(?:^|[_.-])(?:test|sealed)(?:$|[_.-])", re.IGNORECASE)
_LAYERS = {"intent": "意图", "retrieval": "检索文档", "tools": "工具调用", "answer": "最终回答"}
type _Key = tuple[str, FaultMode]


class CompareConditions(BaseModel):
    embedding: Literal["same", "different", "unknown"] = "unknown"
    same_machine: bool = False
    same_gateway: bool = False
    same_fault_profile: bool = False
    dify_warmup: int = 0
    langgraph_warmup: int | None = None


class _Difference(BaseModel):
    case_id: str
    fault_mode: FaultMode
    synthetic: bool | None
    layers: dict[str, LayerDifference]


def _check_development_path(path: Path) -> None:
    resolved = path.resolve()
    if any(resolved.is_relative_to(root) for root in _CASES_DENIED) or _TEST_NAME.search(
        resolved.name
    ):
        raise ValueError("阶段 37 只接收开发集，封存和归档文件禁止读取")


def read_development_cases(synthetic: Path, policy: Path | None) -> list[CopilotCase]:
    """只读合成开发集与作者规程开发集，保持原评测顺序。"""
    _check_development_path(synthetic)
    if policy is not None:
        _check_development_path(policy)
    cases = load_cases(synthetic)
    if any(not case.synthetic or case.split != "dev" for case in cases):
        raise ValueError("主回放文件须是 synthetic dev")
    if policy is not None:
        policies = load_cases(policy)
        if any(case.category != "policy" or case.split != "dev" for case in policies):
            raise ValueError("规程回放文件须是 policy dev")
        cases.extend(policies)
    if len({case.id for case in cases}) != len(cases):
        raise ValueError("评测用例 ID 有重复")
    return cases


def _jsonl[T: BaseModel](path: Path, model: type[T]) -> list[T]:
    with path.open(encoding="utf-8") as content:
        return [model.model_validate_json(line) for line in content if line.strip()]


def _write_jsonl(path: Path, rows: Sequence[BaseModel]) -> None:
    staging = path.with_suffix(".tmp")
    staging.write_text("".join(f"{row.model_dump_json()}\n" for row in rows), encoding="utf-8")
    staging.replace(path)


def _dataset_hash(cases: Sequence[CopilotCase]) -> str:
    return hashlib.sha256("\n".join(case.model_dump_json() for case in cases).encode()).hexdigest()


def _file_hash(path: Path | None) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path is not None else "未登记"


def _manifest(args: argparse.Namespace, cases: Sequence[CopilotCase]) -> dict[str, str]:
    settings = get_settings()
    signature = {
        "dataset_sha256": _dataset_hash(cases),
        "fault_condition": args.fault_mode,
        "gateway_small_model": settings.gateway_small_model,
        "gateway_large_model": settings.gateway_large_model,
        "dify_base_url": args.dify_url,
        "dify_embedding": args.embedding_model,
        "workflow_sha256": _file_hash(args.chatflow),
        "corpus_sha256": _file_hash(args.question_pack),
    }
    path = args.run_dir / "manifest.json"
    if path.exists():
        if not (args.resume or args.report_only):
            raise SystemExit("运行目录已有回放清单，请使用 --resume 或 --report-only")
        if json.loads(path.read_text(encoding="utf-8")) != signature:
            raise SystemExit("续跑题集、画布或运行配置与清单不同")
    elif args.report_only:
        raise SystemExit("运行目录缺少回放清单")
    else:
        args.run_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(signature, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return signature


def _cached(path: Path) -> dict[_Key, DifyMeasurement]:
    records = _jsonl(path, DifyMeasurement) if path.is_file() else []
    cached = {(item.case_id, item.fault_mode): item for item in records}
    if len(cached) != len(records):
        raise ValueError(f"{path} 有重复观察记录")
    return cached


def _pending(
    args: argparse.Namespace, cases: Sequence[CopilotCase], cached: set[_Key]
) -> list[tuple[CopilotCase, FaultMode]]:
    jobs = []
    for case, tier, fault in _jobs(cases, args.fault_mode):
        if tier == "S" and (case.id, fault) not in cached:
            jobs.append((case, cast(FaultMode, fault)))
    return jobs


async def _warmup(replay: DifyReplay, count: int) -> None:
    examples = ("こんにちは。", "住宅ローンを申し込む方法を教えてください。")
    for index in range(count):
        case = CopilotCase(
            id=f"warmup-{index}",
            category="intent",
            question=examples[index % len(examples)],
            synthetic=True,
        )
        result = await replay.observe(case, "none")
        if result.missing_usage:
            raise DependencyUnavailableError("Dify 预热缺少网关用量证据，回放已停止")


async def _measure(args: argparse.Namespace, cases: Sequence[CopilotCase]) -> list[DifyMeasurement]:
    settings = get_settings()
    path = args.run_dir / "observations.jsonl"
    cached = _cached(path)
    jobs = _pending(args, cases, set(cached))
    if args.report_only or not jobs or any(row.missing_usage for row in cached.values()):
        return list(cached.values())
    if settings.dify_api_key is None or not settings.dify_api_key.get_secret_value():
        raise SystemExit("请配置 DIFY_API_KEY")
    async with dify_connection(args.dify_url, settings.dify_api_key.get_secret_value()) as client:
        replay = DifyReplay(
            client,
            GatewayJournal(args.gateway_usage),
            BudgetLedger(CACHE_DIR / "budget", settings.daily_budget_cny),
            DocumentCatalog.from_question_pack(args.question_pack),
            small_model=settings.gateway_small_model,
            large_model=settings.gateway_large_model,
        )
        await _warmup(replay, args.warmup)
        with path.open("a", encoding="utf-8") as output:
            for index, (case, fault) in enumerate(jobs, len(cached) + 1):
                item = await replay.observe(case, fault)
                output.write(item.model_dump_json() + "\n")
                output.flush()
                cached[(case.id, fault)] = item
                if index % PROGRESS_INTERVAL == 0:
                    sys.stderr.write(f"Dify 已记录 {index} 条\n")
                if item.missing_usage:
                    break
    return list(cached.values())


def _baseline(
    runs: Sequence[Path], signature: dict[str, str]
) -> tuple[list[EvalRow], dict[_Key, Measurement]]:
    rows: dict[tuple[str, str, str], EvalRow] = {}
    observations: dict[_Key, Measurement] = {}
    for directory in runs:
        _check_development_path(directory)
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("scope") != "development":
            raise ValueError("LangGraph 对照只接收开发运行")
        for field in ("dataset_sha256", "gateway_small_model", "gateway_large_model"):
            if manifest.get(field) != signature[field]:
                raise ValueError(f"LangGraph 运行清单的 {field} 与 Dify 不同")
        for row in _jsonl(directory / "rows.jsonl", EvalRow):
            if row.system != "LangGraph":
                raise ValueError("LangGraph 目录含其他系统的评测行")
            rows[(row.case_id, row.tier, row.fault_mode)] = row
        for entry in _jsonl(directory / "observations.jsonl", DifyMeasurement):
            if entry.tier == "S":
                observations[(entry.case_id, entry.fault_mode)] = Measurement(
                    case_id=entry.case_id,
                    tier=entry.tier,
                    fault_mode=entry.fault_mode,
                    observation=entry.observation,
                )
    return list(rows.values()), observations


def _merge_fault(args: argparse.Namespace, signature: dict[str, str]) -> list[DifyMeasurement]:
    if args.merge_fault_run is None:
        return []
    if args.fault_mode != "none":
        raise ValueError("只可将 Dify 随机条件合并到 Dify 基线")
    directory: Path = args.merge_fault_run
    _check_development_path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest != {**signature, "fault_condition": "5%-timeout"}:
        raise ValueError("Dify 随机条件与基线题集、画布或配置不一致")
    entries = list(_cached(directory / "observations.jsonl").values())
    if any(entry.fault_mode != "5%-timeout" for entry in entries):
        raise ValueError("Dify 随机条件目录含其他条件的观察")
    return entries


def _differences(
    dify: Sequence[DifyMeasurement], langgraph: dict[_Key, Measurement]
) -> list[_Difference]:
    return [
        _Difference(
            case_id=item.case_id,
            fault_mode=item.fault_mode,
            synthetic=item.synthetic,
            layers=compare_observations(
                baseline.observation, item.observation, classifier_class=item.classifier_class
            ),
        )
        for item in dify
        if (baseline := langgraph.get((item.case_id, item.fault_mode))) is not None
    ]


def _difference_section(differences: Sequence[_Difference]) -> str:
    lines = ["## 逐题四层差异", ""]
    if not differences:
        return "\n".join([*lines, "同一用例、S 档和故障条件的观察尚未配对。", ""])
    lines.extend(["| 层 | 一致 | 差异 | 未测 |", "|---|---:|---:|---:|"])
    for layer, label in _LAYERS.items():
        counts = Counter(item.layers[layer].state for item in differences)
        lines.append(
            f"| {label} | {counts['same']} | {counts['different']} | {counts['unmeasured']} |"
        )
    lines.extend(
        [
            "",
            "逐题内容见同目录的 differences.jsonl。工具层使用名称、脱敏参数及结果摘要，"
            "检索层保留文档顺序，最终回答按文字比较。",
            "",
            "| 用例 | 条件 | 有差异的层 | 缺少观察的层 |",
            "|---|---|---|---|",
        ]
    )
    for item in differences:
        changed = "、".join(
            _LAYERS[key] for key, value in item.layers.items() if value.state == "different"
        )
        missing = "、".join(
            _LAYERS[key] for key, value in item.layers.items() if value.state == "unmeasured"
        )
        if changed or missing:
            identifier = item.case_id.replace("|", "\\|")
            lines.append(
                f"| {identifier} | {FAULT_LABELS[item.fault_mode]} | "
                f"{changed or '—'} | {missing or '—'} |"
            )
    return "\n".join([*lines, ""])


def _metric(metric: Metric, display: Display) -> str:
    value = metric.value
    if value is None:
        return "未测"
    visible = {
        "rate": f"{value:.2%}",
        "ms": f"{value:,.2f} 毫秒",
        "cny": f"¥{value:.6f}",
        "tokens": f"{value:,.2f}",
        "multiple": f"{value:.2f} 倍",
    }[display]
    return f"{visible}（n={metric.n}）"


def _comparability(conditions: CompareConditions) -> dict[str, str]:
    model = "是，同题、同网关模型" if conditions.same_gateway else "待核对网关模型"
    delay = (
        "是，同机、同网关、串行，双方均预热"
        if conditions.same_machine
        and conditions.same_gateway
        and conditions.dify_warmup
        and conditions.langgraph_warmup
        else "待核对同机、同网关及双方预热"
    )
    embedding = {
        "same": "有限，嵌入权重相同；切分、过滤或混合召回设置可能不同",
        "different": "否，嵌入模型不同",
        "unknown": "待核对嵌入模型",
    }[conditions.embedding]
    return {
        "intent": model,
        "top5": embedding,
        "first_token": delay,
        "latency": delay,
        "cost": model,
        "tool_failure": "有限，固定种子同配置；实际调用顺序可不同"
        if conditions.same_fault_profile
        else "待核对故障条件",
        "regression": "按同题同评分口径；仅覆盖双方有分数的用例",
        "offline": "待作者校准或已按校准口径统计",
    }


def _bootstrap_values(
    key: str, rows: Sequence[EvalRow], samples: NDArray[np.int64]
) -> NDArray[np.float64]:
    if key == "tool_failure":
        failed = np.asarray([row.tools_failed or 0 for row in rows], dtype=float)[samples].sum(1)
        total = np.asarray(
            [
                (row.tools_ok or 0) + (row.tools_failed or 0) + (row.tools_denied or 0)
                for row in rows
            ],
            dtype=float,
        )[samples].sum(1)
        rates: NDArray[np.float64] = np.divide(
            failed, total, out=np.full_like(failed, np.nan), where=total > 0
        )
        return rates
    indicator = INDICATORS[key]
    values = np.asarray([indicator.measure(row) for row in rows], dtype=float)[samples]
    if indicator.display == "ms":
        percentiles: NDArray[np.float64] = np.percentile(values, LATENCY_PERCENTILE, axis=1)
        return percentiles
    return values.mean(axis=1)


def _paired_interval(key: str, dify: Sequence[EvalRow], langgraph: Sequence[EvalRow]) -> str:
    if not dify:
        return "未测"
    samples = np.random.default_rng(0).integers(0, len(dify), (BOOTSTRAP_RESAMPLES, len(dify)))
    values = _bootstrap_values(key, dify, samples) - _bootstrap_values(key, langgraph, samples)
    finite = values[np.isfinite(values)]
    if not finite.size:
        return "未测"
    tail = (100 - CONFIDENCE) / 2
    lower, upper = np.percentile(finite, [tail, 100 - tail])
    display = INDICATORS[key].display
    if display == "rate":
        return f"[{lower * 100:+.2f}, {upper * 100:+.2f}] 个百分点"
    if display == "ms":
        return f"[{lower:+,.2f} 毫秒, {upper:+,.2f} 毫秒]"
    return f"[{lower:+.6f}, {upper:+.6f}] 元"


def _paired_metric_rows(
    rows: Sequence[EvalRow],
    fault: FaultMode,
    conditions: CompareConditions,
    calibration: Calibration | None,
) -> list[str]:
    dify = {
        row.case_id: row
        for row in rows
        if row.system == SYSTEM and row.tier == "S" and row.fault_mode == fault
    }
    langgraph = {
        row.case_id: row
        for row in rows
        if row.system == "LangGraph" and row.tier == "S" and row.fault_mode == fault
    }
    ids = sorted(dify.keys() & langgraph.keys())
    compare = _comparability(conditions)
    lines = [
        f"### S 档 / {FAULT_LABELS[fault]}",
        "",
        f"相同用例 ID 共 {len(ids)} 条。",
        "",
        "| 指标 | Dify V3 | LangGraph | 配对差值 95% 区间 | 是否干净对照 |",
        "|---|---:|---:|---|---|",
    ]
    for key, label in compare.items():
        indicator = INDICATORS[key]
        measured = [
            case_id
            for case_id in ids
            if indicator.measure(dify[case_id]) is not None
            and indicator.measure(langgraph[case_id]) is not None
        ]
        d_rows, l_rows = ([group[case_id] for case_id in measured] for group in (dify, langgraph))
        a = build_metrics(d_rows, calibration=calibration)[key]
        b = build_metrics(l_rows, calibration=calibration)[key]
        left, right = _metric(a, indicator.display), _metric(b, indicator.display)
        if key == "cost" and a.value and b.value is not None:
            left += " / 1.00 倍"
            right += f" / {b.value / a.value:.2f} 倍"
        both_measured = a.value is not None and b.value is not None
        interval = _paired_interval(key, d_rows, l_rows) if both_measured else "未测"
        lines.append(
            f"| {indicator.label} | {left} | {right} | {interval} | "
            f"{label if both_measured else '未测'} |"
        )
    return [*lines, "| 坐席采纳率 | 未测 | 未测 | 未测 | 本地无真人坐席 |", ""]


def comparison_table(
    rows: Sequence[EvalRow],
    conditions: CompareConditions,
    calibration: Calibration | None = None,
) -> str:
    lines = [
        "## Dify V3 和 LangGraph 同题对照",
        "",
        "差值为 Dify V3 减 LangGraph。同一用例的两侧一起重采样。",
        "",
    ]
    for fault in FAULT_LABELS:
        lines.extend(_paired_metric_rows(rows, fault, conditions, calibration))
    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--policy-dev", type=Path)
    parser.add_argument(
        "--question-pack", type=Path, default=CACHE_DIR / "policy-question-pack.zip"
    )
    parser.add_argument("--chatflow", type=Path)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--langgraph-run", type=Path, action="append", default=[])
    parser.add_argument("--merge-fault-run", type=Path)
    parser.add_argument("--fault-mode", choices=("none", "5%-timeout"), default="none")
    parser.add_argument("--dify-url", default=get_settings().dify_base_url)
    parser.add_argument("--gateway-usage", type=Path, default=DEFAULT_JOURNAL)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--warmup", type=int, default=0)
    parser.add_argument("--langgraph-warmup", type=int)
    parser.add_argument("--hardware", default=f"{platform.machine()} / {platform.platform()}")
    parser.add_argument("--same-machine", action="store_true")
    parser.add_argument("--same-gateway", action="store_true")
    parser.add_argument("--same-fault-profile", action="store_true")
    parser.add_argument("--embedding", choices=("same", "different", "unknown"), default="unknown")
    parser.add_argument("--embedding-model", default="未登记")
    parser.add_argument("--judge-command")
    parser.add_argument("--calibration", type=Path)
    parser.set_defaults(prepare_calibration=False)
    return parser.parse_args()


def _validate_args(args: argparse.Namespace) -> None:
    if args.run_dir.resolve().is_relative_to(
        REPO_ROOT
    ) and not args.run_dir.resolve().is_relative_to(CACHE_DIR):
        raise SystemExit("观察和逐题答复只可存入本机 .cache 或仓库外目录")
    url = urlsplit(args.dify_url)
    if (
        url.username
        or url.password
        or url.query
        or url.fragment
        or url.scheme not in {"http", "https"}
    ):
        raise SystemExit("Dify URL 须为无凭据、无查询参数的 HTTP 地址")
    if args.warmup < 0 or (args.langgraph_warmup is not None and args.langgraph_warmup < 0):
        raise SystemExit("预热次数须为非负整数")


def _write_report(
    args: argparse.Namespace,
    signature: dict[str, str],
    rows: Sequence[EvalRow],
    calibration: Calibration | None,
    dify: Sequence[DifyMeasurement],
    differences: Sequence[_Difference],
) -> None:
    metadata = RunMetadata(
        dataset="development",
        dataset_version=signature["dataset_sha256"],
        corpus_version=signature["corpus_sha256"],
        config={
            "Dify": "1.19.0",
            "故障": args.fault_mode,
            "LangGraph 预热": str(args.langgraph_warmup),
            "用量": "串行独占网关回调按请求窗口归集",
        },
        models={
            "small": signature["gateway_small_model"],
            "large": signature["gateway_large_model"],
            "Dify embedding": signature["dify_embedding"],
        },
        hardware=args.hardware,
        concurrency=1,
        warmup=args.warmup,
        started_at=datetime.now(UTC).isoformat(),
    )
    conditions = CompareConditions(
        embedding=args.embedding,
        dify_warmup=args.warmup,
        langgraph_warmup=args.langgraph_warmup,
        same_machine=args.same_machine,
        same_gateway=args.same_gateway,
        same_fault_profile=args.same_fault_profile,
    )
    missing = sum(bool(item.missing_usage) for item in dify)
    notes = (
        "## Dify 观察说明\n\n"
        f"- 缺少完整网关用量或无法归属的会话 {missing} 条，成本与 token 写作未测。\n"
        "- 检索文档按 S 档文件名和元数据映射。缺少版本 ID、节点输出被截断或工具执行摘要缺失时，"
        "该层写作未测。\n"
        "- Dify 工具节点耗时取本次 HTTP 实测；数字溯源需有明确出口检查结果。\n\n"
    )
    report = "\n".join(
        [
            render_report(rows, metadata, calibration=calibration),
            comparison_table(rows, conditions, calibration),
            notes,
            _difference_section(differences),
        ]
    )
    (args.run_dir / "report.md").write_text(report, encoding="utf-8")


def main() -> None:
    args = _parse_args()
    _validate_args(args)
    cases = read_development_cases(args.cases, args.policy_dev)
    signature = _manifest(args, cases)
    baseline, observations = _baseline(args.langgraph_run, signature)
    own = asyncio.run(_measure(args, cases))
    dify = [*own, *_merge_fault(args, signature)]
    assessed, calibration = asyncio.run(
        _review(
            args,
            {case.id: case for case in cases},
            [
                Measurement(
                    case_id=item.case_id,
                    tier=item.tier,
                    fault_mode=item.fault_mode,
                    observation=item.observation,
                )
                for item in dify
            ],
        )
    )
    rows = [
        *baseline,
        *(
            row.model_copy(update={"system": SYSTEM, "intent": row.intent or item.classifier_class})
            for row, item in zip(assessed, dify, strict=True)
        ),
    ]
    differences = _differences(dify, observations)
    _write_jsonl(args.run_dir / "rows.jsonl", rows)
    _write_jsonl(args.run_dir / "differences.jsonl", differences)
    _write_report(args, signature, rows, calibration, dify, differences)
    sys.stdout.write(f"Dify 已记录 {len(dify)} 条；与 LangGraph 配对 {len(differences)} 条\n")
    if not args.report_only and any(item.missing_usage for item in own):
        raise SystemExit("缺少完整网关证据，已保留部分观察与报告；回放停止")


if __name__ == "__main__":
    main()
