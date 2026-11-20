"""把已保存的 HTML、PDF 和 Markdown 转为现有切块器的输入。"""

import re
from pathlib import Path

from bs4 import BeautifulSoup
from bs4.element import Comment, NavigableString, PageElement, Tag
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.errors import CorpusError
from app.ingest.cleaner import CleanDocument

_FRONT_MATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
_HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")
_PARAGRAPHS = {"p", "dt", "dd", "blockquote", "figcaption", "summary"}
_BLOCKS = {
    *_HEADINGS,
    *_PARAGRAPHS,
    "table",
    "ol",
    "ul",
    "article",
    "section",
    "div",
    "aside",
    "details",
    "figure",
    "dl",
}
_IGNORED = "nav, header, footer, script, style, noscript, template, iframe, button, [hidden]"
_MAX_TABLE_SPAN = 32


def load_source(path: Path) -> CleanDocument:
    """从本地文件加载正文和标题。"""
    suffix = path.suffix.lower()
    if suffix == ".html":
        title, markdown = _load_html(path)
    elif suffix == ".pdf":
        title, markdown = _load_pdf(path)
    elif suffix == ".md":
        title, markdown = _load_markdown(path)
    else:
        raise CorpusError(f"不支持的语料格式：{suffix}")
    if not markdown.strip():
        raise CorpusError(f"语料没有可提取的正文：{path.name}")
    return CleanDocument(title or path.stem, None, markdown.strip(), [])


def _load_html(path: Path) -> tuple[str, str]:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    content = soup.find("main") or soup.find("article") or soup.body
    if content is None:
        return "", ""
    for tag in content.select(_IGNORED):
        if tag.parent is not None:
            tag.decompose()
    page_title = _text(soup.title).partition("｜")[0].strip() if soup.title else ""
    heading = content.find("h1")
    if heading is not None:
        title = _text(heading)
        heading.decompose()
    else:
        title = page_title
    if title == "よくあるご質問" and page_title:
        title = page_title
    return title, "\n\n".join(_container(content))


def _text(node: PageElement) -> str:
    return " ".join(node.get_text().split())


def _container(tag: Tag) -> list[str]:
    blocks: list[str] = []
    pending: list[str] = []
    for child in tag.children:
        if isinstance(child, Tag) and child.name in _BLOCKS:
            _flush_inline(pending, blocks)
            blocks.extend(_block(child))
        elif isinstance(child, Tag):
            pending.append(" " if child.name == "br" else child.get_text())
        elif isinstance(child, NavigableString) and not isinstance(child, Comment):
            pending.append(str(child))
    _flush_inline(pending, blocks)
    return blocks


def _flush_inline(pending: list[str], blocks: list[str]) -> None:
    normalized = " ".join("".join(pending).split())
    if normalized:
        blocks.append(normalized)
    pending.clear()


def _block(tag: Tag) -> list[str]:
    if tag.name == "table":
        table = _table(tag)
        return [table] if table else []
    if tag.name in ("ul", "ol"):
        items = [_text(item) for item in tag.find_all("li", recursive=False)]
        formatted = "\n".join(f"- {item}" for item in items if item)
        return [formatted] if formatted else []
    if tag.name in _HEADINGS:
        content = _text(tag)
        level = _HEADINGS.index(tag.name) + 1
        return [f"{'#' * level} {content}"] if content else []
    if tag.name in _PARAGRAPHS:
        text = _text(tag)
        return [text] if text else []
    return _container(tag)


def _table(tag: Tag) -> str:
    grid: dict[tuple[int, int], str] = {}
    rows = [row for row in tag.find_all("tr") if row.find_parent("table") is tag]
    for row_number, row in enumerate(rows):
        column = 0
        for cell in row.find_all(("th", "td"), recursive=False):
            while (row_number, column) in grid:
                column += 1
            _place_cell(grid, row_number, column, cell)
            column += _span(cell, "colspan")
    if not grid:
        return ""
    width = max(column for _, column in grid) + 1
    lines = [
        "| " + " | ".join(grid.get((row, column), "") for column in range(width)) + " |"
        for row in range(len(rows))
    ]
    lines.insert(1, "| " + " | ".join(["---"] * width) + " |")
    return "\n".join(lines)


def _place_cell(grid: dict[tuple[int, int], str], row: int, column: int, cell: Tag) -> None:
    content = _text(cell).replace("|", "｜")
    grid.update(
        {
            (y, x): content
            for y in range(row, row + _span(cell, "rowspan"))
            for x in range(column, column + _span(cell, "colspan"))
        }
    )


def _span(cell: Tag, attribute: str) -> int:
    raw = cell.get(attribute)
    if isinstance(raw, str) and re.fullmatch(r"[0-9]{1,2}", raw):
        return max(1, min(_MAX_TABLE_SPAN, int(raw)))
    return 1


def _load_pdf(path: Path) -> tuple[str, str]:
    try:
        with path.open("rb") as stream:
            pdf = PdfReader(stream)
            title = pdf.metadata.title if pdf.metadata else None
            pages = [page.extract_text().strip() for page in pdf.pages]
    except PdfReadError as error:
        raise CorpusError(f"PDF 无法解析：{path.name}") from error
    markdown = "\n\n".join(
        f"## {number} ページ\n\n{text}" for number, text in enumerate(pages, 1) if text
    )
    return title or "", markdown


def _load_markdown(path: Path) -> tuple[str, str]:
    markdown = _FRONT_MATTER.sub("", path.read_text(encoding="utf-8"), count=1).strip()
    heading, _, body = markdown.partition("\n")
    if heading.startswith("# "):
        return heading[2:].strip(), body.strip()
    return path.stem, markdown
