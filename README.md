<!-- mcp-name: io.github.heyinnaneo/crossref-mcp -->

# crossref-mcp

An [MCP](https://modelcontextprotocol.io) server wrapping the
[Crossref REST API](https://api.crossref.org), exposing scholarly-metadata
lookups (works, members, journals, funders, types, licenses, prefixes) as tools
that an LLM client can call.

> Not affiliated with or endorsed by Crossref. Data is served live from the
> public Crossref API. Please set `CROSSREF_MAILTO` to join Crossref's
> [polite pool](https://api.crossref.org/swagger-ui/index.html).

## Status

Under construction — see [Roadmap.md](./Roadmap.md). Currently implemented:
**M1** (skeleton) and **M2** (core `works` tools).

## Quick start (local, stdio)

```bash
uv sync
export CROSSREF_MAILTO="you@example.com"   # recommended (polite pool)
uv run crossref-mcp                         # starts a stdio MCP server
```

Or inspect it with the MCP Inspector:

```bash
uv run mcp dev src/crossref_mcp/server.py
```

## Configuration

| Env var | Required | Default | Description |
|---------|----------|---------|-------------|
| `CROSSREF_MAILTO` | recommended | — | Email for Crossref's polite pool. |
| `CROSSREF_PLUS_TOKEN` | no | — | Crossref Plus API token (sent as a header). |
| `CROSSREF_BASE_URL` | no | `https://api.crossref.org` | API base URL. |
| `CROSSREF_TIMEOUT` | no | `30` | Per-request timeout (seconds). |
| `MCP_TRANSPORT` | no | `stdio` | `stdio` or `http`. |
| `LOG_LEVEL` | no | `INFO` | Log level (logs go to stderr). |

## Tools (current)

- `ping` — server name + version.
- `search_works` — search works (query / filter / sort / rows / offset / select).
- `get_work` — single work metadata by DOI.
- `get_work_references` — a work's reference list (capped at 50).
- `get_work_quality` — DOI registration agency.

All query tools return simplified fields by default; pass `raw=true` for the full
Crossref JSON.

## License

[MIT](./LICENSE).
