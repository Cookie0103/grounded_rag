import json

import httpx
import pytest

from scripts.load_test import run_load, summarize


def test_summary_counts_errors_and_computes_percentiles_from_successes() -> None:
    result = summarize([float(ms) for ms in range(1, 101)], errors=4, elapsed_seconds=2.0)

    assert result.requests == 104
    assert result.errors == 4
    assert result.qps == pytest.approx(52.0)
    assert result.p50_ms == pytest.approx(50.5)
    assert result.p95_ms == pytest.approx(95.05)
    assert "QPS 52.00" in result.render()


def test_summary_without_successes_is_all_zero() -> None:
    result = summarize([], errors=3, elapsed_seconds=1.0)

    assert (result.p50_ms, result.p95_ms, result.p99_ms) == (0.0, 0.0, 0.0)
    assert result.requests == 3


async def test_run_load_sends_the_right_bodies_and_counts_failures() -> None:
    seen: list[dict[str, str]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        if len(seen) == 3:
            return httpx.Response(500)
        if len(seen) == 4:
            raise httpx.ConnectError("refused")
        return httpx.Response(200, json={})

    client = httpx.AsyncClient(base_url="http://x", transport=httpx.MockTransport(handle))

    result = await run_load(client, "chat", ["甲", "乙"], requests=6, concurrency=1, unique=True)

    assert seen[0] == {"question": "甲（0）"}
    assert seen[1] == {"question": "乙（1）"}
    assert (result.requests, result.errors) == (6, 2)
    retrieve = await run_load(
        httpx.AsyncClient(
            base_url="http://x", transport=httpx.MockTransport(lambda r: httpx.Response(200))
        ),
        "retrieve",
        ["甲"],
        requests=1,
        concurrency=1,
        unique=False,
    )
    assert retrieve.errors == 0
