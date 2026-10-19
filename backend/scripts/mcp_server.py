"""启动 MCP 服务（stdio）：`uv run poe mcp`。

在 Claude Code 里注册：`claude mcp add grounded-rag -- uv run --directory <仓库>/backend poe mcp`。
第一次工具调用时才建检索器（加载模型要几十秒）；日志默认写到标准错误，不会污染标准输出。
"""

import asyncio

from app.api.mcp_server import create_mcp_server
from app.core.config import get_settings
from app.core.errors import DependencyUnavailableError
from app.core.logging import configure_logging
from app.db.engine import create_engine
from app.orchestration.factory import Services, build_services


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    engine = create_engine(settings)
    state: dict[str, Services] = {}
    lock = asyncio.Lock()

    async def get_services() -> Services:
        async with lock:
            if "services" not in state:
                try:
                    state["services"] = await build_services(engine, settings)
                except OSError as error:
                    raise DependencyUnavailableError("服务初始化失败：数据库不可用") from error
            return state["services"]

    create_mcp_server(get_services).run("stdio")


if __name__ == "__main__":
    main()
