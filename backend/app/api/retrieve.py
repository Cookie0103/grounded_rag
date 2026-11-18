"""POST /retrieve：只检索，返回每个候选在各环节的名次和分数。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.api.services import enforce_rate_limit, get_services
from app.core.config import DEFAULT_POLICY_RERANK, FINAL_TOP_K
from app.core.policy import PolicyMetadata
from app.core.trace import trace_id_var
from app.db.policy_filter import MetaFilter
from app.retrieval.retriever import Candidate, ParentContext, Retriever

router = APIRouter(dependencies=[Depends(enforce_rate_limit)])

MAX_TOP_K = 20
MAX_QUERY_CHARS = 500


class RetrieveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_QUERY_CHARS)
    ]
    top_k: int = Field(default=FINAL_TOP_K, ge=1, le=MAX_TOP_K)
    filter: MetaFilter = Field(default_factory=MetaFilter)
    rerank: bool = DEFAULT_POLICY_RERANK


class CandidateOut(BaseModel):
    rank: int
    chunk_id: str
    document_id: str
    parent_id: str
    heading_path: str
    text: str
    metadata: PolicyMetadata | None
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
    filter: MetaFilter
    candidates: list[CandidateOut]
    parents: list[ParentOut]
    timings_ms: dict[str, float]
    degraded: bool


async def get_retriever(request: Request) -> Retriever:
    services = await get_services(request)
    return services.retriever


@router.post("/retrieve")
async def retrieve(
    body: RetrieveRequest, retriever: Annotated[Retriever, Depends(get_retriever)]
) -> RetrieveResponse:
    result = await retriever.retrieve(
        body.query, top_k=body.top_k, filters=body.filter, rerank=body.rerank
    )
    return RetrieveResponse(
        trace_id=trace_id_var.get(),
        query=result.query,
        filter=body.filter,
        candidates=[_candidate_out(candidate) for candidate in result.candidates],
        parents=[_parent_out(parent) for parent in result.parents],
        timings_ms=result.timings_ms,
        degraded=result.degraded,
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
        metadata=chunk.policy,
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
