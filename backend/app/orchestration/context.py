"""上下文组装与引用解析。"""

import re
from collections.abc import Sequence

from app.orchestration.models import Citation
from app.retrieval.retriever import ParentContext

MAX_CONTEXT_CHARS = 12000
MIN_USEFUL_CHARS = 200
CITATION = re.compile(r"\[(\d+)\]")


def assemble(parents: Sequence[ParentContext]) -> tuple[list[Citation], str]:
    """父块去重（按 id，保持原有顺序），编号，按字数预算截断。返回引用表和给模型的文本。"""
    seen: set[str] = set()
    citations: list[Citation] = []
    blocks: list[str] = []
    used = 0
    for parent in parents:
        if parent.id in seen:
            continue
        seen.add(parent.id)
        room = MAX_CONTEXT_CHARS - used
        if blocks and room < MIN_USEFUL_CHARS:
            break
        index = len(citations) + 1
        header = f"[{index}] 文档：{parent.document_id}｜{parent.heading_path}\n"
        body = (
            parent.text[: max(room - len(header), 0)]
            if used + len(parent.text) > MAX_CONTEXT_CHARS
            else parent.text
        )
        blocks.append(header + body)
        citations.append(
            Citation(index=index, document_id=parent.document_id, heading_path=parent.heading_path)
        )
        used += len(header) + len(body)
    return citations, "\n\n---\n\n".join(blocks)


def resolve_citations(answer: str, citations: Sequence[Citation]) -> tuple[str, list[Citation]]:
    """回答里编号不存在的引用去掉；返回清理后的回答和真正被引用的条目（按编号）。"""
    valid = {citation.index: citation for citation in citations}

    def keep(match: re.Match[str]) -> str:
        return match.group(0) if int(match.group(1)) in valid else ""

    cleaned = CITATION.sub(keep, answer)
    used = sorted({int(number) for number in CITATION.findall(cleaned)})
    return cleaned, [valid[number] for number in used]
