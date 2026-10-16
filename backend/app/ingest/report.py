"""入库后的数据报告：给作者看的一页 Markdown。"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import CHILD_MAX_CHARS, INGEST_VERSION
from app.db.corpus import CorpusOverview, NearestChunk, nearest_chunks
from app.ingest.pipeline import IngestStats
from app.providers.base import Embedder

TOP_K = 5

# (查询, 预期命中的文档 ID 或前缀)。报告里只陈述实际结果和是否命中，判断交给作者。
CHECK_QUERIES: list[tuple[str, tuple[str, ...]]] = [
    (
        "知识库单次最多上传几个文件",
        ("self-host/use-dify/knowledge/create-knowledge/import-text-data/readme",),
    ),
    (
        "怎么修改上传文件的大小限制",
        (
            "self-host/use-dify/knowledge/create-knowledge/import-text-data/readme",
            "self-host/deploy/configuration/environments",
        ),
    ),
    ("云版本怎么查看应用的监控数据", ("cloud/use-dify/monitor/",)),
]


@dataclass(frozen=True)
class CheckResult:
    query: str
    expected: tuple[str, ...]
    found: list[NearestChunk]

    @property
    def hit(self) -> bool:
        return any(
            chunk.document_id.startswith(prefix) for chunk in self.found for prefix in self.expected
        )


@dataclass(frozen=True)
class ReportMeta:
    commit: str
    model: str
    started_at: datetime
    total_seconds: float


async def run_checks(engine: AsyncEngine, embedder: Embedder) -> list[CheckResult]:
    results: list[CheckResult] = []
    vectors = await embedder.embed_queries([query for query, _ in CHECK_QUERIES])
    for (query, expected), vector in zip(CHECK_QUERIES, vectors, strict=True):
        async with engine.connect() as connection:
            found = await nearest_chunks(connection, vector, model=embedder.name, limit=TOP_K)
        results.append(CheckResult(query, expected, found))
    return results


def render_report(
    meta: ReportMeta, stats: IngestStats, overview: CorpusOverview, checks: list[CheckResult]
) -> str:
    sections = [
        _header(meta, stats),
        _documents(stats, overview),
        _chunks(overview),
        _cleaning(stats),
        _checks(checks),
    ]
    return "\n\n".join(sections) + "\n"


def _header(meta: ReportMeta, stats: IngestStats) -> str:
    speed = stats.embedded_chunks / stats.embed_seconds if stats.embed_seconds else 0.0
    return "\n".join(
        [
            "# 入库数据报告",
            "",
            f"- 时间：{meta.started_at:%Y-%m-%d %H:%M:%S}",
            f"- 语料 commit：`{meta.commit}`",
            f"- INGEST_VERSION：`{INGEST_VERSION}`",
            f"- 嵌入模型：`{meta.model}`",
            f"- 总耗时：{meta.total_seconds:.1f} 秒",
            f"- 本次嵌入：{stats.embedded_chunks} 个子块，{stats.embed_seconds:.1f} 秒"
            f"（{speed:.1f} 块/秒）",
        ]
    )


def _documents(stats: IngestStats, overview: CorpusOverview) -> str:
    lines = [
        "## 文档",
        "",
        f"- 库里共 {overview.counts['documents']} 篇；本次 新增 {stats.added} / 变化 "
        f"{stats.changed} / 未变 {stats.unchanged} / 删除 {stats.removed}",
        "",
        "| 版本 | 篇数 |",
        "|---|---|",
        *[f"| {name} | {count} |" for name, count in overview.documents_by_edition.items()],
        "",
        "| 类别 | 篇数 |",
        "|---|---|",
        *[f"| {name} | {count} |" for name, count in overview.documents_by_category.items()],
    ]
    return "\n".join(lines)


def _chunks(overview: CorpusOverview) -> str:
    counts = overview.counts
    lines = [
        "## 块",
        "",
        f"- 父块 {counts['parent_chunks']}，子块 {counts['chunks']}，"
        f"向量 {counts['chunk_embeddings']}",
        f"- 子块长度（字）：最小 {overview.chunk_length_min} / 中位 {overview.chunk_length_p50} / "
        f"p95 {overview.chunk_length_p95} / 最大 {overview.chunk_length_max}",
        "",
        f"最长的 10 个子块（上限 {CHILD_MAX_CHARS}；超过的应当只有代码块和表格）：",
        "",
        "| 子块 | 字数 | 开头 |",
        "|---|---|---|",
        *[
            f"| `{chunk.chunk_id}` | {chunk.length} | {_one_line(chunk.preview)} |"
            for chunk in overview.longest_chunks
        ],
    ]
    return "\n".join(lines)


def _one_line(text: str) -> str:
    """表格单元格里不能有换行和竖线。"""
    return " ".join(text.split()).replace("|", "/")


def _cleaning(stats: IngestStats) -> str:
    unknown = dict(stats.unknown_components) or "无"
    return "\n".join(
        ["## 清洗", "", f"- 未知组件：{unknown}", f"- 残留标签数：{stats.residual_tags}（应为 0）"]
    )


def _checks(checks: list[CheckResult]) -> str:
    lines = ["## 检查查询（只用向量检索，前 5 个子块）"]
    for check in checks:
        expected = "、".join(f"`{item}`" for item in check.expected)
        lines += [
            "",
            f"### {check.query}",
            "",
            f"预期命中：{expected} → {'命中' if check.hit else '**没命中**'}",
            "",
            "| 距离 | 文档 | 标题路径 |",
            "|---|---|---|",
            *[
                f"| {chunk.distance:.3f} | `{chunk.document_id}` | {chunk.heading_path} |"
                for chunk in check.found
            ],
        ]
    return "\n".join(lines)
