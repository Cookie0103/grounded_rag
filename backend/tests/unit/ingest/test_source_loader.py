from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import ContentStream, DictionaryObject, NameObject

from app.ingest.source_loader import load_source


def test_html_keeps_headings_and_table_rows_without_navigation(tmp_path: Path) -> None:
    source = tmp_path / "public.html"
    source.write_text(
        """
        <html><head><title>住宅ローンの手続</title></head><body>
        <nav>共通の案内</nav>
        <main><h1>返済の手続</h1><h2>必要な書類</h2>
        <p>手続に必要な書類を確認します。</p>
        <script>表示されない説明</script>
        <table><tr><th>項目</th><th>内容</th></tr>
        <tr><th rowspan="2">確認資料</th><td>申込書</td></tr>
        <tr><td>本人確認書類</td></tr></table>
        </main><footer>共通の注意</footer></body></html>
        """,
        encoding="utf-8",
    )

    document = load_source(source)

    assert document.title == "返済の手続"
    assert "## 必要な書類" in document.markdown
    assert "| 確認資料 | 本人確認書類 |" in document.markdown
    assert "表示されない説明" not in document.markdown
    assert "共通の" not in document.markdown


def test_markdown_uses_the_title_and_keeps_synthetic_metadata_out_of_body(tmp_path: Path) -> None:
    source = tmp_path / "procedure.md"
    source.write_text(
        "---\nsynthetic: true\n---\n# 合成手順書\n\n## 手続\n\n手順を確認します。\n",
        encoding="utf-8",
    )

    document = load_source(source)

    assert document.title == "合成手順書"
    assert document.markdown == "## 手続\n\n手順を確認します。"


def test_faq_uses_the_question_title_instead_of_the_generic_page_heading(tmp_path: Path) -> None:
    source = tmp_path / "faq.html"
    source.write_text(
        "<title>手続は何ですか？｜よくあるご質問｜検証サイト</title>"
        "<main><h1>よくあるご質問</h1><h2>手続は何ですか？</h2><p>手続を確認します。</p></main>",
        encoding="utf-8",
    )

    assert load_source(source).title == "手続は何ですか？"


def test_pdf_extracts_text_from_each_page(tmp_path: Path) -> None:
    source = tmp_path / "policy.pdf"
    writer = PdfWriter()
    writer.add_metadata({"/Title": "合成手順書"})
    for word in ("Repayment", "Document"):
        page = writer.add_blank_page(width=100, height=100)
        font = DictionaryObject(
            {
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
        )
        content = ContentStream(None, writer)
        content.set_data(f"BT /F1 12 Tf 10 75 Td ({word}) Tj ET".encode())
        page.replace_contents(content)
    writer.write(source)

    document = load_source(source)

    assert document.title == "合成手順書"
    assert document.markdown == "## 1 ページ\n\nRepayment\n\n## 2 ページ\n\nDocument"
