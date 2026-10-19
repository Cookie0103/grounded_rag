"""把清洗后的语料分成几份 Markdown，给作者上传到 Gemini 网页端出题：`uv run poe export-for-gemini`。

输出到 .cache/gemini-pack/part-NN.md，每份不超过 MAX_CHARS 个字符；每篇文档前有「文档 ID」行，
出题时 gold_docs 必须原样使用这个 ID。
"""

import sys
from pathlib import Path

from app.core.config import CACHE_DIR
from app.ingest.cleaner import clean_mdx
from app.ingest.corpus import RAW_DIR, document_id, list_raw_files

OUTPUT_DIR = CACHE_DIR / "gemini-pack"
MAX_CHARS = 400_000


def render_documents(raw_dir: Path) -> list[str]:
    documents: list[str] = []
    for path in list_raw_files(raw_dir):
        doc_id = document_id(path.relative_to(raw_dir).as_posix())
        cleaned = clean_mdx(path.read_text(encoding="utf-8"), path=doc_id)
        documents.append(f"\n\n=====\n文档 ID：{doc_id}\n\n# {cleaned.title}\n\n{cleaned.markdown}")
    return documents


def split_parts(documents: list[str], max_chars: int = MAX_CHARS) -> list[str]:
    """按文档顺序装箱，一篇文档不拆开。"""
    parts: list[str] = []
    current = ""
    for document in documents:
        if current and len(current) + len(document) > max_chars:
            parts.append(current)
            current = ""
        current += document
    if current:
        parts.append(current)
    return parts


def main() -> None:
    parts = split_parts(render_documents(RAW_DIR))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUTPUT_DIR.glob("part-*.md"):
        old.unlink()
    for number, text in enumerate(parts, start=1):
        (OUTPUT_DIR / f"part-{number:02d}.md").write_text(text, encoding="utf-8", newline="\n")
    sys.stdout.write(f"已写出 {len(parts)} 份到 {OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()
