import math
from pathlib import Path

import pytest

from eval.dataset import Question, load_questions
from eval.metrics import hit_at_k, mean, ranked_documents, reciprocal_rank

SMOKE = Path(__file__).resolve().parents[3] / "eval" / "smoke_retrieval.jsonl"


def test_chunk_ranking_becomes_a_document_ranking_without_repeats() -> None:
    assert ranked_documents(["a", "a", "b", "a", "c", "b"]) == ["a", "b", "c"]


def test_hit_needs_every_gold_document_within_the_top_k() -> None:
    ranked = ["a", "b", "c", "d"]

    assert hit_at_k(["a"], ranked, 1)
    assert hit_at_k(["a", "c"], ranked, 3)
    assert not hit_at_k(["a", "d"], ranked, 3)
    assert not hit_at_k(["z"], ranked, 4)


def test_hit_is_false_when_there_is_no_gold_document() -> None:
    assert not hit_at_k([], ["a"], 5)


def test_reciprocal_rank_uses_the_first_gold_document() -> None:
    assert reciprocal_rank(["c", "b"], ["a", "b", "c"]) == 1 / 2
    assert reciprocal_rank(["z"], ["a", "b"]) == 0.0
    assert reciprocal_rank(["a"], []) == 0.0


def test_mean_of_nothing_is_zero() -> None:
    assert mean([]) == 0.0
    assert math.isclose(mean([1.0, 0.0, 0.5]), 0.5)


def test_questions_are_loaded_with_defaults(tmp_path: Path) -> None:
    path = tmp_path / "q.jsonl"
    path.write_text(
        '{"id": "a", "question": "q1", "gold_docs": ["d1", "d2"]}\n\n'
        '{"id": "b", "question": "q2", "gold_docs": ["d3"], '
        '"edition": "cloud", "lexical": "distant"}\n',
        encoding="utf-8",
    )

    assert load_questions(path) == [
        Question("a", "q1", ("d1", "d2")),
        Question("b", "q2", ("d3",), "cloud", "distant"),
    ]


@pytest.mark.parametrize("line", ["not json", '{"id": "a"}'])
def test_bad_question_lines_report_their_position(tmp_path: Path, line: str) -> None:
    path = tmp_path / "q.jsonl"
    path.write_text(line + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"q.jsonl:1"):
        load_questions(path)


def test_the_smoke_set_is_well_formed() -> None:
    questions = load_questions(SMOKE)

    assert len(questions) == len({q.id for q in questions}) >= 20
    assert all(q.gold_docs and q.edition == "self_host" for q in questions)
    assert {q.lexical for q in questions} == {"similar", "distant"}
