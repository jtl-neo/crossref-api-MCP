"""Live smoke tests against the real Crossref API.

Skipped by default (they hit the network). Run with:

    CROSSREF_LIVE=1 CROSSREF_MAILTO=you@example.com uv run pytest -m live

They guard against Crossref response-shape drift that mocked tests can't catch.
"""

from __future__ import annotations

import os

import pytest

from crossref_mcp.client import CrossrefClient
from crossref_mcp.config import Settings
from crossref_mcp.models import simplify_work

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.environ.get("CROSSREF_LIVE") != "1",
        reason="set CROSSREF_LIVE=1 to run live Crossref API tests",
    ),
]

# A stable, well-known DOI (Crossref's own DOI handbook reference).
KNOWN_DOI = "10.1145/3292500.3330701"


@pytest.fixture
def live_client():
    mailto = os.environ.get("CROSSREF_MAILTO", "ci@example.com")
    return CrossrefClient(settings=Settings(crossref_mailto=mailto))


async def test_live_get_work(live_client):
    try:
        message = await live_client.get_work(KNOWN_DOI)
        out = simplify_work(message)
        assert out["doi"].lower() == KNOWN_DOI.lower()
        assert out["title"]
        assert isinstance(out["authors"], list)
    finally:
        await live_client.aclose()


async def test_live_search_works(live_client):
    try:
        data = await live_client.search_works({"query": "deep learning", "rows": 3})
        items = data["message"]["items"]
        assert 1 <= len(items) <= 3
        assert "DOI" in items[0]
    finally:
        await live_client.aclose()
