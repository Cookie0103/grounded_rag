"""把检索、编排、缓存、降级组装成服务（API 和 MCP 共用）。"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.cache import TtlCache
from app.core.config import Settings
from app.core.resilience import CircuitBreaker
from app.db.observability import PostgresInterventionStore, PostgresTraceStore
from app.db.sessions import PostgresSessionStore
from app.orchestration.observe import TraceStore
from app.orchestration.pipeline import ChatPipeline
from app.orchestration.service import ChatService
from app.providers.cached import CachedEmbedder
from app.providers.cloud_trace import build_cloud_tracer
from app.providers.factory import get_chat_model, get_embedder
from app.retrieval.factory import build_retriever
from app.retrieval.resilient import ResilientRetriever
from app.retrieval.retriever import Retriever

EMBEDDING_CACHE_SIZE, EMBEDDING_CACHE_TTL = 2000, 3600.0
RETRIEVAL_CACHE_SIZE, RETRIEVAL_CACHE_TTL = 500, 600.0
ANSWER_CACHE_SIZE, ANSWER_CACHE_TTL = 200, 600.0
RERANK_FAILURE_THRESHOLD, RERANK_RESET_SECONDS = 3, 30.0


@dataclass(frozen=True)
class Services:
    retriever: Retriever
    chat: ChatService
    traces: TraceStore | None = None


async def build_services(engine: AsyncEngine, settings: Settings) -> Services:
    embedder = CachedEmbedder(
        get_embedder(settings.embedding_model, settings),
        TtlCache(EMBEDDING_CACHE_SIZE, EMBEDDING_CACHE_TTL),
    )
    base = await build_retriever(engine, settings, embedder=embedder)
    retriever = ResilientRetriever(
        base,
        cache=TtlCache(RETRIEVAL_CACHE_SIZE, RETRIEVAL_CACHE_TTL),
        breaker=CircuitBreaker(RERANK_FAILURE_THRESHOLD, RERANK_RESET_SECONDS),
    )
    pipeline = ChatPipeline(get_chat_model(settings), retriever, PostgresSessionStore(engine))
    traces = PostgresTraceStore(engine)
    chat = ChatService(
        pipeline,
        retriever,
        answer_cache=TtlCache(ANSWER_CACHE_SIZE, ANSWER_CACHE_TTL),
        traces=traces,
        interventions=PostgresInterventionStore(engine),
        cloud=build_cloud_tracer(settings),
    )
    return Services(retriever=retriever, chat=chat, traces=traces)
