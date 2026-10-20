import json
from pathlib import Path

import pytest

from app.core.config import REPO_ROOT
from app.providers.fakes import FakeChatModel
from eval.judge import ChatPromptRunner, Judge
from scripts import audit_rejudge, rejudge
from scripts.rejudge_artifacts import FROZEN_FILES, fingerprints
from tests.unit.scripts.test_rejudge import _inputs


async def test_audit_rejects_missing_template_hash_and_accepts_valid_complete_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, questions = _inputs(tmp_path)
    monkeypatch.setattr("eval.judge.gold_document_text", lambda doc: "合成金标")
    good = json.dumps({"nuggets": ["support"], "behavior": "answered"})
    chat = FakeChatModel(responses=[good] * 4)
    monkeypatch.setattr(rejudge, "create_judge", lambda: Judge(ChatPromptRunner(chat)))
    out = tmp_path / "v2"
    await rejudge.run_rejudge(source, out, questions)
    frozen = tmp_path / "frozen.json"
    frozen.write_text(
        json.dumps(
            {"frozen_files": fingerprints([REPO_ROOT / "backend" / name for name in FROZEN_FILES])}
        ),
        encoding="utf-8",
    )
    assert audit_rejudge.audit_run(out, source, questions, frozen) == {
        "planned": 4,
        "judged": 4,
        "errors": 0,
    }
    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    key = next(key for key in manifest["sha256"] if key.endswith("judge_v2.md"))
    manifest["sha256"].pop(key)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="缺键"):
        audit_rejudge.audit_run(out, source, questions, frozen)
