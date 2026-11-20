from app.orchestration.postprocess import MASK_TEXT, collapse_repeats, postprocess


def test_api_keys_and_bearer_tokens_are_masked() -> None:
    result = postprocess("密钥是 sk-abcdefghijklmnop1234，头是 Bearer abcdefghijklmnop12.34")

    assert result.answer == f"密钥是 {MASK_TEXT}，头是 {MASK_TEXT}"
    assert result.notes == ["遮蔽了疑似密钥"] * 2


def test_blocked_terms_block_the_whole_answer() -> None:
    result = postprocess("这里有违禁词甲", blocked_terms=("违禁词甲",))

    assert result.blocked
    assert postprocess("正常内容", blocked_terms=("违禁词甲", "")).blocked is False


def test_sentences_repeated_more_than_twice_are_collapsed_but_short_ones_kept() -> None:
    text = "请检查配置。请检查配置。请检查配置。请检查配置。是。是。是。其他说明。"

    assert collapse_repeats(text) == "请检查配置。请检查配置。是。是。是。其他说明。"


def test_normal_answers_are_untouched() -> None:
    result = postprocess("默认最多 5 个 [1]。需要修改请设置 UPLOAD_FILE_BATCH_LIMIT。")

    assert result.notes == []
    assert result.answer.startswith("默认最多")
