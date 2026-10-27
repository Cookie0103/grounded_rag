from pathlib import Path

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """临时目录指到了仓库的 .cache/ 下（见 pyproject）；干净的 clone 里它还不存在，先建好。"""
    basetemp = config.option.basetemp
    if basetemp:
        Path(basetemp).resolve().parent.mkdir(parents=True, exist_ok=True)
