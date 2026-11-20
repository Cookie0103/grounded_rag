"""双泳道的模型用量与步骤事件。"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Self

from langgraph.config import get_stream_writer

from app.orchestration import prompts
from app.orchestration.models import Step, StepDetails, tool_trace_step
from app.providers.base import ChatMessage, Completion
from app.providers.deepseek import completion_cost_cny
from app.tools.middleware import ToolTrace

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelUsage:
    prompt_tokens: int
    completion_tokens: int
    cost_cny: float

    @classmethod
    def from_completion(cls, completion: Completion) -> Self:
        """沿用网关的费用与 token 口径。"""
        return cls(
            completion.prompt_tokens, completion.completion_tokens, completion_cost_cny(completion)
        )


def model_messages(prompt_name: str, values: dict[str, object]) -> list[ChatMessage]:
    """把日文指令与外部数据放在不同角色里。"""
    return [
        ChatMessage(role="system", content=prompts.render(prompt_name)),
        ChatMessage(role="user", content=json.dumps(values, ensure_ascii=False)),
    ]


def record(name: str, started: float, note: str = "", details: StepDetails | None = None) -> None:
    """发送一个已完成的节点事件。"""
    elapsed = (time.perf_counter() - started) * 1000
    logger.info("节点=%s 耗时毫秒=%.1f 摘要=%s", name, elapsed, note)
    get_stream_writer()(Step(name=name, ms=elapsed, note=note, details=details))


def record_tool(trace: ToolTrace) -> None:
    """只发送中间件提供的脱敏工具摘要。"""
    get_stream_writer()(tool_trace_step(trace))
