"""只读核对公开GitHub语料与本地库，不向模型发出任何请求。"""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.config import get_settings
from app.db.engine import create_engine
from app.db.corpus import document_hashes, load_chunks, load_parents
from app.ingest.corpus import RAW_DIR, CORPUS_COMMIT, document_id
from app.ingest.fetch import fetch_entries, git_blob_sha, tree_url
from app.ingest.pipeline import content_hash
from app.ingest.cleaner import clean_mdx
from app.ingest.chunker import chunk_document
from scripts.fetch_docs import fetch_bytes


async def main():
    entries = fetch_entries(fetch_bytes)
    local = {}
    expected_chunks = {}
    expected_parents = {}
    for entry in entries:
        data = (RAW_DIR / entry.path).read_bytes()
        assert git_blob_sha(data) == entry.sha, entry.path
        doc = document_id(entry.path)
        local[doc] = content_hash(data)
        cleaned = clean_mdx(data.decode("utf-8"), path=doc)
        split = chunk_document(cleaned.title, cleaned.markdown)
        for p in split.parents:
            expected_parents[f"{doc}#p{p.ordinal}"] = (doc, p.heading_path, p.text)
        for c in split.children:
            expected_chunks[f"{doc}#c{c.ordinal}"] = (doc, f"{doc}#p{c.parent_ordinal}", c.heading_path, c.text)
    engine = create_engine(get_settings())
    try:
        async with engine.connect() as conn:
            assert await document_hashes(conn) == local
            actual_chunks = await load_chunks(conn)
            actual_parents = await load_parents(conn, sorted(expected_parents))
        assert {c.id: (c.document_id, c.parent_id, c.heading_path, c.text) for c in actual_chunks} == expected_chunks
        assert {i: (p.document_id, p.heading_path, p.text) for i, p in actual_parents.items()} == expected_parents
    finally:
        await engine.dispose()
    report = {"source": tree_url(), "commit": CORPUS_COMMIT,
        "public_github_blob_hashes_match": len(entries), "database_documents_match": len(local),
        "database_chunks_match": len(expected_chunks), "database_parents_match": len(expected_parents),
        "model_calls": 0, "database_writes": 0,
        "outbound_experiment_inputs": "仅本仓库CC BY 4.0开发题与上述公开Dify语料，以及现有固定提示词",
        "model_destination": "https://api.deepseek.com/chat/completions",
        "authorization": "作者2026-10-22要求实际跑消融；AGENTS.md权限表允许每日10元内真实调用DeepSeek"}
    (Path(__file__).parent / "public-source-audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


asyncio.run(main())
