"""OpenAI 兼容对话客户端和 DeepSeek 用量计费。"""

import asyncio
import json
import math
import re
from collections.abc import Sequence
from typing import Any

import httpx

from app.core.config import (
    DEEPSEEK_INPUT_USD_PER_MILLION,
    DEEPSEEK_OUTPUT_USD_PER_MILLION,
    DEEPSEEK_PRO_INPUT_USD_PER_MILLION,
    DEEPSEEK_PRO_OUTPUT_USD_PER_MILLION,
    USD_TO_CNY,
)
from app.core.errors import ConfigError, DependencyUnavailableError
from app.providers.base import ChatMessage, Completion, FunctionCall, FunctionTool
from app.providers.budget import BudgetLedger

TIMEOUT_SECONDS = 60.0
RETRIES = 2
RETRY_STATUSES = (429, 500, 502, 503, 504)
HTTP_ERROR_STATUS = 400
UNAVAILABLE_LOGPROB = -9999.0
INTENT_FIELD = re.compile(r'[{,]\s*"intent"\s*:\s*"([^"\\]+)"')


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
        if not self._api_key:
            raise ConfigError(f"没有配置 {self.api_key_name}")
        if self._ledger is not None:
            self._ledger.check()
        body: dict[str, Any] = {
            "model": self._model,
            "messages": [message.model_dump() for message in messages],
            "temperature": 0,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        if tools:
            body["tools"] = [{"type": "function", "function": tool.model_dump()} for tool in tools]
        if logprobs and self._supports_logprobs:
            body["logprobs"] = True
        data = await self._post(body)
        usage = data.get("usage", {})
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
        amount = (
            0.0 if self._is_free else cost_cny(prompt_tokens, completion_tokens, model=self._model)
        )
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

    async def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._api_key}"}
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
        if response.status_code >= HTTP_ERROR_STATUS:
            raise DependencyUnavailableError(f"{self.provider_name} 返回 {response.status_code}")
        parsed: dict[str, Any] = response.json()
        return parsed


class DeepSeekChat(OpenAIChat):
    """兼容保留第一版的直接接入方式。"""
