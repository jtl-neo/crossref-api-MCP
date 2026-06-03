# Crossref API MCP Server — 專案規劃

將 Crossref REST API 封裝為 MCP Server，以 Docker Compose 部署。

## 1. 目標與範圍

- 把 Crossref REST API 主要端點包成 MCP tools，讓 LLM client（Claude Desktop、IDE 等）可直接查詢學術文獻 metadata。
- 涵蓋全部主要資源端點：works、members、journals、funders、types、licenses、prefixes。
- 支援 polite pool（mailto）與可選的 Crossref Plus token。
- 以 Docker Compose 一鍵部署，對外提供 HTTP 服務，並保留 stdio 供本地使用。

非目標：不做資料落地儲存／快取資料庫（首版以記憶體 / HTTP 層快取為主）、不做使用者帳號系統。

## 2. 技術選型（建議）

| 項目 | 選擇 | 理由 |
|------|------|------|
| 語言 | Python 3.12 | Crossref 為純 REST API wrapper，Python 開發快、MCP 生態成熟 |
| MCP 框架 | FastMCP（官方 `mcp` SDK） | 內建 stdio + Streamable HTTP，decorator 定義 tools 簡潔 |
| HTTP client | `httpx`（async） | 原生 async、連線池、timeout / retry 易設定 |
| 資料驗證 | `pydantic` v2 | 參數與回傳結構型別化，自動產生 tool schema |
| 套件管理 | `uv` | 安裝快、lock 檔可重現 |
| 容器 | Docker + Docker Compose | 依需求部署 |
| 測試 | `pytest` + `respx`（mock httpx） | 不打真實 API 也能測 |

傳輸方式：**stdio + Streamable HTTP 雙支援**。容器內以 HTTP 對外（預設 port 8000），本地開發可用 stdio。

## 3. Crossref API 端點 → MCP Tools 對應

Base URL：`https://api.crossref.org`

### 核心：Works
| MCP Tool | 對應端點 | 說明 |
|----------|----------|------|
| `search_works` | `GET /works?query=...` | 全文 / 欄位查詢，支援 filter、sort、rows、offset、cursor |
| `get_work` | `GET /works/{doi}` | 依 DOI 取單筆 metadata |
| `get_work_references` | `GET /works/{doi}`（取 reference 欄位） | 取參考文獻清單；`limit` 參數截斷（預設 50） |
| `get_work_quality` | `GET /works/{doi}/agency` | 查 DOI 註冊機構 |

### 資源端點（皆支援 list / get / 其下 works）
| MCP Tool | 對應端點 |
|----------|----------|
| `search_members` / `get_member` | `/members`、`/members/{id}` |
| `get_member_works` | `/members/{id}/works` |
| `search_journals` / `get_journal` | `/journals`、`/journals/{issn}` |
| `get_journal_works` | `/journals/{issn}/works` |
| `search_funders` / `get_funder` | `/funders`、`/funders/{id}` |
| `get_funder_works` | `/funders/{id}/works` |
| `list_types` / `get_type` | `/types`、`/types/{id}` |
| `list_licenses` | `/licenses` |
| `list_prefixes` / `get_prefix` | `/prefixes/{owner_prefix}` |

### 共用查詢能力（封裝為各 tool 參數）
- **query 系列**：`query`、`query.bibliographic`、`query.author`、`query.title` 等欄位查詢。
- **filter**：如 `from-pub-date`、`type`、`has-orcid`、`is-referenced-by-count` 等。
- **分頁**：`rows`（≤1000）、`offset`，深分頁改用 `cursor=*`。cursor 無狀態：tool 回傳含 `next_cursor`，client 下次呼叫把它當參數傳入續抓。
- **排序**：`sort` + `order`。
- **select**：限定回傳欄位以縮小 payload。

工具回傳統一精簡：預設只回關鍵欄位（title、DOI、author、issued、container-title、URL），保留 `raw=true` 取完整 JSON。

## 4. 架構與檔案結構

```
crossref-api-mcp/
├── src/crossref_mcp/
│   ├── __init__.py
│   ├── server.py          # FastMCP 實例、tool 註冊、transport 啟動
│   ├── client.py          # httpx async client、polite pool、retry、rate-limit 處理
│   ├── config.py          # 環境變數（mailto、plus token、base url、timeout）
│   ├── models.py          # pydantic 回傳模型 / 精簡器
│   ├── tools/
│   │   ├── works.py
│   │   ├── members.py
│   │   ├── journals.py
│   │   ├── funders.py
│   │   └── misc.py        # types / licenses / prefixes
│   └── errors.py          # 統一錯誤對應（404、429、5xx）
├── tests/
│   ├── test_works.py
│   ├── test_client.py
│   └── conftest.py
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
├── .env.example
├── .dockerignore
├── .gitignore
└── README.md
```

### 關鍵設計點
- **Polite pool**：所有請求帶 `User-Agent: crossref-mcp/<version> (mailto:...)` 與 `mailto` 參數；有 Plus token 則**並存**再加 `Crossref-Plus-API-Token` header。version 由 `importlib.metadata.version()` 讀，單一來源在 `pyproject.toml`。
- **Rate limiting**：讀取回應的 `X-Rate-Limit-Limit` / `X-Rate-Limit-Interval`，以 token-bucket 控速；遇 429 指數退避重試。**假設單 process / 單 replica**（in-memory bucket，多副本不保證精準）。
- **HTTP 認證（optional）**：環境變數 `MCP_API_KEY`。有設才檢查請求 header（如 `X-API-Key`），未設則不擋（自用預設關閉）。
- **錯誤處理**：DOI 不存在回明確訊息；網路錯誤 / timeout 重試 N 次後回結構化錯誤。
- **設定全走環境變數**，方便容器化。

## 5. 部署流程（定案）

**發佈**：CI 自動 build image 並 push 到 **Docker Hub**。
**部署**：本地用 **Docker Compose** 從 Docker Hub 拉 image 跑起來。

```
push 到 main ──► GitHub Actions：build + push ──► Docker Hub
                                                      │
                          本地 docker compose pull ◄──┘
                          本地 docker compose up -d
```

### Dockerfile
多階段 build：`uv` 安裝依賴 → slim runtime（python:3.12-slim），非 root 使用者，`EXPOSE 8000`，預設 `MCP_TRANSPORT=http`。

### docker-compose.yml（本地用，拉 Docker Hub image）
```yaml
services:
  crossref-mcp:
    image: heyinnaneo/crossref-mcp:latest   # 從 Docker Hub 拉
    ports:
      - "8000:8000"
    env_file: .env
    environment:
      - MCP_TRANSPORT=http
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 5s
      retries: 3
    restart: unless-stopped
```
- 平常用 `docker compose pull && docker compose up -d` 取最新版。
- `.env` 提供 `CROSSREF_MAILTO`、可選 `CROSSREF_PLUS_TOKEN`、可選 `MCP_API_KEY`。
- 保留 `build: .` 註解版，方便本地改 code 時直接 build 測試。
- 健康檢查端點 `/health`：FastMCP `@mcp.custom_route("/health", methods=["GET"])` 回 200（不需 API key）。

### GitHub Actions CI（build + push 到 Docker Hub）
`.github/workflows/ci.yml` 兩個 job：
1. **test**：`uv sync` → `ruff` lint → `pytest`（報 coverage，首版不設硬門檻）。
2. **build-push**（test 過且 push 到 main / 打 tag 才跑）：
   - `docker/login-action` 用 secrets `DOCKERHUB_USERNAME`、`DOCKERHUB_TOKEN` 登入。
   - `docker/build-push-action` build 並 push，tag 規則：`latest` + git sha + （打 tag 時）版本號。
   - 可選 `docker/metadata-action` 自動產生 tag 與 OCI labels。

需在 GitHub repo Settings → Secrets 設定：`DOCKERHUB_USERNAME`、`DOCKERHUB_TOKEN`（Docker Hub Access Token，非密碼）。

## 6. 里程碑

| 階段 | 內容 | 產出 |
|------|------|------|
| M1 骨架 | git init、pyproject、FastMCP hello tool、stdio 可跑 | 可連線的空殼 server |
| M2 核心 works | client + works 四個 tool + polite pool + 測試 | DOI 查詢可用 |
| M3 其餘端點 | members/journals/funders/types/licenses/prefixes | 全端點覆蓋 |
| M4 強化 | rate-limit、錯誤處理、cursor 深分頁、select 精簡 | 穩定度 |
| M5 容器化 | Dockerfile、docker-compose（拉 Docker Hub image）、health check、HTTP transport | 本地一鍵部署 |
| M6 CI 與文件 | GitHub Actions：lint + test + build + push 到 Docker Hub；README、.env.example | 自動發佈 + 可交付 |

## 7. 風險與注意事項

- **Crossref 速率限制**：未進 polite pool 速率較低且不保證；務必設定 `mailto`。
- **大回傳**：works 搜尋 payload 可能很大 → 預設精簡欄位 + `rows` 上限。
- **深分頁**：`offset` 上限 10,000，超過需用 cursor，tool 需正確切換。
- **DOI 格式**：需處理 URL 編碼與大小寫正規化。
- **MCP HTTP 對外**：若公開部署，建議加驗證 / 限流於 proxy 層。

## 8. 部署決策（已定案）

- **發佈**：GitHub Actions CI 自動 build + push 到 Docker Hub。
- **部署**：本地 Docker Compose 拉 Docker Hub image 跑（HTTP transport，port 8000）。
- 自用、本機環境，暫不需 reverse proxy / TLS、不需 Redis 快取層（之後有需要再加）。
- **Docker Hub 帳號**：`heyinnaneo` → image `heyinnaneo/crossref-mcp`。

## 9. 細節決策（已定案）

| # | 項目 | 決策 |
|---|------|------|
| 1 | Docker Hub image | `heyinnaneo/crossref-mcp` |
| 2 | License | **MIT** |
| 3 | HTTP 認證 | optional API key，env `MCP_API_KEY`，有設才檢查 `X-API-Key` header；`/health` 豁免 |
| 4 | `/health` 實作 | FastMCP `@mcp.custom_route("/health", methods=["GET"])` 回 200 |
| 5 | mailto + Plus token | 並存：mailto 永遠送，Plus token 有就再加 header |
| 6 | Rate-limit 範圍 | 單 process / 單 replica 假設，in-memory token-bucket |
| 7 | 版本號來源 | `importlib.metadata.version()`，單一來源 `pyproject.toml` |
| 8 | `get_work_references` | 保留獨立 tool，加 `limit` 參數，預設 cap 50 |
| 9 | Python | `requires-python = ">=3.12"`，runtime image `python:3.12-slim` |
| 10 | 測試覆蓋 | CI 報 coverage，首版不設硬門檻 |
| 11 | cursor 深分頁 | 無狀態：tool 回傳 `next_cursor`，下次當參數傳回續抓 |
