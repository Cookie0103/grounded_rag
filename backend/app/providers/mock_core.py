"""模拟核心业务系统的只读 HTTP 适配器。"""

from http import HTTPStatus
from typing import Literal, Protocol

import httpx
from pydantic import BaseModel

type MockCoreStatus = Literal["ok", "denied", "timeout", "upstream_error", "invalid_response"]


class MockCoreRequest(BaseModel):
    agent_id: str
    customer_id: str
    contract_id: str | None = None
    start_period: int | None = None
    end_period: int | None = None


class MockCoreReply(BaseModel):
    status: MockCoreStatus
    body: object = None


class MockCoreTransport(Protocol):
    async def get(
        self, path: str, request: MockCoreRequest, *, timeout_seconds: float
    ) -> MockCoreReply:
        """读取业务端点，统一转换传输结果。"""


class MockCoreClient:
    def __init__(
        self,
        base_url: str,
        *,
        client: httpx.AsyncClient | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(transport=transport, trust_env=False)

    async def get(
        self, path: str, request: MockCoreRequest, *, timeout_seconds: float
    ) -> MockCoreReply:
        """发送带可信坐席头和客户范围的 GET 请求。"""
        try:
            response = await self._client.get(
                f"{self._base_url}{path}",
                params=request.model_dump(exclude={"agent_id"}, exclude_none=True),
                headers={"X-Agent-Id": request.agent_id},
                timeout=timeout_seconds,
            )
        except httpx.TimeoutException:
            return MockCoreReply(status="timeout")
        except (httpx.RequestError, httpx.InvalidURL):
            return MockCoreReply(status="upstream_error")
        return _read_response(response)

    async def aclose(self) -> None:
        """关闭适配器自行创建的客户端。"""
        if self._owns_client:
            await self._client.aclose()


def _read_response(response: httpx.Response) -> MockCoreReply:
    if response.status_code in {HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN}:
        return MockCoreReply(status="denied")
    if response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
        return MockCoreReply(status="upstream_error")
    if not response.is_success:
        return MockCoreReply(status="invalid_response")
    try:
        return MockCoreReply(status="ok", body=response.json())
    except ValueError:
        return MockCoreReply(status="invalid_response")
