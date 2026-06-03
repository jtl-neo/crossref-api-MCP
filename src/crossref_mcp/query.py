"""Shared search-query parameter builder for all resource list endpoints."""

from __future__ import annotations

from typing import Any

# Crossref hard cap on rows per request.
MAX_ROWS = 1000


def build_search_params(
    *,
    query: str | None = None,
    query_bibliographic: str | None = None,
    query_author: str | None = None,
    query_title: str | None = None,
    filter: str | None = None,
    sort: str | None = None,
    order: str | None = None,
    rows: int = 20,
    offset: int = 0,
    select: str | None = None,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Assemble the Crossref query dict, mapping dotted query fields correctly.

    `filter` uses Crossref's `key:value,key2:value2` syntax. `cursor` (set to "*"
    to start) enables deep paging; the response carries `next-cursor` to continue.
    None values are omitted.
    """
    params: dict[str, Any] = {}
    if query:
        params["query"] = query
    if query_bibliographic:
        params["query.bibliographic"] = query_bibliographic
    if query_author:
        params["query.author"] = query_author
    if query_title:
        params["query.title"] = query_title
    if filter:
        params["filter"] = filter
    if sort:
        params["sort"] = sort
    if order:
        params["order"] = order
    if select:
        params["select"] = select
    if cursor:
        # cursor and offset are mutually exclusive; cursor wins.
        params["cursor"] = cursor
    else:
        params["offset"] = max(0, offset)
    params["rows"] = max(0, min(rows, MAX_ROWS))
    return params
