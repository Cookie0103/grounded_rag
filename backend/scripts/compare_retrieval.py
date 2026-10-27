"""检索方案对比：`uv run poe compare-retrieval [--questions 文件]`。

在一份题集上比较向量 / BM25 / 混合 / 精排、两种分词、两个嵌入模型、两个精排模型的 Recall@5。
默认用 eval/smoke_retrieval.jsonl（只是冒烟集，用来验证流程）；换成正式的开发集才能下结论。
"""

import argparse
import asyncio
import logging
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import CACHE_DIR, EDITION_FILTERS, FINAL_TOP_K, Settings, get_settings
from app.core.logging import configure_logging
from app.db.engine import create_engine
from app.ingest.pipeline import add_missing_embeddings
from app.providers.base import Embedder, Reranker
from app.providers.factory import get_embedder, get_reranker
from app.retrieval.bm25 import Tokenizer
from app.retrieval.factory import build_retriever
from app.retrieval.retriever import BM25, HYBRID, VECTOR, HybridRetriever
from app.retrieval.tokenizer import bigram_tokenize, tokenize
from eval.dataset import Question, load_questions
from eval.metrics import hit_groups_at_k, mean, ranked_documents, reciprocal_rank

DEFAULT_QUESTIONS = Path(__file__).resolve().parents[1] / "eval" / "smoke_retrieval.jsonl"
logger = logging.getLogger("compare_retrieval")


@dataclass(frozen=True)
class Config:
    name: str
    embedder: str  # qwen3 / bge-m3
    tokenizer: str  # jieba3 / bigram
    mode: str
    reranker: str  # none / qwen3 / bge


@dataclass(frozen=True)
class Outcome:
    config: Config
    recall: float
    mrr: float
    recall_similar: float
    recall_distant: float
    latency_ms: float
    misses: list[str]


CONFIGS = [
    Config("只用向量（qwen3 嵌入）", "qwen3", "jieba3", VECTOR, "none"),
    Config("只用 BM25（jieba3）", "qwen3", "jieba3", BM25, "none"),
    Config("只用 BM25（字符二元组）", "qwen3", "bigram", BM25, "none"),
    Config("混合（jieba3），不精排", "qwen3", "jieba3", HYBRID, "none"),
    Config("混合（字符二元组），不精排", "qwen3", "bigram", HYBRID, "none"),
    Config("混合（jieba3）+ qwen3 精排", "qwen3", "jieba3", HYBRID, "qwen3"),
    Config("混合（jieba3）+ bge 精排", "qwen3", "jieba3", HYBRID, "bge"),
    Config("只用向量（bge-m3 嵌入）", "bge-m3", "jieba3", VECTOR, "none"),
    Config("混合（bge-m3 嵌入，jieba3）+ qwen3 精排", "bge-m3", "jieba3", HYBRID, "qwen3"),
]
TOKENIZERS: dict[str, Tokenizer] = {"jieba3": tokenize, "bigram": bigram_tokenize}


async def evaluate(
    retriever: HybridRetriever, config: Config, questions: list[Question]
) -> Outcome:
    hits: list[float] = []
    reciprocal: list[float] = []
    by_group: dict[str, list[float]] = {"similar": [], "distant": []}
    misses: list[str] = []
    started = time.perf_counter()
    for question in questions:
        editions = EDITION_FILTERS[question.edition] if question.edition else None
        result = await retriever.retrieve(
            question.question,
            top_k=FINAL_TOP_K,
            editions=editions,
            rerank=config.reranker != "none",
            mode=config.mode,
        )
        ranked = ranked_documents([c.chunk.document_id for c in result.candidates])
        hit = hit_groups_at_k(question.required_groups, ranked, FINAL_TOP_K)
        hits.append(float(hit))
        reciprocal.append(reciprocal_rank(question.gold_docs, ranked))
        by_group.setdefault(question.lexical, []).append(float(hit))
        if not hit:
            misses.append(question.id)
    elapsed = time.perf_counter() - started
    return Outcome(
        config,
        mean(hits),
        mean(reciprocal),
        mean(by_group["similar"]),
        mean(by_group["distant"]),
        elapsed / len(questions) * 1000,
        misses,
    )


def render(outcomes: list[Outcome], questions: list[Question], source: Path) -> str:
    lines = [
        "# 检索方案对比",
        "",
        f"- 时间：{datetime.now():%Y-%m-%d %H:%M:%S}",
        f"- 题集：`{source.name}`，{len(questions)} 题（冒烟集只验证流程；结论要用正式开发集重跑）",
        f"- 指标：Recall@{FINAL_TOP_K}（金标文档全部进前 {FINAL_TOP_K} 个子块所属的文档）、MRR",
        "",
        "| 方案 | Recall@5 | MRR | 用词接近 | 用词不同 | 平均耗时 ms | 没命中的题 |",
        "|---|---|---|---|---|---|---|",
    ]
    for o in outcomes:
        lines.append(
            f"| {o.config.name} | {o.recall:.3f} | {o.mrr:.3f} | {o.recall_similar:.3f} | "
            f"{o.recall_distant:.3f} | {o.latency_ms:.0f} | {', '.join(o.misses) or '-'} |"
        )
    return "\n".join(lines) + "\n"


async def run(questions_path: Path, *, skip_bge: bool) -> str:
    settings: Settings = get_settings()
    questions = load_questions(questions_path)
    engine = create_engine(settings)
    try:
        configs = [c for c in CONFIGS if not (skip_bge and "bge" in c.name)]
        embedders = {name: get_embedder(name, settings) for name in {c.embedder for c in configs}}
        rerankers: dict[str, Reranker | None] = {
            name: get_reranker(name, settings) for name in {c.reranker for c in configs}
        }
        if "bge-m3" in embedders:
            added = await add_missing_embeddings(embedders["bge-m3"], engine)
            logger.info("给 bge-m3 补了 %d 个子块的向量", added)
        outcomes = await _run_all(engine, settings, configs, embedders, rerankers, questions)
    finally:
        await engine.dispose()
    return render(outcomes, questions, questions_path)


async def _run_all(
    engine: AsyncEngine,
    settings: Settings,
    configs: list[Config],
    embedders: dict[str, Embedder],
    rerankers: dict[str, Reranker | None],
    questions: list[Question],
) -> list[Outcome]:
    bases: dict[tuple[str, str], HybridRetriever] = {}
    outcomes: list[Outcome] = []
    for config in configs:
        key = (config.embedder, config.tokenizer)
        if key not in bases:
            bases[key] = await build_retriever(
                engine,
                settings,
                embedder=embedders[config.embedder],
                reranker=None,
                tokenizer=TOKENIZERS[config.tokenizer],
            )
        retriever = bases[key].with_reranker(rerankers[config.reranker])
        outcome = await evaluate(retriever, config, questions)
        logger.info("%s：Recall@5 = %.3f", config.name, outcome.recall)
        outcomes.append(outcome)
    return outcomes


def main() -> None:
    parser = argparse.ArgumentParser(description="检索方案对比")
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--skip-bge", action="store_true", help="不跑需要下载 bge 模型的方案")
    arguments = parser.parse_args()
    configure_logging("INFO")
    report = asyncio.run(run(arguments.questions, skip_bge=arguments.skip_bge))
    sys.stdout.write(report)
    reports_dir = CACHE_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / f"retrieval-compare-{datetime.now():%Y%m%d-%H%M%S}.md").write_text(
        report, encoding="utf-8"
    )


if __name__ == "__main__":
    main()
