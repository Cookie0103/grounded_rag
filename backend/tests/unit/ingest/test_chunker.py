from pathlib import Path

import pytest

from app.core.config import (
    CHILD_MAX_CHARS,
    CHILD_TARGET_CHARS,
    CODE_BLOCK_MAX_CHARS,
    PARENT_MAX_CHARS,
)
from app.ingest.chunker import ChunkedDocument, chunk_document
from app.ingest.cleaner import clean_mdx
from app.ingest.corpus import RAW_DIR, list_raw_files

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "dify"


def _lines(*parts: str) -> str:
    return "\n".join(parts)


def _sentence(index: int, length: int = 40) -> str:
    """长度固定、以句号结尾的一句话。"""
    body = f"第{index:03}句" + "字" * (length - 6)
    return body + "。"


def _paths(chunked: ChunkedDocument) -> list[str]:
    return [parent.heading_path for parent in chunked.parents]


# ---------------------------------------------------------------- 分节与标题路径


def test_small_document_is_one_parent_and_one_child() -> None:
    chunked = chunk_document("标题", "第一段。\n\n第二段。\n")

    assert [(p.ordinal, p.heading_path, p.text) for p in chunked.parents] == [
        (0, "标题", "第一段。\n\n第二段。")
    ]
    assert [(c.ordinal, c.parent_ordinal, c.heading_path) for c in chunked.children] == [
        (0, 0, "标题")
    ]
    assert chunked.children[0].text == "第一段。\n\n第二段。"


def test_h2_and_h3_build_the_heading_path() -> None:
    markdown = _lines(
        "开头说明", "", "## 甲", "甲的内容", "", "### 甲一", "甲一的内容", "", "### 甲二",
        "甲二的内容", "", "## 乙", "乙的内容", "", "### 乙一", "乙一的内容",
    )  # fmt: skip

    chunked = chunk_document("文档", markdown)

    assert _paths(chunked) == [
        "文档",
        "文档 > 甲",
        "文档 > 甲 > 甲一",
        "文档 > 甲 > 甲二",
        "文档 > 乙",
        "文档 > 乙 > 乙一",
    ]


def test_h3_before_any_h2_hangs_directly_under_the_title() -> None:
    assert _paths(chunk_document("文档", "### 先来个三级\n内容")) == ["文档 > 先来个三级"]


def test_h1_and_h4_headings_stay_inside_the_section_as_text() -> None:
    markdown = _lines(
        "## 节", "前文", "", "#### 小标题", "小标题下的内容", "", "# 一级", "一级下的内容"
    )

    chunked = chunk_document("文档", markdown)

    assert _paths(chunked) == ["文档 > 节"]
    assert chunked.parents[0].text == "前文\n\n#### 小标题\n小标题下的内容\n\n# 一级\n一级下的内容"


def test_heading_markup_is_removed_from_the_path() -> None:
    chunked = chunk_document(
        "环境变量", "### `CONSOLE_API_URL`\n内容\n\n## **加粗** 标题 {#anchor}\n内容"
    )

    assert _paths(chunked) == ["环境变量 > CONSOLE_API_URL", "环境变量 > 加粗 标题"]


def test_sections_without_content_and_horizontal_rules_produce_no_chunks() -> None:
    markdown = _lines("## 只有标题", "", "## 只有分隔线", "---", "", "## 有内容", "正文")

    chunked = chunk_document("文档", markdown)

    assert _paths(chunked) == ["文档 > 有内容"]
    assert [c.text for c in chunked.children] == ["正文"]


def test_empty_document_has_no_chunks() -> None:
    chunked = chunk_document("文档", "\n\n")

    assert (chunked.parents, chunked.children) == ([], [])


# ---------------------------------------------------------------- 父块


def test_long_section_is_split_between_blocks_into_several_parents() -> None:
    paragraphs = [f"段{i}" + "字" * 1500 for i in range(5)]

    chunked = chunk_document("文档", "\n\n".join(paragraphs))

    assert len(chunked.parents) > 1
    assert all(len(p.text) <= PARENT_MAX_CHARS for p in chunked.parents)
    assert "\n\n".join(p.text for p in chunked.parents).split("\n\n") == paragraphs
    assert {p.heading_path for p in chunked.parents} == {"文档"}


# ---------------------------------------------------------------- 子块：装填


def test_short_blocks_are_packed_until_the_target_size() -> None:
    paragraphs = [f"段落{i:02}" + "字" * 94 for i in range(10)]  # 每段 100 字

    chunked = chunk_document("文档", "\n\n".join(paragraphs))

    sizes = [len(c.text) for c in chunked.children]
    assert all(CHILD_TARGET_CHARS <= size <= CHILD_MAX_CHARS for size in sizes[:-1])
    assert "\n\n".join(c.text for c in chunked.children).split("\n\n") == paragraphs


def test_children_never_cross_a_parent_boundary() -> None:
    markdown = "## 甲\n" + "甲内容。" * 10 + "\n\n## 乙\n" + "乙内容。" * 10

    chunked = chunk_document("文档", markdown)

    assert [(c.parent_ordinal, c.heading_path) for c in chunked.children] == [
        (0, "文档 > 甲"),
        (1, "文档 > 乙"),
    ]


def test_long_paragraph_is_split_at_sentence_ends() -> None:
    sentences = [_sentence(i) for i in range(30)]

    chunked = chunk_document("文档", "".join(sentences))

    assert len(chunked.children) > 1
    assert all(len(c.text) <= CHILD_MAX_CHARS for c in chunked.children)
    assert all(c.text.endswith("。") for c in chunked.children)
    assert "".join(c.text.replace("\n\n", "") for c in chunked.children) == "".join(sentences)


def test_text_without_any_punctuation_is_still_cut_to_the_limit() -> None:
    chunked = chunk_document("文档", "字" * 1300)

    assert all(len(c.text) <= CHILD_MAX_CHARS for c in chunked.children)
    assert "".join(c.text for c in chunked.children).replace("\n\n", "") == "字" * 1300


def test_long_quote_is_split_by_lines() -> None:
    quote = "\n".join(f"> 引用第{i:02}行" + "字" * 60 for i in range(20))

    chunked = chunk_document("文档", quote)

    assert all(len(c.text) <= CHILD_MAX_CHARS for c in chunked.children)
    assert "\n".join(c.text for c in chunked.children) == quote


# ---------------------------------------------------------------- 表格


def _table(row_lengths: list[int]) -> str:
    header = ["| 变量 | 默认值 | 说明 |", "|---|---|---|"]
    rows = [f"| `VAR_{i:03}` | `x` | {'说' * length} |" for i, length in enumerate(row_lengths)]
    return "\n".join(header + rows)


def test_long_table_is_split_by_rows_and_every_group_repeats_the_header() -> None:
    table = _table([60] * 30)

    chunked = chunk_document("文档", table)

    assert len(chunked.children) > 1
    for child in chunked.children:
        assert child.text.startswith("| 变量 | 默认值 | 说明 |\n|---|---|---|\n| `VAR_")
        assert len(child.text) <= CHILD_MAX_CHARS
    rows = [line for c in chunked.children for line in c.text.split("\n")[2:]]
    assert rows == table.split("\n")[2:]  # 每一行恰好出现一次，顺序不变，没有切断


def test_rows_per_group_depend_on_row_length_not_on_a_fixed_count() -> None:
    short = chunk_document("文档", _table([20] * 40)).children
    long = chunk_document("文档", _table([200] * 40)).children

    short_rows = len(short[0].text.split("\n")) - 2
    long_rows = len(long[0].text.split("\n")) - 2
    assert short_rows > long_rows >= 1


def test_table_that_fits_stays_in_one_child_with_the_text_around_it() -> None:
    markdown = _lines("前文。", "", "| a | b |", "|---|---|", "| 1 | 2 |", "", "后文。")

    chunked = chunk_document("文档", markdown)

    assert [c.text for c in chunked.children] == [
        "前文。\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n后文。"
    ]


def test_table_larger_than_a_parent_is_split_into_parents_with_the_header_repeated() -> None:
    table = _table([300] * 40)

    chunked = chunk_document("文档", table)

    assert len(chunked.parents) > 1
    for parent in chunked.parents:
        assert len(parent.text) <= PARENT_MAX_CHARS
        assert parent.text.startswith("| 变量 | 默认值 | 说明 |\n|---|---|---|")


# ---------------------------------------------------------------- 代码块


def test_code_block_up_to_the_code_limit_is_never_cut() -> None:
    code = "```bash\n" + "\n".join(f"echo {i:03} " + "x" * 30 for i in range(20)) + "\n```"
    assert CHILD_MAX_CHARS < len(code) <= CODE_BLOCK_MAX_CHARS

    chunked = chunk_document("文档", f"先运行：\n\n{code}\n\n然后重启。")

    assert code in [c.text for c in chunked.children]


def test_very_long_code_block_is_split_by_lines_and_each_part_keeps_its_fences() -> None:
    body = [f"line {i:04} " + "x" * 50 for i in range(60)]
    code = "```python\n" + "\n".join(body) + "\n```"
    assert len(code) > CODE_BLOCK_MAX_CHARS

    chunked = chunk_document("文档", code)

    assert len(chunked.children) > 1
    for child in chunked.children:
        assert child.text.startswith("```python\n")
        assert child.text.endswith("\n```")
    rebuilt = [line for c in chunked.children for line in c.text.split("\n")[1:-1]]
    assert rebuilt == body


def test_tilde_and_longer_fences_are_recognised() -> None:
    markdown = "````md\n```\n内嵌的三个反引号\n```\n````\n\n后文。"

    chunked = chunk_document("文档", markdown)

    assert chunked.children[0].text == "````md\n```\n内嵌的三个反引号\n```\n````\n\n后文。"


# ---------------------------------------------------------------- 列表


def test_long_list_is_split_between_items() -> None:
    items = [f"- 第{i:02}项" + "字" * 80 for i in range(12)]

    chunked = chunk_document("文档", "\n".join(items))

    assert len(chunked.children) > 1
    assert "\n".join(c.text for c in chunked.children) == "\n".join(items)
    assert all(c.text.startswith("- 第") for c in chunked.children)


def test_numbered_item_keeps_its_nested_code_block_when_it_fits() -> None:
    markdown = _lines(
        "1. 安装：",
        "",
        "    ```bash",
        "    pip install x",
        "    ```",
        "",
        "2. 运行：",
        "",
        "    直接运行。",
    )

    chunked = chunk_document("文档", markdown)

    assert len(chunked.children) == 1
    assert "    ```bash\n    pip install x\n    ```" in chunked.children[0].text


def test_oversized_list_item_is_split_by_lines_but_its_code_block_stays_whole() -> None:
    code_lines = [f"    code {i:02} " + "x" * 40 for i in range(8)]
    markdown = "\n".join(
        [
            "1. 一个很长的步骤：",
            *[f"   说明第{i}行" + "字" * 80 for i in range(6)],
            "    ```py",
            *code_lines,
            "    ```",
        ]
    )

    chunked = chunk_document("文档", markdown)

    assert len(chunked.children) > 1
    code_block = "    ```py\n" + "\n".join(code_lines) + "\n    ```"
    assert any(code_block in c.text for c in chunked.children)


def test_blank_lines_between_list_items_do_not_end_the_list() -> None:
    chunked = chunk_document("文档", "- 甲\n\n- 乙\n\n段落。")

    assert _paths(chunked) == ["文档"]
    assert chunked.parents[0].text == "- 甲\n\n- 乙\n\n段落。"


# ---------------------------------------------------------------- 真实文档


def _chunk_fixture(name: str) -> ChunkedDocument:
    source = FIXTURES / f"{name}.mdx"
    document = clean_mdx(source.read_text(encoding="utf-8"), path=source.name)
    return chunk_document(document.title, document.markdown)


def test_real_document_headings_become_paths() -> None:
    chunked = _chunk_fixture("tabs-ifelse")

    assert _paths(chunked) == [
        "If-Else",
        "If-Else > 分支逻辑",
        "If-Else > 条件类型",
        "If-Else > 复杂条件",
        "If-Else > 变量引用",
    ]


def test_real_environment_variables_page_is_split_into_table_groups() -> None:
    chunked = _chunk_fixture("environments-excerpt")

    qdrant = [c for c in chunked.children if "QDRANT_URL" in c.text]
    assert qdrant
    assert qdrant[0].text.startswith("**Qdrant**") or "| 变量 | 默认值 | 说明 |" in qdrant[0].text
    assert all(len(c.text) <= CHILD_MAX_CHARS for c in chunked.children)


def test_every_downloaded_document_chunks_within_the_limits() -> None:
    files = list_raw_files(RAW_DIR)
    if not files:
        pytest.skip("语料还没下载（uv run poe fetch-docs）")

    for path in files:
        document = clean_mdx(path.read_text(encoding="utf-8"), path=path.name)
        chunked = chunk_document(document.title, document.markdown)
        parent_blob = "\n".join(p.text for p in chunked.parents)

        assert all(len(p.text) <= PARENT_MAX_CHARS for p in chunked.parents), path.name
        for child in chunked.children:
            assert child.text.strip(), path.name
            assert len(child.text) <= CHILD_MAX_CHARS or "```" in child.text, path.name
        for line in document.markdown.split("\n"):
            is_section_heading = line.startswith(("## ", "### "))
            is_rule = line.strip().strip("-*_ ") == "" and line.strip() != ""
            if line.strip() and not is_section_heading and not is_rule:
                assert line.strip() in parent_blob, (path.name, line)
