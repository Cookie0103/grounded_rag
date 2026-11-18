"""OpenAI 兼容对话客户端和 DeepSeek 用量计费。"""

import asyncio
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
from app.providers.base import ChatMessage, Completion
from app.providers.budget import BudgetLedger

TIMEOUT_SECONDS = 60.0
RETRIES = 2
RETRY_STATUSES = (429, 500, 502, 503, 504)
HTTP_ERROR_STATUS = 400


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

    async def complete(self, messages: list[ChatMessage], *, json_mode: bool = False) -> Completion:
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
        data = await self._post(body)
        usage = data.get("usage", {})
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
        amount = (
            0.0 if self._is_free else cost_cny(prompt_tokens, completion_tokens, model=self._model)
        )
        completion = Completion(
            text=data["choices"][0]["message"]["content"] or "",
            model=data.get("model", self._model),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_cny=amount,
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
