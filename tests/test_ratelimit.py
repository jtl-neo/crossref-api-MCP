"""Tests for header parsing and the in-memory token bucket."""

from __future__ import annotations

import pytest

import crossref_mcp.ratelimit as rl
from crossref_mcp.ratelimit import InMemoryTokenBucket, parse_rate_limit_headers


def test_parse_headers_basic():
    assert parse_rate_limit_headers(
        {"X-Rate-Limit-Limit": "50", "X-Rate-Limit-Interval": "1s"}
    ) == (
        50,
        1.0,
    )


def test_parse_headers_minutes():
    assert parse_rate_limit_headers(
        {"X-Rate-Limit-Limit": "300", "X-Rate-Limit-Interval": "5m"}
    ) == (300, 300.0)


def test_parse_headers_missing_returns_none():
    assert parse_rate_limit_headers({}) == (None, None)


def test_parse_headers_unparseable_interval():
    limit, interval = parse_rate_limit_headers(
        {"X-Rate-Limit-Limit": "10", "X-Rate-Limit-Interval": "weird"}
    )
    assert limit == 10
    assert interval is None


def test_update_clamps_tokens():
    b = InMemoryTokenBucket(limit=100, interval_s=1.0)
    b.tokens = 100.0
    b.update(10, 1.0)  # capacity shrinks to 10
    assert b.capacity == 10
    assert b.tokens <= 10.0


async def test_bucket_blocks_then_refills(monkeypatch):
    clock = {"now": 0.0}
    sleeps: list[float] = []

    monkeypatch.setattr(rl.time, "monotonic", lambda: clock["now"])

    async def fake_sleep(s: float):
        sleeps.append(s)
        clock["now"] += s  # advance the clock so tokens refill

    monkeypatch.setattr(rl.asyncio, "sleep", fake_sleep)

    b = InMemoryTokenBucket(limit=2, interval_s=1.0)  # capacity 2, rate 2/s
    await b.acquire()  # 2 -> 1, no sleep
    await b.acquire()  # 1 -> 0, no sleep
    await b.acquire()  # empty -> must wait 0.5s (1 token / 2 per s)
    assert sleeps
    assert sleeps[0] == pytest.approx(0.5, abs=0.01)
