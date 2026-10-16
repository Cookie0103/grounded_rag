"""干预库：人工指定「问题 → 标准答案」，优先于生成。

用法：`uv run poe interventions add "问题" "标准答案"`、`list`、`remove "问题"`。
问题按归一化键匹配（小写、去空白和标点）。
"""

import argparse
import asyncio
import sys

from app.core.config import get_settings
from app.db.engine import create_engine
from app.db.observability import PostgresInterventionStore


async def run(arguments: argparse.Namespace) -> str:
    engine = create_engine(get_settings())
    store = PostgresInterventionStore(engine)
    try:
        if arguments.command == "add":
            await store.set(arguments.question, arguments.answer)
            return "已保存\n"
        if arguments.command == "remove":
            return "已删除\n" if await store.remove(arguments.question) else "没有这条\n"
        items = await store.list_all()
        return "".join(f"{question} -> {answer}\n" for question, answer in items) or "（空）\n"
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="干预库")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add")
    add.add_argument("question")
    add.add_argument("answer")
    commands.add_parser("list")
    commands.add_parser("remove").add_argument("question")
    sys.stdout.write(asyncio.run(run(parser.parse_args())))


if __name__ == "__main__":
    main()
