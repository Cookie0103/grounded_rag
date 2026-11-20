"""用 PostgreSQL checkpointer 保存下一轮所需的会话状态。"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from functools import cached_property

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from psycopg import AsyncConnection, Error
from psycopg.rows import DictRow, dict_row
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.engine import make_url

from app.core.errors import DependencyUnavailableError

_MIGRATION_LOCK_POLL_SECONDS = 0.05


@dataclass(frozen=True, slots=True)
class Conversation:
    """下一轮意图识别和规程追问所用的状态。"""

    previous_intent: str | None = None
    previous_policy_question: str | None = None


class PostgresConversationStore:
    """为每个会话保存独立的 LangGraph checkpoint。"""

    def __init__(self, database_url: str, *, timeout_seconds: float = 5.0) -> None:
        self._timeout_seconds = timeout_seconds
        self._connection_string = (
            make_url(database_url)
            .set(drivername="postgresql")
            .render_as_string(hide_password=False)
        )
        self._pool = AsyncConnectionPool[AsyncConnection[DictRow]](
            self._connection_string,
            kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
            min_size=0,
            max_size=1,
            timeout=timeout_seconds,
            open=False,
        )

    async def setup(self) -> None:
        """执行 checkpointer 迁移并开启运行时连接池。"""
        async with (
            self._database_operation(),
            await AsyncConnection.connect(
                self._connection_string, autocommit=True, prepare_threshold=0, row_factory=dict_row
            ) as connection,
        ):
            await _wait_for_migration_lock(connection)
            await AsyncPostgresSaver(connection).setup()
            await self._pool.open()

    async def get(self, thread_id: str) -> Conversation:
        """读取指定会话的最新状态。"""
        async with self._database_operation():
            state = await self._graph.aget_state(_thread_config(thread_id))
            return Conversation(**state.values)

    async def save(self, thread_id: str, conversation: Conversation) -> None:
        """提交一轮完成后的会话状态。"""
        async with self._database_operation():
            await self._graph.aupdate_state(
                _thread_config(thread_id), asdict(conversation), as_node=START
            )

    async def close(self) -> None:
        """关闭运行时连接池。"""
        await self._pool.close(timeout=self._timeout_seconds)

    @cached_property
    def _graph(self) -> CompiledStateGraph[Conversation, None, Conversation, Conversation]:
        # 持久化图只有会话状态，问答图里的工具结果和生成内容无权进入 checkpoint。
        return (
            StateGraph(Conversation)
            .add_edge(START, END)
            .compile(checkpointer=AsyncPostgresSaver(self._pool))
        )

    @asynccontextmanager
    async def _database_operation(self) -> AsyncIterator[None]:
        try:
            async with asyncio.timeout(self._timeout_seconds):
                yield
        except (Error, OSError, TimeoutError) as error:
            raise DependencyUnavailableError("会话数据库不可用") from error


def _thread_config(thread_id: str) -> RunnableConfig:
    return {"configurable": {"thread_id": thread_id}}


async def _wait_for_migration_lock(connection: AsyncConnection[DictRow]) -> None:
    # 阻塞式锁查询持有快照，会与官方迁移的 CREATE INDEX CONCURRENTLY 互等。
    # 此处让每次尝试结束自动提交事务，专用连接关闭时释放会话锁。
    while True:
        cursor = await connection.execute(
            "SELECT 1 WHERE pg_try_advisory_lock(hashtext(current_schema()), hashtext(%s))",
            ("grounded_rag_conversation_checkpoint",),
        )
        if await cursor.fetchone() is not None:
            return
        await asyncio.sleep(_MIGRATION_LOCK_POLL_SECONDS)
