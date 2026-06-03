"""MCP tools for the Crossref /journals endpoints."""

from __future__ import annotations

from collections.abc import Callable

from crossref_mcp.client import CrossrefClient
from crossref_mcp.errors import CrossrefError
from crossref_mcp.models import list_response, simplify_journal, simplify_work
from crossref_mcp.normalize import normalize_issn
from crossref_mcp.query import build_search_params


def register(mcp, get_client: Callable[[], CrossrefClient]) -> None:
    @mcp.tool()
    async def search_journals(
        query: str | None = None,
        rows: int = 20,
        offset: int = 0,
        cursor: str | None = None,
        raw: bool = False,
    ) -> dict:
        """Search journals by title/keyword. Returns title, ISSNs, publisher."""
        params = build_search_params(query=query, rows=rows, offset=offset, cursor=cursor)
        try:
            data = await get_client().get_resource_list("journals", params)
        except CrossrefError as exc:
            return {"error": exc.to_dict()}
        return data if raw else list_response(data.get("message", {}), simplify_journal)

    @mcp.tool()
    async def get_journal(issn: str, raw: bool = False) -> dict:
        """Fetch one journal by ISSN (NNNN-NNNN; hyphen optional)."""
        try:
            normalized = normalize_issn(issn)
        except ValueError as exc:
            return {"error": {"type": "BadRequestError", "message": str(exc)}}
        try:
            message = await get_client().get_resource("journals", normalized)
        except CrossrefError as exc:
            return {"error": exc.to_dict()}
        return message if raw else simplify_journal(message)

    @mcp.tool()
    async def get_journal_works(
        issn: str,
        query: str | None = None,
        filter: str | None = None,
        sort: str | None = None,
        order: str | None = None,
        rows: int = 20,
        offset: int = 0,
        cursor: str | None = None,
        raw: bool = False,
    ) -> dict:
        """List works published in a given journal (by ISSN)."""
        try:
            normalized = normalize_issn(issn)
        except ValueError as exc:
            return {"error": {"type": "BadRequestError", "message": str(exc)}}
        params = build_search_params(
            query=query,
            filter=filter,
            sort=sort,
            order=order,
            rows=rows,
            offset=offset,
            cursor=cursor,
        )
        try:
            data = await get_client().get_resource_works("journals", normalized, params)
        except CrossrefError as exc:
            return {"error": exc.to_dict()}
        return data if raw else list_response(data.get("message", {}), simplify_work)
