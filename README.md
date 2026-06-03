<!-- mcp-name: io.github.jtl-neo/crossref-mcp -->

# crossref-mcp

[![CI](https://github.com/jtl-neo/crossref-api-MCP/actions/workflows/ci.yml/badge.svg)](https://github.com/jtl-neo/crossref-api-MCP/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Docker](https://img.shields.io/badge/docker-heyinnaneo%2Fcrossref--mcp-blue?logo=docker)](https://hub.docker.com/r/heyinnaneo/crossref-mcp)

**English** | [中文](#中文)

An [MCP](https://modelcontextprotocol.io) server wrapping the
[Crossref REST API](https://api.crossref.org), exposing scholarly-metadata
lookups (works, members, journals, funders, types, licenses, prefixes) as tools
an LLM client can call.

> Not affiliated with or endorsed by Crossref. Data is served live from the
> public Crossref API. Set `CROSSREF_MAILTO` to join Crossref's
> [polite pool](https://api.crossref.org/swagger-ui/index.html).

## Features

- All major Crossref resource endpoints as **18 read-only tools**.
- Dual transport: **stdio** (local) and **Streamable HTTP** (container).
- Polite pool (User-Agent + `mailto`), optional Crossref Plus token.
- Token-bucket rate limiting (auto-tuned from `X-Rate-Limit-*` headers) with
  exponential backoff honoring `Retry-After`.
- Cursor deep paging, field `select`, `raw` vs simplified output.
- Optional `X-API-Key` HTTP auth (`/health` exempt), `/health` endpoint.
- Optional Redis response cache + cross-replica rate limiting.
- Optional Caddy TLS reverse proxy for public deployment.

## Quick start (local, stdio)

```bash
uv sync
export CROSSREF_MAILTO="you@example.com"   # recommended (polite pool)
uv run crossref-mcp                         # starts a stdio MCP server
```

Inspect with the MCP Inspector: `uv run mcp dev src/crossref_mcp/server.py`.

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
| `REDIS_URL` | no | — | Enable Redis cache + shared rate limiting (optional). |
| `CACHE_TTL` | no | `86400` | Cache TTL in seconds. |
| `RATELIMIT_BACKEND` | no | `in-memory` | `in-memory` or `redis`. |

## Tools

**Works** — `search_works`, `get_work` (by DOI), `get_work_references` (capped
at 50), `get_work_quality` (registration agency).
**Members / Journals / Funders** — `search_members` · `get_member` ·
`get_member_works`; `search_journals` · `get_journal` (ISSN) ·
`get_journal_works`; `search_funders` · `get_funder` · `get_funder_works`.
**Types / Licenses / Prefixes** — `list_types` · `get_type`; `list_licenses`;
`get_prefix`. Plus `ping`.

**Shared parameters.** Search/list tools take `query` (and
`query_bibliographic` / `query_author` / `query_title` on works), `filter`
(Crossref `key:value,…` syntax), `sort` + `order`, `rows` (≤1000) + `offset`,
and `select`. Deep paging: set `cursor="*"` then reuse the returned
`next_cursor`. All tools return simplified fields by default; pass `raw=true`
for the full Crossref JSON.

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

**Streamable HTTP** — once the container is up, point an HTTP-capable client at
`http://localhost:8000/mcp`. If `MCP_API_KEY` is set, send it as `X-API-Key`.

## Docker / HTTP deployment

```bash
cp .env.example .env          # set CROSSREF_MAILTO
docker compose up -d          # pulls heyinnaneo/crossref-mcp, HTTP on :8000
curl http://localhost:8000/health
```

Serves Streamable HTTP at `/mcp` and `/health` (compose health check). Set
`MCP_API_KEY` to require `X-API-Key` on `/mcp`. To build locally, uncomment
`build: .` in `docker-compose.yml`.

## Public deployment (TLS / reverse proxy) — optional

Put it behind the bundled Caddy proxy (`Caddyfile` + `docker-compose.proxy.yml`):
TLS termination (auto Let's Encrypt), HTTP→HTTPS, SSE streaming, backend not
published on the host.

```bash
cp .env.example .env   # add DOMAIN=, ACME_EMAIL=, MCP_API_KEY=
docker compose -f docker-compose.proxy.yml up -d
curl https://your-domain/health
```

Defense in depth: proxy edge (optional IP allowlist / Basic auth) + `MCP_API_KEY`
app layer; both leave `/health` open. Needs a domain with DNS pointing at the
host and ports 80/443 reachable. Caddy rate limiting needs the `caddy-ratelimit`
plugin (custom build).

## Redis cache + cross-replica rate limiting — optional

Set `REDIS_URL` for a response cache (cache-aside on the raw envelope; `mailto`/
secrets excluded from keys) and, with `RATELIMIT_BACKEND=redis`, a shared token
bucket so replicas stay within Crossref's polite-pool rate.

```bash
docker compose -f docker-compose.redis.yml up -d
curl http://localhost:8000/health   # cache_enabled + ratelimit_backend + redis: up
```

Redis failures degrade gracefully (no cache, in-memory limiting); `/health` stays
200 with `redis: down`.

## CI / publishing

`.github/workflows/ci.yml`: **test** (ruff + format + pytest with coverage on
every push/PR), **security** (Trivy fs scan), **build-push** (multi-arch image to
`heyinnaneo/crossref-mcp` on `main` / `v*` tags), and on tags **publish-pypi**
(OIDC Trusted Publisher) + **publish-registry** (MCP registry).

Repository secrets (**Settings → Secrets and variables → Actions**):
`DOCKERHUB_USERNAME` = `heyinnaneo`, `DOCKERHUB_TOKEN` = a Docker Hub Access
Token (Read/Write). Tag a release (`git tag v0.1.0 && git push origin v0.1.0`);
the tag must match `pyproject.toml`.

## Install from the MCP registry

Published as `io.github.jtl-neo/crossref-mcp` (see [`server.json`](./server.json)),
with a PyPI package (`uvx crossref-mcp`) and an OCI image. Publishing is automated
on version tags (`publish-pypi` + `publish-registry`); requires a public repo and
a configured PyPI Trusted Publisher.

## Security & trust

- **Read-only.** Every tool is a lookup, annotated `readOnlyHint`.
- **Rate limiting.** Single-process in-memory by default — don't run as a public
  proxy for heavy traffic; for replicas use `RATELIMIT_BACKEND=redis`.
- **Polite pool.** Use your own `CROSSREF_MAILTO`.
- **Public HTTP.** Set `MCP_API_KEY` and front with TLS.
- **No bundled secrets.** `.env` is excluded from image and git.

## License

[MIT](./LICENSE). Bibliographic data comes from the public
[Crossref REST API](https://api.crossref.org); not affiliated with Crossref.

---

# 中文

[English](#crossref-mcp) | **中文**

把 [Crossref REST API](https://api.crossref.org) 封裝成 [MCP](https://modelcontextprotocol.io)
server，將學術文獻 metadata 查詢（works、members、journals、funders、types、
licenses、prefixes）包成 LLM client 可呼叫的工具。

> 非 Crossref 官方、未經其背書。資料即時取自公開的 Crossref API。請設定
> `CROSSREF_MAILTO` 以加入 Crossref 的
> [polite pool](https://api.crossref.org/swagger-ui/index.html)。

## 特色

- 主要 Crossref 資源端點，共 **18 個唯讀工具**。
- 雙傳輸：**stdio**（本機）與 **Streamable HTTP**（容器）。
- Polite pool（User-Agent + `mailto`）、可選 Crossref Plus token。
- Token-bucket 速率控制（依 `X-Rate-Limit-*` header 自動調整），429 指數退避並
  尊重 `Retry-After`。
- cursor 深分頁、欄位 `select`、`raw` 與精簡輸出切換。
- 可選 `X-API-Key` HTTP 認證（`/health` 豁免）、`/health` 端點。
- 可選 Redis 回應快取 + 跨副本速率控制。
- 可選 Caddy TLS 反向代理，供公開部署。

## 快速開始（本機 stdio）

```bash
uv sync
export CROSSREF_MAILTO="you@example.com"   # 建議（polite pool）
uv run crossref-mcp                         # 啟動 stdio MCP server
```

用 MCP Inspector 檢視：`uv run mcp dev src/crossref_mcp/server.py`。

## 設定

| 環境變數 | 必填 | 預設 | 說明 |
|---------|------|------|------|
| `CROSSREF_MAILTO` | 建議 | — | Crossref polite pool 用的 email。 |
| `CROSSREF_PLUS_TOKEN` | 否 | — | Crossref Plus API token（以 header 送出）。 |
| `CROSSREF_BASE_URL` | 否 | `https://api.crossref.org` | API base URL。 |
| `CROSSREF_TIMEOUT` | 否 | `30` | 每請求逾時（秒）。 |
| `MCP_TRANSPORT` | 否 | `stdio` | `stdio` 或 `http`。 |
| `MCP_API_KEY` | 否 | — | 設了則 HTTP 請求需帶相符的 `X-API-Key` header（`/health` 豁免）。 |
| `LOG_LEVEL` | 否 | `INFO` | 日誌層級（日誌走 stderr）。 |
| `REDIS_URL` | 否 | — | 啟用 Redis 快取 + 共享速率控制（選用）。 |
| `CACHE_TTL` | 否 | `86400` | 快取 TTL（秒）。 |
| `RATELIMIT_BACKEND` | 否 | `in-memory` | `in-memory` 或 `redis`。 |

## 工具

**Works** — `search_works`、`get_work`（依 DOI）、`get_work_references`（上限
50）、`get_work_quality`（註冊機構）。
**Members / Journals / Funders** — `search_members`／`get_member`／
`get_member_works`；`search_journals`／`get_journal`（ISSN）／`get_journal_works`；
`search_funders`／`get_funder`／`get_funder_works`。
**Types / Licenses / Prefixes** — `list_types`／`get_type`；`list_licenses`；
`get_prefix`。另有 `ping`。

**共用參數。** 搜尋／列表工具接受 `query`（works 另有 `query_bibliographic`／
`query_author`／`query_title`）、`filter`（Crossref `key:value,…` 語法）、`sort`
+ `order`、`rows`（≤1000）+ `offset`、`select`。深分頁：設 `cursor="*"`，再把回傳
的 `next_cursor` 傳回續抓。所有工具預設回精簡欄位；傳 `raw=true` 取完整 Crossref
JSON。

## 連接 MCP client

**stdio（Claude Desktop / Cursor）** — `claude_desktop_config.json`：

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

或以容器跑 stdio：`"command": "docker"`、`"args": ["run", "-i", "--rm", "-e",
"CROSSREF_MAILTO", "heyinnaneo/crossref-mcp"]`。

**Streamable HTTP** — 容器啟動後，將支援 HTTP 的 client 指向
`http://localhost:8000/mcp`。若設了 `MCP_API_KEY`，以 `X-API-Key` header 帶上。

## Docker / HTTP 部署

```bash
cp .env.example .env          # 設定 CROSSREF_MAILTO
docker compose up -d          # 拉 heyinnaneo/crossref-mcp，HTTP 在 :8000
curl http://localhost:8000/health
```

於 `/mcp` 提供 Streamable HTTP，`/health` 供 compose 健康檢查。設 `MCP_API_KEY`
可要求 `/mcp` 帶 `X-API-Key`。要本地 build，取消 `docker-compose.yml` 內
`build: .` 註解。

## 公開部署（TLS / 反向代理）— 選用

放在內附的 Caddy proxy 後（`Caddyfile` + `docker-compose.proxy.yml`）：TLS 終結
（自動 Let's Encrypt）、HTTP→HTTPS、SSE 串流、後端不對 host 公開。

```bash
cp .env.example .env   # 加上 DOMAIN=、ACME_EMAIL=、MCP_API_KEY=
docker compose -f docker-compose.proxy.yml up -d
curl https://your-domain/health
```

縱深防禦：proxy 邊界（可選 IP allowlist / Basic auth）+ `MCP_API_KEY` 應用層；
兩者皆留 `/health` 開放。需網域 DNS 指向主機、80/443 可達。Caddy 限流需
`caddy-ratelimit` plugin（自 build）。

## Redis 快取 + 跨副本速率控制 — 選用

設 `REDIS_URL` 啟用回應快取（cache-aside 存原始 envelope；key 排除 `mailto`／
密鑰），並以 `RATELIMIT_BACKEND=redis` 啟用共享 token bucket，讓多副本維持在
Crossref polite-pool 速率內。

```bash
docker compose -f docker-compose.redis.yml up -d
curl http://localhost:8000/health   # cache_enabled + ratelimit_backend + redis: up
```

Redis 故障會優雅降級（不快取、改 in-memory 限速）；`/health` 仍回 200 並標
`redis: down`。

## CI / 發佈

`.github/workflows/ci.yml`：**test**（每次 push/PR 跑 ruff + format + pytest 含
覆蓋率）、**security**（Trivy fs 掃描）、**build-push**（`main`／`v*` tag 時 push
multi-arch image 到 `heyinnaneo/crossref-mcp`），打 tag 時另跑 **publish-pypi**
（OIDC Trusted Publisher）+ **publish-registry**（MCP registry）。

Repository secrets（**Settings → Secrets and variables → Actions**）：
`DOCKERHUB_USERNAME` = `heyinnaneo`、`DOCKERHUB_TOKEN` = Docker Hub Access Token
（Read/Write）。打 tag 發版（`git tag v0.1.0 && git push origin v0.1.0`）；tag 須
與 `pyproject.toml` 版本一致。

## 從 MCP registry 安裝

以 `io.github.jtl-neo/crossref-mcp` 發佈（見 [`server.json`](./server.json)），含
PyPI 套件（`uvx crossref-mcp`）與 OCI image。發佈於版本 tag 時自動進行
（`publish-pypi` + `publish-registry`）；需公開 repo 與已設定的 PyPI Trusted
Publisher。

## 安全與信任

- **唯讀。** 每個工具都是查詢，標註 `readOnlyHint`。
- **速率控制。** 預設單 process in-memory — 勿當公開代理承載大流量；多副本請用
  `RATELIMIT_BACKEND=redis`。
- **Polite pool。** 用你自己的 `CROSSREF_MAILTO`。
- **公開 HTTP。** 設 `MCP_API_KEY` 並前置 TLS。
- **不內含密鑰。** `.env` 不進 image、不進 git。

## 授權

[MIT](./LICENSE)。文獻資料來自公開的
[Crossref REST API](https://api.crossref.org)；與 Crossref 無隸屬關係。
