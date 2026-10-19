from fastapi import FastAPI
from httpx import AsyncClient

from app.core.errors import AppError


class TeapotError(AppError):
    code = "TEAPOT"
    status_code = 418


def _assert_unified(body: dict[str, object], code: str, trace_id: str) -> None:
    error = body["error"]
    assert isinstance(error, dict)
    assert error["code"] == code
    assert body["trace_id"] == trace_id


async def test_unknown_path_returns_404_in_unified_format(client: AsyncClient) -> None:
    response = await client.get("/nope")

    assert response.status_code == 404
    _assert_unified(response.json(), "NOT_FOUND", response.headers["X-Trace-Id"])


async def test_wrong_method_returns_405(client: AsyncClient) -> None:
    response = await client.post("/health")

    assert response.status_code == 405
    _assert_unified(response.json(), "METHOD_NOT_ALLOWED", response.headers["X-Trace-Id"])


async def test_validation_error_returns_422_with_field_in_message(
    app: FastAPI, client: AsyncClient
) -> None:
    @app.get("/items/{item_id}")
    async def read_item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    response = await client.get("/items/abc")

    assert response.status_code == 422
    body = response.json()
    _assert_unified(body, "INVALID_REQUEST", response.headers["X-Trace-Id"])
    assert "item_id" in body["error"]["message"]


async def test_app_error_subclass_uses_its_own_code_and_status(
    app: FastAPI, client: AsyncClient
) -> None:
    @app.get("/teapot")
    async def teapot() -> None:
        raise TeapotError("我是茶壶")

    response = await client.get("/teapot")

    assert response.status_code == 418
    assert response.json()["error"] == {"code": "TEAPOT", "message": "我是茶壶"}


async def test_unexpected_error_returns_500_without_leaking_details(
    app: FastAPI, client: AsyncClient
) -> None:
    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("secret internal detail")

    response = await client.get("/boom")

    assert response.status_code == 500
    assert "secret internal detail" not in response.text
    _assert_unified(response.json(), "INTERNAL_ERROR", response.headers["X-Trace-Id"])
