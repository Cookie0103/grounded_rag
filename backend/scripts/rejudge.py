"""只读旧回答、使用新模板重评；每套先前三题，再复用标签缓存继续。"""

import argparse
import asyncio
import json
import logging
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from app.core.config import REPO_ROOT
from app.core.logging import configure_logging
from eval.dataset import Question, load_questions
from eval.evaluate import EvalResult, evaluate, load_verdicts, retrieval_stats
from eval.judge import PROMPTS_DIR, CommandPromptRunner, Judge, parse_verdict
from eval.report import render_report
from eval.runner import load_cache
from eval.scoring import JudgeVerdict, ScoredQuestion, score_question, summarize
from eval.systems import SystemAnswer
from scripts.rejudge_artifacts import (
    fingerprints,
    read_hashes,
    record_errors,
    verify_frozen,
    verify_portable_hashes,
    verify_unchanged,
    write_json,
)

PILOT_SIZE = 3
ERROR_RATE_DENOMINATOR = 10
logger = logging.getLogger(__name__)


def create_judge() -> Judge:
    """仅使用作者指定的Claude命令行，不创建被测模型或检索器。"""
    return Judge(CommandPromptRunner(["claude", "-p"]))


def check_output_location(is_test: bool, out_run: Path) -> None:
    """测试输出必须物理位于仓库外，包括目录链接的目标。"""
    if is_test and out_run.resolve().is_relative_to(REPO_ROOT.resolve()):
        raise ValueError("测试题重评产物必须放在仓库外")


def _validate_inputs(
    questions: Sequence[Question],
    answers: dict[str, SystemAnswer],
    old: dict[str, JudgeVerdict],
) -> None:
    if not questions:
        raise ValueError("题集为空")
    missing = [q.id for q in questions if q.id not in answers or q.id not in old]
    if missing:
        raise ValueError(f"旧回答或v1标签不完整：{', '.join(missing)}")


def render_flips(result: EvalResult, old: dict[str, JudgeVerdict]) -> str:
    """完整列出全部标签变化及两向contradiction变化，不添加评审判断。"""
    groups: dict[str, list[ScoredQuestion]] = {
        "contradiction true → false": [],
        "contradiction false → true": [],
        "其他标签变化": [],
    }
    for item in result.scored:
        previous = old[item.question.id]
        if previous == item.verdict:
            continue
        if previous.contradiction and not item.verdict.contradiction:
            name = "contradiction true → false"
        elif not previous.contradiction and item.verdict.contradiction:
            name = "contradiction false → true"
        else:
            name = "其他标签变化"
        groups[name].append(item)
    lines = ["# v1 → v2标签变化（完整清单）", "", "只转录标签及原评分函数的分数，不作判断。", ""]
    for name, items in groups.items():
        lines += [f"## {name}（{len(items)}题）", ""]
        lines += [
            "| 题号 | v1全部标签 | v2全部标签 | v1分数 | v2分数 | 分差 |",
            "|---|---|---|---|---|---|",
        ]
        for item in items:
            previous = old[item.question.id]
            before = score_question(item.question, previous).points
            first = json.dumps(asdict(previous), ensure_ascii=False)
            second = json.dumps(asdict(item.verdict), ensure_ascii=False)
            lines.append(
                f"| {item.question.id} | `{first}` | `{second}` | {before:+g} | "
                f"{item.score.points:+g} | {item.score.points - before:+g} |"
            )
        lines.append("")
    lines += [
        "## nuggets标签变化（含与contradiction同时变化的题）",
        "",
        "这里只转录变化，不能由此把全部分差归因于contexts或某一条规则。",
        "",
        "| 题号 | 要点序号 | v1 | v2 |",
        "|---|---|---|---|",
    ]
    for item in result.scored:
        for index, (before_label, after_label) in enumerate(
            zip(old[item.question.id].nuggets, item.verdict.nuggets, strict=True), 1
        ):
            if before_label != after_label:
                lines.append(f"| {item.question.id} | {index} | {before_label} | {after_label} |")
    return "\n".join(lines)


def _write_result(
    result: EvalResult, old: dict[str, JudgeVerdict], out_run: Path, planned: int
) -> None:
    errors = {**result.system_errors, **result.judge_errors}
    history = record_errors(out_run, errors)
    counts = {
        "planned": planned,
        "cached_answers": len(result.answers),
        "judged": len(result.scored),
        "error_questions": len(errors),
        "not_reviewed": planned - len(result.scored) - len(errors),
        "historical_error_questions": len(history),
    }
    notice = (
        "> v2为评审改动后的初步结果，校准通过前不是正式数字。\n\n"
        f"计划{planned}题；本次使用缓存回答{len(result.answers)}题；"
        f"评审完成{len(result.scored)}题；错误{len(errors)}题；"
        f"待评{counts['not_reviewed']}题。没有重跑系统或检索。\n\n"
        "运行延迟和生成成本来自v1缓存，不是本次重评的费用或耗时。\n\n"
        f"历史出错{len(history)}题，原始错误保留在errors-history.json；补评成功不会删除历史。\n\n"
        "v2同时调整contradiction依据和已批准的support解释，分差不能全部归因于contexts。\n\n"
    )
    (out_run / "report.md").write_text(notice + render_report(result), encoding="utf-8")
    (out_run / "flips.md").write_text(render_flips(result, old), encoding="utf-8")
    write_json(out_run / "errors.json", errors)
    retrieval = retrieval_stats(list(zip(result.questions, result.answers, strict=True)))
    write_json(
        out_run / "metrics.json",
        {
            **counts,
            "trust": asdict(summarize(result.scored)),
            "retrieval": asdict(retrieval),
            "human_calibrated": False,
        },
    )


def _prepare(
    src_run: Path,
    out_run: Path,
    questions_path: Path,
    *,
    template_name: str = "judge_v2.md",
    seed_run: Path | None = None,
) -> tuple[list[Question], dict[str, SystemAnswer], dict[str, JudgeVerdict], dict[str, str]]:
    if out_run.exists():
        raise FileExistsError(f"输出目录已存在，拒绝覆盖：{out_run}")
    questions = load_questions(questions_path)
    check_output_location(any(q.split == "test" for q in questions), out_run)
    if out_run.resolve().is_relative_to(src_run.resolve()):
        raise ValueError("新输出目录不能位于旧运行目录内")
    answers = load_cache(src_run / "answers.jsonl")
    old = load_verdicts(src_run / "verdicts.jsonl")
    _validate_inputs(questions, answers, old)
    protected = [src_run / name for name in ("answers.jsonl", "verdicts.jsonl", "report.md")]
    protected += [questions_path, PROMPTS_DIR / template_name]
    hashes = fingerprints(protected)
    seed_hashes: dict[str, str] = {}
    if seed_run is not None:
        _validate_seed(seed_run, hashes, questions, template_name)
        seed_hashes = fingerprints(
            [seed_run / name for name in ("manifest.json", "verdicts.jsonl", "errors.json")]
        )
        if (seed_run / "errors-history.json").exists():
            seed_hashes.update(fingerprints([seed_run / "errors-history.json"]))
    out_run.mkdir(parents=True, exist_ok=False)
    write_json(
        out_run / "manifest.json",
        {
            "source_run": str(src_run.resolve()),
            "questions": str(questions_path.resolve()),
            "template": template_name,
            "sha256": hashes,
            "judge": "claude -p",
            "human_calibrated": False,
            "system_rerun": False,
            "retrieval_rerun": False,
            "seed_run": str(seed_run.resolve()) if seed_run else None,
            "seed_sha256": seed_hashes,
        },
    )
    if seed_run is not None:
        (out_run / "verdicts.jsonl").write_bytes((seed_run / "verdicts.jsonl").read_bytes())
        history_path = seed_run / "errors-history.json"
        if history_path.exists():
            (out_run / history_path.name).write_bytes(history_path.read_bytes())
        record_errors(out_run, json.loads((seed_run / "errors.json").read_text(encoding="utf-8")))
    return questions, answers, old, {**hashes, **seed_hashes}


def _validate_seed(
    seed_run: Path, hashes: dict[str, str], questions: Sequence[Question], template_name: str
) -> None:
    manifest = json.loads((seed_run / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("template") != template_name or manifest.get("judge") != "claude -p":
        raise ValueError("断点的评审模板或评审器不一致")
    verify_portable_hashes(read_hashes(manifest.get("sha256")), hashes)
    by_id = {q.id: q for q in questions}
    seen: set[str] = set()
    for line in (seed_run / "verdicts.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        question_id = row["question_id"]
        if question_id not in by_id or question_id in seen:
            raise ValueError("断点标签含未知或重复题号")
        parse_verdict(line, len(by_id[question_id].nuggets))
        seen.add(question_id)


def _save_pilot(out_run: Path) -> None:
    (out_run / "pilot-report.md").write_text(
        (out_run / "report.md").read_text(encoding="utf-8"), encoding="utf-8"
    )


async def run_rejudge(
    src_run: Path,
    out_run: Path,
    questions_path: Path,
    *,
    template_name: str = "judge_v2.md",
    seed_run: Path | None = None,
    frozen_path: Path | None = None,
) -> EvalResult:
    """创建新目录，前三题通过后只重评尚未缓存的新模板标签。"""
    if frozen_path is not None:
        await asyncio.to_thread(verify_frozen, frozen_path)
    questions, answers, old, hashes = await asyncio.to_thread(
        _prepare, src_run, out_run, questions_path, template_name=template_name, seed_run=seed_run
    )
    if frozen_path is not None:
        hashes.update(await asyncio.to_thread(fingerprints, [frozen_path]))
    try:
        return await _run_phases(questions, answers, old, out_run, template_name)
    finally:
        await asyncio.to_thread(verify_unchanged, hashes)
        if frozen_path is not None:
            await asyncio.to_thread(verify_frozen, frozen_path)


async def _run_phases(
    questions: list[Question],
    answers: dict[str, SystemAnswer],
    old: dict[str, JudgeVerdict],
    out_run: Path,
    template_name: str,
) -> EvalResult:
    judge = create_judge()
    pilot = questions[:PILOT_SIZE]
    logger.info("开始前三题试评：%d题", len(pilot))
    result = await _evaluate_cache(pilot, answers, judge, out_run, template_name)
    await asyncio.to_thread(_write_result, result, old, out_run, len(questions))
    await asyncio.to_thread(_save_pilot, out_run)
    if not result.judge_errors and not result.system_errors:
        logger.info("前三题通过，复用标签继续评审%d题", len(questions))
        result = await _evaluate_cache(questions, answers, judge, out_run, template_name)
        await asyncio.to_thread(_write_result, result, old, out_run, len(questions))
    logger.info(
        "重评完成：%d/%d，错误%d",
        len(result.scored),
        len(questions),
        len(result.judge_errors) + len(result.system_errors),
    )
    return result


async def _evaluate_cache(
    questions: Sequence[Question],
    answers: dict[str, SystemAnswer],
    judge: Judge,
    out_run: Path,
    template_name: str,
) -> EvalResult:
    result = EvalResult("完整系统缓存重评", list(questions), [answers[q.id] for q in questions])
    for question in questions:
        current = await evaluate(
            result.system_name,
            [question],
            [answers[question.id]],
            judge,
            verdict_cache=out_run / "verdicts.jsonl",
            template_name=template_name,
            include_contexts=template_name == "judge_v2.md",
        )
        result.scored.extend(current.scored)
        result.system_errors.update(current.system_errors)
        result.judge_errors.update(current.judge_errors)
        errors = {**result.system_errors, **result.judge_errors}
        await asyncio.to_thread(record_errors, out_run, errors)
        await asyncio.to_thread(write_json, out_run / "errors.json", errors)
        if len(errors) * ERROR_RATE_DENOMINATOR > len(questions):
            logger.error("当前阶段错误超过10%%，停止后续评审")
            break
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="仅使用缓存回答重评，不重跑系统或检索")
    parser.add_argument("--src-run", type=Path, required=True)
    parser.add_argument("--out-run", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--judge", choices=["claude"], required=True)
    parser.add_argument("--template", choices=["judge_v1.md", "judge_v2.md"], default="judge_v2.md")
    parser.add_argument("--seed-run", type=Path, help="验证旧断点后复制成功标签到全新输出目录")
    parser.add_argument("--frozen", type=Path, help="开始和退出时核对完整实现冻结清单")
    arguments = parser.parse_args()
    configure_logging("INFO")
    result = asyncio.run(
        run_rejudge(
            arguments.src_run,
            arguments.out_run,
            arguments.questions,
            template_name=arguments.template,
            seed_run=arguments.seed_run,
            frozen_path=arguments.frozen,
        )
    )
    sys.stdout.write(f"评审完成{len(result.scored)}题，评审错误{len(result.judge_errors)}题\n")
    if result.judge_errors or result.system_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
