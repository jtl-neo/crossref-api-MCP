"""MCP tool modules grouped by Crossref resource."""

from mcp.types import ToolAnnotations

# Every tool is a read-only lookup against the external Crossref API.
READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True)

__all__ = ["READ_ONLY"]
