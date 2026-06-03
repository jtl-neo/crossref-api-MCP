"""MCP tools for the Crossref /works endpoints."""

from __future__ import annotations

from collections.abc import Callable

from crossref_mcp.client import CrossrefClient
from crossref_mcp.errors import CrossrefError
from crossref_mcp.models import list_response, simplify_work
from crossref_mcp.query import build_search_params

# Hard cap on references returned by get_work_references (PLAN decision 8).
REFERENCES_CAP = 50


def register(mcp, get_client: Callable[[], CrossrefClient]) -> None:
    @mcp.tool()
    async def search_works(
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
        raw: bool = False,
    ) -> dict:
        """Search Crossref works (articles, books, datasets, ...).

        Use `query` for free-text, or the field-scoped variants
        (query_bibliographic / query_author / query_title). `filter` accepts
        Crossref's `key:value,key2:value2` syntax (e.g. "from-pub-date:2020,type:journal-article").
        `rows` is capped at 1000; `select` (e.g. "DOI,title") trims the payload.
        For deep paging set `cursor="*"`, then pass the returned `next_cursor` back.
        Returns simplified items unless `raw=True`.
        """
        params = build_search_params(
            query=query,
            query_bibliographic=query_bibliographic,
            query_author=query_author,
            query_title=query_title,
            filter=filter,
            sort=sort,
            order=order,
            rows=rows,
            offset=offset,
            select=select,
            cursor=cursor,
        )
        try:
            data = await get_client().search_works(params)
        except CrossrefError as exc:
            return {"error": exc.to_dict()}
        if raw:
            return data
        return list_response(data.get("message", {}), simplify_work)

    @mcp.tool()
    async def get_work(doi: str, raw: bool = False) -> dict:
        """Fetch a single work's metadata by DOI.

        Accepts a bare DOI or a doi.org URL. Returns simplified fields unless
        `raw=True`. Returns a structured error if the DOI does not exist.
        """
        try:
            message = await get_client().get_work(doi)
        except CrossrefError as exc:
            return {"error": exc.to_dict()}
        return message if raw else simplify_work(message)

    @mcp.tool()
    async def get_work_references(doi: str, limit: int = REFERENCES_CAP, raw: bool = False) -> dict:
        """List the reference list of a work (the works it cites), by DOI.

        `limit` is hard-capped at 50. Reads the `reference` field of the work.
        """
        capped = REFERENCES_CAP if limit <= 0 else min(limit, REFERENCES_CAP)
        try:
            message = await get_client().get_work(doi)
        except CrossrefError as exc:
            return {"error": exc.to_dict()}
        references = message.get("reference", []) or []
        sliced = references[:capped]
        return {
            "doi": message.get("DOI"),
            "reference_count": message.get("reference-count"),
            "returned": len(sliced),
            "references": sliced,
        }

    @mcp.tool()
    async def get_work_quality(doi: str, raw: bool = False) -> dict:
        """Look up the registration agency for a DOI (Crossref, DataCite, ...)."""
        try:
            message = await get_client().get_work_agency(doi)
        except CrossrefError as exc:
            return {"error": exc.to_dict()}
        if raw:
            return message
        agency = message.get("agency", {}) or {}
        return {
            "doi": message.get("DOI"),
            "agency_id": agency.get("id"),
            "agency_label": agency.get("label"),
        }
