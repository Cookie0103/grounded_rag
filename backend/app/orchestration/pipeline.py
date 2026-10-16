"""问答编排（LangGraph）：护栏 → 路由 → 改写 / 分解 → 检索 → 证据评分 → 生成 → 忠实度校验。

每个节点是一个普通的异步函数；对话模型的输出不合法时都有保守的退路，不让一次格式错误拖垮请求。
"""

import time
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.config import EDITION_FILTERS, FINAL_TOP_K
from app.orchestration import prompts
from app.orchestration.context import assemble, resolve_citations
from app.orchestration.guard import check_input
from app.orchestration.jsonutil import as_bool, parse_object
from app.orchestration.models import (
    ABSTAIN_TEXT,
    CLARIFY,
    DIRECT,
    MULTI,
    REFUSE,
    REFUSE_TEXT,
    ROUTES,
    SINGLE,
    ChatRequest,
    ChatResponse,
    Citation,
    Step,
)
from app.providers.base import ChatMessage, ChatModel, Completion
from app.providers.deepseek import cost_cny
from app.retrieval.retriever import ParentContext, Retriever

MAX_SUBQUESTIONS = 3
MAX_RETRIEVAL_RETRIES = 2
MAX_REGENERATIONS = 1
GREETINGS = ("你好", "您好", "hi", "hello", "嗨", "谢谢", "感谢", "再见")
GREETING_MAX_CHARS = 12


class MeteredChat:
    """包一层对话模型，累计这一次请求用了多少钱。"""

    def __init__(self, chat: ChatModel) -> None:
        self._chat = chat
        self.cost_cny = 0.0

    async def ask(self, prompt: str, *, json_mode: bool = False) -> str:
        completion: Completion = await self._chat.complete(
            [ChatMessage(role="user", content=prompt)], json_mode=json_mode
        )
        self.cost_cny += cost_cny(completion.prompt_tokens, completion.completion_tokens)
        return completion.text


class State(TypedDict, total=False):
    request: ChatRequest
    meter: MeteredChat
    steps: list[Step]
    route: str
    edition: str | None
    queries: list[str]  # 本轮要检索的问题
    used_queries: list[str]
    parents: list[ParentContext]
    doc_ids: list[str]
    retries: int
    missing: str
    sufficient: bool
    all_citations: list[Citation]  # 上下文里全部编号
    citations: list[Citation]  # 回答里真正引用的
    context_text: str
    answer: str
    regenerations: int
    faithful: bool
    abstained: bool


def _record(state: State, name: str, started: float, note: str = "") -> list[Step]:
    steps = [*state.get("steps", [])]
    steps.append(Step(name=name, ms=(time.perf_counter() - started) * 1000, note=note))
    return steps


def _is_greeting(question: str) -> bool:
    text = question.strip().lower().rstrip("！!。.~ ")
    return len(text) <= GREETING_MAX_CHARS and any(text.startswith(word) for word in GREETINGS)


class ChatPipeline:
    def __init__(self, chat: ChatModel, retriever: Retriever) -> None:
        self._chat = chat
        self._retriever = retriever
        self._graph = self._build()

    async def answer(self, request: ChatRequest) -> ChatResponse:
        meter = MeteredChat(self._chat)
        final: State = await self._graph.ainvoke(
            {"request": request, "meter": meter, "steps": [], "retries": 0, "regenerations": 0}
        )
        return ChatResponse(
            answer=final.get("answer", ABSTAIN_TEXT),
            route=final.get("route", REFUSE),
            citations=final.get("citations", []) if not final.get("abstained") else [],
            steps=final.get("steps", []),
            retrieved_docs=final.get("doc_ids", []),
            contexts=[parent.text for parent in final.get("parents", [])],
            cost_cny=meter.cost_cny,
            abstained=bool(final.get("abstained")),
        )

    # ------------------------------------------------------------------ 图

    def _build(self) -> Any:
        graph = StateGraph(State)
        nodes: dict[str, Any] = {
            "guard": self._guard,
            "route": self._route,
            "direct": self._direct,
            "clarify": self._clarify,
            "refuse": self._refuse,
            "rewrite": self._rewrite,
            "decompose": self._decompose,
            "retrieve": self._retrieve,
            "grade": self._grade,
            "retry_query": self._retry_query,
            "generate": self._generate,
            "verify": self._verify,
            "abstain": self._abstain,
        }
        for name, node in nodes.items():
            graph.add_node(name, node)
        graph.add_edge(START, "guard")
        graph.add_conditional_edges(
            "guard", lambda s: "refuse" if s.get("route") == REFUSE else "route"
        )
        graph.add_conditional_edges(
            "route",
            lambda s: {
                DIRECT: "direct",
                CLARIFY: "clarify",
                REFUSE: "refuse",
                MULTI: "decompose",
            }.get(s["route"], "rewrite"),
        )
        graph.add_edge("rewrite", "retrieve")
        graph.add_edge("decompose", "retrieve")
        graph.add_edge("retrieve", "grade")
        graph.add_conditional_edges("grade", self._after_grade)
        graph.add_edge("retry_query", "retrieve")
        graph.add_edge("generate", "verify")
        graph.add_conditional_edges("verify", self._after_verify)
        for terminal in ("direct", "clarify", "refuse", "abstain"):
            graph.add_edge(terminal, END)
        return graph.compile()

    @staticmethod
    def _after_grade(state: State) -> str:
        if state["sufficient"]:
            return "generate"
        return "retry_query" if state["retries"] < MAX_RETRIEVAL_RETRIES else "abstain"

    @staticmethod
    def _after_verify(state: State) -> str:
        if state["faithful"]:
            return END
        return "generate" if state["regenerations"] < MAX_REGENERATIONS else "abstain"

    # ------------------------------------------------------------------ 节点

    async def _guard(self, state: State) -> dict[str, Any]:
        started = time.perf_counter()
        reason = check_input(state["request"].question)
        if reason is None:
            return {"steps": _record(state, "guard", started, "通过")}
        return {
            "route": REFUSE,
            "answer": REFUSE_TEXT,
            "steps": _record(state, "guard", started, reason),
        }

    async def _route(self, state: State) -> dict[str, Any]:
        started = time.perf_counter()
        request = state["request"]
        edition = request.edition
        if _is_greeting(request.question):
            return {"route": DIRECT, "steps": _record(state, "route", started, "规则：问候")}
        output = await state["meter"].ask(
            prompts.render("router_v1", question=request.question), json_mode=True
        )
        data = parse_object(output) or {}
        route = str(data.get("route", "")).strip().upper()
        note = f"{route}：{data.get('reason', '')}"
        if route not in ROUTES:
            route, note = SINGLE, "路由输出不合法，退回 SINGLE"
        if edition is None and data.get("edition") in EDITION_FILTERS:
            edition = str(data["edition"])
        return {
            "route": route,
            "edition": edition,
            "steps": _record(state, "route", started, note),
        }

    async def _direct(self, state: State) -> dict[str, Any]:
        started = time.perf_counter()
        prompt = prompts.render("direct_v1", question=state["request"].question)
        answer = await state["meter"].ask(prompt)
        return {"answer": answer.strip(), "steps": _record(state, "direct", started)}

    async def _clarify(self, state: State) -> dict[str, Any]:
        started = time.perf_counter()
        prompt = prompts.render("clarify_v1", question=state["request"].question)
        answer = await state["meter"].ask(prompt)
        return {"answer": answer.strip(), "steps": _record(state, "clarify", started)}

    async def _refuse(self, state: State) -> dict[str, Any]:
        started = time.perf_counter()
        return {
            "route": REFUSE,
            "answer": REFUSE_TEXT,
            "abstained": True,
            "steps": _record(state, "refuse", started),
        }

    async def _rewrite(self, state: State) -> dict[str, Any]:
        started = time.perf_counter()
        question = state["request"].question
        output = await state["meter"].ask(
            prompts.render("rewrite_v1", question=question), json_mode=True
        )
        query = str((parse_object(output) or {}).get("query", "")).strip()
        note = query if query else "改写失败，用原问题"
        return {"queries": [query or question], "steps": _record(state, "rewrite", started, note)}

    async def _decompose(self, state: State) -> dict[str, Any]:
        started = time.perf_counter()
        question = state["request"].question
        output = await state["meter"].ask(
            prompts.render("decompose_v1", question=question, max_parts=str(MAX_SUBQUESTIONS)),
            json_mode=True,
        )
        raw = (parse_object(output) or {}).get("queries", [])
        queries = (
            [str(item).strip() for item in raw if str(item).strip()]
            if isinstance(raw, list)
            else []
        )
        queries = queries[:MAX_SUBQUESTIONS] or [question]
        return {
            "queries": queries,
            "steps": _record(state, "decompose", started, " | ".join(queries)),
        }

    async def _retrieve(self, state: State) -> dict[str, Any]:
        started = time.perf_counter()
        edition = state.get("edition") or state["request"].edition
        editions = EDITION_FILTERS.get(edition or "")
        parents = [*state.get("parents", [])]
        known = {parent.id for parent in parents}
        doc_ids = [*state.get("doc_ids", [])]
        for query in state["queries"]:
            result = await self._retriever.retrieve(query, top_k=FINAL_TOP_K, editions=editions)
            for parent in result.parents:
                if parent.id not in known:
                    known.add(parent.id)
                    parents.append(parent)
            for candidate in result.candidates:
                if candidate.chunk.document_id not in doc_ids:
                    doc_ids.append(candidate.chunk.document_id)
        citations, context_text = assemble(parents)
        return {
            "parents": parents,
            "doc_ids": doc_ids,
            "all_citations": citations,
            "context_text": context_text,
            "used_queries": [*state.get("used_queries", []), *state["queries"]],
            "steps": _record(state, "retrieve", started, f"{len(parents)} 个父块"),
        }

    async def _grade(self, state: State) -> dict[str, Any]:
        started = time.perf_counter()
        if not state["parents"]:
            return {
                "sufficient": False,
                "missing": state["request"].question,
                "steps": _record(state, "grade", started, "没有检索到任何内容"),
            }
        output = await state["meter"].ask(
            prompts.render(
                "grade_v1",
                question=state["request"].question,
                contexts=state["context_text"],
            ),
            json_mode=True,
        )
        data = parse_object(output)
        if data is None:
            return {
                "sufficient": True,
                "steps": _record(state, "grade", started, "输出不合法，按足够处理"),
            }
        sufficient = as_bool(data.get("sufficient"), True)
        missing = str(data.get("missing", "")).strip()
        return {
            "sufficient": sufficient,
            "missing": missing,
            "steps": _record(state, "grade", started, "足够" if sufficient else f"不足：{missing}"),
        }

    async def _retry_query(self, state: State) -> dict[str, Any]:
        started = time.perf_counter()
        question = state["request"].question
        missing = state.get("missing") or question
        output = await state["meter"].ask(
            prompts.render(
                "retry_query_v1",
                question=question,
                missing=missing,
                previous="；".join(state.get("used_queries", [])),
            ),
            json_mode=True,
        )
        query = str((parse_object(output) or {}).get("query", "")).strip() or missing
        return {
            "queries": [query],
            "retries": state["retries"] + 1,
            "steps": _record(state, "retry_query", started, query),
        }

    async def _generate(self, state: State) -> dict[str, Any]:
        started = time.perf_counter()
        regenerating = "faithful" in state
        note = (
            "\n上一次的回答里有资料找不到依据的说法，请只写资料里明确有的内容。"
            if regenerating
            else ""
        )
        prompt = prompts.render(
            "generate_v1",
            contexts=state["context_text"],
            question=state["request"].question,
            retry_note=note,
        )
        raw = await state["meter"].ask(prompt)
        answer, used = resolve_citations(raw.strip(), state["all_citations"])
        return {
            "answer": answer,
            "citations": used,
            "regenerations": state["regenerations"] + (1 if regenerating else 0),
            "steps": _record(state, "generate", started, f"引用 {[c.index for c in used]}"),
        }

    async def _verify(self, state: State) -> dict[str, Any]:
        started = time.perf_counter()
        _, full_context = assemble(state["parents"])
        output = await state["meter"].ask(
            prompts.render("verify_v1", contexts=full_context, answer=state["answer"]),
            json_mode=True,
        )
        data = parse_object(output)
        faithful = True if data is None else as_bool(data.get("faithful"), True)
        note = "通过" if faithful else f"不通过：{(data or {}).get('unsupported')}"
        return {"faithful": faithful, "steps": _record(state, "verify", started, note)}

    async def _abstain(self, state: State) -> dict[str, Any]:
        started = time.perf_counter()
        return {
            "answer": ABSTAIN_TEXT,
            "abstained": True,
            "steps": _record(state, "abstain", started),
        }
