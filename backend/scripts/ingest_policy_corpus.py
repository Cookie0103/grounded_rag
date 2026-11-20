"""将本机语料写入 pgvector 与 Elasticsearch，并生成 S 档出题用语料包。"""

import argparse
import asyncio
import json
import logging
from collections import Counter
from pathlib import Path
from statistics import median
from zipfile import ZIP_DEFLATED, ZipFile

from app.core.config import CACHE_DIR, DATA_DIR, POLICY_INDEX_ALIAS, get_settings
from app.core.policy import PolicyChunk
from app.db.engine import create_engine
from app.db.policy_index import PolicyIndex
from app.ingest.policy_pipeline import (
    ingest_policy_corpus,
    publish_policy_version,
    read_policy_manifest,
)
from app.ingest.source_loader import load_source
from app.providers.factory import get_embedder

logger = logging.getLogger(__name__)
_MIN_LENGTH = 300
_MAX_LENGTH = 800


def _report(chunks: list[PolicyChunk]) -> dict[str, object]:
    documents = {chunk.document_id: chunk.policy for chunk in chunks}
    lengths = [len(chunk.text) for chunk in chunks]
    core_lengths = [len(chunk.text) for chunk in chunks if chunk.policy.corpus_tier == "S"]
    return {
        "docs": len(documents),
        "sources": dict(Counter(doc.source for doc in documents.values())),
        "s_docs": sum(doc.corpus_tier == "S" for doc in documents.values()),
        "l_docs": len(documents),
        "s_chunks": sum(chunk.policy.corpus_tier == "S" for chunk in chunks),
        "s_chunk_chars_median": median(core_lengths),
        "s_chunk_chars_300_to_800": sum(
            _MIN_LENGTH <= length <= _MAX_LENGTH for length in core_lengths
        ),
        "l_chunks": len(chunks),
        "chunk_chars_median": median(lengths),
        "chunk_chars_lt_300": sum(length < _MIN_LENGTH for length in lengths),
        "chunk_chars_300_to_800": sum(_MIN_LENGTH <= length <= _MAX_LENGTH for length in lengths),
        "chunk_chars_gt_800": sum(length > _MAX_LENGTH for length in lengths),
    }


def _question_pack(target: Path, chunks: list[PolicyChunk]) -> None:
    documents = {
        chunk.document_id.rsplit("@", 1)[0]: (chunk.document_id, chunk.policy)
        for chunk in chunks
        if chunk.policy.corpus_tier == "S"
    }
    entries = []
    with ZipFile(target, "w", ZIP_DEFLATED) as bundle:
        for item in read_policy_manifest(DATA_DIR):
            if item.id not in documents:
                continue
            source = load_source(DATA_DIR / item.path)
            document_id, metadata = documents[item.id]
            filename = item.id.replace("/", "--") + ".md"
            rows = {
                "document_id": document_id,
                "source_id": item.id,
                "file": filename,
                **metadata.model_dump(mode="json"),
            }
            entries.append(json.dumps(rows, ensure_ascii=False))
            synthetic = "synthetic: true\n\n" if metadata.synthetic else ""
            text = f"# {source.title}\n\n文書 ID {document_id}\n\n{synthetic}{source.markdown}"
            bundle.writestr(f"documents/{filename}", text)
        bundle.writestr("index.jsonl", "\n".join(entries) + "\n")
        bundle.writestr(
            "README.md",
            "# 住宅ローン規程の出題用資料\n\n"
            "参照はこの資料内に限定してください。index.jsonl の document_id を根拠とし、"
            "適用日が必要な設問には as_of を記入してください。"
            "synthetic の資料は訓練用であり、実在の銀行の内部運用や過去の金利を表しません。\n",
        )


async def _run(publish: str | None) -> None:
    settings = get_settings()
    engine = create_engine(settings)
    index = PolicyIndex(settings.elasticsearch_url, POLICY_INDEX_ALIAS)
    try:
        if publish is not None:
            count = await publish_policy_version(engine, index, publish)
            logger.info("已发布 %s，并同步 %d 个子块", publish, count)
            return
        stats, chunks = await ingest_policy_corpus(
            DATA_DIR, get_embedder(settings.embedding_model, settings), engine, index
        )
    finally:
        await index.close()
        await engine.dispose()
    CACHE_DIR.mkdir(exist_ok=True)
    report = _report(chunks)
    report.update(
        added=stats.added,
        unchanged=stats.unchanged,
        changed=stats.changed,
        removed=stats.removed,
        embedded_chunks=stats.embedded_chunks,
        embed_seconds=round(stats.embed_seconds, 3),
    )
    content = json.dumps(report, ensure_ascii=False, indent=2)
    (CACHE_DIR / "policy-corpus-report.json").write_text(content + "\n", encoding="utf-8")
    _question_pack(CACHE_DIR / "policy-question-pack.zip", chunks)
    logger.info("规程语料报告\n%s", content)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", help="发布指定的草稿规程文档 ID")
    asyncio.run(_run(parser.parse_args().publish))
