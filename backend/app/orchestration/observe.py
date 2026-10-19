"""观测与干预的存储接口，以及内存实现（单元测试用）。数据库实现在 app/db/observability.py。"""

from datetime import datetime
from typing import Protocol

from app.core.records import BadCase, FeedbackIn, TraceRecord
from app.core.text import question_key


class TraceStore(Protocol):
    async def save(self, record: TraceRecord) -> None: ...

    async def get(self, trace_id: str) -> TraceRecord | None: ...

    async def add_feedback(self, item: FeedbackIn) -> None: ...

    async def bad_cases(self, since: datetime | None = None) -> list[BadCase]: ...


class InterventionStore(Protocol):
    async def get(self, question: str) -> str | None: ...

    async def set(self, question: str, answer: str) -> None: ...

    async def remove(self, question: str) -> bool: ...

    async def list_all(self) -> list[tuple[str, str]]: ...


class InMemoryTraceStore:
    def __init__(self) -> None:
        self.records: dict[str, TraceRecord] = {}
        self.feedback: list[FeedbackIn] = []

    async def save(self, record: TraceRecord) -> None:
        self.records.setdefault(record.trace_id, record)

    async def get(self, trace_id: str) -> TraceRecord | None:
        return self.records.get(trace_id)

    async def add_feedback(self, item: FeedbackIn) -> None:
        self.feedback.append(item)

    async def bad_cases(self, since: datetime | None = None) -> list[BadCase]:
        bad = {item.trace_id for item in self.feedback if item.rating == "bad"}
        cases: list[BadCase] = []
        for record in self.records.values():
            if record.trace_id in bad:
                reason = "bad_feedback"
            elif record.abstained:
                reason = "abstained"
            elif record.degraded:
                reason = "degraded"
            else:
                continue
            cases.append(BadCase(trace_id=record.trace_id, question=record.question, reason=reason))
        return cases


class InMemoryInterventionStore:
    def __init__(self) -> None:
        self._items: dict[str, tuple[str, str]] = {}

    async def get(self, question: str) -> str | None:
        item = self._items.get(question_key(question))
        return item[1] if item else None

    async def set(self, question: str, answer: str) -> None:
        self._items[question_key(question)] = (question, answer)

    async def remove(self, question: str) -> bool:
        return self._items.pop(question_key(question), None) is not None

    async def list_all(self) -> list[tuple[str, str]]:
        return list(self._items.values())
