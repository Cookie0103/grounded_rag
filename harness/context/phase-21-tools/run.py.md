"""开发集真实消融：复用现有系统和评分，不修改业务或评测规则。"""

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import logging
import subprocess
import sys
from contextvars import ContextVar
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import CACHE_DIR, EDITION_FILTERS, FINAL_TOP_K, get_settings
from app.core.errors import BudgetExceededError
from app.core.logging import configure_logging
from app.db.engine import create_engine, ping
from app.ingest.corpus import CORPUS_COMMIT
from app.orchestration.pipeline import ChatPipeline
from app.providers.budget import BudgetLedger
from app.providers.factory import get_chat_model
from app.retrieval.factory import build_retriever
from app.retrieval.retriever import BM25, HYBRID, VECTOR
from eval.dataset import load_questions
from eval.judge import CommandPromptRunner, Judge
from eval.metrics import hit_groups_at_k, ranked_documents, reciprocal_rank
from eval.runner import load_cache
from eval.systems import FullSystem, NaiveRagSystem, NoRetrievalSystem

OUT = Path(__file__).resolve().parent
SOURCE = ROOT / "docs/eval/dev70/questions.jsonl"
NAMES = ("no-retrieval", "naive-rag", "hybrid-no-rerank", "hybrid-rag", "routed", "full")
RETRIEVALS = (("vector", VECTOR, False), ("bm25", BM25, False),
              ("hybrid", HYBRID, False), ("hybrid-rerank", HYBRID, True))
CONCURRENCY = 4
log = logging.getLogger("ablation")
current_task = ContextVar("current_task", default="warmup")


class RecordedChat:
    def __init__(self, chat):
        self.chat = chat

    async def complete(self, messages, *, json_mode=False):
        result = await self.chat.complete(messages, json_mode=json_mode)
        append(OUT / "completions.jsonl", {"task": current_task.get(), "model": result.model,
            "prompt_tokens": result.prompt_tokens, "completion_tokens": result.completion_tokens})
        return result


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(value, ensure_ascii=False) + "\n")


def hashes():
    paths = [SOURCE, SOURCE.with_name("evidence.json"), Path(__file__)]
    for folder in ("app", "eval", "scripts"):
        paths += sorted((ROOT / "backend" / folder).rglob("*.py"))
    paths += sorted((ROOT / "backend/eval/prompts").glob("*.md"))
    paths += sorted((ROOT / "backend/app/prompts").glob("*.md"))
    paths += [ROOT / "backend/pyproject.toml", ROOT / "backend/uv.lock"]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def prepare():
    settings = get_settings()
    assert settings.chat_model == "deepseek" and settings.deepseek_api_key
    assert 0 < settings.daily_budget_cny <= 10
    qs = load_questions(SOURCE)
    assert len(qs) == 70 and all(q.split == "dev" for q in qs)
    config = {k: getattr(settings, k) for k in ("embedding_model", "reranker_model",
              "embed_device", "embed_batch_size", "deepseek_model", "daily_budget_cny")}
    current = hashes()
    manifest_path = OUT / "manifest.json"
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert previous["sha256"] == current, "冻结输入或执行代码变了，禁止混合结果"
        assert previous["config"] == config, "配置发生变化"
    else:
        ledger = BudgetLedger(CACHE_DIR / "budget", settings.daily_budget_cny)
        write_json(manifest_path, {"started_utc": datetime.now(timezone.utc).isoformat(),
            "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "corpus_commit": CORPUS_COMMIT, "sha256": current, "config": config,
            "packages": {p: importlib.metadata.version(p) for p in
                ("torch", "transformers", "sentence-transformers", "langgraph")},
            "questions": 70, "answerable": sum(q.answerable for q in qs),
            "concurrency": CONCURRENCY, "edition_sent": True, "session_history": False,
            "judge": "claude -p / judge_v2.md", "budget_before_cny": ledger.spent(),
            "systems": NAMES, "order": "每题循环轮换系统顺序，四题并行；题集原序固定",
            "scope": "eval FullSystem/ChatPipeline，不含服务缓存、记忆、后处理",
            "cache": "独立且初始为空；只复用本轮断点；GPU预热不计入延迟"})
    return settings, qs


async def retrieval(settings, qs):
    engine = create_engine(settings)
    try:
        await ping(engine, settings.db_timeout_seconds)
        retriever = await build_retriever(engine, settings)
        await retriever.retrieve("Dify 知识库文件上传限制", rerank=True)
        done = set()
        path = OUT / "retrieval.jsonl"
        if path.exists():
            done = {(r["system"], r["question_id"]) for r in map(json.loads, path.read_text(encoding="utf-8").splitlines())}
        eligible = [q for q in qs if q.answerable and q.gold_docs]
        for i, q in enumerate(eligible):
            for offset in range(len(RETRIEVALS)):
                name, mode, rerank = RETRIEVALS[(i + offset) % len(RETRIEVALS)]
                if (name, q.id) in done:
                    continue
                r = await retriever.retrieve(q.question, mode=mode, rerank=rerank,
                    editions=EDITION_FILTERS[q.edition] if q.edition else None)
                docs = ranked_documents([c.chunk.document_id for c in r.candidates])
                append(path, {"system": name, "question_id": q.id,
                    "hit": hit_groups_at_k(q.required_groups, docs, FINAL_TOP_K),
                    "mrr": reciprocal_rank(q.all_gold_docs, docs), "retrieved_docs": docs,
                    "latency_ms": r.timings_ms["total"], "retrieval": asdict(r)})
            log.info("检索 %s (%d/%d)", q.id, i + 1, len(eligible))
    finally:
        await engine.dispose()
    write_json(OUT / "retrieval-status.json", {"status": "completed", "questions": len(eligible), "rows": len(eligible) * 4})


async def generate(settings, qs):
    ledger = BudgetLedger(CACHE_DIR / "budget", settings.daily_budget_cny)
    ledger.check()
    engine = create_engine(settings)
    cache = {name: load_cache(OUT / name / "answers.jsonl") for name in NAMES}
    stop = asyncio.Event()
    errors = {}
    try:
        retriever = await build_retriever(engine, settings)
        await retriever.retrieve("Dify 知识库文件上传限制", rerank=True)
        chat = RecordedChat(get_chat_model(settings))
        systems = {"no-retrieval": NoRetrievalSystem(chat),
            "naive-rag": NaiveRagSystem(retriever, chat),
            "hybrid-no-rerank": NaiveRagSystem(retriever, chat, mode=HYBRID, rerank=False),
            "hybrid-rag": NaiveRagSystem(retriever, chat, mode=HYBRID, rerank=True),
            "routed": FullSystem(ChatPipeline(chat, retriever, grade=False, verify=False)),
            "full": FullSystem(ChatPipeline(chat, retriever))}
        sem = asyncio.Semaphore(CONCURRENCY)

        async def work(i, q):
            async with sem:
                for offset in range(len(NAMES)):
                    name = NAMES[(i + offset) % len(NAMES)]
                    if q.id in cache[name]:
                        continue
                    if stop.is_set():
                        return
                    # 原provider仍强制执行10元预算；预留并发在途调用的余额，不修改账本。
                    if ledger.spent() >= settings.daily_budget_cny - 0.7:
                        stop.set()
                        return
                    try:
                        current_task.set(f"{name}/{q.id}")
                        answer = await systems[name].answer(q)
                    except Exception as exc:
                        errors[f"{name}/{q.id}"] = f"{type(exc).__name__}: {exc}"
                        append(OUT / "generation-errors.jsonl", {"system": name, "question_id": q.id,
                            "error": errors[f"{name}/{q.id}"]})
                        if isinstance(exc, BudgetExceededError) or len(errors) >= 3:
                            stop.set()
                        continue
                    cache[name][q.id] = answer
                    append(OUT / name / "answers.jsonl", answer.to_json())
                    log.info("作答 %s %s (%d/70) ¥%.4f", name, q.id, len(cache[name]), ledger.spent())
                    write_json(OUT / "generation-status.json", {"status": "running",
                        "counts": {n: len(c) for n, c in cache.items()}, "spent_cny": ledger.spent(), "errors": errors})
        await asyncio.gather(*(work(i, q) for i, q in enumerate(qs)))
    finally:
        await engine.dispose()
    counts = {n: len(c) for n, c in cache.items()}
    write_json(OUT / "generation-status.json", {"status": "completed" if all(n == len(qs) for n in counts.values()) else "incomplete",
        "counts": counts, "spent_cny": ledger.spent(), "errors": errors,
        "budget_reserve_cny": 0.7 if stop.is_set() else 0})


async def judge_answers(qs):
    from eval.evaluate import load_verdicts
    judge = Judge(CommandPromptRunner(["claude", "-p"]))
    done = {name: load_verdicts(OUT / name / "verdicts.jsonl") for name in NAMES}
    failures = 0
    sem = asyncio.Semaphore(CONCURRENCY)
    stopped = asyncio.Event()

    async def review(name, q, answer):
        nonlocal failures
        async with sem:
            if stopped.is_set():
                return
            try:
                verdict = await judge.judge(q, answer.answer, contexts=answer.contexts, template_name="judge_v2.md")
            except Exception as exc:
                failures += 1
                append(OUT / "judge-errors.jsonl", {"system": name, "question_id": q.id,
                    "error": f"{type(exc).__name__}: {exc}"})
                log.error("评审失败 %s %s %s", name, q.id, exc)
                if failures >= 3:
                    stopped.set()
                return
            done[name][q.id] = verdict
            append(OUT / name / "verdicts.jsonl", {"question_id": q.id, **asdict(verdict)})
            log.info("评审 %s %s (%d/70)", name, q.id, len(done[name]))

    while not stopped.is_set():
        answers = {name: load_cache(OUT / name / "answers.jsonl") for name in NAMES}
        pending = []
        for i, q in enumerate(qs):
            for offset in range(len(NAMES)):
                name = NAMES[(i + offset) % len(NAMES)]
                if q.id not in done[name] and q.id in answers[name]:
                    pending.append(review(name, q, answers[name][q.id]))
        if pending:
            await asyncio.gather(*pending)
        write_json(OUT / "judge-status.json", {"counts": {n: len(c) for n, c in done.items()}, "failures": failures})
        status_path = OUT / "generation-status.json"
        status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
        if status.get("status") in ("completed", "incomplete") or stopped.is_set():
            # 最后一次快照可能发生在作答结束之前，再扫一遍遗漏。
            latest = {name: load_cache(OUT / name / "answers.jsonl") for name in NAMES}
            missing = [(n, q, latest[n][q.id]) for q in qs for n in NAMES
                       if q.id in latest[n] and q.id not in done[n]]
            if missing and not stopped.is_set():
                await asyncio.gather(*(review(n, q, a) for n, q, a in missing))
            break
        await asyncio.sleep(15)
    write_json(OUT / "judge-status.json", {"counts": {n: len(c) for n, c in done.items()}, "failures": failures})


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("retrieval", "generate", "judge", "audit"))
    args = parser.parse_args()
    configure_logging("INFO")
    settings, qs = prepare()
    if args.stage == "retrieval":
        await retrieval(settings, qs)
    elif args.stage == "generate":
        await generate(settings, qs)
    elif args.stage == "judge":
        await judge_answers(qs)
    write_json(OUT / f"{args.stage}-audit.json", {"protected_hashes_unchanged": hashes() ==
        json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))["sha256"],
        "date_utc": datetime.now(timezone.utc).isoformat()})


if __name__ == "__main__":
    asyncio.run(main())
