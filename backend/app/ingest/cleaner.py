"""mdx → 干净的 Markdown：去掉 JSX 组件、图片、链接地址、翻译声明，保留文字结构。

流程：解析 front matter → 把代码块和行内代码换成占位符 → 去注释、整块删除无文字价值的元素、
转换 HTML 表格 → 按行处理组件标签（组件内容缩进要还原）→ 去图片 / 链接地址 → 还原代码。
"""

import re
from dataclasses import dataclass
from typing import Any

import yaml

from app.core.errors import CorpusError

ADMONITIONS = {
    "Note": "注意",
    "Tip": "提示",
    "Info": "说明",
    "Warning": "警告",
    "Danger": "危险",
    "Check": "确认",
    "Callout": "说明",
}
TITLED_COMPONENTS = {"Tab", "Accordion", "Card"}
STRIPPED_COMPONENTS = {
    "Tabs",
    "CardGroup",
    "AccordionGroup",
    "Columns",
    "Column",
    "CodeGroup",
    "Badge",
}
STEP_COMPONENTS = {"Steps", "Step"}
KNOWN_COMPONENTS = set(ADMONITIONS) | TITLED_COMPONENTS | STRIPPED_COMPONENTS | STEP_COMPONENTS
HTML_TAGS = {
    "div", "span", "p", "br", "a", "img", "ul", "ol", "li", "table", "thead", "tbody", "tr",
    "th", "td", "strong", "em", "b", "i", "u", "h1", "h2", "h3", "h4", "h5", "h6", "video",
    "iframe", "input", "form", "label", "button", "textarea", "details", "summary", "section",
    "center", "hr", "sup", "sub", "small",
}  # fmt: skip
CONTAINER_HTML = {"div", "ul", "ol", "section", "center", "details", "p"}  # 内容有缩进的块级 HTML

TRANSLATION_NOTICE = "> 本文档由 AI 自动翻译"

_TAG = re.compile(r"<(/?)([A-Za-z][A-Za-z0-9]*)((?:\s[^<>]*?)?)(/?)>")
_FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})")
_INLINE_CODE = re.compile(r"(`+)(.+?)\1")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
_MDX_COMMENT = re.compile(r"\{/\*.*?\*/\}", re.S)
_FRAME = re.compile(r"<Frame(\s[^<>]*)?>.*?</Frame>", re.S)
_PAIRED_DROPPED = re.compile(r"<(style|video|iframe)\b[^<>]*>.*?</\1>", re.S)
_HTML_TABLE = re.compile(r"^([ \t]*)<table\b[^<>]*>.*?</table>", re.S | re.M)
_ROW = re.compile(r"<tr\b[^<>]*>(.*?)</tr>", re.S)
_CELL = re.compile(r"<(th|td)\b[^<>]*>(.*?)</\1>", re.S)
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_BLANK_RUN = re.compile(r"\n{3,}")
_PLACEHOLDER = re.compile(r"\x00([CI])(\d+)\x00")
_RESIDUAL = re.compile(
    r"</?(?:[A-Z][A-Za-z0-9]*|" + "|".join(sorted(HTML_TAGS)) + r")(?:\s[^<>]*)?/?>"
)
_BREAK = "\x02"  # <br> 的临时标记：表格行里换成空格，其他地方换成换行
_ITEM_START = "\x03"  # <li> 的开始 / 结束标记：表格里用「；」连接，其他地方变成「- 」
_ITEM_END = "\x04"
_ITEM_MARKERS = (_ITEM_START, _ITEM_END)
_FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.S)


@dataclass(frozen=True)
class CleanDocument:
    title: str
    description: str | None
    markdown: str
    unknown_components: list[str]


# ---------------------------------------------------------------- 入口


def clean_mdx(raw: str, *, path: str = "") -> CleanDocument:
    meta, body = _split_front_matter(raw, path)
    title = meta.get("title")
    if not isinstance(title, str) or not title.strip():
        raise CorpusError(f"front matter 缺少 title：{path}")
    description = meta.get("description")

    text = "\n".join(
        line for line in body.replace("\r\n", "\n").split("\n") if not _is_translation_notice(line)
    )
    masked, fences, inlines = _mask_code(text)
    masked = _drop_noise(masked)
    converter = _Converter(_closing_names(masked))
    for line in _join_multiline_tags(masked).split("\n"):
        converter.feed(line)
    cleaned = _squeeze_table_padding(_strip_images_and_links("\n".join(converter.lines)))
    markdown = _restore_code(cleaned, fences, inlines)
    return CleanDocument(
        title=title.strip(),
        description=description.strip() if isinstance(description, str) else None,
        markdown=_collapse_blank_lines(markdown),
        unknown_components=converter.unknown,
    )


def count_residual_tags(markdown: str) -> int:
    """代码以外还残留的 JSX / HTML 标签数；清洗后应为 0。"""
    masked, _, _ = _mask_code(markdown)
    return len(_RESIDUAL.findall(masked))


# ---------------------------------------------------------------- front matter


def _split_front_matter(raw: str, path: str) -> tuple[dict[str, Any], str]:
    text = raw.lstrip("﻿").replace("\r\n", "\n")
    match = _FRONT_MATTER.match(text)
    if not match:
        raise CorpusError(f"缺少 front matter：{path}")
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as error:
        raise CorpusError(f"front matter 不是合法的 YAML：{path}") from error
    if not isinstance(meta, dict):
        raise CorpusError(f"front matter 不是键值对：{path}")
    return meta, text[match.end() :]


def _is_translation_notice(line: str) -> bool:
    return line.startswith(TRANSLATION_NOTICE)


# ---------------------------------------------------------------- 代码保护


def _mask_code(text: str) -> tuple[str, list[tuple[int, list[str]]], list[str]]:
    """围栏代码块和行内代码换成占位符；围栏占位符独占一行并保留缩进。"""
    fences: list[tuple[int, list[str]]] = []
    out: list[str] = []
    block: list[str] | None = None
    fence_indent, marker = 0, ""
    for line in text.split("\n"):
        if block is None:
            opened = _FENCE.match(line)
            if opened:
                fence_indent, marker = len(opened.group(1)), opened.group(2)
                block = [line]
            else:
                out.append(line)
            continue
        block.append(line)
        closed = _FENCE.match(line)
        if closed and closed.group(2)[0] == marker[0] and len(closed.group(2)) >= len(marker):
            out.append(f"{' ' * fence_indent}\x00C{len(fences)}\x00")
            fences.append((fence_indent, block))
            block = None
    if block is not None:  # 没有闭合的围栏：到文末为止
        out.append(f"{' ' * fence_indent}\x00C{len(fences)}\x00")
        fences.append((fence_indent, block))

    inlines: list[str] = []

    def mask_inline(match: re.Match[str]) -> str:
        inlines.append(match.group(0))
        return f"\x00I{len(inlines) - 1}\x00"

    masked = "\n".join(_INLINE_CODE.sub(mask_inline, line) for line in out)
    return masked, fences, inlines


def _restore_code(text: str, fences: list[tuple[int, list[str]]], inlines: list[str]) -> str:
    def restore(match: re.Match[str]) -> str:
        kind, index = match.group(1), int(match.group(2))
        if kind == "I":
            return inlines[index]
        fence_indent, lines = fences[index]
        return "\n".join(lines) if fence_indent == 0 else _dedent_fence(text, match, lines)

    # 围栏占位符所在行的缩进可能被还原过，按新缩进给整个代码块减缩进
    return _PLACEHOLDER.sub(restore, text)


def _dedent_fence(text: str, match: re.Match[str], lines: list[str]) -> str:
    """组件内容缩进被还原后，占位符所在行的缩进变了；代码块的每一行减去同样多的缩进。"""
    line_start = text.rfind("\n", 0, match.start()) + 1
    new_indent = match.start() - line_start
    fence_indent = len(lines[0]) - len(lines[0].lstrip(" "))
    remove = max(fence_indent - new_indent, 0)
    restored = [
        line[min(remove, len(line) - len(line.lstrip(" "))) :] if index else line.lstrip(" ")
        for index, line in enumerate(lines)
    ]
    return "\n".join(restored)


# ---------------------------------------------------------------- 去噪与整块转换


def _drop_noise(text: str) -> str:
    text = _HTML_COMMENT.sub("", text)
    text = _MDX_COMMENT.sub("", text)
    text = _FRAME.sub(_frame_caption, text)
    text = _PAIRED_DROPPED.sub("", text)
    return _HTML_TABLE.sub(_html_table_to_markdown, text)


def _frame_caption(match: re.Match[str]) -> str:
    """Frame 里是图片，整个删除；有 caption 就保留说明文字。"""
    return _attribute(match.group(1) or "", "caption") or ""


def _html_table_to_markdown(match: re.Match[str]) -> str:
    indent = match.group(1)
    rows = [[_cell_text(cell) for _, cell in _CELL.findall(row)] for row in _ROW.findall(match[0])]
    rows = [row for row in rows if row]
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]
    lines = [f"| {' | '.join(padded[0])} |", f"|{'---|' * width}"]
    lines += [f"| {' | '.join(row)} |" for row in padded[1:]]
    # 前后各空一行，表格才不会和相邻的段落、标题连在一起
    return "\n" + "\n".join(f"{indent}{line}" for line in lines) + "\n"


def _cell_text(cell: str) -> str:
    """单元格里的列表项用「；」连接，其余标签去掉。"""
    cell = re.sub(r"<li\b[^<>]*>", "\x01", cell)
    cell = re.sub(r"<br\s*/?>", " ", cell)
    cell = re.sub(r"<[^<>]+>", "", cell)
    head, *items = cell.split("\x01")
    parts = [" ".join(head.split())] + [" ".join(item.split()) for item in items]
    lead = parts[0]
    joined = "；".join(item for item in parts[1:] if item)
    return " ".join(part for part in (lead, joined) if part).replace("|", "\\|")


def _attribute(attributes: str, name: str) -> str | None:
    """取属性值：支持 name="x"、name='x'、name={"x"} 三种写法。"""
    quoted = r"(?:\"([^\"]*)\"|'([^']*)'|\{\s*[\"']([^\"']*)[\"']\s*\})"
    match = re.search(rf"\b{name}\s*=\s*{quoted}", attributes)
    if not match:
        return None
    return next(group for group in match.groups() if group is not None)


# ---------------------------------------------------------------- 组件标签


def _join_multiline_tags(text: str) -> str:
    """属性跨行的标签合并成一行，后面按行处理才简单。"""
    return _TAG.sub(lambda match: re.sub(r"\s*\n\s*", " ", match[0]), text)


def _closing_names(text: str) -> set[str]:
    return {name for closing, name, _, _ in _TAG.findall(text) if closing}


@dataclass
class _Open:
    name: str
    raw_indent: int  # 开标签所在行的原始缩进
    block: bool  # 开标签独占一行
    strip: int | None  # 内容比开标签多缩进几格；块级组件在看到第一行内容时确定
    steps: int = 0  # Steps 里已经出现的 Step 数


class _Converter:
    """按行处理组件标签；用栈记住当前在哪些组件里，以便还原组件内容的缩进。"""

    def __init__(self, closing_names: set[str]) -> None:
        self._closing_names = closing_names
        self._stack: list[_Open] = []
        self._orphan_steps = 0
        self.lines: list[str] = []
        self.unknown: list[str] = []

    def feed(self, raw: str) -> None:
        if not raw.strip():
            self.lines.append("")
            return
        indent = len(raw) - len(raw.lstrip(" "))
        self._learn_strip(raw, indent)
        removed = min(sum(entry.strip or 0 for entry in self._stack), indent)
        self._emit(raw[removed:], indent - removed, raw_indent=indent)

    def _learn_strip(self, raw: str, indent: int) -> None:
        top = self._stack[-1] if self._stack else None
        if top is not None and top.block and top.strip is None:
            top.strip = 0 if raw.lstrip().startswith("</") else max(indent - top.raw_indent, 0)

    def _emit(self, line: str, indent: int, *, raw_indent: int) -> None:
        segments = self._split(line)
        has_tag = any(isinstance(segment, re.Match) for segment in segments)
        structural = has_tag and all(
            isinstance(segment, re.Match) or not segment.strip() for segment in segments
        )
        outputs = [
            self._tag(segment, raw_indent, block=structural)
            if isinstance(segment, re.Match)
            else segment
            for segment in segments
        ]
        prefix = " " * indent
        if structural:  # 只有标签的行：标签本身不输出，标记（如「注意：」）单独成行
            for segment, output in zip(segments, outputs, strict=True):
                if isinstance(segment, re.Match) and output.strip() and output not in _ITEM_MARKERS:
                    self._append_marker("" if output == _BREAK else f"{prefix}{output}")
            return
        text = "".join(outputs).rstrip()
        if text.strip():
            self.lines.append(self._finish_inline(text, prefix))

    @staticmethod
    def _finish_inline(text: str, prefix: str) -> str:
        """把 <br> 和 <li> 的临时标记换成最终写法：表格行必须保持单行，不能真的换行。"""
        if text.lstrip().startswith("|"):
            text = re.sub(f"{_BREAK}+", " ", text)
            text = text.replace(_ITEM_START, "").replace(_ITEM_END, "；")
            text = re.sub(r"；(?=\s*(?:\||$))", "", text)
            return re.sub(r"([。！？；])；", r"\1", text)
        text = text.replace(_ITEM_START, "- ").replace(_ITEM_END, "")
        return text.replace(_BREAK, f"\n{prefix}")

    def _append_marker(self, marker: str) -> None:
        """标记行（如「**注意：**」）前面空一行，让每个组件的内容自成一段。"""
        if marker and self.lines and self.lines[-1] != "":
            self.lines.append("")
        self.lines.append(marker)

    def _split(self, line: str) -> list[str | re.Match[str]]:
        """把一行拆成文字和标签；不是标签的尖括号（如 <your_token>）留在文字里。"""
        segments: list[str | re.Match[str]] = []
        position = 0
        for match in _TAG.finditer(line):
            if self._kind(match) == "literal":
                continue
            segments += [line[position : match.start()], match]
            position = match.end()
        segments.append(line[position:])
        return [segment for segment in segments if segment != ""]

    def _kind(self, match: re.Match[str]) -> str:
        closing, name, _, self_closing = match.groups()
        if name in HTML_TAGS:
            return "html"
        if name in KNOWN_COMPONENTS:  # 已知组件即使没写闭合标签也当组件处理
            return "component"
        if name[0].isupper() and (closing or self_closing or name in self._closing_names):
            return "component"
        return "literal"

    def _tag(self, match: re.Match[str], raw_indent: int, *, block: bool) -> str:
        """一个标签要输出的文字（多数标签什么都不输出）。"""
        closing, name, attributes, self_closing = match.groups()
        if self._kind(match) == "html":
            if name in CONTAINER_HTML and not self_closing:  # 和组件一样还原内容缩进
                if closing:
                    self._close(name)
                else:
                    self._push(name, raw_indent, block=block)
                return ""
            return self._html(name, closing=bool(closing))
        if closing:
            self._close(name)
            return ""
        if self_closing:
            return ""
        return self._open(name, attributes, raw_indent, block=block)

    @staticmethod
    def _html(name: str, *, closing: bool) -> str:
        if name == "br":
            return _BREAK
        if name == "li":
            return _ITEM_END if closing else _ITEM_START
        return ""

    def _close(self, name: str) -> None:
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index].name == name:
                del self._stack[index:]
                return

    def _push(self, name: str, raw_indent: int, *, block: bool) -> None:
        self._stack.append(_Open(name, raw_indent, block, None if block else 0))

    def _open(self, name: str, attributes: str, raw_indent: int, *, block: bool) -> str:
        if name not in KNOWN_COMPONENTS:
            self.unknown.append(name)
        label = self._label(name, attributes)
        self._push(name, raw_indent, block=block)
        return label if block or not label else f"{label} "

    def _label(self, name: str, attributes: str) -> str:
        if name in ADMONITIONS:
            return f"**{ADMONITIONS[name]}：**"
        if name in TITLED_COMPONENTS:
            title = _attribute(attributes, "title")
            return f"**{title}**" if title else ""
        if name == "Step":
            return self._step_label(_attribute(attributes, "title"))
        return ""

    def _step_label(self, title: str | None) -> str:
        parent = next((entry for entry in reversed(self._stack) if entry.name == "Steps"), None)
        if parent is None:
            self._orphan_steps += 1
            number = self._orphan_steps
        else:
            parent.steps += 1
            number = parent.steps
        return f"**步骤 {number}：{title}**" if title else f"**步骤 {number}**"


# ---------------------------------------------------------------- 收尾


def _strip_images_and_links(text: str) -> str:
    return _LINK.sub(r"\1", _IMAGE.sub("", text))


def _squeeze_table_padding(text: str) -> str:
    """原文表格为了对齐用大量空格补位，会让一行长出几十个字符；压成单个空格。"""
    return "\n".join(
        re.sub(r" {2,}", " ", line) if line.lstrip().startswith("|") else line
        for line in text.split("\n")
    )


def _collapse_blank_lines(text: str) -> str:
    lines = [line.rstrip() for line in text.split("\n")]
    return _BLANK_RUN.sub("\n\n", "\n".join(lines)).strip("\n") + "\n"
