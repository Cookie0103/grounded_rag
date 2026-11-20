"""OpenAI 兼容对话客户端和 DeepSeek 用量计费。"""

import asyncio
import json
import math
import re
from collections.abc import AsyncGenerator, AsyncIterator, Sequence
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.core.config import (
    DEEPSEEK_INPUT_USD_PER_MILLION,
    DEEPSEEK_OUTPUT_USD_PER_MILLION,
    DEEPSEEK_PRO_INPUT_USD_PER_MILLION,
    DEEPSEEK_PRO_OUTPUT_USD_PER_MILLION,
    USD_TO_CNY,
)
from app.core.errors import ConfigError, DependencyUnavailableError
from app.providers.base import ChatDelta, ChatMessage, Completion, FunctionCall, FunctionTool
from app.providers.budget import BudgetLedger

TIMEOUT_SECONDS = 60.0
RETRIES = 2
RETRY_STATUSES = (429, 500, 502, 503, 504)
HTTP_ERROR_STATUS = 400
UNAVAILABLE_LOGPROB = -9999.0
INTENT_FIELD = re.compile(r'[{,]\s*"intent"\s*:\s*"([^"\\]+)"')


class _StreamUsage(BaseModel):
    prompt_tokens: int | None = Field(default=None, ge=0, strict=True)
    completion_tokens: int | None = Field(default=None, ge=0, strict=True)


class _StreamChoice(BaseModel):
    delta: dict[str, Any] | None = None


class _StreamChunk(BaseModel):
    model: str | None = None
    choices: list[_StreamChoice] = Field(default_factory=list)
    usage: _StreamUsage | None = None
    error: Any = None

    def visible_text(self) -> str:
        delta = self.choices[0].delta if self.choices else None
        content = delta.get("content") if delta is not None else None
        return content if isinstance(content, str) else ""


async def _sse_data(response: httpx.Response) -> AsyncIterator[str]:
    response.encoding = "utf-8-sig"
    lines: list[str] = []
    async for line in response.aiter_lines():
        if not line and lines:
            yield "\n".join(lines)
            lines.clear()
        elif line == "data" or line.startswith("data:"):
            lines.append(line.partition(":")[2].removeprefix(" "))


def _intent_span(text: str) -> tuple[int, int] | None:
    matches = list(INTENT_FIELD.finditer(text))
    if len(matches) != 1:
        return None
    match = matches[0]
    try:
        classification = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(classification, dict) or classification.get("intent") != match[1]:
        return None
    return match.span(1)


def _intent_confidence(text: str, logprobs: Any) -> float | None:
    if not isinstance(logprobs, dict) or not isinstance(tokens := logprobs.get("content"), list):
        return None
    span = _intent_span(text)
    if span is None:
        return None
    start, end = span
    offset = 0
    scores: list[float] = []
    for token in tokens:
        token_text = token.get("token") if isinstance(token, dict) else None
        if (
            not isinstance(token_text, str)
            or not token_text
            or not text.startswith(token_text, offset)
        ):
            return None
        token_end = offset + len(token_text)
        if offset < end and token_end > start:
            score = token.get("logprob")
            if not _is_available_logprob(score):
                return None
            scores.append(score)
        offset = token_end
    # 只连乘覆盖主意图值的 token 概率，免受 JSON 键名和格式影响。
    return math.exp(sum(scores)) if scores and offset == len(text) else None


def _is_available_logprob(score: Any) -> bool:
    return (
        isinstance(score, (int, float))
        and not isinstance(score, bool)
        and UNAVAILABLE_LOGPROB < score <= 0
    )


def cost_cny(prompt_tokens: int, completion_tokens: int, *, model: str = "deepseek-flash") -> float:
    """按公开的高峰、缓存未命中单价保守记账。"""
    input_price = DEEPSEEK_INPUT_USD_PER_MILLION
    output_price = DEEPSEEK_OUTPUT_USD_PER_MILLION
    if model.startswith("deepseek-v4-pro"):
        input_price = DEEPSEEK_PRO_INPUT_USD_PER_MILLION
        output_price = DEEPSEEK_PRO_OUTPUT_USD_PER_MILLION
    usd = (prompt_tokens * input_price + completion_tokens * output_price) / 1_000_000
    return usd * USD_TO_CNY


def completion_cost_cny(completion: Completion) -> float:
    """优先使用提供方记录的费用，兼容旧的完成响应。"""
    if completion.cost_cny is not None:
        return completion.cost_cny
    return cost_cny(completion.prompt_tokens, completion.completion_tokens)


class OpenAIChat:
    provider_name = "DeepSeek"
    api_key_name = "DEEPSEEK_API_KEY"
    _supports_logprobs = True

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        model: str,
        ledger: BudgetLedger | None = None,
        client: httpx.AsyncClient | None = None,
        retry_delay_seconds: float = 1.0,
        is_free: bool = False,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._ledger = ledger
        self._client = client or httpx.AsyncClient(base_url=base_url, timeout=TIMEOUT_SECONDS)
        self._retry_delay = retry_delay_seconds
        self._is_free = is_free

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        json_mode: bool = False,
        tools: Sequence[FunctionTool] | None = None,
        logprobs: bool = False,
    ) -> Completion:
        headers = self._request_headers()
        body = self._request_body(messages)
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        if tools:
            body["tools"] = [{"type": "function", "function": tool.model_dump()} for tool in tools]
        if logprobs and self._supports_logprobs:
            body["logprobs"] = True
        data = await self._post(body, headers)
        usage = data.get("usage", {})
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
        amount = self._cost(prompt_tokens, completion_tokens)
        choice = data["choices"][0]
        message = choice["message"]
        text = message.get("content") or ""
        completion = Completion(
            text=text,
            model=data.get("model", self._model),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_cny=amount,
            tool_calls=[
                FunctionCall.model_validate(call["function"])
                for call in message.get("tool_calls") or []
                if call.get("type") == "function"
            ],
            confidence=_intent_confidence(text, choice.get("logprobs")) if logprobs else None,
        )
        if self._ledger is not None:
            self._ledger.add(amount)
        return completion

    async def stream(self, messages: list[ChatMessage]) -> AsyncGenerator[ChatDelta | Completion]:
        """逐段转发可见文本，并在结束事件后返回完整响应与上游用量。"""
        headers = self._request_headers()
        body = self._request_body(messages)
        body.update(stream=True, stream_options={"include_usage": True})
        model = self._model
        usage = _StreamUsage()
        parts: list[str] = []
        try:
            # 上游可能在首个可见片段前就已计费，流式请求只发一次。
            async with self._client.stream(
                "POST", "/chat/completions", json=body, headers=headers
            ) as response:
                self._check_status(response)
                async for data in _sse_data(response):
                    if data == "[DONE]":
                        break
                    chunk = _StreamChunk.model_validate_json(data)
                    if chunk.error is not None:
                        raise DependencyUnavailableError(f"{self.provider_name} 返回流式错误")
                    model = chunk.model or model
                    usage = chunk.usage if chunk.usage is not None else usage
                    if text := chunk.visible_text():
                        parts.append(text)
                        yield ChatDelta(text=text)
                else:
                    raise DependencyUnavailableError(f"{self.provider_name} 的模型流提前结束")
        except httpx.RequestError as error:
            raise DependencyUnavailableError(f"{self.provider_name} 的模型流中断") from error
        except ValidationError:
            raise DependencyUnavailableError(f"{self.provider_name} 返回无效的流式响应") from None
        finally:
            amount = self._record_stream_usage(usage)
        yield Completion(
            text="".join(parts),
            model=model,
            prompt_tokens=usage.prompt_tokens or 0,
            completion_tokens=usage.completion_tokens or 0,
            cost_cny=amount,
        )

    def _record_stream_usage(self, usage: _StreamUsage) -> float | None:
        if usage.prompt_tokens is None or usage.completion_tokens is None:
            return None
        amount = self._cost(usage.prompt_tokens, usage.completion_tokens)
        if self._ledger is not None and amount:
            self._ledger.add(amount)
        return amount

    def _request_headers(self) -> dict[str, str]:
        if not self._api_key:
            raise ConfigError(f"没有配置 {self.api_key_name}")
        if self._ledger is not None:
            self._ledger.check()
        return {"Authorization": f"Bearer {self._api_key}"}

    def _request_body(self, messages: list[ChatMessage]) -> dict[str, Any]:
        return {
            "model": self._model,
            "messages": [message.model_dump() for message in messages],
            "temperature": 0,
        }

    def _cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return (
            0.0 if self._is_free else cost_cny(prompt_tokens, completion_tokens, model=self._model)
        )

    async def _post(self, body: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        for attempt in range(RETRIES + 1):
            try:
                response = await self._client.post("/chat/completions", json=body, headers=headers)
            except httpx.TransportError as error:
                if attempt == RETRIES:
                    raise DependencyUnavailableError(
                        f"{self.provider_name} 不可用：{error!r}"
                    ) from error
            else:
                if response.status_code not in RETRY_STATUSES:
                    return self._parse(response)
                if attempt == RETRIES:
                    raise DependencyUnavailableError(
                        f"{self.provider_name} 返回 {response.status_code}"
                    )
            await asyncio.sleep(self._retry_delay * (attempt + 1))
        raise AssertionError("unreachable")  # pragma: no cover

    def _parse(self, response: httpx.Response) -> dict[str, Any]:
        self._check_status(response)
        parsed: dict[str, Any] = response.json()
        return parsed

    def _check_status(self, response: httpx.Response) -> None:
        if response.status_code >= HTTP_ERROR_STATUS:
            raise DependencyUnavailableError(f"{self.provider_name} 返回 {response.status_code}")


class DeepSeekChat(OpenAIChat):
    """兼容保留第一版的直接接入方式。"""
