import pytest

from app.core.config import Settings
from app.core.errors import DependencyUnavailableError
from app.db.engine import create_engine, ping

UNREACHABLE_URL = "postgresql+asyncpg://nobody:nobody@127.0.0.1:1/none"


async def test_ping_converts_connection_failure_to_dependency_unavailable() -> None:
    engine = create_engine(Settings(_env_file=None, database_url=UNREACHABLE_URL))
    try:
        with pytest.raises(DependencyUnavailableError) as raised:
            await ping(engine, timeout_seconds=2.0)
    finally:
        await engine.dispose()

    assert raised.value.message == "数据库不可用"
