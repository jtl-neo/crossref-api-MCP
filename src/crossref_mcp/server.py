"""FastMCP server: instance, tool registration, transport startup."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from crossref_mcp import __version__
from crossref_mcp.client import CrossrefClient
from crossref_mcp.config import get_settings
from crossref_mcp.log import get_logger
from crossref_mcp.tools import funders, journals, members, misc, works

log = get_logger("server")

mcp = FastMCP("crossref-mcp")

# Module-level client singleton, created lazily and shared across tool calls.
_client: CrossrefClient | None = None


def get_client() -> CrossrefClient:
    global _client
    if _client is None:
        _client = CrossrefClient()
    return _client


@mcp.tool()
def ping() -> str:
    """Health check tool: returns the server name and version."""
    return f"pong from crossref-mcp {__version__}"


@mcp.custom_route("/health", methods=["GET"])
async def health(_request: Request) -> JSONResponse:
    """Liveness probe. Always 200, never requires the API key."""
    return JSONResponse({"status": "ok", "version": __version__})


# Register resource tools.
works.register(mcp, get_client)
members.register(mcp, get_client)
journals.register(mcp, get_client)
funders.register(mcp, get_client)
misc.register(mcp, get_client)


def _run_http(settings) -> None:
    """Run the Streamable HTTP transport, binding 0.0.0.0 and applying optional auth."""
    import uvicorn

    mcp.settings.host = "0.0.0.0"  # noqa: S104 - container needs external binding
    mcp.settings.port = 8000
    app = mcp.streamable_http_app()
    if settings.mcp_api_key:
        from crossref_mcp.http_auth import ApiKeyMiddleware

        app.add_middleware(ApiKeyMiddleware, api_key=settings.mcp_api_key)
        log.info("X-API-Key auth enabled (/health exempt)")
    uvicorn.run(app, host=mcp.settings.host, port=mcp.settings.port, log_level="info")


def main() -> None:
    settings = get_settings()
    transport = settings.mcp_transport.lower()
    log.info("starting crossref-mcp %s (transport=%s)", __version__, transport)
    if not settings.crossref_mailto:
        log.warning("CROSSREF_MAILTO unset — set it to join Crossref's polite pool.")
    if transport == "http":
        _run_http(settings)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
