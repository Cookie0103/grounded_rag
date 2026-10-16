"""跑评测：`uv run poe eval-dev [--system retrieval] [--questions 文件] [--judge none|claude]`。

结果（回答缓存、评审缓存、报告）写到 .cache/eval/<系统名>/，中断后重跑会接着做。
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from app.core.config import CACHE_DIR, get_settings
from app.core.logging import configure_logging
from app.db.engine import create_engine
from app.retrieval.factory import build_retriever
from eval.attribution import attribute_errors
from eval.dataset import load_questions
from eval.evaluate import evaluate
from eval.judge import CommandPromptRunner, Judge
from eval.report import render_report
from eval.runner import run_system
from eval.systems import RetrievalOnlySystem

DEFAULT_QUESTIONS = Path(__file__).resolve().parents[1] / "eval" / "data" / "dev.jsonl"
JUDGE_COMMANDS = {"claude": ["claude", "-p"]}
logger = logging.getLogger("eval_run")


async def run(arguments: argparse.Namespace) -> str:
    questions = load_questions(arguments.questions)
    output_dir = CACHE_DIR / "eval" / arguments.system
    settings = get_settings()
    engine = create_engine(settings)
    try:
        retriever = await build_retriever(engine, settings)
        system = RetrievalOnlySystem(retriever)
        answers = await run_system(
            system,
            questions,
            cache_path=output_dir / "answers.jsonl",
            progress=lambda done, total: logger.info("检索 %d/%d", done, total),
        )
    finally:
        await engine.dispose()
    judge = Judge(CommandPromptRunner(JUDGE_COMMANDS[arguments.judge])) if arguments.judge else None
    result = await evaluate(
        system.name, questions, answers, judge, verdict_cache=output_dir / "verdicts.jsonl"
    )
    attributions = await attribute_errors(result.scored, answers, judge) if judge else None
    report = render_report(result, attributions)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "report.md").write_text(report, encoding="utf-8", newline="\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="跑评测")
    parser.add_argument("--system", choices=["retrieval"], default="retrieval")
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument(
        "--judge",
        choices=sorted(JUDGE_COMMANDS),
        help="不给就不评审，只出检索指标；claude 会消耗你的 Claude 用量",
    )
    arguments = parser.parse_args()
    configure_logging("INFO")
    sys.stdout.write(asyncio.run(run(arguments)))


if __name__ == "__main__":
    main()
