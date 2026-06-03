"""Shared test fixtures. All tests run against respx mocks — no real network."""

from __future__ import annotations

import pytest

from crossref_mcp.client import CrossrefClient
from crossref_mcp.config import Settings

BASE_URL = "https://api.crossref.org"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        crossref_mailto="test@example.com",
        crossref_base_url=BASE_URL,
        crossref_timeout=5.0,
    )


@pytest.fixture
async def client(settings: Settings) -> CrossrefClient:
    c = CrossrefClient(settings=settings, max_retries=2)
    try:
        yield c
    finally:
        await c.aclose()


class FakeMCP:
    """Captures @tool-decorated functions so they can be called directly."""

    def __init__(self) -> None:
        self.tools: dict = {}

    def tool(self, *args, **kwargs):
        def deco(fn):
            self.tools[fn.__name__] = fn
            return fn

        return deco


@pytest.fixture
def work_message() -> dict:
    """A single work 'message' (as returned under envelope['message'])."""
    return {
        "DOI": "10.1000/xyz123",
        "title": ["A Study of Things"],
        "author": [
            {"given": "Ada", "family": "Lovelace", "sequence": "first"},
            {"given": "Alan", "family": "Turing", "sequence": "additional"},
        ],
        "issued": {"date-parts": [[2021, 5, 17]]},
        "container-title": ["Journal of Things"],
        "URL": "https://doi.org/10.1000/xyz123",
        "type": "journal-article",
        "reference-count": 3,
        "reference": [
            {"key": "ref1", "DOI": "10.1/a"},
            {"key": "ref2", "DOI": "10.1/b"},
            {"key": "ref3", "DOI": "10.1/c"},
        ],
    }


@pytest.fixture
def work_envelope(work_message: dict) -> dict:
    return {"status": "ok", "message-type": "work", "message": work_message}


@pytest.fixture
def works_list_envelope(work_message: dict) -> dict:
    return {
        "status": "ok",
        "message-type": "work-list",
        "message": {"total-results": 42, "items": [work_message, work_message]},
    }


@pytest.fixture
def agency_envelope() -> dict:
    return {
        "status": "ok",
        "message-type": "work-agency",
        "message": {
            "DOI": "10.1000/xyz123",
            "agency": {"id": "crossref", "label": "Crossref"},
        },
    }
