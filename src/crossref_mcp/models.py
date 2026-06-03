"""Response simplifiers. All None-safe against sparse real-world Crossref data."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def _first(value: Any) -> Any:
    """Return the first element of a list, else the value itself, else None."""
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _author_name(author: dict) -> str:
    given = (author.get("given") or "").strip()
    family = (author.get("family") or "").strip()
    if given and family:
        return f"{given} {family}"
    return family or given or (author.get("name") or "").strip() or "Unknown"


def _issued(message: dict) -> str | None:
    """Build an ISO-ish date string from issued.date-parts."""
    issued = message.get("issued") or {}
    parts = issued.get("date-parts") or []
    first = parts[0] if parts else None
    if not first:
        return None
    return "-".join(f"{p:02d}" if i else str(p) for i, p in enumerate(first))


def simplify_work(message: dict) -> dict:
    """Reduce a Crossref work to the key fields."""
    if not isinstance(message, dict):
        return {}
    authors = [_author_name(a) for a in (message.get("author") or []) if isinstance(a, dict)]
    return {
        "title": _first(message.get("title")),
        "doi": message.get("DOI"),
        "authors": authors,
        "issued": _issued(message),
        "container_title": _first(message.get("container-title")),
        "url": message.get("URL"),
        "type": message.get("type"),
    }


def simplify_work_list(items: list[dict]) -> list[dict]:
    return [simplify_work(item) for item in (items or []) if isinstance(item, dict)]


# --- resource (member / journal / funder / type / prefix) simplifiers ----


def simplify_member(m: dict) -> dict:
    return {
        "id": m.get("id"),
        "primary_name": m.get("primary-name"),
        "location": m.get("location"),
        "total_dois": (m.get("counts") or {}).get("total-dois"),
    }


def simplify_journal(m: dict) -> dict:
    return {
        "title": m.get("title"),
        "issn": m.get("ISSN") or [],
        "publisher": m.get("publisher"),
    }


def simplify_funder(m: dict) -> dict:
    return {
        "id": m.get("id"),
        "name": m.get("name"),
        "location": m.get("location"),
        "uri": m.get("uri"),
    }


def simplify_type(m: dict) -> dict:
    return {"id": m.get("id"), "label": m.get("label")}


def simplify_prefix(m: dict) -> dict:
    return {"prefix": m.get("prefix"), "name": m.get("name"), "member": m.get("member")}


def list_response(message: dict, simplifier: Callable[[dict], dict]) -> dict:
    """Wrap a Crossref list 'message' into a compact paged response.

    Carries `next_cursor` (from `next-cursor`) so deep paging can continue by
    passing it back as the `cursor` argument.
    """
    items = message.get("items", []) or []
    return {
        "total_results": message.get("total-results"),
        "next_cursor": message.get("next-cursor"),
        "items_count": len(items),
        "items": [simplifier(i) for i in items if isinstance(i, dict)],
    }
