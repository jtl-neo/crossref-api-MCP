# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Core MCP server (FastMCP) with stdio and Streamable HTTP transports.
- `works` tools: `search_works`, `get_work`, `get_work_references` (capped at 50),
  `get_work_quality`.
- Resource tools: members, journals (by ISSN), funders, types, licenses, prefixes.
- Polite-pool client (User-Agent + `mailto`), optional Crossref Plus token.
- In-memory token-bucket rate limiting that re-tunes from `X-Rate-Limit-*`
  headers; exponential backoff honoring `Retry-After` on 429.
- Unified structured errors; cursor deep paging (`next_cursor`); `select` and
  `raw` output control.
- Optional `X-API-Key` HTTP auth (timing-safe; `/health` exempt) and a `/health`
  endpoint.
- Read-only tool annotations and server instructions for MCP clients.
- Containerization: multi-stage Dockerfile (non-root), docker-compose with
  health check, `.env.example`.
- Optional reverse-proxy/TLS deployment (Caddy) and optional Redis response
  cache + cross-replica token-bucket rate limiting (`REDIS_URL`,
  `RATELIMIT_BACKEND=redis`), both degrading gracefully and disabled by default.
- CI: lint + format + test (with coverage); multi-arch build/push to Docker Hub
  on `main` / version tags, gated by a version-consistency check.

[Unreleased]: https://github.com/jtl-neo/crossref-api-MCP/commits/main
