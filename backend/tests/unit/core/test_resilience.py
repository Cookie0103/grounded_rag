from app.core.cache import TtlCache
from app.core.resilience import CLOSED, HALF_OPEN, OPEN, CircuitBreaker, TokenBucketLimiter


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_cache_hit_miss_and_counters() -> None:
    cache: TtlCache[str, int] = TtlCache(2, 10)

    assert cache.get("a") is None
    cache.put("a", 1)

    assert cache.get("a") == 1
    assert (cache.hits, cache.misses) == (1, 1)


def test_cache_entries_expire_after_ttl() -> None:
    clock = Clock()
    cache: TtlCache[str, int] = TtlCache(2, 10, clock)
    cache.put("a", 1)

    clock.now = 10
    assert cache.get("a") == 1
    clock.now = 10.5
    assert cache.get("a") is None
    assert len(cache) == 0


def test_cache_evicts_the_least_recently_used() -> None:
    cache: TtlCache[str, int] = TtlCache(2, 10)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.get("a")  # a 变成最近使用
    cache.put("c", 3)

    assert cache.get("b") is None
    assert cache.get("a") == 1
    assert cache.get("c") == 3


def test_breaker_opens_after_consecutive_failures_and_a_success_resets_the_count() -> None:
    breaker = CircuitBreaker(threshold=3, reset_seconds=30, clock=Clock())

    breaker.record_failure()
    breaker.record_failure()
    breaker.record_success()
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.state == CLOSED
    assert breaker.allow()

    breaker.record_failure()
    assert breaker.state == OPEN
    assert not breaker.allow()


def test_breaker_half_opens_after_the_timeout_and_lets_one_probe_through() -> None:
    clock = Clock()
    breaker = CircuitBreaker(threshold=1, reset_seconds=30, clock=clock)
    breaker.record_failure()

    clock.now = 30
    assert breaker.state == HALF_OPEN
    assert breaker.allow()
    assert not breaker.allow()  # 试探还没出结果，别的调用继续被挡

    breaker.record_success()
    assert breaker.state == CLOSED
    assert breaker.allow()


def test_failed_probe_reopens_the_breaker_for_a_full_period() -> None:
    clock = Clock()
    breaker = CircuitBreaker(threshold=1, reset_seconds=30, clock=clock)
    breaker.record_failure()
    clock.now = 30
    assert breaker.allow()

    breaker.record_failure()

    assert breaker.state == OPEN
    clock.now = 59
    assert not breaker.allow()
    clock.now = 60
    assert breaker.allow()


def test_limiter_blocks_after_the_burst_isolates_keys_and_refills() -> None:
    clock = Clock()
    limiter = TokenBucketLimiter(per_minute=60, clock=clock)

    assert all(limiter.allow("a") for _ in range(60))
    assert not limiter.allow("a")
    assert limiter.allow("b")

    clock.now = 2  # 每秒补 1 个
    assert limiter.allow("a")
    assert limiter.allow("a")
    assert not limiter.allow("a")


def test_limiter_with_zero_means_unlimited_and_caps_the_number_of_keys() -> None:
    assert all(TokenBucketLimiter(0).allow("a") for _ in range(1000))

    limiter = TokenBucketLimiter(1, max_keys=2)
    for key in ("a", "b", "c"):
        assert limiter.allow(key)
    assert len(limiter._buckets) <= 2
