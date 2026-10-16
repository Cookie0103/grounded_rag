"""检索演示：`uv run poe retrieve-demo [问题 ...]`。用真实模型和已入库的语料，打印前 5 个候选。"""

import argparse
import asyncio
import logging
import sys

from app.core.config import EDITION_FILTERS, get_settings
from app.core.logging import configure_logging
from app.db.engine import create_engine
from app.retrieval.factory import build_retriever

DEFAULT_QUERIES = [
    "知识库单次最多上传几个文件",
    "怎么修改上传文件的大小限制",
    "UPLOAD_FILE_SIZE_LIMIT 是什么",
    "云版本怎么查看应用的监控数据",
    "工作流和对话流有什么区别",
]

logger = logging.getLogger("retrieve_demo")


def _fmt(value: float | int | None, spec: str = "") -> str:
    return "-" if value is None else format(value, spec)


async def run(queries: list[str], edition: str | None) -> str:
    settings = get_settings()
    engine = create_engine(settings)
    try:
        retriever = await build_retriever(engine, settings)
        editions = EDITION_FILTERS[edition] if edition else None
        lines: list[str] = []
        for query in queries:
            result = await retriever.retrieve(query, editions=editions)
            lines += [
                f"\n### {query}",
                "| # | 文档 | 标题路径 | 向量名次 | BM25 名次 | 精排分 |",
                "|---|---|---|---|---|---|",
            ]
            for c in result.candidates:
                lines.append(
                    f"| {c.rank} | `{c.chunk.document_id}` | {c.chunk.heading_path} | "
                    f"{_fmt(c.vector_rank)} | {_fmt(c.bm25_rank)} | {_fmt(c.rerank_score, '.3f')} |"
                )
            lines.append(f"耗时（毫秒）：{result.timings_ms}")
        return "\n".join(lines) + "\n"
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="检索演示")
    parser.add_argument("queries", nargs="*", help="不给就用内置的几个问题")
    parser.add_argument("--edition", choices=sorted(EDITION_FILTERS), help="只查某个版本")
    arguments = parser.parse_args()
    configure_logging("INFO")
    sys.stdout.write(asyncio.run(run(arguments.queries or DEFAULT_QUERIES, arguments.edition)))


if __name__ == "__main__":
    main()
