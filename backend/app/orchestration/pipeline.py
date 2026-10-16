"""问答编排（LangGraph）：护栏 → 路由 → 改写 / 分解 → 检索 → 证据评分 → 生成 → 忠实度校验。

每个节点是一个普通的异步函数；对话模型的输出不合法时都有保守的退路，不让一次格式错误拖垮请求。
"""

import logging
import time
from collections.abc import AsyncIterator
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.config import EDITION_FILTERS, FINAL_TOP_K
from app.core.errors import AppError
from app.core.session import Session, Turn
from app.orchestration import prompts
from app.orchestration.context import assemble, resolve_citations
from app.orchestration.guard import check_input
from app.orchestration.jsonutil import as_bool, parse_object
from app.orchestration.memory import (
    SessionStore,
    format_history,
    needs_summary,
    split_for_summary,
)
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

logger = logging.getLogger(__name__)
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
    question: str  # 路由和检索用的问题（追问独立化之后）
    session: Session | None
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
    degraded: bool


def _record(state: State, name: str, started: float, note: str = "") -> list[Step]:
    steps = [*state.get("steps", [])]
    steps.append(Step(name=name, ms=(time.perf_counter() - started) * 1000, note=note))
    return steps


def _is_greeting(question: str) -> bool:
    text = question.strip().lower().rstrip("！!。.~ ")
    return len(text) <= GREETING_MAX_CHARS and any(text.startswith(word) for word in GREETINGS)


class ChatPipeline:
    def __init__(
        self,
        chat: ChatModel,
        retriever: Retriever,
        store: SessionStore | None = None,
        *,
        grade: bool = True,
        verify: bool = True,
    ) -> None:
        """grade / verify 关掉后跳过证据评分和忠实度校验（消融实验用；线上都开）。"""
        self._chat = chat
        self._retriever = retriever
        self._store = store
        self._grade_enabled = grade
        self._verify_enabled = verify
        self._graph = self._build()

    async def answer(self, request: ChatRequest) -> ChatResponse:
        response: ChatResponse | None = None
        async for item in self.stream(request):
            if isinstance(item, ChatResponse):
                response = item
        if response is None:
            raise RuntimeError("stream 没有产出 ChatResponse")
        return response

    async def stream(self, request: ChatRequest) -> AsyncIterator[Step | ChatResponse]:
        """每个环节做完就产出一个 Step，最后产出完整的 ChatResponse。"""
        meter = MeteredChat(self._chat)
        session = await self._load_session(request)
        initial: State = {
            "request": request,
            "question": request.question,
            "session": session,
            "edition": request.edition or (session.edition if session else None),
            "meter": meter,
            "steps": [],
            "retries": 0,
            "regenerations": 0,
        }
        final = initial
        emitted = 0
        async for state in self._graph.astream(initial, stream_mode="values"):
            final = state
            for step in state.get("steps", [])[emitted:]:
                yield step
            emitted = len(state.get("steps", []))
        await self._remember(final, session, meter)
        question = final.get("question", request.question)
        yield ChatResponse(
            answer=final.get("answer", ABSTAIN_TEXT),
            route=final.get("route", REFUSE),
            citations=final.get("citations", []) if not final.get("abstained") else [],
            steps=final.get("steps", []),
            retrieved_docs=final.get("doc_ids", []),
            contexts=[parent.text for parent in final.get("parents", [])],
            cost_cny=meter.cost_cny,
            abstained=bool(final.get("abstained")),
            degraded=bool(final.get("degraded")),
            standalone_question=question if question != request.question else None,
        )

    async def _load_session(self, request: ChatRequest) -> Session | None:
        if self._store is None or not request.session_id:
            return None
        return await self._store.load(request.session_id) or Session(id=request.session_id)

    async def _remember(self, final: State, session: Session | None, meter: MeteredChat) -> None:
        """把这一轮写进会话：被拒绝的回合不进历史；历史太长就把最早的并进摘要。"""
        if self._store is None or session is None or final.get("route") == REFUSE:
            return
        request = final["request"]
        session.edition = request.edition or final.get("edition") or session.edition
        session.turns.append(Turn(question=request.question, answer=final["answer"]))
        if needs_summary(session):
            old, recent = split_for_summary(session)
            session.summary = await self._summarize(meter, session.summary, old)
            session.turns = recent
        await self._store.save(session)

    @staticmethod
    async def _summarize(meter: MeteredChat, summary: str, old: list[Turn]) -> str:
        turns = "\n".join(f"用户：{turn.question}\n助手：{turn.answer}" for turn in old)
        prompt = prompts.render("summarize_v1", summary=summary or "（无）", turns=turns)
        try:
            text = await meter.ask(prompt)
        except AppError:
            logger.warning("摘要失败，直接丢掉最早的 %d 轮", len(old))
            return summary
        return text.strip() or summary

    # ------------------------------------------------------------------ 图

    def _build(self) -> Any:
        graph = StateGraph(State)
        nodes: dict[str, Any] = {
            "guard": self._guard,
            "standalone": self._standalone,
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
            "guard", lambda s: "refuse" if s.get("route") == REFUSE else "standalone"
        )
        graph.add_edge("standalone", "route")
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
        reason = check_input(state["question"])
        if reason is None:
            return {"steps": _record(state, "guard", started, "通过")}
        return {
            "route": REFUSE,
            "answer": REFUSE_TEXT,
            "steps": _record(state, "guard", started, reason),
        }

    async def _standalone(self, state: State) -> dict[str, Any]:
        """有历史时，把追问改写成不看对话也能看懂的完整问题；改写失败就用原问题。"""
        session = state.get("session")
        if session is None or not (session.turns or session.summary):
            return {}
        started = time.perf_counter()
        prompt = prompts.render(
            "standalone_v1", history=format_history(session), question=state["question"]
        )
        data = parse_object(await state["meter"].ask(prompt, json_mode=True)) or {}
        question = str(data.get("question", "")).strip() or state["question"]
        return {"question": question, "steps": _record(state, "standalone", started, question)}

    async def _route(self, state: State) -> dict[str, Any]:
        started = time.perf_counter()
        question = state["question"]
        edition = state.get("edition")
        if _is_greeting(question):
            return {"route": DIRECT, "steps": _record(state, "route", started, "规则：问候")}
        output = await state["meter"].ask(
            prompts.render("router_v1", question=question), json_mode=True
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
        prompt = prompts.render("direct_v1", question=state["question"])
        answer = await state["meter"].ask(prompt)
        return {"answer": answer.strip(), "steps": _record(state, "direct", started)}

    async def _clarify(self, state: State) -> dict[str, Any]:
        started = time.perf_counter()
        prompt = prompts.render("clarify_v1", question=state["question"])
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
        question = state["question"]
        output = await state["meter"].ask(
            prompts.render("rewrite_v1", question=question), json_mode=True
        )
        query = str((parse_object(output) or {}).get("query", "")).strip()
        note = query if query else "改写失败，用原问题"
        return {"queries": [query or question], "steps": _record(state, "rewrite", started, note)}

    async def _decompose(self, state: State) -> dict[str, Any]:
        started = time.perf_counter()
        question = state["question"]
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
        edition = state.get("edition")
        editions = EDITION_FILTERS.get(edition or "")
        parents = [*state.get("parents", [])]
        known = {parent.id for parent in parents}
        doc_ids = [*state.get("doc_ids", [])]
        degraded = state.get("degraded", False)
        for query in state["queries"]:
            result = await self._retriever.retrieve(query, top_k=FINAL_TOP_K, editions=editions)
            degraded = degraded or result.degraded
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
            "degraded": degraded,
            "all_citations": citations,
            "context_text": context_text,
            "used_queries": [*state.get("used_queries", []), *state["queries"]],
            "steps": _record(state, "retrieve", started, f"{len(parents)} 个父块"),
        }

    async def _grade(self, state: State) -> dict[str, Any]:
        started = time.perf_counter()
        if not self._grade_enabled:
            return {"sufficient": True, "steps": _record(state, "grade", started, "已关闭")}
        if not state["parents"]:
            return {
                "sufficient": False,
                "missing": state["question"],
                "steps": _record(state, "grade", started, "没有检索到任何内容"),
            }
        output = await state["meter"].ask(
            prompts.render(
                "grade_v1",
                question=state["question"],
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
        question = state["question"]
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
            question=state["question"],
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
        if not self._verify_enabled:
            return {"faithful": True, "steps": _record(state, "verify", started, "已关闭")}
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
