"""GET /traces/{trace_id}（复盘一次问答）和 POST /feedback（对某次回答打分）。"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, StringConstraints

from app.api.services import get_services
from app.core.errors import DependencyUnavailableError, TraceNotFoundError
from app.core.records import FeedbackIn, TraceRecord
from app.orchestration.factory import Services
from app.orchestration.observe import TraceStore

router = APIRouter()


class FeedbackBody(BaseModel):
    trace_id: Annotated[str, StringConstraints(min_length=1, max_length=64)]
    rating: Literal["good", "bad"]
    comment: Annotated[str, StringConstraints(max_length=1000)] = ""


async def _traces(services: Services) -> TraceStore:
    if services.traces is None:
        raise DependencyUnavailableError("没有配置 trace 存储")
    return services.traces


@router.get("/traces/{trace_id}")
async def get_trace(
    trace_id: str, services: Annotated[Services, Depends(get_services)]
) -> TraceRecord:
    record = await (await _traces(services)).get(trace_id)
    if record is None:
        raise TraceNotFoundError(f"没有 trace {trace_id}")
    return record


@router.post("/feedback")
async def post_feedback(
    body: FeedbackBody, services: Annotated[Services, Depends(get_services)]
) -> dict[str, str]:
    item = FeedbackIn.model_validate(body.model_dump())
    traces = await _traces(services)
    if await traces.get(item.trace_id) is None:
        raise TraceNotFoundError(f"没有 trace {item.trace_id}")
    await traces.add_feedback(item)
    return {"status": "ok"}
