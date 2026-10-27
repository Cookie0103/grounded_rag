import json
from pathlib import Path

import pytest

from app.core.config import REPO_ROOT
from scripts import rejudge_artifacts as artifacts


@pytest.mark.parametrize("change", ["missing", "extra", "wrong", "empty", "duplicate"])
def test_hash_validation_fails_closed(change: str) -> None:
    expected = {"/new/judge_v2.md": "abc", "/new/judge.py": "def"}
    recorded = {"C:\\old\\judge_v2.md": "abc", "C:\\old\\judge.py": "def"}
    if change == "missing":
        del recorded["C:\\old\\judge_v2.md"]
    elif change == "extra":
        recorded["C:\\old\\extra.py"] = "xyz"
    elif change == "wrong":
        recorded["C:\\old\\judge_v2.md"] = "wrong"
    elif change == "duplicate":
        recorded["C:\\other\\judge_v2.md"] = "abc"
    else:
        recorded = {}
    with pytest.raises(ValueError, match=r"哈希|重名"):
        artifacts.verify_portable_hashes(recorded, expected)


def test_hash_validation_supports_explicit_cross_platform_filename_mapping() -> None:
    artifacts.verify_portable_hashes(
        {"C:\\old\\judge_v2.md": "abc", "C:\\old\\judge.py": "def"},
        {"/new/judge_v2.md": "abc", "/new/judge.py": "def"},
    )


def test_successful_retry_keeps_error_history(tmp_path: Path) -> None:
    artifacts.record_errors(tmp_path, {"q1": "首次额度错误"})
    artifacts.record_errors(tmp_path, {"q1": "第二次错误", "q2": "另一个错误"})
    history = artifacts.record_errors(tmp_path, {})
    assert history == {"q1": ["首次额度错误", "第二次错误"], "q2": ["另一个错误"]}


def test_frozen_verification_requires_exact_implementation_list(tmp_path: Path) -> None:
    path = tmp_path / "frozen.json"
    expected = artifacts.fingerprints(
        [REPO_ROOT / "backend" / name for name in artifacts.FROZEN_FILES]
    )
    path.write_text(json.dumps({"frozen_files": expected}), encoding="utf-8")
    artifacts.verify_frozen(path)
    expected.pop(next(key for key in expected if key.endswith("judge_v2.md")))
    path.write_text(json.dumps({"frozen_files": expected}), encoding="utf-8")
    with pytest.raises(ValueError, match="缺键"):
        artifacts.verify_frozen(path)
