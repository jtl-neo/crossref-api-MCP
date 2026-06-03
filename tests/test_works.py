"""Tool-level tests for tools/works.py via a FakeMCP recorder + respx."""

from __future__ import annotations

import httpx
import pytest
import respx

from crossref_mcp.client import CrossrefClient
from crossref_mcp.tools import works

from .conftest import BASE_URL, FakeMCP


@pytest.fixture
def tools(client: CrossrefClient):
    fake = FakeMCP()
    works.register(fake, lambda: client)
    return fake.tools


@respx.mock
async def test_search_works_simplified_and_raw(tools, works_list_envelope):
    respx.get(f"{BASE_URL}/works").mock(return_value=httpx.Response(200, json=works_list_envelope))

    simplified = await tools["search_works"](query="things")
    assert simplified["total_results"] == 42
    assert simplified["items_count"] == 2
    assert simplified["items"][0]["doi"] == "10.1000/xyz123"
    assert simplified["items"][0]["authors"] == ["Ada Lovelace", "Alan Turing"]
    assert "reference" not in simplified["items"][0]  # trimmed

    raw = await tools["search_works"](query="things", raw=True)
    assert raw == works_list_envelope  # full envelope


@respx.mock
async def test_get_work_simplified_fields(tools, work_envelope):
    respx.get(f"{BASE_URL}/works/10.1000/xyz123").mock(
        return_value=httpx.Response(200, json=work_envelope)
    )
    out = await tools["get_work"](doi="10.1000/xyz123")
    assert out["title"] == "A Study of Things"
    assert out["issued"] == "2021-05-17"
    assert out["container_title"] == "Journal of Things"
    assert out["url"] == "https://doi.org/10.1000/xyz123"


@respx.mock
async def test_get_work_doi_url_is_normalized(tools, work_envelope):
    route = respx.get(f"{BASE_URL}/works/10.1000/xyz123").mock(
        return_value=httpx.Response(200, json=work_envelope)
    )
    # Pass a doi.org URL with mixed case; should hit the normalized path.
    await tools["get_work"](doi="https://doi.org/10.1000/XYZ123")
    assert route.called


@respx.mock
async def test_get_work_references_caps_at_50(tools):
    refs = [{"key": f"r{i}"} for i in range(120)]
    env = {"message": {"DOI": "10.1/x", "reference-count": 120, "reference": refs}}
    respx.get(f"{BASE_URL}/works/10.1/x").mock(return_value=httpx.Response(200, json=env))

    out = await tools["get_work_references"](doi="10.1/x", limit=100)
    assert out["returned"] == 50
    assert out["reference_count"] == 120

    out5 = await tools["get_work_references"](doi="10.1/x", limit=5)
    assert out5["returned"] == 5


@respx.mock
async def test_get_work_quality_agency(tools, agency_envelope):
    respx.get(f"{BASE_URL}/works/10.1000/xyz123/agency").mock(
        return_value=httpx.Response(200, json=agency_envelope)
    )
    out = await tools["get_work_quality"](doi="10.1000/xyz123")
    assert out["agency_id"] == "crossref"
    assert out["agency_label"] == "Crossref"


@respx.mock
async def test_get_work_404_returns_structured_error(tools):
    respx.get(f"{BASE_URL}/works/10.1000/missing").mock(
        return_value=httpx.Response(404, text="not found")
    )
    out = await tools["get_work"](doi="10.1000/missing")
    assert "error" in out
    assert out["error"]["type"] == "NotFoundError"
    assert out["error"]["status"] == 404
