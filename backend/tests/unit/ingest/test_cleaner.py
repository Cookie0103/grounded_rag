from pathlib import Path

import pytest

from app.core.errors import CorpusError
from app.ingest.cleaner import clean_mdx, count_residual_tags
from app.ingest.corpus import RAW_DIR, list_raw_files

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "dify"


def _lines(*parts: str) -> str:
    return "\n".join(parts)


def _clean(body: str, *, title: str = "标题") -> str:
    return clean_mdx(f"---\ntitle: {title}\n---\n\n{body}").markdown


# ---------------------------------------------------------------- 真实文档（golden）


@pytest.mark.parametrize("source", sorted(FIXTURES.glob("*.mdx")), ids=lambda path: path.stem)
def test_real_documents_match_the_reviewed_output(source: Path) -> None:
    expected = source.with_suffix(".expected.md").read_text(encoding="utf-8")

    document = clean_mdx(source.read_text(encoding="utf-8"), path=source.name)

    assert document.markdown == expected
    assert document.unknown_components == []
    assert count_residual_tags(document.markdown) == 0


def test_every_downloaded_document_cleans_without_residual_tags() -> None:
    files = list_raw_files(RAW_DIR)
    if not files:
        pytest.skip("语料还没下载（uv run poe fetch-docs）")

    for path in files:
        document = clean_mdx(path.read_text(encoding="utf-8"), path=path.name)
        assert count_residual_tags(document.markdown) == 0, path.name
        assert document.unknown_components == [], path.name


# ---------------------------------------------------------------- front matter 与翻译声明


def test_front_matter_gives_title_and_description() -> None:
    document = clean_mdx(
        "---\ntitle: 上传本地文件\ndescription: 说明文字\nsidebarTitle: x\n---\n正文\n"
    )

    assert (document.title, document.description) == ("上传本地文件", "说明文字")
    assert document.markdown == "正文\n"


def test_description_is_optional() -> None:
    assert clean_mdx("---\ntitle: T\n---\n正文").description is None


@pytest.mark.parametrize(
    "raw",
    [
        "没有 front matter\n",
        "---\ndescription: 只有描述\n---\n正文",
        "---\ntitle: [未闭合\n---\n正文",
    ],
)
def test_bad_front_matter_is_rejected(raw: str) -> None:
    with pytest.raises(CorpusError):
        clean_mdx(raw, path="x.mdx")


def test_translation_notice_is_removed() -> None:
    body = "> 本文档由 AI 自动翻译。如有任何不准确之处，请参考 [英文原版](/en/x)。\n\n正文\n"

    assert _clean(body) == "正文\n"


# ---------------------------------------------------------------- 代码保护


def test_fenced_code_is_kept_verbatim_even_with_tags_inside() -> None:
    body = "<Note>\n正文\n</Note>\n\n```html\n<Note>不要动</Note>\n![x](y)\n```\n"

    assert _clean(body) == "**注意：**\n正文\n\n```html\n<Note>不要动</Note>\n![x](y)\n```\n"


def test_inline_code_is_kept_verbatim() -> None:
    assert _clean("用 `<Tip>` 标签和 `![a](b)` 语法") == "用 `<Tip>` 标签和 `![a](b)` 语法\n"


def test_fenced_code_inside_a_component_is_dedented_with_the_component() -> None:
    body = _lines(
        '<Step title="安装">',
        "    运行：",
        "",
        "    ```bash",
        "    pip install x",
        "      --upgrade",
        "    ```",
        "</Step>",
    )

    assert _clean(body) == _lines(
        "**步骤 1：安装**", "运行：", "", "```bash", "pip install x", "  --upgrade", "```", ""
    )


def test_unclosed_fence_runs_to_the_end() -> None:
    assert _clean("前\n\n```python\nx = 1\n") == "前\n\n```python\nx = 1\n"


# ---------------------------------------------------------------- 组件


@pytest.mark.parametrize(
    ("tag", "label"),
    [("Note", "注意"), ("Tip", "提示"), ("Info", "说明"), ("Warning", "警告"), ("Danger", "危险")],
)
def test_admonitions_get_a_label_line(tag: str, label: str) -> None:
    assert (
        _clean(f"前文\n<{tag}>\n  内容\n</{tag}>\n后文") == f"前文\n\n**{label}：**\n内容\n后文\n"
    )


def test_inline_admonition_stays_on_one_line() -> None:
    assert _clean("| a | b<Note>注释</Note> |") == "| a | b**注意：** 注释 |\n"


def test_frame_is_removed_and_its_caption_is_kept() -> None:
    body = _lines(
        '<Frame caption="流程图">',
        "  ![x](https://a/b.png)",
        "</Frame>",
        "",
        "<Frame>",
        "  ![y](z)",
        "</Frame>",
        "",
        "正文",
    )

    assert _clean(body) == "流程图\n\n正文\n"


def test_tabs_accordions_and_cards_keep_their_titles() -> None:
    body = _lines(
        "<Tabs>",
        '  <Tab title="甲">',
        "    内容甲",
        "  </Tab>",
        '  <Tab title="乙">',
        "    内容乙",
        "  </Tab>",
        "</Tabs>",
        "",
        "<AccordionGroup>",
        '<Accordion title="丙">',
        "丙的内容",
        "</Accordion>",
        "</AccordionGroup>",
        "",
        "<CardGroup cols={2}>",
        '  <Card title="丁" icon="x" href="/y">',
        "    丁的内容",
        "  </Card>",
        "</CardGroup>",
    )

    assert (
        _clean(body) == "**甲**\n内容甲\n\n**乙**\n内容乙\n\n**丙**\n丙的内容\n\n**丁**\n丁的内容\n"
    )


def test_steps_are_numbered_per_steps_block() -> None:
    body = (
        '<Steps>\n  <Step title="一">\n    甲\n  </Step>\n  <Step>\n    乙\n  </Step>\n</Steps>\n\n'
        '<Steps>\n  <Step title="二">\n    丙\n  </Step>\n</Steps>'
    )

    assert _clean(body) == "**步骤 1：一**\n甲\n\n**步骤 2**\n乙\n\n**步骤 1：二**\n丙\n"


def test_inline_components_keep_only_their_text() -> None:
    assert _clean('适用于 <Badge color="blue">专业版</Badge> 用户') == "适用于 专业版 用户\n"


def test_unknown_component_is_stripped_and_recorded() -> None:
    document = clean_mdx("---\ntitle: T\n---\n<Mystery>\n内容\n</Mystery>\n")

    assert document.markdown == "内容\n"
    assert document.unknown_components == ["Mystery"]


@pytest.mark.parametrize(
    "text", ["设置 <your_token> 后", "协议 <SCHEME>://host", "泛型 <string, any>"]
)
def test_angle_brackets_that_are_not_tags_are_kept(text: str) -> None:
    assert _clean(text) == f"{text}\n"


def test_multiline_tag_attributes_are_joined() -> None:
    body = '<Card\n  title="标题"\n  href="/x"\n>\n  内容\n</Card>'

    assert _clean(body) == "**标题**\n内容\n"


def test_component_content_indentation_is_restored_inside_lists() -> None:
    body = "- 项目\n\n    <Tip>\n        提示内容\n    </Tip>\n"

    assert _clean(body) == "- 项目\n\n    **提示：**\n    提示内容\n"


# ---------------------------------------------------------------- 图片、链接、注释、HTML


def test_images_are_removed_and_links_keep_their_text() -> None:
    body = "见 [知识库](/zh/x/y) 和 ![截图](https://a/b.png) 以及 [![图](u)](v)。"

    assert _clean(body) == "见 知识库 和  以及 。\n"


def test_comments_are_removed() -> None:
    assert _clean("甲<!-- 隐藏\n多行 -->乙{/* 注释 */}丙") == "甲乙丙\n"


def test_br_becomes_a_newline_outside_tables_and_a_space_inside() -> None:
    assert _clean("第一行<br/>第二行<br>第三行") == "第一行\n第二行\n第三行\n"
    assert _clean("| 列 |\n|---|\n| 甲<br/><br/>乙 |") == "| 列 |\n|---|\n| 甲 乙 |\n"


def test_html_list_items_become_bullets_outside_tables() -> None:
    assert _clean("<ul>\n  <li>甲</li>\n  <li>乙</li>\n</ul>") == "- 甲\n- 乙\n"


def test_html_list_items_in_table_cells_are_joined_with_semicolons() -> None:
    row = "| 字段 | 包括：<ul><li>甲。</li><li>乙</li></ul> |"

    assert _clean(row) == "| 字段 | 包括：甲。乙 |\n"


def test_html_table_becomes_a_markdown_table() -> None:
    body = (
        "前文\n<table>\n  <thead><tr><th>名称</th><th>说明</th></tr></thead>\n"
        "  <tbody>\n    <tr><td>甲</td><td>第一<br/>行<ul><li>一</li><li>二</li></ul></td></tr>\n"
        "    <tr><td>乙|丙</td><td></td></tr>\n  </tbody>\n</table>\n后文"
    )

    assert _clean(body) == (
        "前文\n\n| 名称 | 说明 |\n|---|---|\n| 甲 | 第一 行 一；二 |\n| 乙\\|丙 |  |\n\n后文\n"
    )


def test_layout_html_is_stripped_but_text_is_kept() -> None:
    body = '<div style={{display: "flex"}}>\n  <p className="x">你好 <span>世界</span></p>\n</div>'

    assert _clean(body) == "你好 世界\n"


def test_blank_lines_are_collapsed_and_trailing_spaces_removed() -> None:
    assert _clean("甲  \n\n\n\n\n乙\n\n\n") == "甲\n\n乙\n"


# ---------------------------------------------------------------- 残留标签


def test_residual_tags_are_counted_outside_code_only() -> None:
    markdown = "正文 <Note>x</Note>\n\n`<Tip>` 行内\n\n```\n<Frame>代码</Frame>\n```\n<div>"

    assert count_residual_tags(markdown) == 3
