import pytest

from app.retrieval.tokenizer import bigram_tokenize, tokenize


def test_identifiers_are_kept_whole_and_lowercased() -> None:
    tokens = tokenize("怎么修改 UPLOAD_FILE_SIZE_LIMIT 的值")

    assert "upload_file_size_limit" in tokens
    assert "upload" not in tokens  # 没有被下划线拆开


@pytest.mark.parametrize("term", ["工作流", "知识流水线", "元数据", "对话流"])
def test_protected_terms_are_not_split(term: str) -> None:
    assert term in tokenize(f"{term}有什么区别")


def test_search_mode_also_emits_sub_words_of_long_words() -> None:
    tokens = tokenize("机器人")

    assert "机器人" in tokens
    assert "机器" in tokens


def test_punctuation_and_whitespace_are_dropped() -> None:
    assert all(
        token.strip() and any(c.isalnum() for c in token) for token in tokenize("你好，世界！ OK?")
    )


def test_english_words_are_lowercased() -> None:
    assert "chatflow" in tokenize("Chatflow 和 Workflow")


def test_empty_text_has_no_tokens() -> None:
    assert tokenize("") == []
    assert tokenize("，。 ！") == []


def test_bigram_tokenizer_cuts_chinese_into_overlapping_pairs_and_keeps_identifiers() -> None:
    assert bigram_tokenize("知识流水线 UPLOAD_FILE_SIZE_LIMIT a") == [
        "知识",
        "识流",
        "流水",
        "水线",
        "upload_file_size_limit",
        "a",
    ]


def test_single_character_function_words_are_dropped() -> None:
    tokens = tokenize("上传的文件和大小")

    assert "的" not in tokens
    assert "和" not in tokens
    assert "文件" in tokens
