"""会话记忆：存储接口、内存实现、历史的字数预算与摘要。"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol

from app.core.session import Session, Turn

logger = logging.getLogger(__name__)

MAX_TURNS = 6
KEEP_TURNS = 3
HISTORY_MAX_CHARS = 3000


class SessionStore(Protocol):
    async def load(self, session_id: str) -> Session | None: ...

    async def save(self, session: Session) -> None: ...

    async def purge_expired(self, max_age_days: int) -> int:
        """删除超过 max_age_days 天没有更新的会话，返回删了几个。"""
        ...


class InMemorySessionStore:
    def __init__(self, now: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self._sessions: dict[str, tuple[Session, datetime]] = {}
        self._now = now

    async def load(self, session_id: str) -> Session | None:
        entry = self._sessions.get(session_id)
        return entry[0].model_copy(deep=True) if entry else None

    async def save(self, session: Session) -> None:
        self._sessions[session.id] = (session.model_copy(deep=True), self._now())

    async def purge_expired(self, max_age_days: int) -> int:
        cutoff = self._now() - timedelta(days=max_age_days)
        expired = [key for key, (_, updated) in self._sessions.items() if updated < cutoff]
        for key in expired:
            del self._sessions[key]
        return len(expired)


def format_history(session: Session, max_chars: int = HISTORY_MAX_CHARS) -> str:
    """给模型看的历史：摘要 + 最近几轮；超出字数预算就从最旧的轮次丢起（摘要保留）。"""
    summary = f"（更早的对话摘要）{session.summary}\n" if session.summary else ""
    lines = [f"用户：{turn.question}\n助手：{turn.answer}" for turn in session.turns]
    while lines and len(summary) + sum(len(line) + 1 for line in lines) > max_chars:
        lines.pop(0)
    return summary + "\n".join(lines)


def needs_summary(session: Session) -> bool:
    return len(session.turns) > MAX_TURNS


def split_for_summary(session: Session) -> tuple[list[Turn], list[Turn]]:
    """返回（要并进摘要的旧轮次，继续保留原文的最近轮次）。"""
    return session.turns[:-KEEP_TURNS], session.turns[-KEEP_TURNS:]
