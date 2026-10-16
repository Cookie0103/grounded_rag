"""trace、反馈、干预库的读写。"""

from datetime import datetime
from typing import Any

from sqlalchemy import Row, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.records import BadCase, FeedbackIn, TraceRecord
from app.core.text import question_key
from app.db.tables import feedback, interventions, traces


class PostgresTraceStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def save(self, record: TraceRecord) -> None:
        values = record.model_dump(exclude={"created_at"})
        statement = insert(traces).values(**values)
        statement = statement.on_conflict_do_nothing(index_elements=[traces.c.trace_id])
        async with self._engine.begin() as connection:
            await connection.execute(statement)

    async def get(self, trace_id: str) -> TraceRecord | None:
        async with self._engine.connect() as connection:
            row = (
                await connection.execute(select(traces).where(traces.c.trace_id == trace_id))
            ).first()
        return TraceRecord.model_validate(row._asdict()) if row else None

    async def add_feedback(self, item: FeedbackIn) -> None:
        async with self._engine.begin() as connection:
            await connection.execute(insert(feedback).values(**item.model_dump()))

    async def bad_cases(self, since: datetime | None = None) -> list[BadCase]:
        """差评、拒答、降级的 trace，每个 trace 只出现一次（原因按差评 > 拒答 > 降级）。"""
        bad_ids = select(feedback.c.trace_id).where(feedback.c.rating == "bad")
        query = select(traces).where(
            traces.c.trace_id.in_(bad_ids) | traces.c.abstained | traces.c.degraded
        )
        if since is not None:
            query = query.where(traces.c.created_at >= since)
        async with self._engine.connect() as connection:
            rows = (await connection.execute(query.order_by(traces.c.created_at))).all()
            bad = {row.trace_id for row in (await connection.execute(bad_ids)).all()}
        return [
            BadCase(trace_id=row.trace_id, question=row.question, reason=_reason(row, bad))
            for row in rows
        ]


def _reason(row: Row[Any], bad: set[str]) -> str:
    if row.trace_id in bad:
        return "bad_feedback"
    return "abstained" if row.abstained else "degraded"


class PostgresInterventionStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def get(self, question: str) -> str | None:
        async with self._engine.connect() as connection:
            return (
                await connection.execute(
                    select(interventions.c.answer).where(
                        interventions.c.question_key == question_key(question)
                    )
                )
            ).scalar_one_or_none()

    async def set(self, question: str, answer: str) -> None:
        statement = insert(interventions).values(
            question_key=question_key(question), question=question, answer=answer
        )
        statement = statement.on_conflict_do_update(
            index_elements=[interventions.c.question_key],
            set_={"question": question, "answer": answer, "created_at": func.now()},
        )
        async with self._engine.begin() as connection:
            await connection.execute(statement)

    async def remove(self, question: str) -> bool:
        async with self._engine.begin() as connection:
            result = await connection.execute(
                delete(interventions).where(interventions.c.question_key == question_key(question))
            )
        return bool(result.rowcount)

    async def list_all(self) -> list[tuple[str, str]]:
        async with self._engine.connect() as connection:
            rows = (
                await connection.execute(
                    select(interventions.c.question, interventions.c.answer).order_by(
                        interventions.c.created_at
                    )
                )
            ).all()
        return [(row.question, row.answer) for row in rows]
