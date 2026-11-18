"""模型提供方接口：业务代码只依赖这里的 Protocol，不直接用第三方 SDK。"""

from collections.abc import Sequence
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

ChatTier = Literal["small", "large"]


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class FunctionTool(BaseModel):
    """发给模型的函数名称、日文说明与 JSON Schema。"""

    name: str
    description: str
    parameters: dict[str, Any]


class FunctionCall(BaseModel):
    """模型提出的函数调用，参数保留原始字符串，留给工具层校验。"""

    name: str
    arguments: str


class Completion(BaseModel):
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_cny: float | None = None
    tool_calls: list[FunctionCall] = Field(default_factory=list)
    confidence: float | None = None


class ChatModel(Protocol):
    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        json_mode: bool = False,
        tools: Sequence[FunctionTool] | None = None,
        logprobs: bool = False,
    ) -> Completion: ...


class Embedder(Protocol):
    """查询和文档分开嵌入：Qwen3-Embedding 只给查询加指令。"""

    name: str
    dimension: int

    async def embed_queries(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


class Reranker(Protocol):
    name: str

    async def rerank(self, query: str, documents: list[str]) -> list[float]:
        """每个文档一个 0～1 的分数，顺序与输入一致。"""
        ...
