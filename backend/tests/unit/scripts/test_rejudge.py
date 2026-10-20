import json
from pathlib import Path

import pytest

from app.core.config import REPO_ROOT
from app.providers.fakes import FakeChatModel
from eval.judge import ChatPromptRunner, Judge
from eval.systems import SystemAnswer
from scripts import rejudge


def _inputs(tmp_path: Path, *, split: str = "dev", count: int = 4) -> tuple[Path, Path]:
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
        for i in range(count)
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
    (source / "report.md").write_text("旧报告只读", encoding="utf-8")
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
    assert len(result.judge_errors) == 1
    assert len(chat.calls) == 2
    assert "q3" not in (output / "report.md").read_text(encoding="utf-8")
    assert set(json.loads((output / "errors.json").read_text(encoding="utf-8"))) == {
        "q0",
    }


async def test_full_phase_stops_only_after_more_than_ten_percent_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, questions = _inputs(tmp_path, count=20)
    good = json.dumps({"nuggets": ["support"], "behavior": "answered"})
    chat = FakeChatModel(responses=[good] * 3 + ["非法"] * 6 + [good] * 14)
    monkeypatch.setattr(rejudge, "create_judge", lambda: Judge(ChatPromptRunner(chat)))
    output = tmp_path / "v2"
    result = await rejudge.run_rejudge(source, output, questions)
    assert len(chat.calls) == 9
    assert set(result.judge_errors) == {"q3", "q4", "q5"}
    assert len(result.scored) == 3
    metrics = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["not_reviewed"] == 14
    assert metrics["historical_error_questions"] == 3


async def test_seed_labels_are_reused_in_new_directory_and_history_is_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, questions = _inputs(tmp_path)
    seed = tmp_path / "interrupted"
    good = json.dumps({"nuggets": ["support"], "behavior": "answered"})
    # 首轮pilot报错，不产生任何标签；随后模拟一个已落盘成功标签。
    chat = FakeChatModel(responses=["非法"] * 2)
    monkeypatch.setattr(rejudge, "create_judge", lambda: Judge(ChatPromptRunner(chat)))
    await rejudge.run_rejudge(source, seed, questions)
    row = json.loads((source / "verdicts.jsonl").read_text(encoding="utf-8").splitlines()[1])
    (seed / "verdicts.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    original = {p.name: p.read_bytes() for p in seed.iterdir()}
    chat = FakeChatModel(responses=[good] * 3)
    monkeypatch.setattr(rejudge, "create_judge", lambda: Judge(ChatPromptRunner(chat)))
    output = tmp_path / "continued"
    result = await rejudge.run_rejudge(source, output, questions, seed_run=seed)
    assert len(chat.calls) == 3
    assert len(result.scored) == 4
    assert {p.name: p.read_bytes() for p in seed.iterdir()} == original
    assert json.loads((output / "errors.json").read_text(encoding="utf-8")) == {}
    assert "q0" in json.loads((output / "errors-history.json").read_text(encoding="utf-8"))


async def test_seed_with_different_template_hash_is_rejected_before_any_judge_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, questions = _inputs(tmp_path)
    seed = tmp_path / "seed"
    rejudge._prepare(source, seed, questions)
    manifest_path = seed / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    key = next(key for key in manifest["sha256"] if key.endswith("judge_v2.md"))
    manifest["sha256"][key] = "wrong"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    called = False

    def forbidden() -> Judge:
        nonlocal called
        called = True
        raise AssertionError("不得调用评审")

    monkeypatch.setattr(rejudge, "create_judge", forbidden)
    output = tmp_path / "continued"
    with pytest.raises(ValueError, match="哈希"):
        await rejudge.run_rejudge(source, output, questions, seed_run=seed)
    assert not called
    assert not output.exists()


async def test_abnormal_exit_still_checks_protected_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, questions = _inputs(tmp_path)

    def changed_then_failed() -> Judge:
        (source / "report.md").write_text("意外改动", encoding="utf-8")
        raise ValueError("模拟初始化异常")

    monkeypatch.setattr(rejudge, "create_judge", changed_then_failed)
    with pytest.raises(RuntimeError, match="发生变化") as error:
        await rejudge.run_rejudge(source, tmp_path / "v2", questions)
    assert isinstance(error.value.__context__, ValueError)


async def test_abnormal_exit_preserves_original_error_when_hashes_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, questions = _inputs(tmp_path)

    def failed() -> Judge:
        raise ValueError("模拟初始化异常")

    monkeypatch.setattr(rejudge, "create_judge", failed)
    with pytest.raises(ValueError, match="模拟初始化异常"):
        await rejudge.run_rejudge(source, tmp_path / "v2", questions)
