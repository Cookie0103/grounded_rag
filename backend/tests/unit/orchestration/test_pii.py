import pytest

from app.orchestration.pii import redact_pii


@pytest.mark.parametrize(
    ("question", "redacted"),
    [
        ("連絡先は０９０－１２３４－５６７８です。", "連絡先は［電話番号］です。"),
        ("+81 (0)3-1234-5678へ電話してください。", "［電話番号］へ電話してください。"),
        ("電話番号は0312345678です。", "電話番号は［電話番号］です。"),
        ("窓口の連絡先は0120-123-456です。", "窓口の連絡先は［電話番号］です。"),
        ("口座番号（普通）：１２３４５６７です。", "口座番号（普通）：［口座番号］です。"),
        ("カード番号：1111222233334444です。", "カード番号：［カード番号］です。"),
        ("1111 2222 3333 4444を入力しました。", "［カード番号］を入力しました。"),
        ("カードは4111111111111111です。", "カードは［カード番号］です。"),
        ("個人番号は１２３４ ５６７８ ９０１２です。", "個人番号は［マイナンバー］です。"),
        ("１２３４５６７８９０１２を送ります。", "［マイナンバー］を送ります。"),
        ("メールはｔｅｓｔ＠ｅｘａｍｐｌｅ．ｃｏｍです。", "メールは［メールアドレス］です。"),
    ],
)
def test_redact_pii_with_japanese_placeholders(question: str, redacted: str) -> None:
    assert redact_pii(question) == redacted
    assert redact_pii(redacted) == redacted


def test_redact_pii_preserves_loan_facts_and_contract_identifiers() -> None:
    question = (
        "契約番号は123456789012、契約IDはLC-0012345です。"
        "2026-09-30の残高は1,234,567円で、合計123456789012円です。"
        "普通預金口座の開設から10日後が対象です。"
    )
    assert redact_pii(question) == question
