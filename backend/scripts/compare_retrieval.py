"""阶段 32 的日文检索冒烟对比。"""

import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import replace
from datetime import date
from math import ceil
from statistics import median

from pydantic import BaseModel

from app.core.config import CACHE_DIR, MODEL_CACHE_DIR, REPO_ROOT, get_settings
from app.core.policy import CorpusTier
from app.db.engine import create_engine
from app.db.policy_filter import MetaFilter
from app.providers.factory import SPECS, get_embedder
from app.providers.local_embedder import SentenceTransformerEmbedder
from app.retrieval.factory import build_retriever
from app.retrieval.retriever import HYBRID, KEYWORD, VECTOR, Retriever
from eval.metrics import hit_at_k, mean, ranked_documents, reciprocal_rank

logger = logging.getLogger(__name__)
_CASES = REPO_ROOT / "backend" / "eval" / "smoke_policy_retrieval.jsonl"
_SNAPSHOT_DAY = date(2026, 11, 18)
_TIERS: tuple[CorpusTier, ...] = ("S", "L")
_MODES = (
    (VECTOR, VECTOR, False),
    (KEYWORD, KEYWORD, False),
    (HYBRID, HYBRID, False),
    ("hybrid_rerank", HYBRID, True),
)
_P95 = 0.95
_LEGACY_INSTRUCTION = (
    "Given a question about the Dify platform, retrieve documentation passages that answer it"
)


class SmokeCase(BaseModel):
    query: str
    gold: str
    as_of: date = _SNAPSHOT_DAY


async def _mode(
    retriever: Retriever, cases: list[SmokeCase], *, tier: CorpusTier, mode: str, rerank: bool
) -> dict[str, object]:
    hits = 0
    expired = 0
    degraded = 0
    reciprocal: list[float] = []
    timings: dict[str, list[float]] = defaultdict(list)
    for case in cases:
        filters = MetaFilter(as_of=case.as_of, corpus_tier=tier)
        result = await retriever.retrieve(case.query, filters=filters, mode=mode, rerank=rerank)
        docs = ranked_documents(
            [candidate.chunk.document_id.rsplit("@", 1)[0] for candidate in result.candidates]
        )
        hits += hit_at_k((case.gold,), docs, 5)
        reciprocal.append(reciprocal_rank((case.gold,), docs))
        for name, value in result.timings_ms.items():
            timings[name].append(value)
        degraded += result.degraded
        expired += any(
            policy.effective_from > case.as_of
            or (policy.effective_to is not None and case.as_of >= policy.effective_to)
            for item in result.recall_candidates
            if (policy := item.chunk.policy) is not None
        )
    total = sorted(timings["total"])
    return {
        "cases": len(cases),
        "top5_hits": hits,
        "top5": hits / len(cases),
        "mrr": mean(reciprocal),
        "p95_ms": total[ceil(len(total) * _P95) - 1],
        "median_ms": {stage: median(values) for stage, values in timings.items()},
        "invalid_date_cases": expired,
        "degraded_cases": degraded,
    }


async def _run() -> None:
    cases = [
        SmokeCase.model_validate_json(line) for line in _CASES.read_text().splitlines() if line
    ]
    settings = get_settings()
    engine = create_engine(settings)
    try:
        model = get_embedder("qwen3", settings)
        retriever = await build_retriever(engine, settings, embedder=model)
        await retriever.retrieve(
            "住宅ローンの手続", filters=MetaFilter(as_of=_SNAPSHOT_DAY), rerank=True
        )
        report = {}
        for tier in _TIERS:
            for label, mode, rerank in _MODES:
                report[f"{tier}/{label}"] = await _mode(
                    retriever, cases, tier=tier, mode=mode, rerank=rerank
                )
                logger.info("%s/%s %s", tier, label, report[f"{tier}/{label}"])
        legacy = SentenceTransformerEmbedder(
            replace(SPECS["qwen3"], query_instruction=_LEGACY_INSTRUCTION),
            device=settings.embed_device,
            batch_size=settings.embed_batch_size,
            cache_dir=MODEL_CACHE_DIR,
        )
        previous = await build_retriever(engine, settings, embedder=legacy)
        await previous.retrieve(
            "住宅ローンの手続", filters=MetaFilter(as_of=_SNAPSHOT_DAY), mode=VECTOR
        )
        for tier in _TIERS:
            key = f"{tier}/old_query_instruction"
            report[key] = await _mode(previous, cases, tier=tier, mode=VECTOR, rerank=False)
            logger.info("%s %s", key, report[key])
    finally:
        await engine.dispose()
    CACHE_DIR.mkdir(exist_ok=True)
    (CACHE_DIR / "phase-32-retrieval-smoke.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    asyncio.run(_run())
