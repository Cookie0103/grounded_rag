"""熔断器和令牌桶限流器。时钟可以注入，测试不用真的等。"""

import time
from collections.abc import Callable
from dataclasses import dataclass

CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"


class CircuitBreaker:
    """连续失败 threshold 次后打开；reset_seconds 之后半开放一次试探：成功关闭，失败重新打开。"""

    def __init__(
        self,
        threshold: int = 3,
        reset_seconds: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._threshold = threshold
        self._reset = reset_seconds
        self._clock = clock
        self._failures = 0
        self._opened_at: float | None = None
        self._probing = False

    @property
    def state(self) -> str:
        if self._opened_at is None:
            return CLOSED
        if self._clock() - self._opened_at >= self._reset:
            return HALF_OPEN
        return OPEN

    def allow(self) -> bool:
        """现在能不能调用。半开时只放第一个调用进去试探。"""
        state = self.state
        if state == CLOSED:
            return True
        if state == HALF_OPEN and not self._probing:
            self._probing = True
            return True
        return False

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None
        self._probing = False

    def record_failure(self) -> None:
        self._failures += 1
        self._probing = False
        if self._failures >= self._threshold or self._opened_at is not None:
            self._opened_at = self._clock()


@dataclass
class _Bucket:
    tokens: float
    updated: float


class TokenBucketLimiter:
    """每个 key 一个桶：容量 = 每分钟次数，匀速补充。`per_minute <= 0` 表示不限制。"""

    def __init__(
        self, per_minute: int, clock: Callable[[], float] = time.monotonic, max_keys: int = 10000
    ) -> None:
        self._capacity = float(per_minute)
        self._rate = per_minute / 60.0
        self._clock = clock
        self._max_keys = max_keys
        self._buckets: dict[str, _Bucket] = {}

    def allow(self, key: str) -> bool:
        if self._capacity <= 0:
            return True
        now = self._clock()
        bucket = self._buckets.get(key)
        if bucket is None:
            if len(self._buckets) >= self._max_keys:
                self._buckets.clear()  # 防止被伪造的 key 撑爆内存；代价是放过一轮
            bucket = self._buckets[key] = _Bucket(self._capacity, now)
        bucket.tokens = min(self._capacity, bucket.tokens + (now - bucket.updated) * self._rate)
        bucket.updated = now
        if bucket.tokens < 1:
            return False
        bucket.tokens -= 1
        return True
