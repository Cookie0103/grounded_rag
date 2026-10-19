"""请求级 trace_id。"""

import re
import uuid
from contextvars import ContextVar

TRACE_HEADER = "X-Trace-Id"
NO_TRACE = "-"

trace_id_var: ContextVar[str] = ContextVar("trace_id", default=NO_TRACE)

_VALID_TRACE_ID = re.compile(r"[A-Za-z0-9-]{1,64}")


def new_trace_id() -> str:
    return uuid.uuid4().hex


def is_valid_trace_id(value: str) -> bool:
    """调用方传入的 trace_id 只接受字母、数字、短横线，长度不超过 64。"""
    return _VALID_TRACE_ID.fullmatch(value) is not None
