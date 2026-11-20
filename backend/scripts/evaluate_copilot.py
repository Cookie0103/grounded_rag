"""运行第二版日文评测并按轮次保存实测，可安全续跑。"""

import argparse
import asyncio
import hashlib
import json
import platform
import shlex
import sys
from collections.abc import Sequence
from datetime import UTC, date, datetime
from http import HTTPStatus
from http.client import HTTPConnection
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from app.core.config import CACHE_DIR, REPO_ROOT, get_settings
from app.core.policy import CorpusTier
from app.orchestration.models import Step
from app.providers.budget import BudgetLedger
from app.tools.middleware import ToolTrace
from eval.copilot_cases import CopilotCase, load_cases
from eval.copilot_judging import (
    PolicyCorpus,
    load_calibration,
    policy_acceptable,
    review_policy_raw,
)
from eval.copilot_observations import TurnObservation, expired_documents, score_observation
from eval.copilot_report import Calibration, EvalRow, RunMetadata, render_report
from eval.judge import CommandPromptRunner, Judge
from eval.scoring import ACCEPTABLE, PERFECT
from scripts.stream_client import StreamResult, ask_stream

DEFAULT_CASES = CACHE_DIR / "copilot-eval" / "synthetic-dev.jsonl"
TODAY = date(2026, 11, 18)
REVIEW_SAMPLE = 20


class Measurement(BaseModel):
    case_id: str
    tier: CorpusTier
    fault_mode: str
    observation: TurnObservation


class PolicyLabel(BaseModel):
    case_id: str
    tier: CorpusTier
    passed: bool
    sendable: bool


def _request(case: CopilotCase, tier: CorpusTier, session_id: str) -> dict[str, object]:
    values: dict[str, object] = {
        "question": case.question,
        "channel": case.channel,
        "filter": {"corpus_tier": tier, "as_of": (case.as_of or TODAY).isoformat()},
        "session_id": session_id,
    }
    if case.channel == "agent":
        values.update(agent_id=case.agent_id, customer_id=case.customer_id)
    return values


def _read_trace_question(port: int, trace_id: str) -> str | None:
    connection = HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        connection.request("GET", f"/traces/{trace_id}")
        with connection.getresponse() as response:
            if response.status != HTTPStatus.OK:
                return None
            raw = json.load(response)
            return str(raw["question"])
    finally:
        connection.close()


def _answer(result: StreamResult) -> dict[str, object]:
    if result.answer is None:
        raise RuntimeError("评测请求缺少终态答复")
    if any("模型不可用" in step["note"] for step in result.answer["steps"]):
        raise RuntimeError("网关模型不可用，停止本轮评测")
    return result.answer


def _observe(port: int, case: CopilotCase, tier: CorpusTier) -> TurnObservation:
    settings = get_settings()
    ledger = BudgetLedger(CACHE_DIR / "budget", settings.daily_budget_cny)
    body = _request(case, tier, uuid4().hex)
    replies: list[dict[str, object]] = []
    for question in case.history:
        ledger.check()
        replies.append(_answer(ask_stream(port, {**body, "question": question})))
    ledger.check()
    result = ask_stream(port, body, evaluation_fault=case.fault)
    final = result.answer
    replies.append(_answer(result))
    if final is None:
        raise RuntimeError("评测请求缺少终态答复")
    steps = [Step.model_validate(item) for item in final["steps"]]
    trace_question = (
        _read_trace_question(port, final["trace_id"])
        if case.expected_outcome == "redacted"
        else None
    )
    return TurnObservation(
        answer=final["answer"],
        intent=final["intent"],
        steps=steps,
        retrieved_docs=tuple(final["retrieved_docs"]),
        citation_docs=tuple(item["document_id"] for item in final["citations"]),
        contexts=tuple(
            step.details.context for step in steps if step.details and step.details.context
        ),
        dropped_or_expired_docs=expired_documents(steps, case.as_of or TODAY),
        tool_calls=[ToolTrace.model_validate(item) for item in final["tool_calls"]],
        latency_ms=result.total_ms,
        first_token_ms=result.first_delta_ms,
        cost_cny=sum(float(str(reply["cost_cny"])) for reply in replies),
        prompt_tokens=sum(int(str(reply["prompt_tokens"])) for reply in replies),
        completion_tokens=sum(int(str(reply["completion_tokens"])) for reply in replies),
        degraded=final["degraded"],
        abstained=final["abstained"],
        trace_question=trace_question,
    )


def _jobs(
    cases: Sequence[CopilotCase], fault_mode: str
) -> list[tuple[CopilotCase, CorpusTier, str]]:
    if fault_mode == "5%-timeout":
        return [
            (case, "S", fault_mode)
            for case in cases
            if case.category == "lookup"
            and case.fault is None
            and case.expected_outcome == "answer"
        ]
    main: list[tuple[CopilotCase, CorpusTier, str]] = [
        (case, "S", "explicit" if case.fault else "none") for case in cases
    ]
    return [*main, *((case, "L", "none") for case in cases if case.category == "policy")]


def _read_input(args: argparse.Namespace) -> list[CopilotCase]:
    if args.sealed_test is not None:
        if args.sealed_test.resolve().is_relative_to(
            REPO_ROOT
        ) or args.run_dir.resolve().is_relative_to(REPO_ROOT):
            raise SystemExit("封存用例与运行输出须在仓库外")
        cases = load_cases(args.sealed_test)
        if (
            args.policy_dev
            or args.prepare_calibration
            or any(case.split != "test" for case in cases)
        ):
            raise SystemExit("封存运行仅接收作者的 test 标签文件")
        return cases
    cases = load_cases(args.cases)
    if args.policy_dev is not None:
        policy = load_cases(args.policy_dev)
        if any(case.category != "policy" or case.split != "dev" for case in policy):
            raise SystemExit("规程开发题须是 dev 标签；封存题请由作者单独运行")
        cases.extend(policy)
    if any(case.split == "test" for case in cases):
        raise SystemExit("常规评测目录中包含封存标签，已停止")
    if len({case.id for case in cases}) != len(cases):
        raise SystemExit("评测用例 ID 有重复")
    return cases


def _manifest(args: argparse.Namespace, cases: Sequence[CopilotCase]) -> dict[str, str]:
    settings = get_settings()
    serialized = "\n".join(case.model_dump_json() for case in cases)
    signature = {
        "dataset_sha256": hashlib.sha256(serialized.encode()).hexdigest(),
        "fault_condition": args.fault_mode,
        "gateway_small_model": settings.gateway_small_model,
        "gateway_large_model": settings.gateway_large_model,
        "embedding_model": settings.embedding_model,
        "embedding_device": settings.embed_device,
        "scope": "sealed" if args.sealed_test is not None else "development",
    }
    manifest = args.run_dir / "manifest.json"
    if manifest.exists():
        if not args.resume:
            raise SystemExit("运行目录已有清单，续跑请指定 --resume")
        if json.loads(manifest.read_text(encoding="utf-8")) != signature:
            raise SystemExit("续跑输入或配置与已有清单不同")
    else:
        args.run_dir.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(signature, indent=2) + "\n", encoding="utf-8")
    return signature


def _measure(args: argparse.Namespace, cases: Sequence[CopilotCase]) -> list[Measurement]:
    path: Path = args.run_dir / "observations.jsonl"
    cached = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            saved = Measurement.model_validate_json(line)
            cached[(saved.case_id, saved.tier, saved.fault_mode)] = saved
    measurements: list[Measurement] = []
    jobs = _jobs(cases, args.fault_mode)
    with path.open("a", encoding="utf-8") as out:
        for index, (case, tier, fault_mode) in enumerate(jobs, 1):
            key = (case.id, tier, fault_mode)
            row = cached.get(key)
            if row is None:
                row = Measurement(
                    case_id=case.id,
                    tier=tier,
                    fault_mode=fault_mode,
                    observation=_observe(args.port, case, tier),
                )
                out.write(row.model_dump_json() + "\n")
                out.flush()
            measurements.append(row)
            if index % REVIEW_SAMPLE == 0:
                sys.stderr.write(f"已记录 {index}/{len(jobs)} 条\n")
    return measurements


async def _review(
    args: argparse.Namespace, cases: dict[str, CopilotCase], measurements: list[Measurement]
) -> tuple[list[EvalRow], Calibration | None]:
    calibration = load_calibration(args.calibration)
    verdicts = await _review_policy_rows(args, cases, measurements, calibration.accepted)
    rows = []
    for row in measurements:
        case = cases[row.case_id]
        judged = verdicts.get((case.id, row.tier)) if calibration.accepted else None
        rows.append(
            score_observation(
                case,
                row.observation,
                tier=row.tier,
                fault_mode=row.fault_mode,
                policy_pass=judged.passed if judged is not None else None,
                offline_acceptable=judged.sendable if judged is not None else None,
            )
        )
    return rows, Calibration(
        matched=calibration.agreements, total=calibration.count
    ) if calibration.count else None


async def _review_policy_rows(
    args: argparse.Namespace,
    cases: dict[str, CopilotCase],
    measurements: list[Measurement],
    accepted: bool,
) -> dict[tuple[str, CorpusTier], PolicyLabel]:
    if not args.judge_command or not (args.prepare_calibration or accepted):
        return {}
    judge = Judge(CommandPromptRunner(shlex.split(args.judge_command)))
    corpus = PolicyCorpus.from_question_pack(args.question_pack)
    eligible = [row for row in measurements if _has_policy_review(cases[row.case_id])]
    if args.prepare_calibration:
        eligible = sorted(
            (
                row
                for row in eligible
                if row.tier == "S" and cases[row.case_id].category == "policy"
            ),
            key=lambda row: hashlib.sha256(row.case_id.encode()).digest(),
        )[:REVIEW_SAMPLE]
        if len(eligible) < REVIEW_SAMPLE:
            raise SystemExit("至少需要 20 条有答复的规程开发题才能准备校准")
    judge_digest = hashlib.sha256(args.judge_command.encode() + args.question_pack.read_bytes())
    path = args.run_dir / f"policy-verdicts-{judge_digest.hexdigest()[:12]}.jsonl"
    labels = await _collect_policy_labels(path, eligible, cases, judge=judge, corpus=corpus)
    if args.prepare_calibration:
        _write_calibration(args.run_dir, eligible, cases, labels)
    return labels


def _has_policy_review(case: CopilotCase) -> bool:
    return case.category == "policy" or (case.category == "lane" and bool(case.gold_docs))


async def _collect_policy_labels(
    path: Path,
    rows: list[Measurement],
    cases: dict[str, CopilotCase],
    *,
    judge: Judge,
    corpus: PolicyCorpus,
) -> dict[tuple[str, CorpusTier], PolicyLabel]:
    labels: dict[tuple[str, CorpusTier], PolicyLabel] = {}
    if await asyncio.to_thread(path.is_file):
        source = await asyncio.to_thread(path.read_text, encoding="utf-8")
        for line in source.splitlines():
            previous = PolicyLabel.model_validate_json(line)
            labels[(previous.case_id, previous.tier)] = previous
    with path.open("a", encoding="utf-8") as out:
        for row in rows:
            key = (row.case_id, row.tier)
            if key in labels:
                continue
            observation = row.observation
            scored = await review_policy_raw(
                cases[row.case_id],
                observation.answer,
                observation.contexts,
                judge=judge,
                corpus=corpus,
            )
            label = PolicyLabel(
                case_id=row.case_id,
                tier=row.tier,
                passed=scored.score.label in {PERFECT, ACCEPTABLE},
                sendable=policy_acceptable(scored),
            )
            labels[key] = label
            out.write(label.model_dump_json() + "\n")
            out.flush()
    return labels


def _write_calibration(
    directory: Path,
    rows: list[Measurement],
    cases: dict[str, CopilotCase],
    labels: dict[tuple[str, CorpusTier], PolicyLabel],
) -> None:
    blind_path = directory / "author-calibration-blind.jsonl"
    labels_path = directory / "author-calibration.jsonl"
    with (
        blind_path.open("w", encoding="utf-8") as blind,
        labels_path.open("w", encoding="utf-8") as output,
    ):
        for row in rows:
            case = cases[row.case_id]
            portion = case.model_dump(mode="json", include={"id", "question", "as_of", "gold_docs"})
            blind.write(
                json.dumps({**portion, "answer": row.observation.answer}, ensure_ascii=False) + "\n"
            )
            output.write(
                json.dumps(
                    {"id": case.id, "judge_acceptable": labels[(case.id, row.tier)].sendable}
                )
                + "\n"
            )


def _fault_rows(directory: Path, signature: dict[str, str]) -> list[EvalRow]:
    recorded = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if recorded != {**signature, "fault_condition": "5%-timeout"}:
        raise SystemExit("随机故障回放与基线的题集或模型设置不同")
    rows = [
        EvalRow.model_validate_json(line)
        for line in (directory / "rows.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    if any(row.fault_mode != "5%-timeout" for row in rows):
        raise SystemExit("故障回放目录包含不匹配的条件")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--policy-dev", type=Path)
    parser.add_argument("--sealed-test", type=Path)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=18081)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--fault-mode", choices=("none", "5%-timeout"), default="none")
    parser.add_argument("--merge-fault-run", type=Path)
    parser.add_argument(
        "--question-pack", type=Path, default=CACHE_DIR / "policy-question-pack.zip"
    )
    parser.add_argument("--judge-command")
    parser.add_argument("--prepare-calibration", action="store_true")
    parser.add_argument("--calibration", type=Path)
    parser.add_argument("--hardware", default=f"{platform.machine()} / {platform.platform()}")
    parser.add_argument("--warmup", type=int, default=0)
    parser.add_argument("--commit")
    args = parser.parse_args()
    started_at = datetime.now(UTC).isoformat()
    cases = _read_input(args)
    signature = _manifest(args, cases)
    measurements = _measure(args, cases)
    rows, calibration = asyncio.run(_review(args, {case.id: case for case in cases}, measurements))
    if args.merge_fault_run is not None:
        if args.fault_mode != "none":
            raise SystemExit("随机故障回放只能合并到基线报告")
        rows.extend(_fault_rows(args.merge_fault_run, signature))
    metadata = RunMetadata(
        dataset=signature["scope"],
        dataset_version=signature["dataset_sha256"],
        config={"fault_mode": args.fault_mode, "embedding": signature["embedding_device"]},
        hardware=args.hardware,
        concurrency=1,
        warmup=args.warmup,
        commit=args.commit,
        models={
            "small": signature["gateway_small_model"],
            "large": signature["gateway_large_model"],
            "embedding": signature["embedding_model"],
        },
        started_at=started_at,
        corpus_version=hashlib.sha256(args.question_pack.read_bytes()).hexdigest()
        if args.question_pack.is_file()
        else None,
    )
    (args.run_dir / "rows.jsonl").write_text(
        "".join(row.model_dump_json() + "\n" for row in rows), encoding="utf-8"
    )
    (args.run_dir / "report.md").write_text(
        render_report(rows, metadata, calibration=calibration), encoding="utf-8"
    )
    sys.stdout.write(f"已记录 {len(rows)} 条，报告 {args.run_dir / 'report.md'}\n")


if __name__ == "__main__":
    main()
