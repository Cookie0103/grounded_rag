"""运行一轮独立开发题并冻结归档：不复用其他轮次缓存，不生成跨轮总览。"""

import argparse
import asyncio
import hashlib
import json
import logging
import re
import shutil
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langfuse import Langfuse

from app.core.config import CACHE_DIR, INGEST_VERSION, REPO_ROOT, get_settings
from app.core.logging import configure_logging
from app.core.trace import new_trace_id, trace_id_var
from app.db.engine import create_engine, ping
from app.ingest.corpus import CORPUS_COMMIT
from app.orchestration import prompts
from app.orchestration.factory import build_services
from app.orchestration.models import ChatRequest
from app.orchestration.service import ChatService
from app.providers.budget import BudgetLedger
from eval.dataset import Question, load_questions, validate_questions
from eval.runner import run_system
from eval.systems import SystemAnswer

logger = logging.getLogger(__name__)
ARCHIVE_ROOT = REPO_ROOT / "docs/eval/results/runs"
MAX_AGENT_DAILY_CNY = 10


class RecordedService:
    name = "full-service"

    def __init__(self, chat: ChatService, directory: Path) -> None:
        self._chat = chat
        self._directory = directory

    async def answer(self, question: Question) -> SystemAnswer:
        """调用现有服务并保存其原始响应、应用与云端trace对应关系。"""
        trace_id = new_trace_id()
        token = trace_id_var.set(trace_id)
        started = time.perf_counter()
        try:
            response = await self._chat.answer(
                ChatRequest(question=question.question, edition=question.edition)
            )
            latency = (time.perf_counter() - started) * 1000
            record = {
                "question_id": question.id,
                "app_trace_id": trace_id,
                "cloud_trace_id": Langfuse.create_trace_id(seed=trace_id),
                "question": asdict(question),
                "latency_ms": latency,
                "response": response.model_dump(mode="json"),
            }
            with (self._directory / "traces.jsonl").open("a", encoding="utf-8") as output:
                output.write(json.dumps(record, ensure_ascii=False) + "\n")
            return SystemAnswer(
                question.id,
                response.answer,
                response.route,
                tuple(response.retrieved_docs),
                tuple(response.contexts),
                latency,
                response.cost_cny,
                steps=tuple(response.steps),
            )
        finally:
            trace_id_var.reset(token)


async def prepare_archive(run_id: str, question_path: Path) -> tuple[Path, dict[str, Any]]:
    """新建唯一轮次目录，冻结题集、证据与评分口径；不包含密钥。"""
    if re.fullmatch(r"[A-Za-z0-9_-]+", run_id) is None:
        raise ValueError("run-id只能包含字母、数字、下划线和短横线")
    directory = ARCHIVE_ROOT / run_id
    directory.mkdir(parents=True, exist_ok=False)
    sources = {
        "questions.jsonl": question_path,
        "evidence.json": question_path.with_name("evidence.json"),
        "metrics-v1.md": REPO_ROOT / "docs/eval/metrics-v1.md",
    }
    for name, source in sources.items():
        shutil.copyfile(source, directory / name)
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("未找到git，无法记录代码版本")
    process = await asyncio.create_subprocess_exec(
        git, "rev-parse", "HEAD", cwd=REPO_ROOT, stdout=asyncio.subprocess.PIPE
    )
    stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5)
    if process.returncode != 0:
        raise RuntimeError("无法读取git版本")
    commit = stdout.decode().strip()
    manifest: dict[str, Any] = {
        "run_id": run_id,
        "system": "full-service",
        "split": "dev",
        "started_at": datetime.now(UTC).isoformat(),
        "status": "running",
        "code_commit": commit,
        "corpus_commit": CORPUS_COMMIT,
        "ingest_version": INGEST_VERSION,
        "prompt_hash": prompts.version(),
        "concurrency": 1,
        "session_history": False,
        "answer_cache_initially_empty": True,
        "cold_start_question": "dev001",
        "overall_index_deferred": True,
        "judge": {
            "mode": "current_codex_session",
            "effort_requested": "high",
            "effort_independently_verified": False,
            "human_calibrated": False,
        },
        "snapshot_sha256": {
            name: hashlib.sha256(source.read_bytes()).hexdigest()
            for name, source in sources.items()
        },
    }
    return directory, manifest


async def run(run_id: str, question_path: Path) -> Path:
    """以既有预算、模型与生产服务执行开发题，成功或失败都保留结果。"""
    settings = get_settings()
    questions = load_questions(question_path)
    if any(question.split != "dev" for question in questions) or validate_questions(questions):
        raise ValueError("这里只接受通过现有校验的开发题")
    if not 0 < settings.daily_budget_cny <= MAX_AGENT_DAILY_CNY:
        raise ValueError("agent真实运行要求既有每日预算大于0且不超过10元")
    ledger = BudgetLedger(CACHE_DIR / "budget", settings.daily_budget_cny)
    ledger.check()
    directory, manifest = await prepare_archive(run_id, question_path)
    manifest["config"] = {
        name: getattr(settings, name)
        for name in (
            "embedding_model",
            "reranker_model",
            "embed_device",
            "chat_model",
            "deepseek_model",
            "daily_budget_cny",
        )
    }
    manifest["budget_before_cny"] = ledger.spent()
    engine = create_engine(settings)
    services = None
    try:
        await ping(engine, settings.db_timeout_seconds)
        services = await build_services(engine, settings)
        answers = await run_system(
            RecordedService(services.chat, directory),
            questions,
            cache_path=CACHE_DIR / "eval/runs" / run_id / "answers.jsonl",
            concurrency=1,
            progress=lambda done, total: logger.info("完成 %d/%d", done, total),
        )
        (directory / "answers.jsonl").write_text(
            "".join(json.dumps(a.to_json(), ensure_ascii=False) + "\n" for a in answers),
            encoding="utf-8",
        )
        manifest.update(
            status="answers_completed",
            question_count=len(questions),
            system_errors={a.question_id: a.error for a in answers if a.error},
        )
    finally:
        if services is not None:
            await services.chat.close()
        await engine.dispose()
        manifest.update(finished_at=datetime.now(UTC).isoformat(), budget_after_cny=ledger.spent())
        (directory / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return directory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--questions", required=True, type=Path)
    arguments = parser.parse_args()
    configure_logging("INFO")
    directory = asyncio.run(run(arguments.run_id, arguments.questions))
    logger.info("本轮归档：%s", directory)


if __name__ == "__main__":
    main()
