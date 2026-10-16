import math

from app.retrieval.fusion import rrf


def test_document_in_both_lists_beats_one_that_is_only_in_one() -> None:
    fused = dict(rrf([["a", "b", "c"], ["x", "y", "a"]]))

    assert math.isclose(fused["a"], 1 / 61 + 1 / 63)
    assert math.isclose(fused["b"], 1 / 62)
    assert rrf([["a", "b", "c"], ["x", "y", "a"]])[0][0] == "a"


def test_scores_use_the_given_k() -> None:
    assert math.isclose(dict(rrf([["a"]], k=10))["a"], 1 / 11)


def test_ties_are_broken_by_list_order_then_rank() -> None:
    # b 和 x 分数相同（都只在各自榜单的第 2 名），先出现的榜单里的排前面
    assert [item for item, _ in rrf([["a", "b"], ["z", "x"]])] == ["a", "z", "b", "x"]


def test_duplicates_within_one_list_count_once() -> None:
    assert math.isclose(dict(rrf([["a", "a", "b"]]))["a"], 1 / 61)


def test_empty_input() -> None:
    assert rrf([]) == []
    assert rrf([[], []]) == []
