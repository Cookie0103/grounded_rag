import os
import sys
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters

pytestmark = pytest.mark.integration

BACKEND_DIR = Path(__file__).resolve().parents[2]


async def test_real_server_process_lists_both_tools_over_stdio() -> None:
    environment = {
        **os.environ,
        "CHAT_MODEL": "fake",
        "EMBEDDING_MODEL": "fake",
        "RERANKER_MODEL": "fake",
    }
    parameters = StdioServerParameters(
        command=sys.executable, args=["-m", "scripts.mcp_server"], cwd=BACKEND_DIR, env=environment
    )

    async with Client(parameters) as client:
        tools = await client.list_tools()

    assert {tool.name for tool in tools.tools} == {"search_docs", "ask_docs"}
