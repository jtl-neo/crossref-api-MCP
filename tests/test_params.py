"""Tests for the shared search-param builder."""

from __future__ import annotations

from crossref_mcp.query import build_search_params


def test_dotted_and_basic_fields():
    p = build_search_params(query="x", query_bibliographic="b", query_author="a")
    assert p["query"] == "x"
    assert p["query.bibliographic"] == "b"
    assert p["query.author"] == "a"


def test_none_fields_omitted():
    p = build_search_params(query="x")
    assert "sort" not in p
    assert "filter" not in p
    assert "select" not in p


def test_rows_capped_at_1000():
    assert build_search_params(rows=5000)["rows"] == 1000
    assert build_search_params(rows=10)["rows"] == 10


def test_cursor_and_offset_mutually_exclusive():
    with_cursor = build_search_params(cursor="*", offset=50)
    assert with_cursor["cursor"] == "*"
    assert "offset" not in with_cursor

    with_offset = build_search_params(offset=50)
    assert with_offset["offset"] == 50
    assert "cursor" not in with_offset
