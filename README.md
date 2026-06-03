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

See [Roadmap.md](./Roadmap.md). Implemented: **M1–M6** — all resource endpoints,
rate limiting, retries, HTTP transport, optional auth, containerization, and CI.

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
| `MCP_API_KEY` | no | — | If set, HTTP requests need a matching `X-API-Key` header (`/health` exempt). |
| `LOG_LEVEL` | no | `INFO` | Log level (logs go to stderr). |

## Tools

**Works**
- `search_works` — search works (articles, books, datasets…).
- `get_work` — single work metadata by DOI.
- `get_work_references` — a work's reference list (capped at 50).
- `get_work_quality` — DOI registration agency.

**Members / Journals / Funders**
- `search_members` · `get_member` · `get_member_works`
- `search_journals` · `get_journal` (by ISSN) · `get_journal_works`
- `search_funders` · `get_funder` · `get_funder_works`

**Types / Licenses / Prefixes**
- `list_types` · `get_type`
- `list_licenses`
- `get_prefix` (DOI prefix owner lookup)

Plus `ping` (server name + version).

**Shared parameters.** Search/list tools accept `query` (and `query_bibliographic`
/ `query_author` / `query_title` on works), `filter` (Crossref `key:value,…`
syntax), `sort` + `order`, `rows` (≤1000) + `offset`, and `select`. For deep
paging set `cursor="*"` and pass the returned `next_cursor` back. Every tool
returns simplified fields by default; pass `raw=true` for the full Crossref JSON.

## Connecting an MCP client

**stdio (Claude Desktop / Cursor)** — `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "crossref": {
      "command": "uvx",
      "args": ["crossref-mcp"],
      "env": { "CROSSREF_MAILTO": "you@example.com" }
    }
  }
}
```

Or run the container over stdio: `"command": "docker"`, `"args": ["run", "-i",
"--rm", "-e", "CROSSREF_MAILTO", "heyinnaneo/crossref-mcp"]`.

**Streamable HTTP** — once the container is up (see below), point an HTTP-capable
client at `http://localhost:8000/mcp`. If `MCP_API_KEY` is set, send it as an
`X-API-Key` header.

## Docker / HTTP deployment

```bash
cp .env.example .env          # then set CROSSREF_MAILTO
docker compose up -d          # pulls heyinnaneo/crossref-mcp, serves HTTP on :8000
curl http://localhost:8000/health
```

The container serves the Streamable HTTP transport at `http://localhost:8000/mcp`
and a `/health` liveness endpoint (used by the compose health check). Set
`MCP_API_KEY` in `.env` to require an `X-API-Key` header on `/mcp` (`/health`
stays open). To build from local source instead of pulling, uncomment `build: .`
in `docker-compose.yml`.

## CI / publishing

`.github/workflows/ci.yml` runs two jobs:

1. **test** — `uv sync` → `ruff check` → `ruff format --check` → `pytest` (with
   coverage). Runs on every push and PR.
2. **build-push** — only on pushes to `main` or `v*.*.*` tags (never on PRs).
   Builds a multi-arch (amd64 + arm64) image and pushes to
   `heyinnaneo/crossref-mcp` with `latest`, short-SHA, and version tags.

To enable publishing, add two repository secrets under
**Settings → Secrets and variables → Actions**:

- `DOCKERHUB_USERNAME` — `heyinnaneo`
- `DOCKERHUB_TOKEN` — a Docker Hub **Access Token** (Read/Write), not your password.

Push a tag (`git tag v0.1.0 && git push origin v0.1.0`) to publish a versioned
image; the version must match `pyproject.toml`.

## License

[MIT](./LICENSE). Bibliographic data comes from the public
[Crossref REST API](https://api.crossref.org); this project is not affiliated
with Crossref.
