"""Client-level tests: polite pool headers, mailto injection, retry, errors."""

from __future__ import annotations

import httpx
import pytest
import respx

from crossref_mcp.client import CrossrefClient
from crossref_mcp.config import Settings
from crossref_mcp.errors import NotFoundError, UpstreamError

from .conftest import BASE_URL


@respx.mock
async def test_mailto_always_sent_and_user_agent(client: CrossrefClient):
    route = respx.get(f"{BASE_URL}/works").mock(
        return_value=httpx.Response(200, json={"message": {"items": []}})
    )
    await client.search_works({"query": "x"})

    request = route.calls.last.request
    assert request.url.params["mailto"] == "test@example.com"
    ua = request.headers["User-Agent"]
    assert ua.startswith("crossref-mcp/")
    assert "mailto:test@example.com" in ua


@respx.mock
async def test_plus_token_coexists_with_user_agent():
    settings = Settings(
        crossref_mailto="t@e.com",
        crossref_base_url=BASE_URL,
        crossref_plus_token="secret-token",
    )
    c = CrossrefClient(settings=settings)
    route = respx.get(f"{BASE_URL}/works").mock(
        return_value=httpx.Response(200, json={"message": {"items": []}})
    )
    try:
        await c.search_works({})
    finally:
        await c.aclose()

    headers = route.calls.last.request.headers
    assert headers["Crossref-Plus-API-Token"] == "secret-token"
    assert headers["User-Agent"].startswith("crossref-mcp/")  # UA preserved


@respx.mock
async def test_404_raises_not_found_without_retry(client: CrossrefClient):
    route = respx.get(f"{BASE_URL}/works/10.1000/missing").mock(
        return_value=httpx.Response(404, text="Resource not found")
    )
    with pytest.raises(NotFoundError):
        await client.get_work("10.1000/missing")
    assert route.call_count == 1  # not retried


@respx.mock
async def test_retry_on_500_then_success(client: CrossrefClient):
    route = respx.get(f"{BASE_URL}/works").mock(
        side_effect=[
            httpx.Response(500, text="boom"),
            httpx.Response(200, json={"message": {"items": []}}),
        ]
    )
    data = await client.search_works({})
    assert data == {"message": {"items": []}}
    assert route.call_count == 2


@respx.mock
async def test_retry_exhausted_raises_upstream(client: CrossrefClient):
    route = respx.get(f"{BASE_URL}/works").mock(
        return_value=httpx.Response(503, text="unavailable")
    )
    with pytest.raises(UpstreamError):
        await client.search_works({})
    # max_retries=2 -> 1 initial + 2 retries = 3 attempts
    assert route.call_count == 3
