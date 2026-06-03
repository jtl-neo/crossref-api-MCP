"""Response simplifiers. All None-safe against sparse real-world Crossref data."""

from __future__ import annotations

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
