"""FastMCP server: instance, tool registration, transport startup."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

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


# Register resource tools.
works.register(mcp, get_client)
members.register(mcp, get_client)
journals.register(mcp, get_client)
funders.register(mcp, get_client)
misc.register(mcp, get_client)


def main() -> None:
    settings = get_settings()
    transport = settings.mcp_transport.lower()
    log.info("starting crossref-mcp %s (transport=%s)", __version__, transport)
    if transport == "http":
        # Full HTTP transport + /health land in M4/M5; stdio is the M1/M2 path.
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
