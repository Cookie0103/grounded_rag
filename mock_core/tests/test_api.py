from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import ClassVar

import httpx
import pytest

from mock_core.main import create_app

pytestmark = pytest.mark.anyio
CUSTOMER = {"customer_id": "C0001"}
CONTRACT = {"customer_id": "C0001", "contract_id": "L0001"}
OWNER = {"X-Agent-Id": "A001"}
OUTSIDER = {"X-Agent-Id": "A002"}
ROUTES = [
    ("/loan-contracts", CUSTOMER),
    ("/repayment-schedule", CONTRACT),
    ("/delinquency", CUSTOMER),
    ("/rate-terms", CONTRACT),
    ("/benefits", CUSTOMER),
]


class SeededDatabase:
    """在无 MySQL 的测试中提供固定归属及业务响应。"""

    customers: ClassVar[set[tuple[str, str]]] = {("A001", "C0001"), ("A020", "C0001")}
    contracts: ClassVar[dict[str, str]] = {"L0001": "C0001", "L0002": "C0002"}

    async def is_authorized(
        self, agent_id: str, customer_id: str, contract_id: str | None = None
    ) -> bool:
        return (agent_id, customer_id) in self.customers and (
            contract_id is None or self.contracts.get(contract_id) == customer_id
        )

    async def loan_contracts(self, customer_id: str) -> list[dict[str, str | int]]:
        return [
            {
                "contract_id": "L0001",
                "product": "変動セレクト住宅ローン",
                "principal_yen": 30_000_000,
                "disbursed_on": "2024-01-15",
                "status": "返済中",
            }
        ]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@asynccontextmanager
async def _client() -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    app.state.database = SeededDatabase()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client


@pytest.mark.parametrize(("path", "params"), ROUTES)
async def test_business_reads_require_agent_and_block_outsiders_before_faults(
    path: str, params: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MOCK_ALLOW_FAULT_HEADERS", "true")
    async with _client() as client:
        assert (await client.get(path, params=params)).status_code == 401
        response = await client.get(
            path, params=params, headers={**OUTSIDER, "X-Mock-Fault": "5xx"}
        )
    assert response.status_code == 403


async def test_contract_belonging_to_another_customer_is_denied_with_no_lookup() -> None:
    params = {**CONTRACT, "contract_id": "L0002"}

    async with _client() as client:
        assert (await client.get("/authorization", params=params, headers=OWNER)).json() == {
            "authorized": False,
        }
        assert (await client.get("/rate-terms", params=params, headers=OWNER)).status_code == 403


async def test_fault_header_requires_opt_in_and_applies_after_authorization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = {**OWNER, "X-Mock-Fault": "5xx"}
    monkeypatch.setenv("MOCK_ALLOW_FAULT_HEADERS", "false")
    async with _client() as client:
        response = await client.get("/loan-contracts", params=CUSTOMER, headers=headers)
        assert response.status_code == 200
        assert response.json()["synthetic"] is True
        assert response.json()["total"] == 1
        assert (
            await client.post("/loan-contracts", params=CUSTOMER, headers=OWNER)
        ).status_code == 405

    monkeypatch.setenv("MOCK_ALLOW_FAULT_HEADERS", "true")
    async with _client() as client:
        assert (
            await client.get("/loan-contracts", params=CUSTOMER, headers=headers)
        ).status_code == 503
        assert (
            await client.get("/authorization", params=CONTRACT, headers=headers)
        ).status_code == 503
        assert (await client.get("/authorization", params=CONTRACT, headers=OWNER)).json() == {
            "authorized": True,
        }


async def test_endpoint_fault_rate_overrides_global_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MOCK_FAULT_5XX_RATE", "0")
    monkeypatch.setenv("MOCK_FAULT_LOAN_CONTRACTS_5XX_RATE", "1")
    async with _client() as client:
        assert (
            await client.get("/authorization", params=CONTRACT, headers=OWNER)
        ).status_code == 200
        assert (
            await client.get("/loan-contracts", params=CUSTOMER, headers=OWNER)
        ).status_code == 503
