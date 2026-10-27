"""入库：`uv run poe ingest [--model qwen3|bge-m3|fake]`。

读 data/raw/ 里的语料，清洗、切块、嵌入后写进开发库；内容没变的文档会跳过。
结束后在终端打印数据报告，并写入 .cache/reports/ingest-<时间>.md。
"""

import argparse
import asyncio
import logging
import sys
import time
from datetime import datetime

from app.core.config import CACHE_DIR, get_settings
from app.core.logging import configure_logging
from app.db.corpus import corpus_overview
from app.db.engine import create_engine
from app.ingest.corpus import CORPUS_COMMIT, RAW_DIR
from app.ingest.pipeline import add_missing_embeddings, ingest_corpus
from app.ingest.report import ReportMeta, render_report, run_checks
from app.providers.factory import get_embedder

logger = logging.getLogger("ingest")


async def run(model: str | None) -> str:
    settings = get_settings()
    embedder = get_embedder(model or settings.embedding_model, settings)
    engine = create_engine(settings)
    started_at = datetime.now()
    started = time.perf_counter()
    try:
        stats = await ingest_corpus(RAW_DIR, embedder, engine)
        logger.info("入库完成：%s", stats)
        async with engine.connect() as connection:
            overview = await corpus_overview(connection)
        checks = await run_checks(engine, embedder)
    finally:
        await engine.dispose()
    meta = ReportMeta(CORPUS_COMMIT, embedder.name, started_at, time.perf_counter() - started)
    return render_report(meta, stats, overview, checks)


async def add_embeddings(model: str | None) -> str:
    settings = get_settings()
    embedder = get_embedder(model or settings.embedding_model, settings)
    engine = create_engine(settings)
    try:
        added = await add_missing_embeddings(embedder, engine)
    finally:
        await engine.dispose()
    return f"给 {embedder.name} 补了 {added} 个子块的向量\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="语料入库并生成数据报告")
    parser.add_argument(
        "--model", choices=["qwen3", "bge-m3", "fake"], help="默认读 EMBEDDING_MODEL"
    )
    parser.add_argument(
        "--add-embeddings", action="store_true", help="只给已入库的子块补这个模型的向量"
    )
    arguments = parser.parse_args()

    configure_logging("INFO")
    if arguments.add_embeddings:
        sys.stdout.write(asyncio.run(add_embeddings(arguments.model)))
        return
    report = asyncio.run(run(arguments.model))
    sys.stdout.write(report)
    reports_dir = CACHE_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    target = reports_dir / f"ingest-{datetime.now():%Y%m%d-%H%M%S}.md"
    target.write_text(report, encoding="utf-8")
    logger.info("报告已写入 %s", target)


if __name__ == "__main__":
    main()
