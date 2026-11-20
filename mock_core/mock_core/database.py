"""通过固定查询从模拟 MySQL 读取授权与业务数据。"""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from .config import MysqlSettings
from .seed_data import AS_OF

if TYPE_CHECKING:
    from aiomysql import Pool

type Value = str | int | float | date | Decimal | None
type Row = dict[str, Value]


async def create_pool(settings: MysqlSettings) -> "Pool":
    """通过 TCP 连接 MySQL 8.4。"""
    import aiomysql

    return await aiomysql.create_pool(
        host=settings.host,
        port=settings.port,
        user=settings.user,
        password=settings.password,
        db=settings.database,
        charset="utf8mb4",
        minsize=1,
        maxsize=8,
        autocommit=True,
        connect_timeout=5,
    )


class Database:
    def __init__(self, pool: "Pool") -> None:
        self.pool = pool

    async def _fetch(self, sql: str, params: Sequence[Value] = ()) -> list[Row]:
        from aiomysql import DictCursor

        async with self.pool.acquire() as connection, connection.cursor(DictCursor) as cursor:
            await cursor.execute(sql, params)
            return list(cast(tuple[Row, ...], await cursor.fetchall()))

    async def is_healthy(self) -> bool:
        """确认数据库连接可用。"""
        from pymysql import MySQLError

        try:
            await self._fetch("SELECT 1")
        except (MySQLError, OSError):
            return False
        return True

    async def is_authorized(
        self, agent_id: str, customer_id: str, contract_id: str | None = None
    ) -> bool:
        """同时核对坐席归属及合同所属。"""
        rows = await self._fetch(
            """
            SELECT EXISTS (
                SELECT 1 FROM agent_customer AS ac
                WHERE ac.agent_id = %s AND ac.customer_id = %s
                  AND (%s IS NULL OR EXISTS (
                    SELECT 1 FROM loan_contracts AS lc
                    WHERE lc.customer_id = ac.customer_id AND lc.contract_id = %s
                  ))
            ) AS authorized
            """,
            (agent_id, customer_id, contract_id, contract_id),
        )
        return bool(rows[0]["authorized"])

    async def loan_contracts(self, customer_id: str) -> list[Row]:
        """读取客户名下的合成合同。"""
        return await self._fetch(
            """
            SELECT contract_id, product, principal_yen, disbursed_on, status
            FROM loan_contracts WHERE customer_id = %s ORDER BY contract_id
            """,
            (customer_id,),
        )

    async def repayment_schedule(
        self, contract_id: str, start_period: int | None, end_period: int | None
    ) -> tuple[dict[str, object], int]:
        """读取选定区间和整笔贷款截至种子日期的还款概况。"""
        schedule = await self._fetch(
            """
            SELECT period, due_date, amount_yen, principal_yen, interest_yen
            FROM repayment_schedule
            WHERE contract_id = %s
                AND (%s IS NULL OR period >= %s)
                AND (%s IS NULL OR period <= %s)
            ORDER BY period
            """,
            (contract_id, start_period, start_period, end_period, end_period),
        )
        unpaid = await self._fetch(
            """
            SELECT s.due_date, s.amount_yen, s.principal_yen
            FROM repayment_schedule AS s
            LEFT JOIN repayment_history AS h
                ON h.contract_id = s.contract_id AND h.period = s.period
            WHERE s.contract_id = %s AND h.contract_id IS NULL
            ORDER BY s.period
            """,
            (contract_id,),
        )
        next_payment = next((row for row in unpaid if cast(date, row["due_date"]) >= AS_OF), {})
        return (
            {
                "next_payment_date": next_payment.get("due_date"),
                "next_payment_yen": next_payment.get("amount_yen"),
                "outstanding_principal_yen": sum(cast(int, row["principal_yen"]) for row in unpaid),
                "remaining_installments": len(unpaid),
                "schedule": schedule,
            },
            len(schedule),
        )

    async def delinquency(self, customer_id: str) -> Row:
        """汇总客户的合成延滞记录。"""
        rows = await self._fetch(
            """
            SELECT COALESCE(MAX(days_overdue), 0) AS days_overdue,
                   CAST(COALESCE(SUM(amount_yen), 0) AS UNSIGNED) AS amount_yen,
                   CAST(COALESCE(SUM(late_fee_yen), 0) AS UNSIGNED) AS late_fee_yen
            FROM delinquencies WHERE customer_id = %s
            """,
            (customer_id,),
        )
        return rows[0]

    async def rate_terms(self, contract_id: str) -> Row:
        """读取合同的合成适用利率与団信条件。"""
        rows = await self._fetch(
            """
            SELECT CAST(annual_rate_percent AS DOUBLE) AS annual_rate_percent,
                   rate_type, fixed_until, insurance_type,
                   CAST(insurance_increment_percent AS DOUBLE) AS insurance_increment_percent
            FROM rate_terms WHERE contract_id = %s
            """,
            (contract_id,),
        )
        return rows[0]

    async def benefits(self, customer_id: str) -> list[Row]:
        """读取客户的合成优惠状态。"""
        return await self._fetch(
            "SELECT name, status FROM benefits WHERE customer_id = %s ORDER BY name",
            (customer_id,),
        )
