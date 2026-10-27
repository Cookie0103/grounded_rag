"""会话表的读写。"""

from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.session import Session, Turn
from app.db.tables import sessions


class PostgresSessionStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def load(self, session_id: str) -> Session | None:
        async with self._engine.connect() as connection:
            row = (
                await connection.execute(select(sessions).where(sessions.c.id == session_id))
            ).first()
        if row is None:
            return None
        return Session(
            id=row.id,
            edition=row.edition,
            summary=row.summary,
            turns=[Turn.model_validate(turn) for turn in row.turns],
        )

    async def save(self, session: Session) -> None:
        values = {
            "id": session.id,
            "edition": session.edition,
            "summary": session.summary,
            "turns": [turn.model_dump() for turn in session.turns],
        }
        statement = insert(sessions).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=[sessions.c.id],
            set_={**{k: v for k, v in values.items() if k != "id"}, "updated_at": func.now()},
        )
        async with self._engine.begin() as connection:
            await connection.execute(statement)

    async def purge_expired(self, max_age_days: int) -> int:
        cutoff = func.now() - timedelta(days=max_age_days)
        async with self._engine.begin() as connection:
            result = await connection.execute(
                delete(sessions).where(sessions.c.updated_at < cutoff)
            )
        return result.rowcount
