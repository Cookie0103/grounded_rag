"""跑评测：`uv run poe eval-dev [--system 系统] [--questions 文件] [--judge 评审]`。

系统：retrieval（只检索）、no-retrieval、naive-rag（两个基线）、full（完整编排）。
评审：不给就只出检索指标；claude（命令行 `claude -p`，消耗 Claude 用量）；deepseek（用 `CHAT_MODEL`
配置的对话模型，有每日预算）。结果写到 .cache/eval/<系统>/，中断后重跑会接着做。
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from app.core.config import CACHE_DIR, Settings, get_settings
from app.core.logging import configure_logging
from app.db.engine import create_engine
from app.orchestration.pipeline import ChatPipeline
from app.providers.factory import get_chat_model
from app.retrieval.factory import build_retriever
from eval.attribution import attribute_errors
from eval.dataset import load_questions
from eval.evaluate import evaluate
from eval.judge import ChatPromptRunner, CommandPromptRunner, Judge
from eval.report import render_report
from eval.runner import run_system
from eval.systems import FullSystem, NaiveRagSystem, NoRetrievalSystem, RetrievalOnlySystem, System

DEFAULT_QUESTIONS = Path(__file__).resolve().parents[1] / "eval" / "data" / "dev.jsonl"
SYSTEMS = ("retrieval", "no-retrieval", "naive-rag", "full")
JUDGES = ("claude", "deepseek")
logger = logging.getLogger("eval_run")


def build_judge(name: str | None, settings: Settings) -> Judge | None:
    if name == "claude":
        return Judge(CommandPromptRunner(["claude", "-p"]))
    if name == "deepseek":
        return Judge(ChatPromptRunner(get_chat_model(settings)))
    return None


async def run(arguments: argparse.Namespace) -> str:
    questions = load_questions(arguments.questions)
    output_dir = CACHE_DIR / "eval" / arguments.system
    settings = get_settings()
    engine = create_engine(settings)
    try:
        system: System
        if arguments.system == "no-retrieval":
            system = NoRetrievalSystem(get_chat_model(settings))
        else:
            retriever = await build_retriever(engine, settings)
            if arguments.system == "naive-rag":
                system = NaiveRagSystem(retriever, get_chat_model(settings))
            elif arguments.system == "full":
                system = FullSystem(ChatPipeline(get_chat_model(settings), retriever))
            else:
                system = RetrievalOnlySystem(retriever)
        answers = await run_system(
            system,
            questions,
            cache_path=output_dir / "answers.jsonl",
            progress=lambda done, total: logger.info("作答 %d/%d", done, total),
        )
    finally:
        await engine.dispose()
    judge = build_judge(arguments.judge, settings)
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
    parser.add_argument("--system", choices=SYSTEMS, default="retrieval")
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--judge", choices=JUDGES, help="不给就不评审，只出检索指标")
    arguments = parser.parse_args()
    configure_logging("INFO")
    sys.stdout.write(asyncio.run(run(arguments)))


if __name__ == "__main__":
    main()
