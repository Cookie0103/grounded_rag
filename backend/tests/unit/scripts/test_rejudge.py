import json
from pathlib import Path

import pytest

from app.core.config import REPO_ROOT
from app.providers.fakes import FakeChatModel
from eval.judge import ChatPromptRunner, Judge
from eval.systems import SystemAnswer
from scripts import rejudge


def _inputs(tmp_path: Path, *, split: str = "dev") -> tuple[Path, Path]:
    source = tmp_path / "v1"
    source.mkdir()
    questions = tmp_path / "questions.jsonl"
    rows = [
        {
            "id": f"q{i}",
            "question": "合成问题",
            "gold_docs": ["a"],
            "split": split,
            "nuggets": [{"text": "合成要点", "importance": "vital"}],
        }
        for i in range(4)
    ]
    questions.write_text("\n".join(json.dumps(q) for q in rows), encoding="utf-8")
    answers = [
        SystemAnswer(str(q["id"]), "缓存回答", "SINGLE", ("a",), ("缓存资料",), 1.0) for q in rows
    ]
    (source / "answers.jsonl").write_text(
        "\n".join(json.dumps(a.to_json()) for a in answers), encoding="utf-8"
    )
    (source / "verdicts.jsonl").write_text(
        "\n".join(
            json.dumps(
                {
                    "question_id": q["id"],
                    "nuggets": ["support"],
                    "contradiction": i % 2 == 0,
                    "behavior": "answered",
                    "corrects_premise": False,
                    "covers_interpretations": False,
                }
            )
            for i, q in enumerate(rows)
        ),
        encoding="utf-8",
    )
    return source, questions


@pytest.fixture(autouse=True)
def _fake_gold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("eval.judge.gold_document_text", lambda doc: "合成金标")


async def test_rejudge_refuses_even_an_empty_existing_output(tmp_path: Path) -> None:
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(FileExistsError):
        await rejudge.run_rejudge(tmp_path / "missing", output, tmp_path / "missing.jsonl")
    assert list(output.iterdir()) == []


def test_rejudge_test_output_must_be_outside_repository() -> None:
    with pytest.raises(ValueError, match="仓库外"):
        rejudge.check_output_location(True, REPO_ROOT / ".cache" / "test-v2")
    rejudge.check_output_location(False, REPO_ROOT / ".cache" / "dev-v2")
    rejudge.check_output_location(True, REPO_ROOT.parent / "private-test-v2")


async def test_rejudge_reuses_pilot_labels_and_preserves_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, questions = _inputs(tmp_path)
    original = {p.name: p.read_bytes() for p in source.iterdir()}
    responses = [
        json.dumps({"nuggets": ["support"], "contradiction": i % 2 != 0, "behavior": "answered"})
        for i in range(4)
    ]
    chat = FakeChatModel(responses=responses)
    monkeypatch.setattr(rejudge, "create_judge", lambda: Judge(ChatPromptRunner(chat)))
    output = tmp_path / "v2"

    result = await rejudge.run_rejudge(source, output, questions)

    assert len(chat.calls) == 4  # 前三题不会在整套阶段再次评审
    assert len(result.scored) == 4
    assert all("缓存资料" in call[0].content for call in chat.calls)
    assert {p.name: p.read_bytes() for p in source.iterdir()} == original
    assert not (output / "answers.jsonl").exists()
    flips = (output / "flips.md").read_text(encoding="utf-8")
    assert "true → false" in flips
    assert "false → true" in flips
    assert all(f"q{i}" in flips for i in range(4))


async def test_pilot_judge_errors_are_reported_and_stop_full_phase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, questions = _inputs(tmp_path)
    chat = FakeChatModel(responses=["非法"] * 6)
    monkeypatch.setattr(rejudge, "create_judge", lambda: Judge(ChatPromptRunner(chat)))
    output = tmp_path / "failed-v2"
    result = await rejudge.run_rejudge(source, output, questions)
    assert len(result.judge_errors) == 3
    assert len(chat.calls) == 6
    assert "q3" not in (output / "report.md").read_text(encoding="utf-8")
    assert set(json.loads((output / "errors.json").read_text(encoding="utf-8"))) == {
        "q0",
        "q1",
        "q2",
    }
