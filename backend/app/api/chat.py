"""问答和可续推的 SSE 接口。"""

import logging
from collections.abc import AsyncIterator
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, StringConstraints

from app.api.chat_replay import ChatStreams, OutgoingEvent
from app.api.services import enforce_rate_limit, get_services
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.trace import trace_id_var
from app.db.policy_filter import MetaFilter
from app.orchestration.factory import Services
from app.orchestration.models import (
    AnswerDelta,
    AnswerRetraction,
    Channel,
    ChatRequest,
    ChatResponse,
    Citation,
    Intent,
    Step,
)
from app.providers.mock_core import EvaluationFault, evaluation_fault
from app.tools.middleware import ToolTrace

router = APIRouter(dependencies=[Depends(enforce_rate_limit)])
logger = logging.getLogger(__name__)

MAX_QUESTION_CHARS = 500
Identity = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]


class ChatBody(BaseModel):
    question: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_QUESTION_CHARS)
    ]
    edition: Literal["self_host", "cloud"] | None = None
    session_id: Annotated[str, StringConstraints(min_length=1, max_length=100)] | None = None
    channel: Channel = "customer"
    agent_id: Identity | None = None
    customer_id: Identity | None = None
    filter: MetaFilter | None = None
    rerank: bool = False
    stream: bool = False


class ChatOut(BaseModel):
    trace_id: str
    answer: str
    intent: Intent | None
    secondary_intent: Intent | None
    tool_calls: list[ToolTrace]
    prompt_tokens: int
    completion_tokens: int
    synthetic: bool
    first_token_ms: float | None = None
    total_ms: float | None = None
    citations: list[Citation]
    retrieved_docs: list[str]
    steps: list[Step]
    cost_cny: float
    abstained: bool
    degraded: bool
    cached: bool
    standalone_question: str | None = None


def _out(response: ChatResponse) -> ChatOut:
    return ChatOut(
        trace_id=trace_id_var.get(),
        steps=[_public_step(step) for step in response.steps],
        **response.model_dump(exclude={"contexts", "route", "steps"}),
    )


def _public_step(step: Step) -> Step:
    if step.name == "output_guard" and step.details is not None:
        return step.model_copy(update={"details": step.details.model_copy(update={"output": None})})
    return step


async def _events(services: Services, request: ChatRequest) -> AsyncIterator[OutgoingEvent]:
    try:
        async for item in services.chat.stream(request, stream_tokens=True):
            if isinstance(item, ChatResponse):
                yield OutgoingEvent("answer", _out(item).model_dump(mode="json"))
            elif isinstance(item, AnswerDelta):
                yield OutgoingEvent("delta", item.model_dump(mode="json"))
            elif isinstance(item, AnswerRetraction):
                yield OutgoingEvent("retract", item.model_dump(mode="json"))
            else:
                yield OutgoingEvent("step", _public_step(item).model_dump(mode="json"))
    except AppError as error:
        yield OutgoingEvent("error", {"code": error.code, "message": error.message})
    except RuntimeError:
        logger.exception("流式问答出错")
        yield OutgoingEvent("error", {"code": "INTERNAL_ERROR", "message": "服务内部错误"})


def _streams(request: Request) -> ChatStreams:
    streams: ChatStreams = request.app.state.chat_streams
    return streams


@router.post("/chat", response_model=None)
async def chat(
    body: ChatBody,
    services: Annotated[Services, Depends(get_services)],
    streams: Annotated[ChatStreams, Depends(_streams)],
    http_request: Request,
    mock_fault: Annotated[EvaluationFault | None, Header(alias="X-Eval-Fault")] = None,
) -> ChatOut | StreamingResponse:
    request = ChatRequest(
        question=body.question,
        edition=body.edition,
        session_id=body.session_id,
        channel=body.channel,
        agent_id=body.agent_id if body.channel == "agent" else None,
        customer_id=body.customer_id if body.channel == "agent" else None,
        filter=body.filter,
        rerank=body.rerank,
    )
    if mock_fault is not None and not _allow_fault(http_request):
        raise HTTPException(status_code=403, detail="合成评测故障仅允许本机显式开启")
    scope = evaluation_fault.set(mock_fault)
    try:
        if body.stream:
            return await streams.start(_events(services, request))
        return _out(await services.chat.answer(request))
    finally:
        evaluation_fault.reset(scope)


def _allow_fault(request: Request) -> bool:
    return (
        get_settings().evaluation_mock_faults
        and request.client is not None
        and request.client.host in {"127.0.0.1", "::1"}
    )


@router.get("/chat/stream/{response_id}", response_model=None)
async def resume_chat(
    response_id: Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")],
    streams: Annotated[ChatStreams, Depends(_streams)],
    last_id: Annotated[int, Header(alias="Last-Event-ID", ge=0, le=2**63 - 1)] = 0,
) -> StreamingResponse:
    return await streams.resume(response_id, last_id)
