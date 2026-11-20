"""建表、灌入并验证住宅贷款合成种子。"""

import argparse
import asyncio
import json
import sys
from hashlib import sha256
from importlib.resources import files
from typing import TYPE_CHECKING, cast

from .config import MysqlSettings
from .database import create_pool
from .seed_data import (
    AS_OF,
    COMPOSITE_KEYS,
    SEED,
    TABLES,
    SeedRow,
    SeedRows,
    build_seed,
    fingerprint,
    summarize,
)

if TYPE_CHECKING:
    from aiomysql import Connection, Pool

SEED_BATCH_SIZE = 1000


async def _insert_rows(connection: "Connection", rows: SeedRows) -> None:
    await connection.begin()
    try:
        async with connection.cursor() as cursor:
            for table, columns in TABLES.items():
                placeholders = ", ".join(["%s"] * len(columns))
                sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
                records = rows[table]
                for start in range(0, len(records), SEED_BATCH_SIZE):
                    await cursor.executemany(sql, records[start : start + SEED_BATCH_SIZE])
        await connection.commit()
    finally:
        if not connection.closed and connection.get_transaction_status():
            await connection.rollback()


async def initialize(pool: "Pool", database_name: str, seed: int = SEED) -> bool:
    """新建缺失的合成表并在空库中一次性灌库。"""
    lock_name = "mock_core:" + sha256(database_name.encode()).hexdigest()[:54]
    schema = files(__package__).joinpath("schema.sql").read_text(encoding="utf-8")
    async with pool.acquire() as connection, connection.cursor() as cursor:
        await cursor.execute("SELECT GET_LOCK(%s, 30)", (lock_name,))
        if await cursor.fetchone() != (1,):
            raise RuntimeError("未取得模拟库初始化锁")
        try:
            for statement in schema.split(";"):
                if statement.strip():
                    await cursor.execute(statement)
            await cursor.execute("SELECT 1 FROM customers LIMIT 1")
            if await cursor.fetchone() is not None:
                return False
            await _insert_rows(connection, build_seed(seed))
            return True
        finally:
            if not connection.closed:
                await cursor.execute("SELECT RELEASE_LOCK(%s)", (lock_name,))


async def _export(pool: "Pool") -> SeedRows:
    rows: SeedRows = {}
    async with pool.acquire() as connection, connection.cursor() as cursor:
        for table, columns in TABLES.items():
            key = columns[:2] if table in COMPOSITE_KEYS else columns[:1]
            await cursor.execute(
                f"SELECT {', '.join(columns)} FROM {table} ORDER BY {', '.join(key)}"
            )
            rows[table] = list(cast(tuple[SeedRow, ...], await cursor.fetchall()))
    return rows


async def _run_command(action: str, seed: int) -> dict[str, object]:
    expected = build_seed(seed)
    expected_sha = fingerprint(expected)
    result = {
        "synthetic": True,
        "as_of": AS_OF.isoformat(),
        "seed": seed,
        "sha256": expected_sha,
        "statistics": summarize(expected),
    }
    if action == "fingerprint":
        return result

    settings = MysqlSettings.from_env()
    pool = await create_pool(settings)
    try:
        if action == "init":
            result["inserted"] = await initialize(pool, settings.database, seed)
        actual_sha = fingerprint(await _export(pool))
    finally:
        pool.close()
        await pool.wait_closed()
    if actual_sha != expected_sha:
        raise ValueError(f"合成数据库指纹不符。数据库 {actual_sha}，预期 {expected_sha}")
    result["database_sha256"] = actual_sha
    return result


def main() -> None:
    """执行独立的建表或指纹校验命令。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("init", "verify", "fingerprint"))
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    result = asyncio.run(_run_command(args.action, args.seed))
    sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
