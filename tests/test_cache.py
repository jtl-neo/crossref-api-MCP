"""Tests for the Redis response cache (cache-aside) using fakeredis."""

from __future__ import annotations

import httpx
import pytest
import respx
from fakeredis import aioredis as fake_aioredis

from crossref_mcp.cache import ResponseCache, normalize_cache_key
from crossref_mcp.client import CrossrefClient
from crossref_mcp.config import Settings

from .conftest import BASE_URL


@pytest.fixture
async def redis():
    r = fake_aioredis.FakeRedis(decode_responses=True)
    try:
        yield r
    finally:
        await r.flushall()
        await r.aclose()


@pytest.fixture
async def cached_client(redis):
    settings = Settings(crossref_mailto="t@e.com", crossref_base_url=BASE_URL)
    cache = ResponseCache(redis, namespace="test:v1", ttl=60)
    c = CrossrefClient(settings=settings, cache=cache, max_retries=1)
    try:
        yield c
    finally:
        await c.aclose()


def test_key_ignores_mailto_and_order():
    a = normalize_cache_key("ns", "/works", {"query": "x", "rows": 5, "mailto": "a@b.c"})
    b = normalize_cache_key("ns", "/works", {"rows": 5, "query": "x", "mailto": "z@z.z"})
    assert a == b  # mailto excluded, order-independent


@respx.mock
async def test_second_call_hits_cache(cached_client):
    route = respx.get(f"{BASE_URL}/works").mock(
        return_value=httpx.Response(200, json={"message": {"items": []}})
    )
    await cached_client.search_works({"query": "x"})
    await cached_client.search_works({"query": "x"})
    assert route.call_count == 1  # second served from cache


@respx.mock
async def test_fresh_bypasses_then_refills(cached_client):
    route = respx.get(f"{BASE_URL}/works").mock(
        return_value=httpx.Response(200, json={"message": {"items": []}})
    )
    await cached_client._get("/works", {"query": "x"})
    await cached_client._get("/works", {"query": "x"}, fresh=True)  # bypass read
    assert route.call_count == 2


@respx.mock
async def test_errors_are_not_cached(cached_client):
    route = respx.get(f"{BASE_URL}/works/10.1/x").mock(
        return_value=httpx.Response(404, text="nope")
    )
    from crossref_mcp.errors import NotFoundError

    for _ in range(2):
        with pytest.raises(NotFoundError):
            await cached_client.get_work("10.1/x")
    assert route.call_count == 2  # 404 never cached
