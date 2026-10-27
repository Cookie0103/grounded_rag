"""Langfuse 可选云端观测；本地 trace 与预算账本仍是独立记录。"""

import asyncio
import logging
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from typing import Any

from langfuse import Langfuse, propagate_attributes
from pydantic import BaseModel

from app.core.config import Settings
from app.core.records import TraceRecord

logger = logging.getLogger(__name__)
CLOUD_TIMEOUT_SECONDS = 5
CLOUD_ERRORS = (OSError, RuntimeError, ValueError)


class CloudRun:
    """单次请求的云端记录；步骤以完成事件呈现，真实耗时保存在 ms 字段。"""

    def __init__(self, span: Any = None) -> None:
        self._span = span

    def step(self, step: BaseModel) -> None:
        """发送已有步骤模型，不另建一套 chunk 或编排类型。"""
        if self._span is None:
            return
        data = step.model_dump(mode="json")
        try:
            self._span.start_observation(
                name=data["name"],
                as_type="event",
                output=data,
                metadata={"duration_ms": data["ms"]},
            )
        except CLOUD_ERRORS as error:
            logger.warning("云端步骤记录失败：%s", type(error).__name__)

    def finish(self, record: TraceRecord) -> None:
        """发送最终回答和完整本地证据，方便按应用 trace_id 查找。"""
        if self._span is None:
            return
        try:
            self._span.update(
                output=record.answer,
                metadata=record.model_dump(mode="json", exclude={"answer", "question", "steps"}),
            )
        except CLOUD_ERRORS as error:
            logger.warning("云端回答记录失败：%s", type(error).__name__)


class CloudTracer:
    def __init__(self, client: Langfuse | None = None) -> None:
        self._client = client

    @contextmanager
    def observe(
        self,
        question: str,
        trace_id: str,
        *,
        session_id: str | None = None,
        name: str = "grounded-rag",
        expected: BaseModel | None = None,
    ) -> Iterator[CloudRun]:
        """包住一次请求；应用步骤逐个完成时上传，SDK 在后台批量发送。"""
        with ExitStack() as stack:
            run = CloudRun()
            if self._client is not None:
                try:
                    stack.enter_context(
                        propagate_attributes(session_id=session_id, trace_name=name)
                    )
                    span = stack.enter_context(
                        self._client.start_as_current_observation(
                            name=name,
                            trace_context={"trace_id": Langfuse.create_trace_id(seed=trace_id)},
                            input={
                                "question": question,
                                "expected": expected.model_dump(mode="json")
                                if expected is not None
                                else None,
                            },
                            metadata={"app_trace_id": trace_id},
                        )
                    )
                    run = CloudRun(span)
                except CLOUD_ERRORS as error:
                    logger.warning("云端记录启动失败：%s", type(error).__name__)
            yield run

    async def close(self) -> None:
        """退出时等待 SDK 发送队列，网络异常只记日志。"""
        if self._client is not None:
            try:
                await asyncio.to_thread(self._client.shutdown)
            except CLOUD_ERRORS as error:
                logger.warning("云端队列发送失败：%s", type(error).__name__)


def build_cloud_tracer(settings: Settings) -> CloudTracer:
    """缺凭据时完全停用，不启动网络或 SDK 后台线程。"""
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.info("Langfuse 未配置完整，过程仍保存在本地")
        return CloudTracer()
    try:
        client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            base_url=settings.langfuse_base_url,
            timeout=CLOUD_TIMEOUT_SECONDS,
        )
    except CLOUD_ERRORS as error:
        logger.warning("云端客户端初始化失败：%s", type(error).__name__)
        return CloudTracer()
    return CloudTracer(client)
