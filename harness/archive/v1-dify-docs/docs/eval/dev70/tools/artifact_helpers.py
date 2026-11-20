"""证据构建工具：只接受可逐字定位到冻结原文、生产子块和父块的片段。"""

from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path

from source_index import CORPUS_COMMIT, INDEX_PATH, ROOT, clean_mdx


class EvidenceError(ValueError):
    pass


def load_index(path: str | Path = INDEX_PATH) -> dict:
    return json.loads(Path(path).read_text())


def locate_evidence(
    document_id: str, original_excerpt: str, *, index: dict | None = None,
    cleaned_excerpt: str | None = None, raw_line_start: int | None = None,
    chunk_id: str | None = None,
) -> dict:
    """定位一个证据叶子。原文重复时必须给 raw_line_start；跨子块则缩小 excerpt 或拆 all_of。"""
    index = index or load_index()
    docs = index["documents"]
    if document_id not in docs:
        raise EvidenceError(f"不在冻结语料：{document_id}")
    if not original_excerpt.strip():
        raise EvidenceError("original_excerpt 不可为空")
    doc = docs[document_id]
    raw = doc["raw_text"]
    matches = []
    start = 0
    while (found := raw.find(original_excerpt, start)) >= 0:
        line = raw.count("\n", 0, found) + 1
        if raw_line_start is None or line == raw_line_start:
            matches.append(found)
        start = found + 1
    if len(matches) != 1:
        raise EvidenceError(f"原文精确匹配需唯一，实得 {len(matches)} 处；{document_id}（可用 raw_line_start 消歧）")
    raw_start = matches[0]
    first = raw.count("\n", 0, raw_start) + 1
    last = raw.count("\n", 0, raw_start + len(original_excerpt) - 1) + 1
    if cleaned_excerpt is None:
        cleaned_excerpt = original_excerpt if original_excerpt in doc["cleaned_markdown"] else clean_mdx(
            "---\ntitle: 证据临时清洗\n---\n" + original_excerpt).markdown
    if not cleaned_excerpt or cleaned_excerpt not in doc["cleaned_markdown"]:
        raise EvidenceError(f"清洗片段未精确出现在文档，请显式给 cleaned_excerpt：{document_id}")
    candidates = [c for c in doc["children"] if cleaned_excerpt in c["text"]
                  and (chunk_id is None or c["chunk_id"] == chunk_id)]
    if not candidates:
        raise EvidenceError(f"没有子块完整包含片段（可能跨子块）；不得伪造 chunk：{document_id}")
    child = candidates[0]
    parent = doc["parents"][child["parent_ordinal"]]
    if cleaned_excerpt not in parent["text"]:
        raise EvidenceError(f"父块未包含片段：{parent['parent_id']}")
    offset = doc["cleaned_markdown"].find(cleaned_excerpt)
    return {
        "document_id": document_id, "heading_path": child["heading_path"],
        "source_url": f"https://github.com/langgenius/dify-docs/blob/{CORPUS_COMMIT}/zh/{document_id}.mdx#L{first}-L{last}",
        "frozen_path": doc["frozen_path"], "raw_line_start": first, "raw_line_end": last,
        "original_excerpt": original_excerpt,
        "direct_evidence": {"chunk_id": child["chunk_id"], "excerpt": cleaned_excerpt, "contains_excerpt": True},
        "supporting_parent": {"parent_id": parent["parent_id"], "heading_path": parent["heading_path"], "contains_excerpt": True},
        "cleaned_character_offset": offset,
        "within_current_judge_first_12000_chars": offset + len(cleaned_excerpt) <= 12000,
        "database_verified": False, "verification_method": "冻结文件+生产clean_mdx/chunk_document，本机重建；未查询数据库",
        "source_file_sha256": doc["source_file_sha256"],
    }


def any_of(*sources: dict) -> dict:
    if not sources:
        raise EvidenceError("any_of 至少一个来源")
    return {"any_of": list(sources)}


def nugget_evidence(nugget_index: int, text: str, importance: str, *required_groups: dict) -> dict:
    if not required_groups or any(not x.get("any_of") for x in required_groups):
        raise EvidenceError("all_of 的每一组都需要非空 any_of 来源")
    return {"nugget_index": nugget_index, "text": text, "importance": importance,
            "all_of": list(required_groups)}


def compare_twins(document_id: str, *, index: dict | None = None) -> tuple[str, dict]:
    """产出兼容现有 twin-comparisons.json 的逐字符比较，内容差异不等于答案差异。"""
    index = index or load_index()
    if document_id.startswith("cloud/"):
        cloud, self_host = document_id, document_id.replace("cloud/", "self-host/", 1)
    elif document_id.startswith("self-host/"):
        cloud, self_host = document_id.replace("self-host/", "cloud/", 1), document_id
    else:
        raise EvidenceError("不是cloud/self-host孪生路径")
    if cloud not in index["documents"] or self_host not in index["documents"]:
        raise EvidenceError(f"冻结语料不含完整孪生：{cloud} / {self_host}")
    a, b = index["documents"][cloud], index["documents"][self_host]
    raw_a, raw_b = a["raw_text"], b["raw_text"]
    operations = [{"operation": op, "a_start": a0, "a_end": a1, "b_start": b0, "b_end": b1,
                   "a_text": raw_a[a0:a1], "b_text": raw_b[b0:b1]}
                  for op, a0, a1, b0, b1 in difflib.SequenceMatcher(None, raw_a, raw_b, autojunk=False).get_opcodes() if op != "equal"]
    return f"{cloud} <=> {self_host}", {
        "documents": [cloud, self_host], "raw_text_identical": raw_a == raw_b,
        "raw_bytes_identical": a["source_file_sha256"] == b["source_file_sha256"],
        "cleaned_text_identical": a["cleaned_markdown"] == b["cleaned_markdown"],
        "raw_sha256": {cloud: a["source_file_sha256"], self_host: b["source_file_sha256"]},
        "character_diff": operations,
        "cleaned_unified_diff": list(difflib.unified_diff(a["cleaned_markdown"].splitlines(), b["cleaned_markdown"].splitlines(), fromfile=cloud, tofile=self_host, lineterm="")),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document_id")
    parser.add_argument("--excerpt")
    parser.add_argument("--excerpt-file", type=Path)
    parser.add_argument("--cleaned-excerpt")
    parser.add_argument("--raw-line-start", type=int)
    parser.add_argument("--chunk-id")
    parser.add_argument("--index", type=Path, default=INDEX_PATH)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    excerpt = args.excerpt_file.read_text().rstrip("\n") if args.excerpt_file else args.excerpt
    if excerpt is None:
        parser.error("必须给 --excerpt 或 --excerpt-file")
    result = locate_evidence(args.document_id, excerpt, index=load_index(args.index),
                             cleaned_excerpt=args.cleaned_excerpt, raw_line_start=args.raw_line_start,
                             chunk_id=args.chunk_id)
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(output)
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
