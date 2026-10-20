"""只读旧回答、使用新模板重评；每套先前三题，再复用标签缓存继续。"""

import argparse
import asyncio
import hashlib
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
from eval.judge import PROMPTS_DIR, CommandPromptRunner, Judge
from eval.report import render_report
from eval.runner import load_cache
from eval.scoring import JudgeVerdict, ScoredQuestion, score_question, summarize
from eval.systems import SystemAnswer

PILOT_SIZE = 3
logger = logging.getLogger(__name__)


def create_judge() -> Judge:
    """仅使用作者指定的Claude命令行，不创建被测模型或检索器。"""
    return Judge(CommandPromptRunner(["claude", "-p"]))


def check_output_location(is_test: bool, out_run: Path) -> None:
    """测试输出必须物理位于仓库外，包括目录链接的目标。"""
    if is_test and out_run.resolve().is_relative_to(REPO_ROOT.resolve()):
        raise ValueError("测试题重评产物必须放在仓库外")


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _fingerprints(paths: Sequence[Path]) -> dict[str, str]:
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


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
    return "\n".join(lines)


def _write_result(
    result: EvalResult, old: dict[str, JudgeVerdict], out_run: Path, planned: int
) -> None:
    errors = {**result.system_errors, **result.judge_errors}
    counts = {
        "planned": planned,
        "cached_answers": len(result.answers),
        "judged": len(result.scored),
        "error_questions": len(errors),
        "not_reviewed": planned - len(result.scored) - len(errors),
    }
    notice = (
        "> v2为评审改动后的初步结果，校准通过前不是正式数字。\n\n"
        f"计划{planned}题；本次使用缓存回答{len(result.answers)}题；"
        f"评审完成{len(result.scored)}题；错误{len(errors)}题；"
        f"待评{counts['not_reviewed']}题。没有重跑系统或检索。\n\n"
        "运行延迟和生成成本来自v1缓存，不是本次重评的费用或耗时。\n\n"
    )
    (out_run / "report.md").write_text(notice + render_report(result), encoding="utf-8")
    (out_run / "flips.md").write_text(render_flips(result, old), encoding="utf-8")
    _write_json(out_run / "errors.json", errors)
    retrieval = retrieval_stats(list(zip(result.questions, result.answers, strict=True)))
    _write_json(
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
    hashes = _fingerprints([path for path in protected if path.exists()])
    out_run.mkdir(parents=True, exist_ok=False)
    _write_json(
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
        },
    )
    return questions, answers, old, hashes


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
) -> EvalResult:
    """创建新目录，前三题通过后只重评尚未缓存的新模板标签。"""
    questions, answers, old, hashes = await asyncio.to_thread(
        _prepare, src_run, out_run, questions_path, template_name=template_name
    )
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
    if await asyncio.to_thread(_fingerprints, [Path(path) for path in hashes]) != hashes:
        raise RuntimeError("旧运行、题集或评审模板在重评期间发生变化")
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
    return await evaluate(
        "完整系统缓存重评",
        questions,
        [answers[q.id] for q in questions],
        judge,
        verdict_cache=out_run / "verdicts.jsonl",
        template_name=template_name,
        include_contexts=template_name == "judge_v2.md",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="仅使用缓存回答重评，不重跑系统或检索")
    parser.add_argument("--src-run", type=Path, required=True)
    parser.add_argument("--out-run", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--judge", choices=["claude"], required=True)
    parser.add_argument("--template", choices=["judge_v1.md", "judge_v2.md"], default="judge_v2.md")
    arguments = parser.parse_args()
    configure_logging("INFO")
    result = asyncio.run(
        run_rejudge(
            arguments.src_run,
            arguments.out_run,
            arguments.questions,
            template_name=arguments.template,
        )
    )
    sys.stdout.write(f"评审完成{len(result.scored)}题，评审错误{len(result.judge_errors)}题\n")
    if result.judge_errors or result.system_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
