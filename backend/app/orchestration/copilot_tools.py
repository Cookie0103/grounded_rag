"""坐席泳道的受控工具子图。"""

import asyncio
import json
import operator
import time
from dataclasses import dataclass
from typing import Annotated, Literal, TypedDict, cast

from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.core.errors import DependencyUnavailableError
from app.orchestration.copilot_trace import ModelUsage, model_messages, record, record_tool
from app.orchestration.models import ChatRequest
from app.providers.base import ChatModel, FunctionCall, FunctionTool
from app.tools.definitions import (
    TOOL_DEFINITIONS,
    LoanContractsData,
    RepaymentScheduleData,
    ToolName,
)
from app.tools.middleware import ToolContext, ToolResult, ToolRunner, ToolStatus, ToolTrace

MAX_PLANNING_ROUNDS = 2
FUNCTIONS = tuple(
    FunctionTool(name=tool.name, description=tool.description, parameters=tool.parameters)
    for tool in TOOL_DEFINITIONS.values()
)


@dataclass(frozen=True)
class _PlannedTool:
    name: ToolName
    arguments: dict[str, object]


@dataclass(frozen=True)
class ToolRun:
    plan: _PlannedTool
    result: ToolResult
    trace: ToolTrace

    def model_evidence(self) -> dict[str, object]:
        """只把中间件裁剪后的合成结果作为模型证据。"""
        return {
            "tool": self.plan.name,
            **self.result.model_dump(mode="json", include={"data", "total", "synthetic"}),
        }


class ToolInput(TypedDict):
    request: ChatRequest


class ToolOutcome(TypedDict, total=False):
    tool_status: ToolStatus
    tool_runs: list[ToolRun]
    usage: Annotated[list[ModelUsage], operator.add]


class _ToolState(ToolOutcome, total=False):
    request: ChatRequest
    planned: list[_PlannedTool]
    round_number: int


class ToolBranch:
    def __init__(self, model: ChatModel, runner: ToolRunner) -> None:
        self._model = model
        self._runner = runner

    def build(self) -> CompiledStateGraph[_ToolState, None, ToolInput, ToolOutcome]:
        """把规划轮次限制在工具泳道内部，便于检索和实际工具执行重叠。"""
        builder: StateGraph[_ToolState, None, ToolInput, ToolOutcome] = StateGraph(
            _ToolState, input_schema=ToolInput, output_schema=ToolOutcome
        )
        builder.add_node("plan_tools", self._plan)
        builder.add_node("run_tools", self._run)
        builder.add_edge(START, "plan_tools")
        builder.add_conditional_edges("plan_tools", _after_plan)
        builder.add_conditional_edges("run_tools", _after_run)
        return builder.compile()

    async def _plan(self, state: _ToolState) -> _ToolState:
        started = time.perf_counter()
        previous = state.get("tool_runs", [])
        round_number = state.get("round_number", 0) + 1
        payload: dict[str, object] = {"question": state["request"].question}
        if previous:
            payload["previous_results"] = [run.model_evidence() for run in previous]
        messages = model_messages("plan_tools_v1", payload)
        try:
            completion = await self._model.complete(messages, tools=FUNCTIONS)
        except DependencyUnavailableError:
            record("plan_tools", started, "规划模型不可用")
            return {"tool_status": "failed", "planned": []}
        planned = _select_calls(completion.tool_calls, previous)
        usage = ModelUsage.from_completion(completion)
        record("plan_tools", started, f"第 {round_number} 轮，{len(planned or [])} 个工具")
        update: _ToolState = {"round_number": round_number, "usage": [usage]}
        if planned is None or (not planned and not previous):
            return {**update, "tool_status": "failed", "planned": []}
        return {**update, "planned": planned}

    async def _run(self, state: _ToolState) -> _ToolState:
        started = time.perf_counter()
        request = state["request"]
        context = ToolContext(agent_id=request.agent_id, customer_id=request.customer_id)
        runs = await asyncio.gather(*(self._call(plan, context) for plan in state["planned"]))
        status = _overall_status(runs)
        record("run_tools", started, f"{len(runs)} 个工具：{status}")
        return {"tool_runs": [*state.get("tool_runs", []), *runs], "tool_status": status}

    async def _call(self, plan: _PlannedTool, context: ToolContext) -> ToolRun:
        traces: list[ToolTrace] = []
        result = await self._runner.call(plan.name, context, plan.arguments, recorder=traces.append)
        trace = traces[0]
        record_tool(trace)
        return ToolRun(plan, result, trace)


def _select_calls(calls: list[FunctionCall], previous: list[ToolRun]) -> list[_PlannedTool] | None:
    if len(calls) > len(FUNCTIONS) or any(call.name not in TOOL_DEFINITIONS for call in calls):
        return None
    planned: list[_PlannedTool] = []
    for call in calls:
        try:
            raw = json.loads(call.arguments)
        except (json.JSONDecodeError, RecursionError):
            raw = None
        # 让中间件按现有契约记录不合法的入参，不接触上游。
        arguments = raw if isinstance(raw, dict) else {"": None}
        candidate = _PlannedTool(cast(ToolName, call.name), arguments)
        if candidate not in planned and not any(run.plan == candidate for run in previous):
            planned.append(candidate)
    return planned


def _overall_status(runs: list[ToolRun]) -> ToolStatus:
    expected = {run.result.status for run in runs}
    if "denied" in expected:
        return "denied"
    if "failed" in expected:
        return "failed"
    return "ok"


def _may_need_details(run: ToolRun) -> bool:
    data = run.result.data
    if isinstance(data, LoanContractsData):
        return bool(data.contracts)
    return (
        isinstance(data, RepaymentScheduleData)
        and run.result.total is not None
        and run.result.total > len(data.schedule)
    )


def _after_plan(state: _ToolState) -> Literal["run_tools", "__end__"]:
    return "run_tools" if state["planned"] else "__end__"


def _after_run(state: _ToolState) -> Literal["plan_tools", "__end__"]:
    if (
        state["tool_status"] == "ok"
        and state["round_number"] < MAX_PLANNING_ROUNDS
        and any(_may_need_details(run) for run in state["tool_runs"])
    ):
        return "plan_tools"
    return "__end__"
