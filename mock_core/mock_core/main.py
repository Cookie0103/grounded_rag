"""只读住宅贷款模拟 HTTP API。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request

from .config import Endpoint, FaultInjector, MysqlSettings
from .database import Database, create_pool
from .seed import initialize


def _require_agent(agent_id: Annotated[str | None, Header(alias="X-Agent-Id")] = None) -> str:
    if agent_id is None or not agent_id.strip():
        raise HTTPException(status_code=401, detail="担当者IDが必要です")
    return agent_id


type AgentId = Annotated[str, Depends(_require_agent)]
type CustomerId = Annotated[str, Query(min_length=1, max_length=16)]
type ContractId = Annotated[str, Query(min_length=1, max_length=16)]
type OptionalContractId = Annotated[str | None, Query(min_length=1, max_length=16)]
type OptionalPeriod = Annotated[int | None, Query(ge=1)]
type Result = dict[str, object]


@asynccontextmanager
async def _lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings = MysqlSettings.from_env()
    pool = await create_pool(settings)
    try:
        await initialize(pool, settings.database)
        application.state.database = Database(pool)
        yield
    finally:
        pool.close()
        await pool.wait_closed()


def _envelope(data: Result, total: int | None = None) -> Result:
    return {"synthetic": True, "data": data, "total": total}


async def _authorize(
    request: Request, endpoint: Endpoint, agent_id: str, customer_id: str, contract_id: str | None
) -> bool:
    database: Database = request.app.state.database
    if not await database.is_authorized(agent_id, customer_id, contract_id):
        return False
    faults: FaultInjector = request.app.state.faults
    await faults.apply(endpoint, request.headers.get("X-Mock-Fault"))
    return True


async def _require_access(
    request: Request,
    endpoint: Endpoint,
    agent_id: str,
    customer_id: str,
    contract_id: str | None = None,
) -> Database:
    if not await _authorize(request, endpoint, agent_id, customer_id, contract_id):
        raise HTTPException(status_code=403, detail="担当外の照会です")
    return request.app.state.database


def create_app() -> FastAPI:
    """创建住宅贷款模拟 API。"""
    application = FastAPI(title="住宅ローン業務 API（synthetic）", lifespan=_lifespan)
    application.state.faults = FaultInjector()

    @application.get("/health")
    async def health(request: Request) -> Result:
        database: Database = request.app.state.database
        if not await database.is_healthy():
            raise HTTPException(status_code=503, detail="模擬データベースに接続できません")
        return {"status": "ok", "synthetic": True}

    @application.get("/authorization")
    async def authorization(
        request: Request,
        agent_id: AgentId,
        customer_id: CustomerId,
        contract_id: OptionalContractId = None,
    ) -> dict[str, bool]:
        is_authorized = await _authorize(
            request, "authorization", agent_id, customer_id, contract_id
        )
        return {"authorized": is_authorized}

    @application.get("/loan-contracts")
    async def loan_contracts(
        request: Request, agent_id: AgentId, customer_id: CustomerId
    ) -> Result:
        database = await _require_access(request, "loan-contracts", agent_id, customer_id)
        contracts = await database.loan_contracts(customer_id)
        return _envelope({"contracts": contracts}, len(contracts))

    @application.get("/repayment-schedule")
    async def repayment_schedule(
        request: Request,
        agent_id: AgentId,
        customer_id: CustomerId,
        contract_id: ContractId,
        start_period: OptionalPeriod = None,
        end_period: OptionalPeriod = None,
    ) -> Result:
        database = await _require_access(
            request, "repayment-schedule", agent_id, customer_id, contract_id
        )
        if start_period is not None and end_period is not None and start_period > end_period:
            raise HTTPException(status_code=422, detail="返済回の範囲が無効です")
        data, total = await database.repayment_schedule(contract_id, start_period, end_period)
        return _envelope(data, total)

    @application.get("/delinquency")
    async def delinquency(request: Request, agent_id: AgentId, customer_id: CustomerId) -> Result:
        database = await _require_access(request, "delinquency", agent_id, customer_id)
        return _envelope(await database.delinquency(customer_id))

    @application.get("/rate-terms")
    async def rate_terms(
        request: Request, agent_id: AgentId, customer_id: CustomerId, contract_id: ContractId
    ) -> Result:
        database = await _require_access(request, "rate-terms", agent_id, customer_id, contract_id)
        return _envelope(await database.rate_terms(contract_id))

    @application.get("/benefits")
    async def benefits(request: Request, agent_id: AgentId, customer_id: CustomerId) -> Result:
        database = await _require_access(request, "benefits", agent_id, customer_id)
        rows = await database.benefits(customer_id)
        return _envelope({"benefits": rows}, len(rows))

    return application


app = create_app()
