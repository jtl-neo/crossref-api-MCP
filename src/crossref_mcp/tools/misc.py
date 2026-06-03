"""MCP tools for Crossref /types, /licenses, /prefixes endpoints."""

from __future__ import annotations

from collections.abc import Callable

from crossref_mcp.client import CrossrefClient
from crossref_mcp.errors import CrossrefError
from crossref_mcp.models import list_response, simplify_prefix, simplify_type
from crossref_mcp.normalize import normalize_id
from crossref_mcp.query import build_search_params
from crossref_mcp.tools import READ_ONLY


def _simplify_license(m: dict) -> dict:
    return {"url": m.get("URL"), "work_count": m.get("work-count")}


def register(mcp, get_client: Callable[[], CrossrefClient]) -> None:
    @mcp.tool(annotations=READ_ONLY)
    async def list_types(rows: int = 100, offset: int = 0, raw: bool = False) -> dict:
        """List Crossref work types (journal-article, book-chapter, ...)."""
        params = build_search_params(rows=rows, offset=offset)
        try:
            data = await get_client().get_resource_list("types", params)
        except CrossrefError as exc:
            return {"error": exc.to_dict()}
        return data if raw else list_response(data.get("message", {}), simplify_type)

    @mcp.tool(annotations=READ_ONLY)
    async def get_type(type_id: str, raw: bool = False) -> dict:
        """Fetch one work type by id (e.g. "journal-article")."""
        try:
            message = await get_client().get_resource("types", normalize_id(type_id))
        except CrossrefError as exc:
            return {"error": exc.to_dict()}
        return message if raw else simplify_type(message)

    @mcp.tool(annotations=READ_ONLY)
    async def list_licenses(
        query: str | None = None,
        rows: int = 20,
        offset: int = 0,
        raw: bool = False,
    ) -> dict:
        """List licenses Crossref has seen. No single-license lookup exists."""
        params = build_search_params(query=query, rows=rows, offset=offset)
        try:
            data = await get_client().get_resource_list("licenses", params)
        except CrossrefError as exc:
            return {"error": exc.to_dict()}
        return data if raw else list_response(data.get("message", {}), _simplify_license)

    @mcp.tool(annotations=READ_ONLY)
    async def get_prefix(owner_prefix: str, raw: bool = False) -> dict:
        """Look up the owner of a DOI prefix (e.g. "10.1038").

        Crossref only exposes /prefixes/{owner_prefix}; there is no list endpoint.
        """
        try:
            message = await get_client().get_resource("prefixes", normalize_id(owner_prefix))
        except CrossrefError as exc:
            return {"error": exc.to_dict()}
        return message if raw else simplify_prefix(message)
