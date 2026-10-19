"""POST /chat：问答。`stream=true` 时用 SSE 推每个环节的进度，最后推完整回答。"""

import json
import logging
from collections.abc import AsyncIterator
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, StringConstraints

from app.api.services import enforce_rate_limit, get_services
from app.core.errors import AppError
from app.core.trace import trace_id_var
from app.orchestration.factory import Services
from app.orchestration.models import ChatRequest, ChatResponse, Citation, Step

router = APIRouter(dependencies=[Depends(enforce_rate_limit)])
logger = logging.getLogger(__name__)

MAX_QUESTION_CHARS = 500


class ChatBody(BaseModel):
    question: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_QUESTION_CHARS)
    ]
    edition: Literal["self_host", "cloud"] | None = None
    session_id: Annotated[str, StringConstraints(min_length=1, max_length=100)] | None = None
    stream: bool = False


class ChatOut(BaseModel):
    trace_id: str
    answer: str
    route: str
    citations: list[Citation]
    retrieved_docs: list[str]
    steps: list[Step]
    cost_cny: float
    abstained: bool
    degraded: bool
    cached: bool
    standalone_question: str | None = None


def _out(response: ChatResponse) -> ChatOut:
    return ChatOut(trace_id=trace_id_var.get(), **response.model_dump(exclude={"contexts"}))


def _event(name: str, data: object) -> str:
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _sse(services: Services, request: ChatRequest) -> AsyncIterator[str]:
    try:
        async for item in services.chat.stream(request):
            if isinstance(item, ChatResponse):
                yield _event("answer", _out(item).model_dump())
            else:
                yield _event("step", item.model_dump())
    except AppError as error:
        yield _event("error", {"code": error.code, "message": error.message})
    except RuntimeError:
        logger.exception("流式问答出错")
        yield _event("error", {"code": "INTERNAL_ERROR", "message": "服务内部错误"})


@router.post("/chat", response_model=None)
async def chat(
    body: ChatBody, services: Annotated[Services, Depends(get_services)]
) -> ChatOut | StreamingResponse:
    request = ChatRequest(question=body.question, edition=body.edition, session_id=body.session_id)
    if body.stream:
        return StreamingResponse(
            _sse(services, request),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    return _out(await services.chat.answer(request))
