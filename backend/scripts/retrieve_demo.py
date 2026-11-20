"""检索演示：`uv run poe retrieve-demo [问题 ...]`。用真实模型和已入库的语料，打印前 5 个候选。"""

import argparse
import asyncio
import sys
from datetime import date

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.engine import create_engine
from app.db.policy_filter import MetaFilter
from app.retrieval.factory import build_retriever

DEFAULT_QUERIES = [
    "繰上返済の手続を確認したいです。",
    "住宅ローンの手数料の一覧はありますか。",
    "変動金利の見直しルールを調べたいです。",
]


def _fmt(value: float | int | None, spec: str = "") -> str:
    return "-" if value is None else format(value, spec)


async def run(queries: list[str], filters: MetaFilter, *, rerank: bool) -> str:
    settings = get_settings()
    engine = create_engine(settings)
    try:
        retriever = await build_retriever(engine, settings)
        lines: list[str] = []
        for query in queries:
            result = await retriever.retrieve(query, filters=filters, rerank=rerank)
            lines += [
                f"\n### {query}",
                "| # | 文档 | 标题路径 | 向量名次 | 关键词名次 | 精排分 |",
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
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    parser.add_argument("--corpus-tier", choices=("S", "L"), default="L")
    parser.add_argument("--rerank", action="store_true")
    arguments = parser.parse_args()
    configure_logging("INFO")
    filters = MetaFilter(as_of=arguments.as_of, corpus_tier=arguments.corpus_tier)
    sys.stdout.write(
        asyncio.run(run(arguments.queries or DEFAULT_QUERIES, filters, rerank=arguments.rerank))
    )


if __name__ == "__main__":
    main()
