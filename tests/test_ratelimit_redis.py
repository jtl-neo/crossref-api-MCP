"""Tests for the Redis-backed cross-replica token bucket (fakeredis + Lua)."""

from __future__ import annotations

import pytest
from fakeredis import aioredis as fake_aioredis

from crossref_mcp.ratelimit import RedisTokenBucket


@pytest.fixture
async def redis():
    r = fake_aioredis.FakeRedis(decode_responses=True)
    try:
        yield r
    finally:
        await r.flushall()
        await r.aclose()


async def test_shared_bucket_limits_two_replicas(redis, monkeypatch):
    # Two limiters = two replicas sharing one Redis key.
    import crossref_mcp.ratelimit as rl

    sleeps: list[float] = []

    async def fake_sleep(s: float):
        sleeps.append(s)

    monkeypatch.setattr(rl.asyncio, "sleep", fake_sleep)

    key = "test:rl"
    a = RedisTokenBucket(redis, key=key, limit=3, interval_s=1.0)
    b = RedisTokenBucket(redis, key=key, limit=3, interval_s=1.0)

    # Capacity 3, shared. First 3 acquires across both replicas succeed instantly.
    await a.acquire()
    await b.acquire()
    await a.acquire()
    assert sleeps == []  # no waiting yet

    # 4th acquire must wait (bucket drained) — fake_sleep records the wait and
    # returns immediately; the refilled token then lets it through.
    await b.acquire()
    assert sleeps, "expected a wait once the shared bucket was drained"


async def test_degrades_when_redis_eval_fails(monkeypatch):
    class BrokenRedis:
        async def eval(self, *a, **k):
            raise RuntimeError("redis down")

    bucket = RedisTokenBucket(BrokenRedis(), limit=5, interval_s=1.0)
    # Should fall back to the in-memory bucket and not raise.
    await bucket.acquire()
