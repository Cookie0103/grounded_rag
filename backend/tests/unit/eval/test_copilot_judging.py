import json
from datetime import date
from pathlib import Path
from zipfile import ZipFile

import pytest

from app.providers.fakes import FakeChatModel
from eval.copilot_cases import CopilotCase
from eval.copilot_judging import (
    Calibration,
    PolicyCorpus,
    load_calibration,
    policy_acceptable,
    review_policy,
    review_policy_raw,
)
from eval.dataset import Nugget
from eval.judge import ChatPromptRunner, Judge

DOC_ID = "synthetic/test@v2"


@pytest.fixture
def pack(tmp_path: Path) -> Path:
    target = tmp_path / "pack.zip"
    with ZipFile(target, "w") as archive:
        archive.writestr(
            "index.jsonl",
            json.dumps({"document_id": DOC_ID, "file": "test.md", "synthetic": True}),
        )
        archive.writestr("documents/test.md", "synthetic: true\n架空の申請は郵送で受け付けます。")
    return target


@pytest.fixture
def case() -> CopilotCase:
    return CopilotCase(
        id="q-synthetic",
        category="policy",
        synthetic=True,
        question="架空の手続きはどの方法で申し込めますか？",
        gold_docs=(DOC_ID,),
        nuggets=(Nugget("郵送で申請する", "vital"),),
        as_of=date(2026, 11, 18),
    )


@pytest.mark.parametrize(
    ("count", "agreements", "rate", "accepted"),
    [(19, 19, 1.0, False), (20, 16, 0.8, False), (20, 17, 0.85, True)],
)
def test_calibration_requires_enough_independent_agreements(
    tmp_path: Path, count: int, agreements: int, rate: float, *, accepted: bool
) -> None:
    path = tmp_path / "calibration.jsonl"
    path.write_text(
        "\n".join(
            json.dumps(
                {
                    "id": f"q-{i}",
                    "human_acceptable": True,
                    "judge_acceptable": i < agreements,
                }
            )
            for i in range(count)
        ),
        encoding="utf-8",
    )

    calibration = load_calibration(path)

    assert (calibration.count, calibration.agreements) == (count, agreements)
    assert calibration.rate == rate
    assert calibration.accepted is accepted


def test_missing_calibration_remains_unmeasured() -> None:
    calibration = load_calibration(None)

    assert (calibration.count, calibration.agreements, calibration.rate) == (0, 0, None)
    assert calibration.accepted is False


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        (
            '{"id":"q1","human_acceptable":true,"judge_acceptable":"false"}',
            "必须是布尔值",
        ),
        (
            '{"id":"q1","human_acceptable":true,"judge_acceptable":true}\n'
            '{"id":"q1","human_acceptable":true,"judge_acceptable":true}',
            "重复",
        ),
    ],
)
def test_invalid_calibration_rows_cannot_inflate_agreement(
    tmp_path: Path, contents: str, message: str
) -> None:
    path = tmp_path / "calibration.jsonl"
    path.write_text(contents, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_calibration(path)


async def test_raw_review_uses_gold_document_date_and_retrieved_context(
    pack: Path, case: CopilotCase
) -> None:
    chat = FakeChatModel(responses=['{"nuggets":["support"],"behavior":"answered"}'])
    review = await review_policy_raw(
        case,
        "郵送で受け付けます。",
        ("架空の検索結果です。",),
        judge=Judge(ChatPromptRunner(chat)),
        corpus=PolicyCorpus.from_question_pack(pack),
    )

    prompt = chat.calls[0][0].content
    assert "架空の申請は郵送で受け付けます。" in prompt
    assert "架空の検索結果です。" in prompt
    assert "2026-11-18" in prompt
    assert review.score.label == "perfect"
    assert policy_acceptable(review) is True


async def test_policy_review_does_not_call_judge_below_calibration_threshold(
    pack: Path, case: CopilotCase
) -> None:
    chat = FakeChatModel(responses=[])
    accepted = await review_policy(
        case,
        "郵送で受け付けます。",
        (),
        judge=Judge(ChatPromptRunner(chat)),
        corpus=PolicyCorpus.from_question_pack(pack),
        calibration=Calibration(count=20, agreements=16),
    )

    assert accepted is None
    assert chat.calls == []


async def test_calibrated_policy_review_requires_full_vital_support(
    pack: Path, case: CopilotCase
) -> None:
    chat = FakeChatModel(responses=['{"nuggets":["partial_support"],"behavior":"answered"}'])
    accepted = await review_policy(
        case,
        "郵送の選択肢があります。",
        (),
        judge=Judge(ChatPromptRunner(chat)),
        corpus=PolicyCorpus.from_question_pack(pack),
        calibration=Calibration(count=20, agreements=17),
    )

    assert accepted is False


def test_unknown_gold_document_does_not_produce_an_empty_reference(pack: Path) -> None:
    with pytest.raises(ValueError, match=r"unknown@v1"):
        PolicyCorpus.from_question_pack(pack).gold_texts(("unknown@v1",))
