"""MCP 服务：让 Claude Code 等客户端查 Dify 文档。工具：search_docs（检索）、ask_docs（问答）。"""

from collections.abc import Awaitable, Callable

from mcp.server.mcpserver import MCPServer

from app.core.config import EDITION_FILTERS
from app.orchestration.factory import Services
from app.orchestration.models import ChatRequest

MAX_QUERY_CHARS = 500
MAX_TOP_K = 10
SNIPPET_CHARS = 500

ServicesProvider = Callable[[], Awaitable[Services]]


def _check_edition(edition: str | None) -> None:
    if edition is not None and edition not in EDITION_FILTERS:
        raise ValueError(f"edition 只能是 {sorted(EDITION_FILTERS)} 或留空")


def _check_text(text: str, name: str) -> str:
    cleaned = text.strip()
    if not cleaned or len(cleaned) > MAX_QUERY_CHARS:
        raise ValueError(f"{name} 要在 1～{MAX_QUERY_CHARS} 个字之间")
    return cleaned


def create_mcp_server(get_services: ServicesProvider) -> MCPServer:
    server = MCPServer(
        "grounded-rag",
        instructions="Dify 中文文档（自部署版和云版本）的检索与问答。回答都带文档出处。",
    )

    @server.tool()
    async def search_docs(query: str, edition: str | None = None, top_k: int = 5) -> str:
        """在 Dify 中文文档里检索，返回最相关的片段和出处。edition 可选 self_host / cloud。"""
        query = _check_text(query, "query")
        _check_edition(edition)
        if not 1 <= top_k <= MAX_TOP_K:
            raise ValueError(f"top_k 要在 1～{MAX_TOP_K} 之间")
        services = await get_services()
        editions = EDITION_FILTERS.get(edition or "")
        result = await services.retriever.retrieve(query, top_k=top_k, editions=editions)
        if not result.candidates:
            return "没有找到相关文档。"
        lines = [
            f"{c.rank}. 文档：{c.chunk.document_id}｜{c.chunk.heading_path}\n"
            f"{c.chunk.text[:SNIPPET_CHARS]}"
            for c in result.candidates
        ]
        return "\n\n".join(lines)

    @server.tool()
    async def ask_docs(question: str, edition: str | None = None) -> str:
        """回答关于 Dify 的问题，用 [编号] 标注出处并在末尾列出。edition 可选 self_host / cloud。"""
        question = _check_text(question, "question")
        _check_edition(edition)
        services = await get_services()
        response = await services.chat.answer(ChatRequest(question=question, edition=edition))
        text = response.answer
        if response.citations:
            sources = "\n".join(
                f"[{c.index}] {c.document_id}｜{c.heading_path}" for c in response.citations
            )
            text += f"\n\n出处：\n{sources}"
        if response.degraded:
            text += "\n\n（服务降级：生成或精排不可用）"
        return text

    return server
