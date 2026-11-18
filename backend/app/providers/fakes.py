"""离线假实现：确定性、有「语义」（字面越像越相似），供单元测试使用。"""

import hashlib
import math
from collections.abc import Sequence

from app.providers.base import ChatMessage, Completion, FunctionTool

FAKE_MODEL_NAME = "fake"
DEFAULT_DIMENSION = 1024
CHARS_PER_TOKEN = 2  # 粗略估算，只用于假实现的 token 数


def char_bigrams(text: str) -> set[str]:
    """去掉空白后的字符二元组；只有一个字符时返回该字符本身。"""
    chars = "".join(text.split())
    if not chars:
        return set()
    if len(chars) == 1:
        return {chars}
    return {chars[i : i + 2] for i in range(len(chars) - 1)}


def _bigram_dimension(bigram: str, dimension: int) -> int:
    digest = hashlib.sha1(bigram.encode("utf-8"), usedforsecurity=False).hexdigest()
    return int(digest, 16) % dimension


class FakeEmbedder:
    """把二元组哈希到固定维度再归一化，字面相似的文本余弦相似度更高。"""

    def __init__(self, dimension: int = DEFAULT_DIMENSION) -> None:
        self.name = FAKE_MODEL_NAME
        self.dimension = dimension

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for bigram in char_bigrams(text):
            vector[_bigram_dimension(bigram, self.dimension)] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector

    async def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]


class FakeReranker:
    """分数 = 查询和文档二元组集合的 Jaccard 相似度。"""

    def __init__(self) -> None:
        self.name = FAKE_MODEL_NAME

    async def rerank(self, query: str, documents: list[str]) -> list[float]:
        query_grams = char_bigrams(query)
        scores: list[float] = []
        for document in documents:
            document_grams = char_bigrams(document)
            union = query_grams | document_grams
            scores.append(len(query_grams & document_grams) / len(union) if union else 0.0)
        return scores


class FakeChatModel:
    """返回预设文本或完成响应，没有预设时回显最后一条 user 消息。"""

    def __init__(self, responses: Sequence[str | Completion] | None = None) -> None:
        self._responses = list(responses) if responses is not None else None
        self._next = 0
        self.calls: list[list[ChatMessage]] = []
        self.offered_tools: list[list[FunctionTool] | None] = []

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        json_mode: bool = False,
        tools: Sequence[FunctionTool] | None = None,
        logprobs: bool = False,
    ) -> Completion:
        self.calls.append(list(messages))
        self.offered_tools.append(list(tools) if tools is not None else None)
        response = self._next_response(messages)
        if isinstance(response, Completion):
            return response
        prompt_chars = sum(len(message.content) for message in messages)
        return Completion(
            text=response,
            model=FAKE_MODEL_NAME,
            prompt_tokens=prompt_chars // CHARS_PER_TOKEN,
            completion_tokens=len(response) // CHARS_PER_TOKEN,
        )

    def _next_response(self, messages: list[ChatMessage]) -> str | Completion:
        if self._responses is None:
            user_messages = [message for message in messages if message.role == "user"]
            return user_messages[-1].content if user_messages else ""
        if self._next >= len(self._responses):
            raise RuntimeError("FakeChatModel 的预设回答已用完")
        response = self._responses[self._next]
        self._next += 1
        return response
