import asyncio
import json
import signal
import sys
from collections.abc import AsyncIterator
from dataclasses import asdict
from uuid import uuid4

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.schema import CreateSchema, DropSchema

from app.db.conversation import Conversation, PostgresConversationStore

pytestmark = pytest.mark.integration


@pytest.fixture
async def checkpoint_url(test_database_url: str) -> AsyncIterator[str]:
    """每次从测试库内的独立空 schema 启动 checkpointer。"""
    schema = f"checkpoint_test_{uuid4().hex}"
    engine = create_async_engine(test_database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(CreateSchema(schema))
        yield (
            make_url(test_database_url)
            .update_query_dict({"options": f"-csearch_path={schema}"})
            .render_as_string(hide_password=False)
        )
    finally:
        async with engine.begin() as connection:
            await connection.execute(DropSchema(schema, cascade=True, if_exists=True))
        await engine.dispose()


async def _worker(mode: str, database_url: str) -> None:
    store = PostgresConversationStore(database_url)
    try:
        await store.setup()
        if mode == "write":
            await store.save("resume-session", Conversation("lookup"))
            await store.save("resume-session", Conversation("policy", "繰上返済の手続は？"))
            sys.stdout.write("checkpoint committed\n")
            sys.stdout.flush()
            await asyncio.Event().wait()
        else:
            conversation = await store.get("resume-session")
            sys.stdout.write(json.dumps(asdict(conversation)))
    finally:
        await store.close()


async def _start_worker(mode: str) -> asyncio.subprocess.Process:
    return await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "tests.integration.test_conversation_database",
        mode,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )


async def test_checkpoint_recovers_latest_turn_after_sigkill(checkpoint_url: str) -> None:
    payload = f"{checkpoint_url}\n".encode()
    writer = await _start_worker("write")
    assert writer.stdin is not None
    assert writer.stdout is not None
    assert writer.stderr is not None
    try:
        async with asyncio.timeout(25):
            writer.stdin.write(payload)
            await writer.stdin.drain()
            committed = await writer.stdout.readline()
            if not committed:
                pytest.fail((await writer.stderr.read()).decode())
            assert committed == b"checkpoint committed\n"
    finally:
        if writer.returncode is None:
            writer.kill()
        await writer.communicate()
    assert writer.returncode == -signal.SIGKILL

    reader = await _start_worker("read")
    try:
        async with asyncio.timeout(25):
            output, errors = await reader.communicate(payload)
        assert reader.returncode == 0, errors.decode()
    finally:
        if reader.returncode is None:
            reader.kill()
            await reader.communicate()
    assert json.loads(output) == {
        "previous_intent": "policy",
        "previous_policy_question": "繰上返済の手続は？",
    }


async def test_checkpoint_schema_setup_can_run_concurrently(checkpoint_url: str) -> None:
    first = PostgresConversationStore(checkpoint_url)
    second = PostgresConversationStore(checkpoint_url)
    try:
        async with asyncio.TaskGroup() as setup:
            setup.create_task(first.setup())
            setup.create_task(second.setup())
        await first.save("first", Conversation("policy", "繰上返済の手続は？"))
        assert await second.get("other") == Conversation()
    finally:
        await asyncio.gather(first.close(), second.close())


if __name__ == "__main__":
    asyncio.run(_worker(sys.argv[1], sys.stdin.readline().strip()))
