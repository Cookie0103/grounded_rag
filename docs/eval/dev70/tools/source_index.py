"""用生产清洗、切块实现建立冻结语料索引；不读题集，不访问数据库。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path


def repository_root() -> Path:
    """不依赖cwd或工具所在层数，只认同时含项目实现与规则文件的父目录。"""
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "backend/app").is_dir() and (candidate / "AGENTS.md").is_file():
            return candidate
    raise RuntimeError("无法找到同时含 backend/app 和 AGENTS.md 的仓库根目录")


ROOT = repository_root()
sys.path.insert(0, str(ROOT / "backend"))
from app.ingest.chunker import chunk_document
from app.ingest.cleaner import clean_mdx
from app.ingest.corpus import CORPUS_COMMIT, category_of, edition_of, is_corpus_path

INDEX_PATH = ROOT / ".cache/dev70-completion/corpus-index.json"
RAW_ROOT = ROOT / "data/raw/dify-docs" / CORPUS_COMMIT


def sha256(value: bytes | str) -> str:
    return hashlib.sha256(
        value.encode("utf-8") if isinstance(value, str) else value
    ).hexdigest()


def low_coverage_group(doc_id: str) -> str | None:
    """作者指定目录的精确路径映射；不把整个 build 目录泛算为插件/模型。"""
    prefixes = {
        "self-host/deploy/": "部署配置",
        "self-host/use-dify/publish/": "应用发布",
        "cloud/use-dify/workspace/": "工作空间管理",
        "self-host/use-dify/workspace/": "工作空间管理",
        "api-reference/guides/": "API参考",
    }
    explicit = {
        "cloud/use-dify/workspace/subscription-management": "云版计费",
        "cloud/use-dify/workspace/model-providers": "模型接入",
        "self-host/use-dify/workspace/model-providers": "模型接入",
        "cloud/use-dify/workspace/plugins": "插件",
        "self-host/use-dify/workspace/plugins": "插件",
    }
    if doc_id in explicit:
        return explicit[doc_id]
    return next(
        (name for prefix, name in prefixes.items() if doc_id.startswith(prefix)), None
    )


def headings(markdown: str) -> list[dict]:
    result = []
    fence = None
    for line_number, line in enumerate(markdown.splitlines(), 1):
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            if fence is None:
                fence = marker[1]
            elif marker[1][0] == fence[0] and len(marker[1]) >= len(fence):
                fence = None
            continue
        found = re.match(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if fence is None and found:
            result.append(
                {"level": len(found[1]), "text": found[2], "cleaned_line": line_number}
            )
    return result


def build_index(raw_root: Path = RAW_ROOT) -> dict:
    docs = {}
    for path in sorted(
        raw_root.rglob("*.mdx"), key=lambda p: p.relative_to(raw_root).as_posix()
    ):
        relative = path.relative_to(raw_root).as_posix()
        if not is_corpus_path(relative):
            continue
        doc_id = relative.removeprefix("zh/").removesuffix(".mdx")
        raw_bytes = path.read_bytes()
        raw = raw_bytes.decode("utf-8").replace("\r\n", "\n")
        cleaned = clean_mdx(raw, path=relative)
        chunked = chunk_document(cleaned.title, cleaned.markdown)
        parents = [
            {
                **asdict(p),
                "parent_id": f"{doc_id}#p{p.ordinal}",
                "sha256": sha256(p.text),
            }
            for p in chunked.parents
        ]
        children = [
            {
                **asdict(c),
                "chunk_id": f"{doc_id}#c{c.ordinal}",
                "parent_id": f"{doc_id}#p{c.parent_ordinal}",
                "sha256": sha256(c.text),
            }
            for c in chunked.children
        ]
        docs[doc_id] = {
            "document_id": doc_id,
            "frozen_path": path.relative_to(ROOT).as_posix(),
            "source_file_sha256": sha256(raw_bytes),
            "raw_text": raw,
            "raw_line_count": len(raw.splitlines()),
            "title": cleaned.title,
            "description": cleaned.description,
            "headings": headings(cleaned.markdown),
            "cleaned_markdown": cleaned.markdown,
            "cleaned_characters": len(cleaned.markdown),
            "cleaned_sha256": sha256(cleaned.markdown),
            "parents": parents,
            "children": children,
            "edition": edition_of(doc_id),
            "category": category_of(doc_id),
            "directory": doc_id.rsplit("/", 1)[0] if "/" in doc_id else ".",
            "low_coverage_group": low_coverage_group(doc_id),
        }
    implementations = {
        name: sha256((ROOT / "backend/app/ingest" / name).read_bytes())
        for name in ("cleaner.py", "chunker.py", "corpus.py")
    }
    return {
        "corpus_commit": CORPUS_COMMIT,
        "method": "直接调用 app.ingest.cleaner.clean_mdx 与 chunk_document；未访问数据库",
        "implementation_sha256": implementations,
        "document_count": len(docs),
        "documents": docs,
    }


def distribution(index: dict) -> dict:
    docs = index["documents"]
    long = [
        {
            "document_id": doc_id,
            "title": d["title"],
            "cleaned_characters": d["cleaned_characters"],
            "parents": len(d["parents"]),
            "children": len(d["children"]),
        }
        for doc_id, d in docs.items()
        if d["cleaned_characters"] >= 6000
    ]
    return {
        "corpus_commit": index["corpus_commit"],
        "document_count": len(docs),
        "implementation_sha256": index["implementation_sha256"],
        "parent_count": sum(len(d["parents"]) for d in docs.values()),
        "child_count": sum(len(d["children"]) for d in docs.values()),
        "cleaned_characters": sum(d["cleaned_characters"] for d in docs.values()),
        "by_directory": dict(
            sorted(Counter(d["directory"] for d in docs.values()).items())
        ),
        "by_category": dict(
            sorted(Counter(d["category"] for d in docs.values()).items())
        ),
        "by_edition": dict(
            sorted(Counter(d["edition"] for d in docs.values()).items())
        ),
        "long_document_minimum_characters": 6000,
        "long_documents": sorted(
            long, key=lambda d: (-d["cleaned_characters"], d["document_id"])
        ),
        "low_coverage_mapping_note": "部署/发布/工作空间/API按明确路径计数；插件/模型/云版计费仅列精确文档；build不泛计",
        "low_coverage_documents": [
            {"document_id": k, "group": d["low_coverage_group"]}
            for k, d in docs.items()
            if d["low_coverage_group"]
        ],
        "documents": [
            {
                "document_id": k,
                "title": d["title"],
                "directory": d["directory"],
                "category": d["category"],
                "cleaned_characters": d["cleaned_characters"],
                "parent_count": len(d["parents"]),
                "child_count": len(d["children"]),
                "source_file_sha256": d["source_file_sha256"],
            }
            for k, d in docs.items()
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=INDEX_PATH)
    parser.add_argument(
        "--distribution",
        type=Path,
        default=ROOT / "docs/eval/dev70/corpus-distribution.json",
    )
    args = parser.parse_args()
    index = build_index()
    summary = distribution(index)
    for path, data in ((args.index, index), (args.distribution, summary)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: summary[k]
                for k in (
                    "document_count",
                    "parent_count",
                    "child_count",
                    "cleaned_characters",
                )
            },
            ensure_ascii=False,
        )
    )
    print(
        json.dumps(
            {
                "long_document_count": len(summary["long_documents"]),
                "index": str(args.index),
                "distribution": str(args.distribution),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
