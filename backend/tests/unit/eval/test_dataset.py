import json
from pathlib import Path

import pytest

from eval.dataset import Nugget, Question, load_questions, quota_report, validate_questions

NUGGETS = (Nugget("a", "vital"), Nugget("b", "okay"))


def _ok(**fields: object) -> Question:
    base: dict[str, object] = {
        "id": "q",
        "question": "怎么上传",
        "gold_docs": ("d",),
        "nuggets": NUGGETS,
    }
    return Question(**{**base, **fields})  # type: ignore[arg-type]


def _errors(*questions: Question, known: set[str] | None = None) -> list[str]:
    return [i.message for i in validate_questions(list(questions), known) if i.is_error]


def test_valid_question_has_no_issues() -> None:
    assert validate_questions([_ok()], {"d"}) == []


def test_duplicate_ids_and_unknown_documents_are_errors() -> None:
    messages = _errors(_ok(), _ok(), known={"other"})

    assert "id 重复" in messages
    assert any("不在语料里" in m for m in messages)


@pytest.mark.parametrize(
    ("fields", "text"),
    [
        ({"question": " "}, "题干为空"),
        ({"type": "bogus"}, "type="),
        ({"edition": "x"}, "edition="),
        ({"expected_route": "X"}, "expected_route="),
        ({"gold_docs": ()}, "必须有金标文档"),
        ({"type": "reasoning"}, "至少要 2 篇"),
        ({"type": "version"}, "必须写明 edition"),
        ({"type": "unanswerable"}, "没有 unanswerable_category"),
        ({"nuggets": (Nugget("a", "vital"),)}, "关键点要"),
        ({"nuggets": (Nugget("a", "okay"), Nugget("b", "okay"))}, "至少要有一条 vital"),
        ({"nuggets": (Nugget("a", "vital"), Nugget("b", "weird"))}, "关键点不合法"),
    ],
)
def test_answerable_question_errors(fields: dict[str, object], text: str) -> None:
    assert any(text in message for message in _errors(_ok(**fields)))


def test_unanswerable_question_rules() -> None:
    good = Question("u", "q", (), type="unanswerable", unanswerable_category="injection")
    bad_category = Question("u", "q", (), type="unanswerable", unanswerable_category="zzz")
    wrong_type = Question("u", "q", (), unanswerable_category="injection")
    with_nuggets = Question(
        "u", "q", (), type="unanswerable", unanswerable_category="injection", nuggets=NUGGETS
    )

    assert _errors(good) == []
    assert any("不合法" in m for m in _errors(bad_category))
    assert any("type 必须是" in m for m in _errors(wrong_type))
    assert any("不需要关键点" in m for m in _errors(with_nuggets))


def test_leaky_phrase_is_only_a_warning() -> None:
    issues = validate_questions([_ok(question="根据文档，怎么上传")])

    assert [i.is_error for i in issues] == [False]


def test_load_questions_parses_jsonl_and_infers_type(tmp_path: Path) -> None:
    path = tmp_path / "q.jsonl"
    rows = [
        {
            "id": "a",
            "question": "q",
            "gold_docs": ["d"],
            "nuggets": [{"text": "x", "importance": "vital"}],
        },
        {"id": "b", "question": "q", "gold_docs": [], "unanswerable_category": "injection"},
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n\n", encoding="utf-8")

    first, second = load_questions(path)

    assert first.nuggets == (Nugget("x", "vital"),)
    assert first.type == "fact_single"
    assert second.type == "unanswerable"
    assert not second.answerable


def test_load_questions_reports_the_bad_line(tmp_path: Path) -> None:
    path = tmp_path / "q.jsonl"
    path.write_text('{"id": "a"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match=r"q\.jsonl:1"):
        load_questions(path)


def test_quota_report_lists_every_type() -> None:
    lines = quota_report([_ok()])

    assert lines[0] == "共 1 题"
    assert any("fact_single：1" in line for line in lines)
    assert any("injection" in line for line in lines)


def test_gold_doc_groups_are_loaded_and_checked_against_the_corpus(tmp_path: Path) -> None:
    line = (
        '{"id": "q1", "question": "问", "gold_docs": ["a"], "gold_doc_groups": [["a", "b"]],'
        ' "nuggets": [{"text": "x", "importance": "vital"}, {"text": "y", "importance": "okay"}]}'
    )
    path = tmp_path / "q.jsonl"
    path.write_text(line, encoding="utf-8")

    (question,) = load_questions(path)

    assert question.gold_doc_groups == (("a", "b"),)
    messages = [issue.message for issue in validate_questions([question], {"a"})]
    assert any("b" in message for message in messages)
