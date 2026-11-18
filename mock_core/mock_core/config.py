"""从环境变量读取 MySQL 和故障注入配置。"""

import asyncio
from dataclasses import dataclass
from os import getenv
from random import Random
from typing import Literal

from fastapi import HTTPException

type Endpoint = Literal[
    "authorization",
    "loan-contracts",
    "repayment-schedule",
    "delinquency",
    "rate-terms",
    "benefits",
]
ENDPOINTS: tuple[Endpoint, ...] = (
    "authorization",
    "loan-contracts",
    "repayment-schedule",
    "delinquency",
    "rate-terms",
    "benefits",
)


@dataclass(frozen=True)
class MysqlSettings:
    host: str
    port: int
    database: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> "MysqlSettings":
        """读取可独立部署的模拟 MySQL 连接设置。"""
        return cls(
            host=getenv("MOCK_MYSQL_HOST", "mysql"),
            port=int(getenv("MOCK_MYSQL_PORT", "3306")),
            database=getenv("MOCK_MYSQL_DATABASE", "grounded_mock"),
            user=getenv("MOCK_MYSQL_USER", "grounded"),
            password=getenv("MOCK_MYSQL_PASSWORD", "grounded"),
        )


@dataclass(frozen=True)
class FaultSettings:
    delay_ms: int
    timeout_rate: float
    error_rate: float

    @classmethod
    def from_env(cls, endpoint: Endpoint) -> "FaultSettings":
        """用接口级设置覆盖全局故障设置。"""
        prefix = f"MOCK_FAULT_{endpoint.upper().replace('-', '_')}"
        settings = cls(
            delay_ms=int(getenv(f"{prefix}_DELAY_MS", getenv("MOCK_FAULT_DELAY_MS", "0"))),
            timeout_rate=float(
                getenv(f"{prefix}_TIMEOUT_RATE", getenv("MOCK_FAULT_TIMEOUT_RATE", "0"))
            ),
            error_rate=float(getenv(f"{prefix}_5XX_RATE", getenv("MOCK_FAULT_5XX_RATE", "0"))),
        )
        if settings.delay_ms < 0 or not (
            0 <= settings.timeout_rate <= 1
            and 0 <= settings.error_rate <= 1
            and settings.timeout_rate + settings.error_rate <= 1
        ):
            raise ValueError(f"无效的模拟故障设置 {prefix}")
        return settings


class FaultInjector:
    def __init__(self) -> None:
        self._allow_headers = getenv("MOCK_ALLOW_FAULT_HEADERS", "false").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        seed = int(getenv("MOCK_FAULT_SEED", "331107"))
        self._random = {endpoint: Random(f"{seed}:{endpoint}") for endpoint in ENDPOINTS}
        self._settings = {endpoint: FaultSettings.from_env(endpoint) for endpoint in ENDPOINTS}

    async def apply(self, endpoint: Endpoint, header: str | None) -> None:
        """对已鉴权的请求应用固定延迟和可重放的故障序列。"""
        settings = self._settings[endpoint]
        mode = header if self._allow_headers else None
        if mode not in {"5xx", "timeout", "delay"}:
            draw = self._random[endpoint].random()
            if draw < settings.timeout_rate:
                mode = "timeout"
            elif draw < settings.timeout_rate + settings.error_rate:
                mode = "5xx"
        delay_ms = max(settings.delay_ms, 250) if mode == "delay" else settings.delay_ms
        if delay_ms:
            await asyncio.sleep(delay_ms / 1000)
        if mode == "timeout":
            # 留出足够时间让调用方触发自己的超时和降级。
            await asyncio.sleep(5)
            raise HTTPException(status_code=504, detail="シミュレーション応答タイムアウト")
        if mode == "5xx":
            raise HTTPException(status_code=503, detail="シミュレーションサービス障害")
