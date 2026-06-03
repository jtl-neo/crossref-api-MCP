"""DOI / ISSN / identifier normalization. Single home, reused by all tools."""

from __future__ import annotations

import re
from urllib.parse import quote

_DOI_PREFIXES = ("https://doi.org/", "http://doi.org/", "doi:")
_ISSN_RE = re.compile(r"^\d{4}-?\d{3}[\dxX]$")


def normalize_doi(doi: str) -> str:
    """Strip URL/scheme prefixes and percent-encode a DOI for use in a path.

    DOIs are case-insensitive; Crossref lowercases them. The path segment is
    encoded but '/' is preserved (DOIs always contain a '/').
    """
    if not doi or not doi.strip():
        raise ValueError("DOI must not be empty")
    d = doi.strip()
    low = d.lower()
    for prefix in _DOI_PREFIXES:
        if low.startswith(prefix):
            d = d[len(prefix) :]
            break
    d = d.lower()
    return quote(d, safe="/")


def normalize_issn(issn: str) -> str:
    """Validate and normalize an ISSN to NNNN-NNNN (uppercase X check digit)."""
    if not issn or not issn.strip():
        raise ValueError("ISSN must not be empty")
    s = issn.strip().upper().replace(" ", "")
    if not _ISSN_RE.match(s):
        raise ValueError(f"Invalid ISSN format: {issn!r} (expected NNNN-NNNN)")
    digits = s.replace("-", "")
    return f"{digits[:4]}-{digits[4:]}"


def normalize_id(value: str | int) -> str:
    """Normalize a member / funder / type / prefix id into a safe path segment."""
    s = str(value).strip()
    if not s:
        raise ValueError("id must not be empty")
    return quote(s, safe="")
