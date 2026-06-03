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

## Public deployment (TLS / reverse proxy) — optional

To expose the server publicly over HTTPS, put it behind the bundled Caddy proxy
(`Caddyfile` + `docker-compose.proxy.yml`). Caddy terminates TLS (auto Let's
Encrypt), redirects HTTP→HTTPS, streams SSE correctly (`flush_interval -1`), and
the backend is no longer published on the host — only Caddy's 80/443.

```bash
cp .env.example .env
# add to .env:  DOMAIN=mcp.example.com   ACME_EMAIL=you@example.com
#               MCP_API_KEY=...           (strongly recommended when public)
docker compose -f docker-compose.proxy.yml up -d
curl https://mcp.example.com/health
```

Defense in depth: the proxy is the edge (optional IP allowlist / Basic auth in
`Caddyfile`), `MCP_API_KEY` is the app layer (Caddy forwards `X-API-Key`); both
leave `/health` open. Requires a domain with DNS pointing at the host and ports
80/443 reachable. Caddy rate limiting needs the `caddy-ratelimit` plugin (custom
build) — see the commented block in `Caddyfile`. Multi-replica scaling needs the
shared rate-limit backend from M9 (see Roadmap).

## Redis cache + cross-replica rate limiting — optional

By default the server caches nothing and rate-limits in a single process. Set
`REDIS_URL` to enable a response cache (cache-aside on the raw envelope, so
`raw` and simplified reads share one entry; `mailto`/secrets excluded from keys)
and, with `RATELIMIT_BACKEND=redis`, a shared token bucket so multiple replicas
stay within Crossref's polite-pool rate.

```bash
docker compose -f docker-compose.redis.yml up -d
curl http://localhost:8000/health   # shows cache_enabled + ratelimit_backend + redis: up
```

Redis failures degrade gracefully — the server keeps serving (no cache,
in-memory limiting) and `/health` stays 200 with `redis: down`. For multiple
replicas, scale behind the Caddy proxy and keep `RATELIMIT_BACKEND=redis`.

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

## Install from the MCP registry

Published as `io.github.heyinnaneo/crossref-mcp` (see [`server.json`](./server.json)),
with a PyPI package (`uvx crossref-mcp`) and an OCI image. Publishing is automated
on version tags by the `publish-pypi` and `publish-registry` CI jobs; both require
the GitHub repo to be public and a PyPI Trusted Publisher to be configured. The
`mcp-name` marker in this README and the `io.modelcontextprotocol.server.name`
image label are the registry ownership proofs.

## Security & trust

- **Read-only.** Every tool is a Crossref lookup and is annotated `readOnlyHint`;
  the server cannot modify anything.
- **Rate limiting.** Defaults to a single-process in-memory limiter against the
  upstream Crossref API. Do not run this as a public proxy for heavy traffic; for
  multiple replicas enable the shared Redis limiter (`RATELIMIT_BACKEND=redis`).
- **Polite pool.** Set your own `CROSSREF_MAILTO`; don't reuse someone else's.
- **Public HTTP.** When exposed, set `MCP_API_KEY` and front it with TLS (see
  *Public deployment*).
- **No bundled secrets.** `.env` is excluded from the image and from git.

## License

[MIT](./LICENSE). Bibliographic data comes from the public
[Crossref REST API](https://api.crossref.org); this project is not affiliated
with Crossref.
