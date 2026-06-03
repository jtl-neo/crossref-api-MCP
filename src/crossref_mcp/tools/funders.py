"""MCP tools for the Crossref /funders endpoints."""

from __future__ import annotations

from collections.abc import Callable

from crossref_mcp.client import CrossrefClient
from crossref_mcp.errors import CrossrefError
from crossref_mcp.models import list_response, simplify_funder, simplify_work
from crossref_mcp.normalize import normalize_id
from crossref_mcp.query import build_search_params


def register(mcp, get_client: Callable[[], CrossrefClient]) -> None:
    @mcp.tool()
    async def search_funders(
        query: str | None = None,
        rows: int = 20,
        offset: int = 0,
        cursor: str | None = None,
        raw: bool = False,
    ) -> dict:
        """Search funding bodies by name. Returns funder id, name, location."""
        params = build_search_params(query=query, rows=rows, offset=offset, cursor=cursor)
        try:
            data = await get_client().get_resource_list("funders", params)
        except CrossrefError as exc:
            return {"error": exc.to_dict()}
        return data if raw else list_response(data.get("message", {}), simplify_funder)

    @mcp.tool()
    async def get_funder(funder_id: str, raw: bool = False) -> dict:
        """Fetch one funder by its Crossref Funder Registry id (e.g. 100000001)."""
        try:
            message = await get_client().get_resource("funders", normalize_id(funder_id))
        except CrossrefError as exc:
            return {"error": exc.to_dict()}
        return message if raw else simplify_funder(message)

    @mcp.tool()
    async def get_funder_works(
        funder_id: str,
        query: str | None = None,
        filter: str | None = None,
        sort: str | None = None,
        order: str | None = None,
        rows: int = 20,
        offset: int = 0,
        cursor: str | None = None,
        raw: bool = False,
    ) -> dict:
        """List works funded by a given funder id."""
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
            data = await get_client().get_resource_works("funders", normalize_id(funder_id), params)
        except CrossrefError as exc:
            return {"error": exc.to_dict()}
        return data if raw else list_response(data.get("message", {}), simplify_work)
