"""Environment-driven configuration for the Crossref MCP server."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from crossref_mcp import __version__


class Settings(BaseSettings):
    """Server settings, populated from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    # Polite pool: mailto is always sent. Strongly recommended by Crossref.
    crossref_mailto: str = Field(default="", validation_alias="CROSSREF_MAILTO")
    # Optional Crossref Plus token (sent alongside, never replaces, the UA / mailto).
    crossref_plus_token: str | None = Field(default=None, validation_alias="CROSSREF_PLUS_TOKEN")
    crossref_base_url: str = Field(
        default="https://api.crossref.org", validation_alias="CROSSREF_BASE_URL"
    )
    crossref_timeout: float = Field(default=30.0, validation_alias="CROSSREF_TIMEOUT")

    # Transport: "stdio" or "http". Defaults to stdio for local dev (M5 flips to http).
    mcp_transport: str = Field(default="stdio", validation_alias="MCP_TRANSPORT")

    # Optional HTTP auth. When set, HTTP requests must carry a matching X-API-Key
    # header (timing-safe compare); /health is always exempt. Unset = no auth.
    mcp_api_key: str | None = Field(default=None, validation_alias="MCP_API_KEY")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


def get_version() -> str:
    """Single source of truth for the package version (pyproject.toml)."""
    return __version__
