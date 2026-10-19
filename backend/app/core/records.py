"""观测数据：问答记录、反馈、坏例。存储实现在 app/db/observability.py。"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class TraceRecord(BaseModel):
    trace_id: str
    question: str
    route: str
    edition: str | None = None
    session_id: str | None = None
    answer: str
    abstained: bool = False
    degraded: bool = False
    cached: bool = False
    cost_cny: float = 0.0
    steps: list[dict[str, Any]] = Field(default_factory=list)
    retrieved_docs: list[str] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime | None = None


class FeedbackIn(BaseModel):
    trace_id: str
    rating: Literal["good", "bad"]
    comment: str = ""


class BadCase(BaseModel):
    trace_id: str
    question: str
    reason: str  # bad_feedback / abstained / degraded
