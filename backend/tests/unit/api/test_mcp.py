import pytest
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import UnexpectedToolError

from app.api.mcp_server import create_mcp_server
from app.orchestration.factory import Services
from app.orchestration.models import ChatRequest, ChatResponse, Citation
from app.retrieval.retriever import Candidate, ChunkInfo, ParentContext, RetrievalResult


class StubRetriever:
    def __init__(self, found: bool = True) -> None:
        self.calls: list[dict[str, object]] = []
        self._found = found

    async def retrieve(self, query: str, **kwargs: object) -> RetrievalResult:
        self.calls.append({"query": query, **kwargs})
        if not self._found:
            return RetrievalResult(query, [], [])
        chunk = ChunkInfo("c1", "learn/a", "p1", "标题 > 节", "正文内容", "common")
        return RetrievalResult(
            query,
            [Candidate(rank=1, chunk=chunk)],
            [ParentContext("p1", "learn/a", "标题", "父块")],
        )


class StubChat:
    def __init__(self, response: ChatResponse) -> None:
        self.requests: list[ChatRequest] = []
        self._response = response

    async def answer(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        return self._response


def _server(
    retriever: StubRetriever | None = None, response: ChatResponse | None = None
) -> tuple[MCPServer, StubRetriever, StubChat]:
    retriever = retriever or StubRetriever()
    chat = StubChat(
        response
        or ChatResponse(
            answer="最多 5 个 [1]",
            route="SINGLE",
            citations=[Citation(index=1, document_id="learn/a", heading_path="标题")],
        )
    )
    services = Services(retriever=retriever, chat=chat)  # type: ignore[arg-type]

    async def provide() -> Services:
        return services

    return create_mcp_server(provide), retriever, chat


async def _call(server: MCPServer, name: str, arguments: dict[str, object]) -> str:
    result = await server.call_tool(name, arguments)
    return str(result.content[0].text)  # type: ignore[union-attr]


async def test_server_exposes_the_two_tools_with_descriptions() -> None:
    server, _, _ = _server()

    tools = {tool.name: tool for tool in await server.list_tools()}

    assert set(tools) == {"search_docs", "ask_docs"}
    assert all(tool.description for tool in tools.values())
    assert tools["search_docs"].input_schema["required"] == ["query"]


async def test_search_docs_returns_snippets_with_sources_and_applies_filters() -> None:
    server, retriever, _ = _server()

    text = await _call(server, "search_docs", {"query": "上传限制", "edition": "cloud", "top_k": 3})

    assert "文档：learn/a｜标题 > 节" in text
    assert "正文内容" in text
    assert retriever.calls[0]["top_k"] == 3
    assert retriever.calls[0]["editions"] == ("cloud", "common")


async def test_search_docs_with_no_hits_says_so() -> None:
    server, _, _ = _server(StubRetriever(found=False))

    assert await _call(server, "search_docs", {"query": "不存在"}) == "没有找到相关文档。"


async def test_ask_docs_lists_the_sources_and_flags_degradation() -> None:
    server, _, chat = _server()

    text = await _call(server, "ask_docs", {"question": "最多传几个", "edition": "self_host"})

    assert text.startswith("最多 5 个 [1]")
    assert "[1] learn/a｜标题" in text
    assert chat.requests == [ChatRequest(question="最多传几个", edition="self_host")]

    degraded = ChatResponse(answer="片段", route="SINGLE", degraded=True)
    server2, _, _ = _server(response=degraded)
    assert "服务降级" in await _call(server2, "ask_docs", {"question": "问"})


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("search_docs", {"query": "  "}),
        ("search_docs", {"query": "x" * 501}),
        ("search_docs", {"query": "问", "edition": "mars"}),
        ("search_docs", {"query": "问", "top_k": 0}),
        ("search_docs", {"query": "问", "top_k": 11}),
        ("ask_docs", {"question": ""}),
        ("ask_docs", {"question": "问", "edition": "mars"}),
    ],
)
async def test_invalid_arguments_are_reported_as_tool_errors(
    tool: str, arguments: dict[str, object]
) -> None:
    server, retriever, chat = _server()

    with pytest.raises(UnexpectedToolError):
        await server.call_tool(tool, arguments)

    assert retriever.calls == []
    assert chat.requests == []
