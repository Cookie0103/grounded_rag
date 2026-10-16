import asyncio
from pathlib import Path

from eval.dataset import Question
from eval.runner import load_cache, run_system
from eval.systems import SystemAnswer


def _questions(count: int) -> list[Question]:
    return [Question(f"q{i}", "问", ("d",)) for i in range(count)]


class CountingSystem:
    name = "counting"

    def __init__(self, fail: set[str] | None = None) -> None:
        self.calls: list[str] = []
        self.running = 0
        self.peak = 0
        self._fail = fail or set()

    async def answer(self, question: Question) -> SystemAnswer:
        self.calls.append(question.id)
        self.running += 1
        self.peak = max(self.peak, self.running)
        await asyncio.sleep(0.01)
        self.running -= 1
        if question.id in self._fail:
            raise RuntimeError("boom")
        return SystemAnswer(question.id, "答", None, ("d",), (), 1.0)


async def test_answers_keep_question_order_and_respect_concurrency() -> None:
    system = CountingSystem()

    answers = await run_system(system, _questions(6), concurrency=2)

    assert [a.question_id for a in answers] == [f"q{i}" for i in range(6)]
    assert system.peak == 2


async def test_failing_question_is_recorded_not_raised_and_not_cached(tmp_path: Path) -> None:
    cache = tmp_path / "answers.jsonl"

    answers = await run_system(CountingSystem(fail={"q1"}), _questions(3), cache_path=cache)

    assert answers[1].error == "RuntimeError: boom"
    assert answers[1].answer is None
    assert set(load_cache(cache)) == {"q0", "q2"}


async def test_cached_questions_are_not_asked_again(tmp_path: Path) -> None:
    cache = tmp_path / "sub" / "answers.jsonl"
    await run_system(CountingSystem(fail={"q1"}), _questions(3), cache_path=cache)
    second = CountingSystem()
    progress: list[tuple[int, int]] = []

    answers = await run_system(
        second,
        _questions(3),
        cache_path=cache,
        progress=lambda done, total: progress.append((done, total)),
    )

    assert second.calls == ["q1"]
    assert all(a.error is None for a in answers)
    assert progress == [(3, 3)]


def test_missing_cache_file_means_empty() -> None:
    assert load_cache(None) == {}
    assert load_cache(Path("nope.jsonl")) == {}
