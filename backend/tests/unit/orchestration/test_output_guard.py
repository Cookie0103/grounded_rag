import pytest

from app.orchestration.models import Citation
from app.orchestration.output_guard import validate_output

_SYNTHETIC_TOOLS = [
    {
        "synthetic": True,
        "data": {
            "next_payment_date": "2026-09-01",
            "next_payment_yen": 1234567,
            "remaining_installments": 420,
            "schedule": [{"period": 12, "due_date": "2026-09-01", "amount_yen": 1234567}],
        },
        "total": 420,
    },
    {"synthetic": True, "data": {"annual_rate_percent": 0.83, "insurance_increment_percent": 0.1}},
    {"synthetic": True, "data": {"days_overdue": 3, "amount_yen": 5000}},
]


@pytest.mark.parametrize(
    "answer",
    [
        "次回返済日は２０２６年９月１日、返済額は１，２３４，５６７円です。",
        "次回返済額は約１２３万円です。",
        "次回返済額は約 123 万円です。",
        "次回返済額は123.4567万円です。",
        "第１２回の返済予定です。残りは420回です。",
        "契約の適用金利は０．８３％です。",
        "遅延は３日です。",
        "次回は9月1日です。",
        "次回は2026年9月です。",
        "延滞額は五千円です。",
    ],
)
def test_validate_output_accepts_grounded_japanese_numbers(answer: str) -> None:
    decision = validate_output(answer, tool_evidence=_SYNTHETIC_TOOLS)
    assert decision.passed
    assert decision.reasons == ()


@pytest.mark.parametrize(
    "answer",
    [
        "次回返済額は123万円です。",
        "次回返済額は約124万円です。",
        "次回返済額は約123.5万円です。",
        "延滞日数は1234567日です。",
        "次回返済額は3円です。",
        "次回返済額は1,239,567円です。",
        "次回返済日は2026年9月3日です。",
        "遅延は3営業日です。",
        "利率は0.93%です。",
        "第420回の返済予定です。",
        "次回返済額は一億円です。",
    ],
)
def test_validate_output_rejects_unverified_or_recombined_numbers(answer: str) -> None:
    decision = validate_output(answer, tool_evidence=_SYNTHETIC_TOOLS)
    assert not decision.passed
    assert decision.reasons == ("unsupported_number",)


@pytest.mark.parametrize(
    "answer",
    [
        "審査に通ります。",
        "審査は必ず通過します。",
        "審査に通ることを保証します。",
        "今回の審査結果は承認です。",
        "必ず融資を受けられます。",
        "この金利が適用されることを保証します。",
        "金利は必ず0.83%になります。",
        "適用金利は0.83%で確定です。",
        "この条件で間違いありません。",
    ],
)
def test_validate_output_rejects_guarantees(answer: str) -> None:
    decision = validate_output(answer, tool_evidence=_SYNTHETIC_TOOLS)
    assert not decision.passed
    assert decision.reasons == ("prohibited_expression",)


@pytest.mark.parametrize(
    "answer",
    [
        "お申し込みの対象です。",
        "本審査に通りますとは限りません。",
        "必ず本人確認書類をご提出ください。",
        "この金利が適用されることを保証するものではありません。",
        "金利は審査後に確定します。",
    ],
)
def test_validate_output_accepts_eligibility_and_non_guarantees(answer: str) -> None:
    assert validate_output(answer).passed


def test_validate_output_accepts_valid_citations_and_policy_evidence() -> None:
    citation = Citation(index=1, document_id="synthetic-policy", heading_path="架空の条件")
    decision = validate_output(
        "対象です。お手続きは３０営業日以内です[1]。",
        policy_texts=["[1] 資料：synthetic-policy｜架空の条件\n手続き期限は30営業日以内。"],
        allowed_citations=[citation],
        active_document_ids={citation.document_id},
        require_citations=True,
    )
    assert decision.passed


def test_validate_output_rejects_any_unknown_or_inactive_citation() -> None:
    current = Citation(index=1, document_id="synthetic-current", heading_path="架空の条件")
    inactive = Citation(index=2, document_id="synthetic-inactive", heading_path="架空の条件")
    for answer in (
        "対象です[1][9]。",
        "対象です[1][2]。",
        "対象です[1]［９］。",
        "対象です[1]【9】。",
    ):
        decision = validate_output(
            answer,
            allowed_citations=[current, inactive],
            active_document_ids={current.document_id},
            require_citations=True,
        )
        assert decision.reasons == ("invalid_citation",)


def test_validate_output_requires_a_citation_for_policy_answers() -> None:
    assert validate_output("対象です。", require_citations=True).reasons == ("missing_citation",)


def test_validate_output_rejects_an_oversized_citation_index() -> None:
    answer = f"対象です[{'9' * 5000}]。"
    assert validate_output(answer).reasons == ("invalid_citation",)


def test_validate_output_does_not_use_citation_headers_as_numeric_evidence() -> None:
    decision = validate_output(
        "対象の手数料は7,000円です。",
        policy_texts=["[1] 資料：synthetic-policy｜7,000円\n手数料の確認方法を案内します。"],
    )
    assert decision.reasons == ("unsupported_number",)


def test_validate_output_does_not_turn_approximate_policy_wording_into_exact_amount() -> None:
    decision = validate_output("手数料は30万円です。", policy_texts=["目安は約30万円です。"])
    assert decision.reasons == ("unsupported_number",)


def test_validate_output_does_not_recombine_calendar_dates() -> None:
    decision = validate_output(
        "受付開始は2026年10月です。",
        policy_texts=["受付開始は2025年10月1日、受付終了は2026年9月1日です。"],
    )
    assert decision.reasons == ("unsupported_number",)


def test_validate_output_does_not_join_digit_fragments_around_a_citation() -> None:
    citation = Citation(index=1, document_id="synthetic-policy", heading_path="架空の条件")
    decision = validate_output(
        "手数料は1[1]23円です。",
        policy_texts=["手数料は123円です。"],
        allowed_citations=[citation],
        active_document_ids={citation.document_id},
    )
    assert decision.reasons == ("unsupported_number",)
