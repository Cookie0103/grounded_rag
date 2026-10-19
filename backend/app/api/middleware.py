"""trace_id 中间件：沿用合法的请求头，否则新生成；每个响应都带 X-Trace-Id。"""

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.trace import TRACE_HEADER, is_valid_trace_id, new_trace_id, trace_id_var


class TraceMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get(TRACE_HEADER)
        trace_id = incoming if incoming and is_valid_trace_id(incoming) else new_trace_id()
        # 错误处理器通过 request.state 读取，未捕获异常的 500 响应也能带上它
        scope.setdefault("state", {})["trace_id"] = trace_id
        token = trace_id_var.set(trace_id)

        async def send_with_trace(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)[TRACE_HEADER] = trace_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_trace)
        finally:
            trace_id_var.reset(token)
