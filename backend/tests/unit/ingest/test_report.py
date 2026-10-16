from collections import Counter
from datetime import datetime

import pytest

from app.db.corpus import CorpusOverview, LongestChunk, NearestChunk
from app.ingest import pipeline
from app.ingest.pipeline import IngestStats, content_hash
from app.ingest.report import CheckResult, ReportMeta, render_report


def _overview() -> CorpusOverview:
    return CorpusOverview(
        counts={"documents": 182, "parent_chunks": 1256, "chunks": 2090, "chunk_embeddings": 2090},
        documents_by_edition={"cloud": 45, "common": 29, "self_host": 108},
        documents_by_category={"knowledge": 66, "deploy": 14},
        chunk_length_min=3,
        chunk_length_p50=261,
        chunk_length_p95=467,
        chunk_length_max=1497,
        longest_chunks=[LongestChunk("a#c3", 1497, "```bash\n| 带竖线 |")],
    )


def _chunk(document_id: str, distance: float) -> NearestChunk:
    return NearestChunk(
        f"{document_id}#c0", document_id, f"{document_id}#p0", "标题 > 节", "正文", distance
    )


def test_report_has_all_sections_with_the_key_numbers() -> None:
    stats = IngestStats(
        added=182, embedded_chunks=2090, embed_seconds=20.0, unknown_components=Counter()
    )
    meta = ReportMeta("c80a318", "qwen3-embedding-0.6b", datetime(2026, 10, 16, 15, 0, 0), 31.5)
    checks = [
        CheckResult("怎么上传", ("learn/",), [_chunk("learn/x", 0.12)]),
        CheckResult("怎么监控", ("cloud/use-dify/monitor/",), [_chunk("learn/y", 0.5)]),
    ]

    report = render_report(meta, stats, _overview(), checks)

    assert report.startswith("# 入库数据报告")
    assert "库里共 182 篇；本次 新增 182 / 变化 0 / 未变 0 / 删除 0" in report
    assert "| self_host | 108 |" in report
    assert "最小 3 / 中位 261 / p95 467 / 最大 1497" in report
    assert "104.5 块/秒" in report
    assert "| `a#c3` | 1497 | ```bash / 带竖线 / |" in report  # 换行和竖线不会破坏表格
    assert "残留标签数：0（应为 0）" in report
    assert "未知组件：无" in report
    assert "预期命中：`learn/` → 命中" in report
    assert "预期命中：`cloud/use-dify/monitor/` → **没命中**" in report
    assert "| 0.120 | `learn/x` | 标题 > 节 |" in report


def test_report_lists_unknown_components() -> None:
    stats = IngestStats(unknown_components=Counter({"Mystery": 2}))
    meta = ReportMeta("c", "fake", datetime(2026, 1, 1), 1.0)

    assert "{'Mystery': 2}" in render_report(meta, stats, _overview(), [])


def test_stats_document_total_counts_every_kind() -> None:
    assert IngestStats(added=1, changed=2, unchanged=3, removed=9).documents == 6


def test_content_hash_depends_on_both_the_file_and_the_ingest_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = content_hash(b"abc")
    assert first == content_hash(b"abc")
    assert first != content_hash(b"abd")

    monkeypatch.setattr(pipeline, "INGEST_VERSION", "2")
    assert content_hash(b"abc") != first
