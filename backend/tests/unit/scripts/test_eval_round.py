from pathlib import Path

import pytest

from app.core.config import REPO_ROOT
from scripts.eval_round import check_archive_root

OUTSIDE = REPO_ROOT.parent / "eval-private-archive"


def test_sealed_test_archive_must_live_outside_the_repository() -> None:
    check_archive_root("test", OUTSIDE)  # 仓库外：允许
    check_archive_root("dev", REPO_ROOT / "docs/eval/results/runs")  # 开发题可以归档在仓库里
    with pytest.raises(ValueError, match="仓库外"):
        check_archive_root("test", REPO_ROOT / "docs/eval/results/runs")
    with pytest.raises(ValueError, match="仓库外"):
        check_archive_root("test", Path(REPO_ROOT) / ".cache" / "x")
