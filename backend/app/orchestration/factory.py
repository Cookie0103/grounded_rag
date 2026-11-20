"""组装 API 和 MCP 共用的检索、双泳道编排与会话。"""

from contextlib import AsyncExitStack
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.cache import TtlCache
from app.core.config import Settings
from app.core.resilience import CircuitBreaker
from app.db.conversation import PostgresConversationStore
from app.db.observability import PostgresTraceStore
from app.orchestration.copilot import CopilotGraph
from app.orchestration.copilot_service import ChatAccess, CopilotService
from app.orchestration.observe import TraceStore
from app.providers.cached import CachedEmbedder
from app.providers.cloud_trace import build_cloud_tracer
from app.providers.factory import create_chat_http_client, get_chat_model, get_embedder
from app.providers.mock_core import MockCoreClient
from app.retrieval.factory import build_retriever
from app.retrieval.resilient import ResilientRetriever
from app.retrieval.retriever import Retriever
from app.tools.cache import RedisToolCache
from app.tools.middleware import ToolRunner

EMBEDDING_CACHE_SIZE, EMBEDDING_CACHE_TTL = 2000, 3600.0
RERANK_FAILURE_THRESHOLD, RERANK_RESET_SECONDS = 3, 30.0


@dataclass(frozen=True)
class Services:
    retriever: Retriever
    chat: ChatAccess
    traces: TraceStore | None = None


async def build_services(engine: AsyncEngine, settings: Settings) -> Services:
    embedder = CachedEmbedder(
        get_embedder(settings.embedding_model, settings),
        TtlCache(EMBEDDING_CACHE_SIZE, EMBEDDING_CACHE_TTL),
    )
    base = await build_retriever(engine, settings, embedder=embedder)
    retriever = ResilientRetriever(
        base,
        cache=None,
        breaker=CircuitBreaker(RERANK_FAILURE_THRESHOLD, RERANK_RESET_SECONDS),
    )
    traces = PostgresTraceStore(engine)
    async with AsyncExitStack() as resources:
        conversations = PostgresConversationStore(
            settings.database_url, timeout_seconds=settings.db_timeout_seconds
        )
        resources.push_async_callback(conversations.close)
        await conversations.setup()

        transport = MockCoreClient(settings.mock_core_base_url)
        resources.push_async_callback(transport.aclose)
        tool_cache = RedisToolCache(settings.redis_url)
        resources.push_async_callback(tool_cache.aclose)

        models_http = await resources.enter_async_context(create_chat_http_client(settings))
        graph = CopilotGraph(
            get_chat_model(settings, tier="small", client=models_http),
            get_chat_model(settings, tier="large", client=models_http),
            retriever,
            ToolRunner(transport, tool_cache),
            strict=settings.strict_answer_checks,
        )
        cloud = build_cloud_tracer(settings)
        chat = CopilotService(
            graph, conversations, traces=traces, cloud=cloud, resources=resources.pop_all()
        )
    return Services(retriever=retriever, chat=chat, traces=traces)
