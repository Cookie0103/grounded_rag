"""统一错误格式：{"error": {"code", "message"}, "trace_id"}。"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AppError
from app.core.trace import NO_TRACE, TRACE_HEADER

logger = logging.getLogger(__name__)

_HTTP_ERROR_CODES = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}


def _trace_id(request: Request) -> str:
    return str(getattr(request.state, "trace_id", NO_TRACE))


def error_response(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    trace_id = _trace_id(request)
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}, "trace_id": trace_id},
        headers={TRACE_HEADER: trace_id},
    )


async def handle_app_error(request: Request, exc: Exception) -> JSONResponse:
    error = exc if isinstance(exc, AppError) else AppError(str(exc))
    return error_response(request, error.status_code, error.code, error.message)


async def handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    details = exc.errors() if isinstance(exc, RequestValidationError) else []
    message = "; ".join(f"{'.'.join(map(str, item['loc']))}: {item['msg']}" for item in details)
    return error_response(request, 422, "INVALID_REQUEST", message or "请求参数不合法")


async def handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    status_code = exc.status_code if isinstance(exc, StarletteHTTPException) else 500
    detail = exc.detail if isinstance(exc, StarletteHTTPException) else str(exc)
    code = _HTTP_ERROR_CODES.get(status_code, "HTTP_ERROR")
    return error_response(request, status_code, code, detail)


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.error("未捕获的异常", exc_info=exc)
    return error_response(request, 500, "INTERNAL_ERROR", "服务器内部错误")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(Exception, handle_unexpected_error)
