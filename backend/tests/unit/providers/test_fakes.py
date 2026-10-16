import math

import pytest

from app.providers.base import ChatMessage
from app.providers.fakes import FakeChatModel, FakeEmbedder, FakeReranker, char_bigrams


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_char_bigrams_ignore_whitespace() -> None:
    assert char_bigrams("上 传\n文件") == {"上传", "传文", "文件"}
    assert char_bigrams("a") == {"a"}
    assert char_bigrams("  ") == set()


async def test_embedding_is_deterministic_and_normalized() -> None:
    embedder = FakeEmbedder(dimension=64)

    first = (await embedder.embed_documents(["知识库上传文件"]))[0]
    second = (await embedder.embed_documents(["知识库上传文件"]))[0]

    assert first == second
    assert len(first) == embedder.dimension == 64
    assert math.isclose(math.sqrt(sum(v * v for v in first)), 1.0)


async def test_queries_and_documents_use_the_same_embedding() -> None:
    embedder = FakeEmbedder(dimension=64)

    assert await embedder.embed_queries(["上传限制"]) == await embedder.embed_documents(
        ["上传限制"]
    )


async def test_empty_text_embeds_to_zero_vector() -> None:
    vector = (await FakeEmbedder(dimension=8).embed_documents([""]))[0]

    assert vector == [0.0] * 8


async def test_similar_text_has_higher_cosine_similarity_than_unrelated_text() -> None:
    embedder = FakeEmbedder()
    query, similar, unrelated = await embedder.embed_documents(
        ["知识库上传文件大小", "上传文件的大小限制", "数据库连接超时设置"]
    )

    assert _cosine(query, similar) > _cosine(query, unrelated)


async def test_reranker_scores_are_in_unit_range_and_rank_relevant_first() -> None:
    reranker = FakeReranker()

    scores = await reranker.rerank("上传文件大小", ["上传文件大小限制", "数据库连接超时设置", ""])

    assert all(0.0 <= score <= 1.0 for score in scores)
    assert scores[0] > scores[1]
    assert scores[2] == 0.0


async def test_chat_model_returns_scripted_answers_in_order_and_records_calls() -> None:
    model = FakeChatModel(responses=["第一", "第二"])
    messages = [ChatMessage(role="user", content="你好吗")]

    first = await model.complete(messages)
    second = await model.complete(messages, json_mode=True)

    assert (first.text, second.text) == ("第一", "第二")
    assert first.model == "fake"
    assert first.prompt_tokens == 1  # 3 个字符，按每 2 个字符 1 个 token 估算
    assert model.calls == [messages, messages]


async def test_chat_model_echoes_last_user_message_without_script() -> None:
    model = FakeChatModel()

    completion = await model.complete(
        [
            ChatMessage(role="system", content="规则"),
            ChatMessage(role="user", content="问题"),
            ChatMessage(role="assistant", content="回答"),
        ]
    )

    assert completion.text == "问题"


async def test_chat_model_echo_is_empty_when_there_is_no_user_message() -> None:
    completion = await FakeChatModel().complete([ChatMessage(role="system", content="规则")])

    assert completion.text == ""


async def test_chat_model_fails_loudly_when_script_runs_out() -> None:
    model = FakeChatModel(responses=["唯一"])
    messages = [ChatMessage(role="user", content="x")]
    await model.complete(messages)

    with pytest.raises(RuntimeError, match="用完"):
        await model.complete(messages)
