"""Tests for DOI / ISSN / id normalization."""

from __future__ import annotations

import pytest

from crossref_mcp.normalize import normalize_doi, normalize_id, normalize_issn


def test_normalize_doi_strips_prefix_and_lowercases():
    assert normalize_doi("https://doi.org/10.1000/XyZ") == "10.1000/xyz"
    assert normalize_doi("doi:10.1000/ABC") == "10.1000/abc"
    assert normalize_doi("10.1000/Foo") == "10.1000/foo"


def test_normalize_doi_keeps_slash_encodes_specials():
    out = normalize_doi("10.1000/a b")
    assert "/" in out  # slash preserved
    assert " " not in out  # space encoded


def test_normalize_doi_empty_raises():
    with pytest.raises(ValueError):
        normalize_doi("  ")


def test_normalize_issn_valid():
    assert normalize_issn("20493630") == "2049-3630"
    assert normalize_issn("2049-3630") == "2049-3630"
    assert normalize_issn("2049-363x") == "2049-363X"


def test_normalize_issn_invalid():
    with pytest.raises(ValueError):
        normalize_issn("not-an-issn")


def test_normalize_id_encodes():
    assert normalize_id(311) == "311"
    assert normalize_id("10.13039/abc") == "10.13039%2Fabc"
