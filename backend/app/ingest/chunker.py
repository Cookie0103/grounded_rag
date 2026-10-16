"""父子切块：按文档结构切（标题 → 段落 / 列表 / 代码块 / 表格），不按固定字数硬切。

- 先把 Markdown 解析成块，只在块与块之间断开；
- 按 H2 / H3 分节，每节是一个父块（太长就在块边界处再切）；
- 父块内部装填成约 300 字的子块（上限 500 字）；单个块太长才在句号、列表项、表格行处再切。
"""

import re
from collections.abc import Callable
from dataclasses import dataclass

from app.core.config import (
    CHILD_MAX_CHARS,
    CHILD_TARGET_CHARS,
    CODE_BLOCK_MAX_CHARS,
    PARENT_MAX_CHARS,
)

HEADING_SEPARATOR = " > "
BLOCK_SEPARATOR = "\n\n"

_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
_HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
_BULLET = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+")
_TABLE_ROW = re.compile(r"^\s*\|")
_TABLE_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)*\|?\s*$")
_QUOTE = re.compile(r"^\s*>")
_HORIZONTAL_RULE = re.compile(r"^ {0,3}([-*_])(?:\s*\1){2,}\s*$")
_SENTENCE = re.compile(r".*?(?:[。！？；\n]|[.!?;](?=\s|$))|.+$", re.S)
_HEADING_NOISE = re.compile(r"[`*]|\s*\{#[^}]*\}")
_SOFT_BREAKS = "，,、 "
SECTION_LEVELS = (2, 3)  # 按 H2 / H3 分节
H2 = 2


@dataclass(frozen=True)
class ParentChunk:
    ordinal: int
    heading_path: str
    text: str


@dataclass(frozen=True)
class ChildChunk:
    ordinal: int
    parent_ordinal: int
    heading_path: str
    text: str


@dataclass(frozen=True)
class ChunkedDocument:
    parents: list[ParentChunk]
    children: list[ChildChunk]


@dataclass(frozen=True)
class _Block:
    kind: str  # heading / paragraph / list / code / table / quote
    text: str
    level: int = 0  # 标题级别


# ---------------------------------------------------------------- 入口


def chunk_document(title: str, markdown: str) -> ChunkedDocument:
    parents: list[ParentChunk] = []
    children: list[ChildChunk] = []
    for heading_path, blocks in _sections(title, _parse_blocks(markdown)):
        pieces = [piece for block in blocks for piece in _fit(block, PARENT_MAX_CHARS)]
        for group in _pack_parents(pieces):
            parent_ordinal = len(parents)
            parents.append(
                ParentChunk(
                    parent_ordinal, heading_path, BLOCK_SEPARATOR.join(p.text for p in group)
                )
            )
            for text in _child_texts(group):
                children.append(ChildChunk(len(children), parent_ordinal, heading_path, text))
    return ChunkedDocument(parents, children)


# ---------------------------------------------------------------- 解析成块


def _parse_blocks(markdown: str) -> list[_Block]:
    lines = markdown.split("\n")
    blocks: list[_Block] = []
    index = 0
    while index < len(lines):
        if not lines[index].strip():
            index += 1
            continue
        block, index = _take_block(lines, index)
        if block.kind != "rule":  # 分隔线没有内容，不进任何块
            blocks.append(block)
    return _merge_minor_headings(blocks)


def _take_block(lines: list[str], start: int) -> tuple[_Block, int]:
    line = lines[start]
    heading = _HEADING.match(line)
    if _FENCE.match(line):
        return _take_code(lines, start)
    if _HORIZONTAL_RULE.match(line):
        return _Block("rule", ""), start + 1
    if heading:
        return _Block("heading", heading.group(2), len(heading.group(1))), start + 1
    return _take_body(lines, start)


def _take_body(lines: list[str], start: int) -> tuple[_Block, int]:
    line = lines[start]
    if _starts_table(lines, start):
        return _take_while(lines, start, "table", _TABLE_ROW.match)
    if _QUOTE.match(line):
        return _take_while(lines, start, "quote", _QUOTE.match)
    if _BULLET.match(line):
        return _take_list(lines, start)
    return _take_paragraph(lines, start)


def _starts_table(lines: list[str], index: int) -> bool:
    return (
        bool(_TABLE_ROW.match(lines[index]))
        and index + 1 < len(lines)
        and bool(_TABLE_SEPARATOR.match(lines[index + 1]))
    )


def _take_while(
    lines: list[str], start: int, kind: str, predicate: Callable[[str], object]
) -> tuple[_Block, int]:
    end = start
    while end < len(lines) and predicate(lines[end]):
        end += 1
    return _Block(kind, "\n".join(lines[start:end])), end


def _take_code(lines: list[str], start: int) -> tuple[_Block, int]:
    marker = _fence_marker(lines[start])
    end = start + 1
    while end < len(lines):
        closes = _closes_fence(lines[end], marker)
        end += 1
        if closes:
            break
    return _Block("code", "\n".join(lines[start:end])), end


def _fence_marker(line: str) -> str:
    """围栏开头的那串 ``` 或 ~~~。"""
    stripped = line.lstrip()
    return stripped[: len(stripped) - len(stripped.lstrip(stripped[0]))]


def _closes_fence(line: str, marker: str) -> bool:
    stripped = line.strip()
    return len(stripped) >= len(marker) and set(stripped) == {marker[0]}


def _take_paragraph(lines: list[str], start: int) -> tuple[_Block, int]:
    end = start + 1
    while end < len(lines) and lines[end].strip() and not _starts_other_block(lines, end):
        end += 1
    return _Block("paragraph", "\n".join(lines[start:end])), end


def _starts_other_block(lines: list[str], index: int) -> bool:
    line = lines[index]
    return bool(
        _FENCE.match(line)
        or _HEADING.match(line)
        or _HORIZONTAL_RULE.match(line)
        or _starts_table(lines, index)
    )


def _take_list(lines: list[str], start: int) -> tuple[_Block, int]:
    base = _indent(lines[start])
    end = start
    while end < len(lines):
        line = lines[end]
        if not line.strip():
            following = _next_non_blank(lines, end)
            if following is None or not _belongs_to_list(lines[following], base):
                break
            end = following
            continue
        if _FENCE.match(line) and _indent(line) > base:
            end = _take_code(lines, end)[1]
            continue
        if not _belongs_to_list(line, base):
            break
        end += 1
    return _Block("list", "\n".join(lines[start:end]).rstrip()), end


def _belongs_to_list(line: str, base: int) -> bool:
    if _BULLET.match(line):
        return _indent(line) >= base
    return _indent(line) > base


def _next_non_blank(lines: list[str], index: int) -> int | None:
    for candidate in range(index, len(lines)):
        if lines[candidate].strip():
            return candidate
    return None


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


# ---------------------------------------------------------------- 分节


def _sections(title: str, blocks: list[_Block]) -> list[tuple[str, list[_Block]]]:
    """按 H2 / H3 分节；H1 和 H4 以下当普通段落留在所属小节里。"""
    sections: list[tuple[str, list[_Block]]] = []
    h2 = h3 = ""
    current: list[_Block] = []
    path = title

    def flush() -> None:
        if current:
            sections.append((path, list(current)))
            current.clear()

    for block in blocks:
        if block.kind == "heading":  # 解析时已经把 H1、H4 以下的标题并进了正文，剩下的都是 H2 / H3
            flush()
            name = _clean_heading(block.text)
            if block.level == H2:
                h2, h3 = name, ""
            else:
                h3 = name
            path = HEADING_SEPARATOR.join(part for part in (title, h2, h3) if part)
        else:
            current.append(block)
    flush()
    return sections


def _merge_minor_headings(blocks: list[_Block]) -> list[_Block]:
    """H1、H4 以下的标题不分节：和它后面的段落并成一块，后面不是段落就单独成一段。"""
    merged: list[_Block] = []
    pending: str | None = None
    for block in blocks:
        if block.kind == "heading" and block.level not in SECTION_LEVELS:
            if pending is not None:
                merged.append(_Block("paragraph", pending))
            pending = f"{'#' * block.level} {block.text}"
            continue
        kept = block
        if pending is not None:
            if block.kind == "paragraph":
                kept = _Block("paragraph", f"{pending}\n{block.text}")
            else:
                merged.append(_Block("paragraph", pending))
            pending = None
        merged.append(kept)
    if pending is not None:
        merged.append(_Block("paragraph", pending))
    return merged


def _clean_heading(text: str) -> str:
    return _HEADING_NOISE.sub("", text).strip()


# ---------------------------------------------------------------- 父块与子块


def _fit(block: _Block, limit: int) -> list[_Block]:
    """块太长就切成不超过 limit 的几块（切法见 _split）。"""
    if len(block.text) <= limit:
        return [block]
    return _split(block, limit, limit)


def _pack_parents(pieces: list[_Block]) -> list[list[_Block]]:
    groups: list[list[_Block]] = []
    size = 0
    for piece in pieces:
        extra = len(piece.text) + (len(BLOCK_SEPARATOR) if groups and groups[-1] else 0)
        if not groups or size + extra > PARENT_MAX_CHARS:
            groups.append([piece])
            size = len(piece.text)
        else:
            groups[-1].append(piece)
            size += extra
    return groups


def _child_texts(parent_pieces: list[_Block]) -> list[str]:
    atoms: list[_Block] = []
    for piece in parent_pieces:
        if piece.kind == "code":
            atoms += _fit(piece, CODE_BLOCK_MAX_CHARS)
        elif len(piece.text) <= CHILD_MAX_CHARS:
            atoms.append(piece)
        else:
            atoms += _split(piece, CHILD_TARGET_CHARS, CHILD_MAX_CHARS)
    return _pack_children([atom.text for atom in atoms])


def _pack_children(atoms: list[str]) -> list[str]:
    """接近 CHILD_TARGET_CHARS 就开始新的子块，不超过 CHILD_MAX_CHARS。"""
    children: list[str] = []
    current = ""
    for atom in atoms:
        joined = f"{current}{BLOCK_SEPARATOR}{atom}" if current else atom
        if current and (len(current) >= CHILD_TARGET_CHARS or len(joined) > CHILD_MAX_CHARS):
            children.append(current)
            current = atom
        else:
            current = joined
    if current:
        children.append(current)
    return children


# ---------------------------------------------------------------- 单个块太长时再切


def _split(block: _Block, target: int, maximum: int) -> list[_Block]:
    if block.kind == "table":
        header, *rows = block.text.split("\n")
        separator, *rows = rows or [""]
        pieces = _pack_units(rows, _Packing(prefix=f"{header}\n{separator}\n"), target, maximum)
    elif block.kind == "code":
        pieces = _split_code(block.text, target, maximum)
    elif block.kind == "list":
        units = _list_units(block.text, maximum)
        pieces = _pack_units(units, _Packing(), target, maximum)
    elif block.kind == "quote":
        pieces = _pack_units(block.text.split("\n"), _Packing(), target, maximum)
    else:
        rule = _Packing(joiner="", splittable=True)
        pieces = _pack_units(_sentences(block.text), rule, target, maximum)
    return [_Block(block.kind, piece) for piece in pieces]


def _split_code(text: str, target: int, maximum: int) -> list[str]:
    lines = text.split("\n")
    opening = lines[0]
    marker = _fence_marker(opening)
    has_closing = len(lines) > 1 and _closes_fence(lines[-1], marker)
    closing = lines[-1] if has_closing else marker
    body = lines[1:-1] if has_closing else lines[1:]
    rule = _Packing(prefix=f"{opening}\n", suffix=f"\n{closing}")
    return _pack_units(body, rule, target, maximum)


def _list_items(text: str) -> list[str]:
    """按最外层的列表项切；每项连同它的缩进内容、嵌套项和代码块。"""
    lines = text.split("\n")
    base = min(_indent(line) for line in lines if line.strip())
    items: list[list[str]] = []
    in_fence = False
    for line in lines:
        if _FENCE.match(line):
            in_fence = not in_fence
        starts_item = not in_fence and _BULLET.match(line) and _indent(line) == base
        if starts_item or not items:
            items.append([line])
        else:
            items[-1].append(line)
    return ["\n".join(item).rstrip() for item in items]


def _list_units(text: str, maximum: int) -> list[str]:
    """列表项能整项放下就整项；某一项自己就超长（常见于带代码块的步骤）才拆到行，代码块仍不拆开。"""
    units: list[str] = []
    for item in _list_items(text):
        units += [item] if len(item) <= maximum else _item_lines(item)
    return units


def _item_lines(item: str) -> list[str]:
    lines = item.split("\n")
    units: list[str] = []
    index = 0
    while index < len(lines):
        if _FENCE.match(lines[index]):
            code, index = _take_code(lines, index)
            fits = len(code.text) <= CODE_BLOCK_MAX_CHARS
            units += (
                [code.text]
                if fits
                else _split_code(code.text, CODE_BLOCK_MAX_CHARS, CODE_BLOCK_MAX_CHARS)
            )
        else:
            units.append(lines[index])
            index += 1
    return units


def _sentences(text: str) -> list[str]:
    return [piece for piece in _SENTENCE.findall(text) if piece.strip()]


@dataclass(frozen=True)
class _Packing:
    """装填规则：每组带的前缀 / 后缀（如表格表头、代码围栏），以及接近多少字就换下一组。"""

    joiner: str = "\n"
    prefix: str = ""
    suffix: str = ""
    splittable: bool = False  # 单个单元太长时能不能硬切（只有段落里的句子可以）


def _pack_units(units: list[str], rule: _Packing, target: int, maximum: int) -> list[str]:
    """把单元（表格行、句子、列表项、代码行）装进若干组；每组重复前缀和后缀。"""
    joiner, prefix, suffix = rule.joiner, rule.prefix, rule.suffix
    groups: list[str] = []
    current: list[str] = []
    fixed = len(prefix) + len(suffix)
    size = fixed
    for unit in units:
        for part in _oversized_parts(unit, maximum - fixed, splittable=rule.splittable):
            added = len(part) + (len(joiner) if current else 0)
            if current and (size >= target or size + added > maximum):
                groups.append(prefix + joiner.join(current) + suffix)
                current, size, added = [], fixed, len(part)
            current.append(part)
            size += added
    if current:
        groups.append(prefix + joiner.join(current) + suffix)
    return groups


def _oversized_parts(unit: str, room: int, *, splittable: bool) -> list[str]:
    """只有段落里单个句子就超长（例如没有句号的长文字）才硬切；表格行、代码行、列表项不切断。"""
    if not splittable or len(unit) <= room:
        return [unit]
    parts: list[str] = []
    rest = unit
    while len(rest) > room > 0:
        cut = max((rest.rfind(mark, 0, room) for mark in _SOFT_BREAKS), default=-1)
        cut = cut + 1 if cut > room // 2 else room
        parts.append(rest[:cut])
        rest = rest[cut:]
    return [*parts, rest] if rest else parts
