import pytest

from app.retrieval.bm25 import Bm25Index
from app.retrieval.tokenizer import bigram_tokenize

IDS = ["a", "b", "c", "d"]
TEXTS = [
    "知识库单次最多上传五个文件",
    "环境变量 UPLOAD_FILE_SIZE_LIMIT 控制上传文件大小",
    "工作流和 Chatflow 的区别",
    "监控页面可以查看调用次数",
]


@pytest.fixture(scope="module")
def index() -> Bm25Index:
    return Bm25Index(IDS, TEXTS)


def test_exact_identifier_ranks_its_chunk_first(index: Bm25Index) -> None:
    hits = index.search("UPLOAD_FILE_SIZE_LIMIT 是什么", 3)

    assert hits[0][0] == "b"
    assert hits[0][1] > 0


def test_scores_are_sorted_descending_and_only_positive(index: Bm25Index) -> None:
    hits = index.search("上传文件", 4)

    scores = [score for _, score in hits]
    assert scores == sorted(scores, reverse=True)
    assert all(score > 0 for score in scores)
    assert {chunk_id for chunk_id, _ in hits} <= {"a", "b"}


def test_limit_is_respected(index: Bm25Index) -> None:
    assert len(index.search("上传文件", 1)) == 1


def test_allowed_ids_restrict_the_results(index: Bm25Index) -> None:
    hits = index.search("上传文件", 4, allowed_ids=frozenset({"a"}))

    assert [chunk_id for chunk_id, _ in hits] == ["a"]


def test_query_without_any_match_returns_nothing(index: Bm25Index) -> None:
    assert index.search("完全无关的内容xyz", 3) == []
    assert index.search("", 3) == []


def test_empty_index_returns_nothing() -> None:
    assert Bm25Index([], []).search("上传", 3) == []


def test_mismatched_lengths_are_rejected() -> None:
    with pytest.raises(ValueError, match="数量"):
        Bm25Index(["a"], [])


def test_a_different_tokenizer_can_be_plugged_in() -> None:
    bigram_index = Bm25Index(IDS, TEXTS, tokenizer=bigram_tokenize)

    assert bigram_index.search("工作流区别", 1)[0][0] == "c"
    assert len(bigram_index) == 4
