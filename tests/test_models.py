"""Tests for response simplifiers — must be None-safe on sparse data."""

from __future__ import annotations

from crossref_mcp.models import simplify_work, simplify_work_list


def test_simplify_full_work(work_message):
    out = simplify_work(work_message)
    assert out["title"] == "A Study of Things"
    assert out["doi"] == "10.1000/xyz123"
    assert out["authors"] == ["Ada Lovelace", "Alan Turing"]
    assert out["issued"] == "2021-05-17"


def test_simplify_sparse_work_is_safe():
    out = simplify_work({"DOI": "10.1/x"})
    assert out["title"] is None
    assert out["authors"] == []
    assert out["issued"] is None
    assert out["container_title"] is None


def test_simplify_partial_author_and_year_only():
    msg = {
        "DOI": "10.1/y",
        "author": [{"family": "Solo"}, {"name": "Org Name"}],
        "issued": {"date-parts": [[1999]]},
    }
    out = simplify_work(msg)
    assert out["authors"] == ["Solo", "Org Name"]
    assert out["issued"] == "1999"


def test_simplify_work_list_filters_non_dicts():
    assert simplify_work_list([{"DOI": "10.1/a"}, None, "x"]) == [
        {
            "title": None,
            "doi": "10.1/a",
            "authors": [],
            "issued": None,
            "container_title": None,
            "url": None,
            "type": None,
        }
    ]
