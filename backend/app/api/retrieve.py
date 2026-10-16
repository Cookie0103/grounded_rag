"""POST /retrieve：只检索，返回每个候选在各环节的名次和分数。"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import EDITION_FILTERS, FINAL_TOP_K, get_settings
from app.core.errors import DependencyUnavailableError
from app.core.trace import trace_id_var
from app.retrieval.factory import build_retriever
from app.retrieval.retriever import Candidate, ParentContext, Retriever

router = APIRouter()

MAX_TOP_K = 20
MAX_QUERY_CHARS = 500


class RetrieveRequest(BaseModel):
    query: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_QUERY_CHARS)
    ]
    top_k: int = Field(default=FINAL_TOP_K, ge=1, le=MAX_TOP_K)
    edition: Literal["self_host", "cloud"] | None = None
    rerank: bool = True


class CandidateOut(BaseModel):
    rank: int
    chunk_id: str
    document_id: str
    parent_id: str
    heading_path: str
    text: str
    edition: str
    vector_rank: int | None
    vector_distance: float | None
    bm25_rank: int | None
    bm25_score: float | None
    rrf_score: float
    rerank_score: float | None


class ParentOut(BaseModel):
    id: str
    document_id: str
    heading_path: str
    text: str


class RetrieveResponse(BaseModel):
    trace_id: str
    query: str
    edition: str | None
    candidates: list[CandidateOut]
    parents: list[ParentOut]
    timings_ms: dict[str, float]


async def get_retriever(request: Request) -> Retriever:
    """第一次请求时才建检索器（读库建 BM25 索引、加载模型），之后复用。"""
    state = request.app.state
    if state.retriever is None:
        async with state.retriever_lock:
            if state.retriever is None:
                try:
                    state.retriever = await build_retriever(state.engine, get_settings())
                except (SQLAlchemyError, OSError) as error:
                    raise DependencyUnavailableError("检索器初始化失败：数据库不可用") from error
    retriever: Retriever = state.retriever
    return retriever


@router.post("/retrieve")
async def retrieve(
    body: RetrieveRequest, retriever: Annotated[Retriever, Depends(get_retriever)]
) -> RetrieveResponse:
    editions = EDITION_FILTERS[body.edition] if body.edition else None
    result = await retriever.retrieve(
        body.query, top_k=body.top_k, editions=editions, rerank=body.rerank
    )
    return RetrieveResponse(
        trace_id=trace_id_var.get(),
        query=result.query,
        edition=body.edition,
        candidates=[_candidate_out(candidate) for candidate in result.candidates],
        parents=[_parent_out(parent) for parent in result.parents],
        timings_ms=result.timings_ms,
    )


def _candidate_out(candidate: Candidate) -> CandidateOut:
    chunk = candidate.chunk
    return CandidateOut(
        rank=candidate.rank,
        chunk_id=chunk.id,
        document_id=chunk.document_id,
        parent_id=chunk.parent_id,
        heading_path=chunk.heading_path,
        text=chunk.text,
        edition=chunk.edition,
        vector_rank=candidate.vector_rank,
        vector_distance=candidate.vector_distance,
        bm25_rank=candidate.bm25_rank,
        bm25_score=candidate.bm25_score,
        rrf_score=candidate.rrf_score,
        rerank_score=candidate.rerank_score,
    )


def _parent_out(parent: ParentContext) -> ParentOut:
    return ParentOut(
        id=parent.id,
        document_id=parent.document_id,
        heading_path=parent.heading_path,
        text=parent.text,
    )
