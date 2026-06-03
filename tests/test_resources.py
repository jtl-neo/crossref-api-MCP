"""Tool-level tests for members/journals/funders/misc via FakeMCP + respx."""

from __future__ import annotations

import httpx
import pytest
import respx

from crossref_mcp.client import CrossrefClient
from crossref_mcp.tools import funders, journals, members, misc, works

from .conftest import BASE_URL, FakeMCP


def _tools(module, client):
    fake = FakeMCP()
    module.register(fake, lambda: client)
    return fake.tools


@pytest.fixture
def member_tools(client: CrossrefClient):
    return _tools(members, client)


@pytest.fixture
def journal_tools(client: CrossrefClient):
    return _tools(journals, client)


@pytest.fixture
def funder_tools(client: CrossrefClient):
    return _tools(funders, client)


@pytest.fixture
def misc_tools(client: CrossrefClient):
    return _tools(misc, client)


@respx.mock
async def test_search_members_simplified(member_tools):
    env = {
        "message": {
            "total-results": 1,
            "items": [
                {"id": "311", "primary-name": "Wiley", "location": "US"},
            ],
        }
    }
    respx.get(f"{BASE_URL}/members").mock(return_value=httpx.Response(200, json=env))
    out = await member_tools["search_members"](query="wiley")
    assert out["total_results"] == 1
    assert out["items"][0] == {
        "id": "311",
        "primary_name": "Wiley",
        "location": "US",
        "total_dois": None,
    }


@respx.mock
async def test_get_member_works_uses_id_path(member_tools):
    route = respx.get(f"{BASE_URL}/members/311/works").mock(
        return_value=httpx.Response(200, json={"message": {"items": []}})
    )
    await member_tools["get_member_works"](member_id=311)
    assert route.called


@respx.mock
async def test_get_journal_normalizes_issn(journal_tools):
    route = respx.get(f"{BASE_URL}/journals/2049-3630").mock(
        return_value=httpx.Response(
            200, json={"message": {"title": "J", "ISSN": ["2049-3630"], "publisher": "P"}}
        )
    )
    # pass without hyphen — should hit the normalized path
    out = await journal_tools["get_journal"](issn="20493630")
    assert route.called
    assert out["issn"] == ["2049-3630"]


async def test_get_journal_bad_issn_returns_error(journal_tools):
    out = await journal_tools["get_journal"](issn="nope")
    assert out["error"]["type"] == "BadRequestError"


@respx.mock
async def test_search_funders_simplified(funder_tools):
    env = {
        "message": {
            "total-results": 1,
            "items": [
                {"id": "100000001", "name": "NSF", "location": "US", "uri": "http://x"},
            ],
        }
    }
    respx.get(f"{BASE_URL}/funders").mock(return_value=httpx.Response(200, json=env))
    out = await funder_tools["search_funders"](query="nsf")
    assert out["items"][0]["name"] == "NSF"


@respx.mock
async def test_list_types_and_get_prefix(misc_tools):
    respx.get(f"{BASE_URL}/types").mock(
        return_value=httpx.Response(
            200,
            json={"message": {"items": [{"id": "journal-article", "label": "Journal Article"}]}},
        )
    )
    types = await misc_tools["list_types"]()
    assert types["items"][0] == {"id": "journal-article", "label": "Journal Article"}

    respx.get(f"{BASE_URL}/prefixes/10.1038").mock(
        return_value=httpx.Response(
            200,
            json={
                "message": {
                    "prefix": "http://id.crossref.org/prefix/10.1038",
                    "name": "Springer Nature",
                    "member": "297",
                }
            },
        )
    )
    pref = await misc_tools["get_prefix"](owner_prefix="10.1038")
    assert pref["name"] == "Springer Nature"


@respx.mock
async def test_search_works_returns_next_cursor(client: CrossrefClient):
    tools = _tools(works, client)
    env = {"message": {"total-results": 100, "next-cursor": "CURSOR2", "items": []}}
    respx.get(f"{BASE_URL}/works").mock(return_value=httpx.Response(200, json=env))
    out = await tools["search_works"](query="x", cursor="*")
    assert out["next_cursor"] == "CURSOR2"
