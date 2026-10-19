from fastapi import FastAPI
from httpx import AsyncClient

from app.api.health import DatabasePing, get_database_ping
from app.core.errors import DependencyUnavailableError


def _use_ping(app: FastAPI, ping: DatabasePing) -> None:
    app.dependency_overrides[get_database_ping] = lambda: ping


async def _database_ok() -> None:
    return None


async def _database_down() -> None:
    raise DependencyUnavailableError("数据库不可用")


async def test_health_ok_returns_status_and_matching_trace_id(
    app: FastAPI, client: AsyncClient
) -> None:
    _use_ping(app, _database_ok)

    response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert (body["status"], body["database"]) == ("ok", "ok")
    assert body["trace_id"] == response.headers["X-Trace-Id"]


async def test_health_returns_503_in_unified_format_when_database_is_down(
    app: FastAPI, client: AsyncClient
) -> None:
    _use_ping(app, _database_down)

    response = await client.get("/health")

    assert response.status_code == 503
    assert response.json() == {
        "error": {"code": "DEPENDENCY_UNAVAILABLE", "message": "数据库不可用"},
        "trace_id": response.headers["X-Trace-Id"],
    }


async def test_valid_incoming_trace_id_is_reused(app: FastAPI, client: AsyncClient) -> None:
    _use_ping(app, _database_ok)

    response = await client.get("/health", headers={"X-Trace-Id": "req-123"})

    assert response.headers["X-Trace-Id"] == "req-123"
    assert response.json()["trace_id"] == "req-123"


async def test_invalid_incoming_trace_id_is_replaced(app: FastAPI, client: AsyncClient) -> None:
    _use_ping(app, _database_ok)

    response = await client.get("/health", headers={"X-Trace-Id": "bad id;"})

    assert response.headers["X-Trace-Id"] != "bad id;"
    assert response.json()["trace_id"] == response.headers["X-Trace-Id"]
