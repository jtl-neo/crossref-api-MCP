"""FastMCP server: instance, tool registration, transport startup."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from starlette.requests import Request
from starlette.responses import JSONResponse

from crossref_mcp import __version__
from crossref_mcp.client import CrossrefClient
from crossref_mcp.config import get_settings
from crossref_mcp.log import get_logger
from crossref_mcp.tools import funders, journals, members, misc, works

log = get_logger("server")

INSTRUCTIONS = (
    "Query scholarly metadata from the Crossref REST API: works (articles, books, "
    "datasets), members (publishers), journals, funders, types, licenses, and DOI "
    "prefixes. All tools are read-only. Use search_* / get_*_works to find works and "
    "get_work for a DOI. Tools return simplified fields by default; pass raw=true for "
    "the full Crossref JSON. For large result sets, page with cursor='*' then reuse the "
    "returned next_cursor. Set CROSSREF_MAILTO to join Crossref's polite pool."
)

mcp = FastMCP("crossref-mcp", instructions=INSTRUCTIONS)

# Module-level singletons, created lazily and shared across tool calls.
_client: CrossrefClient | None = None
_redis = None  # kept for /health ping; None unless REDIS_URL is set


def get_client() -> CrossrefClient:
    global _client, _redis
    if _client is not None:
        return _client

    settings = get_settings()
    cache = None
    limiter = None
    if settings.redis_url:
        from crossref_mcp.cache import ResponseCache, create_redis

        _redis = create_redis(settings.redis_url)
        cache = ResponseCache(_redis, settings.cache_namespace, settings.cache_ttl)
        if settings.ratelimit_backend.lower() == "redis":
            from crossref_mcp.ratelimit import RedisTokenBucket

            limiter = RedisTokenBucket(_redis)
        log.info("Redis enabled: cache on, ratelimit=%s", settings.ratelimit_backend.lower())

    _client = CrossrefClient(settings=settings, cache=cache, limiter=limiter)
    return _client


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def ping() -> str:
    """Health check tool: returns the server name and version."""
    return f"pong from crossref-mcp {__version__}"


@mcp.custom_route("/health", methods=["GET"])
async def health(_request: Request) -> JSONResponse:
    """Liveness probe. Always 200 (even if Redis is down), never needs the API key."""
    settings = get_settings()
    body: dict = {
        "status": "ok",
        "version": __version__,
        "cache_enabled": bool(settings.redis_url),
        "ratelimit_backend": settings.ratelimit_backend.lower()
        if settings.redis_url
        else "in-memory",
    }
    if _redis is not None:
        try:
            body["redis"] = "up" if await _redis.ping() else "down"
        except Exception:  # noqa: BLE001 - degraded but still alive
            body["redis"] = "down"
    return JSONResponse(body)


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
