"""每日预算记账：按日期记在一个 JSON 文件里，调用前检查、调用后累加。"""

import json
import logging
from collections.abc import Callable
from datetime import date
from pathlib import Path

from app.core.errors import BudgetExceededError

logger = logging.getLogger(__name__)


class BudgetLedger:
    def __init__(
        self,
        directory: Path,
        daily_limit_cny: float,
        today: Callable[[], date] = date.today,
    ) -> None:
        self._directory = directory
        self._limit = daily_limit_cny
        self._today = today

    def _path(self) -> Path:
        return self._directory / f"{self._today().isoformat()}.json"

    def spent(self) -> float:
        path = self._path()
        if not path.exists():
            return 0.0
        try:
            return float(json.loads(path.read_text(encoding="utf-8"))["spent_cny"])
        except (ValueError, KeyError, TypeError):
            logger.warning("预算文件 %s 损坏，今天的花费从 0 重新开始记", path)
            return 0.0

    def check(self) -> None:
        """今天已经花够了就抛错；预算为 0 表示不限制。"""
        if self._limit > 0 and self.spent() >= self._limit:
            raise BudgetExceededError(
                f"今天的模型调用费用 ¥{self.spent():.2f} 已达到预算 ¥{self._limit:.2f}"
            )

    def add(self, cost_cny: float) -> None:
        self._directory.mkdir(parents=True, exist_ok=True)
        record = {"spent_cny": self.spent() + cost_cny}
        self._path().write_text(json.dumps(record), encoding="utf-8")
