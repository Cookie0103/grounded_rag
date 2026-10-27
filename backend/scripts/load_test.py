"""压测：`uv run poe load-test --endpoint chat --concurrency 8 --requests 200`。

先启动服务（`poe serve`），再运行这个脚本。题目取自题集（默认冒烟集）循环使用；
`/chat` 有答案缓存，要测不命中缓存的数字就给 `--unique`（每次在问题后面加一个编号）。
限流默认每分钟 30 次，压测前把服务的 `RATE_LIMIT_PER_MINUTE` 设成 0。
"""

import argparse
import asyncio
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
import numpy as np

from eval.dataset import load_questions

DEFAULT_QUESTIONS = Path(__file__).resolve().parents[1] / "eval" / "smoke_retrieval.jsonl"
TIMEOUT_SECONDS = 120.0


@dataclass(frozen=True)
class LoadResult:
    requests: int
    errors: int
    elapsed_seconds: float
    p50_ms: float
    p95_ms: float
    p99_ms: float

    @property
    def qps(self) -> float:
        return self.requests / self.elapsed_seconds if self.elapsed_seconds else 0.0

    def render(self) -> str:
        error_rate = self.errors / max(self.requests, 1)
        return (
            f"请求 {self.requests}，错误 {self.errors}（{error_rate:.1%}），"
            f"耗时 {self.elapsed_seconds:.1f} 秒，QPS {self.qps:.2f}\n"
            f"延迟 P50 {self.p50_ms:.0f} 毫秒，P95 {self.p95_ms:.0f} 毫秒，"
            f"P99 {self.p99_ms:.0f} 毫秒\n"
        )


def summarize(latencies_ms: list[float], errors: int, elapsed_seconds: float) -> LoadResult:
    """延迟只统计成功的请求。"""
    p50, p95, p99 = (
        (float(np.percentile(latencies_ms, q)) for q in (50, 95, 99))
        if latencies_ms
        else (0.0, 0.0, 0.0)
    )
    return LoadResult(len(latencies_ms) + errors, errors, elapsed_seconds, p50, p95, p99)


async def run_load(
    client: httpx.AsyncClient,
    endpoint: str,
    questions: list[str],
    *,
    requests: int,
    concurrency: int,
    unique: bool,
) -> LoadResult:
    semaphore = asyncio.Semaphore(concurrency)
    latencies: list[float] = []
    errors = 0

    async def one(number: int) -> None:
        nonlocal errors
        question = questions[number % len(questions)]
        if unique:
            question = f"{question}（{number}）"
        body = {"question": question} if endpoint == "chat" else {"query": question}
        async with semaphore:
            started = time.perf_counter()
            try:
                response = await client.post(f"/{endpoint}", json=body)
            except httpx.HTTPError:
                errors += 1
                return
            elapsed = (time.perf_counter() - started) * 1000
        if response.status_code == httpx.codes.OK:
            latencies.append(elapsed)
        else:
            errors += 1

    started = time.perf_counter()
    await asyncio.gather(*(one(number) for number in range(requests)))
    return summarize(latencies, errors, time.perf_counter() - started)


async def main_async(arguments: argparse.Namespace) -> LoadResult:
    questions = [q.question for q in load_questions(arguments.questions)]
    async with httpx.AsyncClient(base_url=arguments.url, timeout=TIMEOUT_SECONDS) as client:
        return await run_load(
            client,
            arguments.endpoint,
            questions,
            requests=arguments.requests,
            concurrency=arguments.concurrency,
            unique=arguments.unique,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="压测")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--endpoint", choices=["chat", "retrieve"], default="retrieve")
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--unique", action="store_true", help="每次请求的问题都不同，避开缓存")
    sys.stdout.write(asyncio.run(main_async(parser.parse_args())).render())


if __name__ == "__main__":
    main()
