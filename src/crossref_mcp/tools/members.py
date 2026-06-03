"""MCP tools for the Crossref /members endpoints."""

from __future__ import annotations

from collections.abc import Callable

from crossref_mcp.client import CrossrefClient
from crossref_mcp.errors import CrossrefError
from crossref_mcp.models import list_response, simplify_member, simplify_work
from crossref_mcp.normalize import normalize_id
from crossref_mcp.query import build_search_params
from crossref_mcp.tools import READ_ONLY


def register(mcp, get_client: Callable[[], CrossrefClient]) -> None:
    @mcp.tool(annotations=READ_ONLY)
    async def search_members(
        query: str | None = None,
        filter: str | None = None,
        rows: int = 20,
        offset: int = 0,
        cursor: str | None = None,
        raw: bool = False,
    ) -> dict:
        """Search Crossref members (publishers/societies). Returns id + primary name."""
        params = build_search_params(
            query=query, filter=filter, rows=rows, offset=offset, cursor=cursor
        )
        try:
            data = await get_client().get_resource_list("members", params)
        except CrossrefError as exc:
            return {"error": exc.to_dict()}
        return data if raw else list_response(data.get("message", {}), simplify_member)

    @mcp.tool(annotations=READ_ONLY)
    async def get_member(member_id: int | str, raw: bool = False) -> dict:
        """Fetch one member (publisher) by numeric Crossref member id."""
        try:
            message = await get_client().get_resource("members", normalize_id(member_id))
        except CrossrefError as exc:
            return {"error": exc.to_dict()}
        return message if raw else simplify_member(message)

    @mcp.tool(annotations=READ_ONLY)
    async def get_member_works(
        member_id: int | str,
        query: str | None = None,
        filter: str | None = None,
        sort: str | None = None,
        order: str | None = None,
        rows: int = 20,
        offset: int = 0,
        cursor: str | None = None,
        raw: bool = False,
    ) -> dict:
        """List works published by a given member id."""
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
            data = await get_client().get_resource_works("members", normalize_id(member_id), params)
        except CrossrefError as exc:
            return {"error": exc.to_dict()}
        return data if raw else list_response(data.get("message", {}), simplify_work)
