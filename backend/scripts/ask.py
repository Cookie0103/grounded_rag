"""终端问答：uv run python -m scripts.ask "你的问题"；与 REST / MCP 复用同一服务。"""

import argparse
import asyncio
import sys

from app.core.config import EDITION_FILTERS, get_settings
from app.core.logging import configure_logging
from app.core.trace import new_trace_id, trace_id_var
from app.db.engine import create_engine
from app.orchestration.factory import build_services
from app.orchestration.models import ChatRequest


async def run(request: ChatRequest, *, as_json: bool = False) -> str:
    """加载已有索引回答一次，保存数据库 trace 并发送云端队列。"""
    settings = get_settings()
    engine = create_engine(settings)
    token = trace_id_var.set(new_trace_id())
    services = None
    try:
        services = await build_services(engine, settings)
        response = await services.chat.answer(request)
        if as_json:
            return response.model_dump_json(indent=2) + "\n"
        return f"{response.answer}\n\nroute={response.route} trace_id={trace_id_var.get()}\n"
    finally:
        if services is not None:
            await services.chat.close()
        await engine.dispose()
        trace_id_var.reset(token)


def main() -> None:
    parser = argparse.ArgumentParser(description="Dify 文档问答")
    parser.add_argument("question")
    parser.add_argument("--edition", choices=sorted(EDITION_FILTERS))
    parser.add_argument("--session-id", help="复用同一 ID 可以测试追问")
    parser.add_argument("--json", action="store_true", help="输出完整过程 JSON")
    arguments = parser.parse_args()
    configure_logging(get_settings().log_level)
    request = ChatRequest(
        question=arguments.question, edition=arguments.edition, session_id=arguments.session_id
    )
    sys.stdout.write(asyncio.run(run(request, as_json=arguments.json)))


if __name__ == "__main__":
    main()
