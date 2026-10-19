"""导出坏例：`uv run poe export-bad-cases [--since 2026-10-16]`。

把差评、拒答、降级的问答导出到 .cache/bad_cases.jsonl。只有问题、原因和 trace_id，
**没有金标**：作者标好金标文档和关键点后，才能进评测回归集。
"""

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import CACHE_DIR, get_settings
from app.core.records import BadCase
from app.db.engine import create_engine
from app.db.observability import PostgresTraceStore

OUTPUT = CACHE_DIR / "bad_cases.jsonl"


def render(cases: list[BadCase]) -> str:
    return "".join(case.model_dump_json() + "\n" for case in cases)


async def fetch(since: datetime | None) -> list[BadCase]:
    engine = create_engine(get_settings())
    try:
        return await PostgresTraceStore(engine).bad_cases(since)
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="导出坏例")
    parser.add_argument("--since", help="只导出这天之后的，格式 2026-10-16")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()
    since = datetime.fromisoformat(arguments.since).replace(tzinfo=UTC) if arguments.since else None
    cases = asyncio.run(fetch(since))
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(render(cases), encoding="utf-8", newline="\n")
    sys.stdout.write(f"导出 {len(cases)} 条到 {arguments.output}\n")


if __name__ == "__main__":
    main()
