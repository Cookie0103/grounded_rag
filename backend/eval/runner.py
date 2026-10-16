"""评测器：让被测系统并发回答所有题；结果落盘缓存，中断后可以续跑，出错不中断。"""

import asyncio
import json
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from eval.dataset import Question
from eval.systems import System, SystemAnswer

DEFAULT_CONCURRENCY = 4
Progress = Callable[[int, int], None]


def load_cache(path: Path | None) -> dict[str, SystemAnswer]:
    if path is None or not path.exists():
        return {}
    cached: dict[str, SystemAnswer] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            answer = SystemAnswer.from_json(json.loads(line))
            cached[answer.question_id] = answer
    return cached


async def run_system(
    system: System,
    questions: Sequence[Question],
    *,
    cache_path: Path | None = None,
    concurrency: int = DEFAULT_CONCURRENCY,
    progress: Progress | None = None,
) -> list[SystemAnswer]:
    """按题目的顺序返回回答。缓存里已有的题不再问；出错的题记下错误、不写缓存（下次会重试）。"""
    cached = load_cache(cache_path)
    answers: dict[str, SystemAnswer] = {q.id: cached[q.id] for q in questions if q.id in cached}
    todo = [q for q in questions if q.id not in answers]
    semaphore = asyncio.Semaphore(concurrency)
    write_lock = asyncio.Lock()
    done = len(answers)

    async def work(question: Question) -> None:
        nonlocal done
        async with semaphore:
            answer = await _safe_answer(system, question)
        answers[question.id] = answer
        if answer.error is None and cache_path is not None:
            async with write_lock:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                with cache_path.open("a", encoding="utf-8", newline="\n") as handle:
                    handle.write(json.dumps(answer.to_json(), ensure_ascii=False) + "\n")
        done += 1
        if progress is not None:
            progress(done, len(questions))

    await asyncio.gather(*(work(question) for question in todo))
    return [answers[question.id] for question in questions]


async def _safe_answer(system: System, question: Question) -> SystemAnswer:
    started = time.perf_counter()
    try:
        return await system.answer(question)
    except Exception as error:  # noqa: BLE001  被测系统出什么错都不能让整轮评测中断
        return SystemAnswer(
            question_id=question.id,
            answer=None,
            route=None,
            retrieved_docs=(),
            contexts=(),
            latency_ms=(time.perf_counter() - started) * 1000,
            error=f"{type(error).__name__}: {error}",
        )
