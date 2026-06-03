# Crossref API MCP Server — 開發路線圖（Roadmap）

本檔把 [PLAN.md](./PLAN.md) 的里程碑展開成可執行的任務、可驗收的標準與依賴關係。
PLAN.md 是「決定了什麼」，本檔是「怎麼做、怎麼驗、依什麼順序」。

- 決策定案見 PLAN.md 第 9 節（License=MIT、image=`heyinnaneo/crossref-mcp`、optional API key、cursor 無狀態…）。
- 本檔在原 M1–M6 之外，依完整性審查補上 **M0 前置**、**M7 維運**，並修正一處排序矛盾（HTTP transport / `/health` 提前到 M4，見下）。

---

## 里程碑總覽與依賴

```
M0 前置 ──► M1 骨架 ──► M2 核心 works ──► M3 其餘端點 ──┐
                                                        ├─► M4 強化 ──► M5 容器化 ──► M6 CI與文件 ──► M7 維運
                                            （M4 依賴 M2+M3）
```

| 階段 | 目標 | 主要產出 | 依賴 |
|------|------|----------|------|
| **M0** | 環境前置 | uv/3.12/Docker/GitHub+Docker Hub repo 就緒 | — |
| **M1** | 專案骨架 | 可連線空殼 server（stdio + ping tool） | M0 |
| **M2** | 核心 works | client + works 四 tool + polite pool + 測試 | M1 |
| **M3** | 其餘端點 | members/journals/funders/types/licenses/prefixes 全覆蓋 | M1, M2 |
| **M4** | 強化穩定度 | rate-limit、結構化錯誤、cursor、select、API key、最小 HTTP | M2, M3 |
| **M5** | 容器化 | Dockerfile + compose + health check + HTTP 對外 | M1–M4 |
| **M6** | CI 與文件 | GitHub Actions（lint+test+build+push）、README、.env.example | M1–M5 |
| **M7** | 維運與發版 | CHANGELOG、版本一致性、漏洞掃描、依賴更新 | M6 |

> **排序修正（審查發現）**：原計畫把 HTTP transport 與 `/health` 放 M5，但 M4 的 optional API key 中介層需要它們才能測試（驗「`/health` 不需 key 回 200」）。因此 **M4 先落地最小可跑的 Streamable HTTP transport + `/health` route**，M5 只負責容器化打磨（Dockerfile / compose / healthcheck）。

---

## 橫切關注（所有里程碑共用，先定調再開工）

這些事項貫穿多個里程碑，若到後期才補會造成返工。**從第一個相關里程碑就遵守**：

1. **Logging → stderr**：stdio 模式下 stdout 是 JSON-RPC 通道，任何誤印會破壞協定。所有 log 一律走 `stderr`，級別由 env（如 `LOG_LEVEL`）控制。從 M1/M2 就定調。記錄 retry / 429 退避 / rate-limit 調整事件。
2. **錯誤類別命名統一**：全程用同一套 — `CrossrefError`（基底）、`NotFoundError`(404)、`BadRequestError`(400/422)、`RateLimitError`(429)、`UpstreamError`(5xx)、`TimeoutError`（網路/逾時）。M2 建立、M4 擴充（**演進非重寫**），避免破壞既有 import。
3. **DOI/ISSN/id 正規化集中一處**：`src/crossref_mcp/normalize.py` 在 **M2 一次落地**，M3/M4 沿用，禁止重複實作 `normalize_doi`。
4. **版本單一來源一致性**（PLAN 決策 7）：`pyproject.toml` version → `__version__` → `/health` version → git tag → image tag 五者必須一致。M7 在 CI 加「git tag == pyproject version」檢查。
5. **ruff format 從 M1 納入**：M1 起 `ruff check` + `ruff format --check` 都跑，避免 M6 CI 才爆出大量格式不一致。
6. **安全基線**：`.env` 不進 git（M1 .gitignore）也不進 image（M5 .dockerignore）；API key 比對用 `secrets.compare_digest`（timing-safe）；容器非 root（M5）；依賴漏洞掃描（M7）。

---

## M0 — 環境前置

**目標**：開工前確保工具鏈與遠端 repo 就緒，避免 M1 中途卡住。

| # | 任務 | 細節 |
|---|------|------|
| 1 | 確認 uv 與 Python 3.12 | 本機系統 python 為 3.9.6，需 `uv python install 3.12`（或確認 uv 自動取得 cpython-3.12）。`uv --version` 可用。 |
| 2 | 確認 Docker 可用 | `docker info` 正常；確認本機架構（Apple Silicon=arm64，影響 M6 multi-arch 決策）。 |
| 3 | 建立 GitHub repo | 私有或公開皆可；記下 remote URL。 |
| 4 | 建立 Docker Hub repo | `heyinnaneo/crossref-mcp`；產生 Access Token（Read/Write）備用於 M6 secrets。 |

**驗收**：`uv python list` 含 3.12；`docker info` 無錯；GitHub repo 與 Docker Hub repo 皆存在。

---

## M1 — 專案骨架

**目標**：用 uv 初始化 Python 3.12 專案，建立套件結構與 FastMCP 實例（含 ping tool），確認 stdio server 可被 MCP client 連上。

### 任務
1. **git init + .gitignore**：預設分支 `main`。.gitignore 含 `__pycache__/`、`*.pyc`、`.venv/`、`.env`、`.pytest_cache/`、`.ruff_cache/`、`dist/`、`build/`、`*.egg-info/`、`.coverage`、`htmlcov/`、`.DS_Store`。**`uv.lock` 須納入版控**（勿誤忽略）。
2. **MIT LICENSE 檔**：標準 MIT 全文，年份 2026，著作權人對應 repo owner。
3. **pyproject.toml**（uv）：`name="crossref-mcp"`、`version="0.1.0"`、`requires-python=">=3.12"`、`license={text="MIT"}`、classifiers 含 `License :: OSI Approved :: MIT License`。deps 最小：`mcp[cli]`（FastMCP 來自官方 mcp SDK，**非獨立 fastmcp 套件**）。dev：`ruff`。build-system 用 `hatchling`，`[tool.hatch.build.targets.wheel] packages=["src/crossref_mcp"]`。`[project.scripts] crossref-mcp="crossref_mcp.server:main"`。
4. **src layout**：`src/crossref_mcp/__init__.py`（`__version__` 用 `importlib.metadata.version("crossref-mcp")`，`try/except PackageNotFoundError` 回退）、`server.py`。
5. **server.py**：`from mcp.server.fastmcp import FastMCP`；`mcp = FastMCP("crossref-mcp")`；`@mcp.tool()` 註冊 `ping`；`def main()` 跑 `mcp.run(transport="stdio")`。**logging 設定走 stderr**（見橫切 #1）。
6. **ruff check + format** 設定（`target-version="py312"`，`select=[E,F,I]`）。
7. **最小 README + 首次 commit**。

### 產出
`.git/`、`.gitignore`、`LICENSE`、`pyproject.toml`、`uv.lock`、`src/crossref_mcp/{__init__,server}.py`、`README.md`、首次 commit。

### 驗收
- `uv sync` 成功；`uv run python -c "import crossref_mcp; print(crossref_mcp.__version__)"` 印 `0.1.0`。
- `uv run crossref-mcp` 以 stdio 啟動並阻塞（用 timeout 或 client 驗，勿前景卡住）。
- MCP client（`mcp dev` Inspector 或 `stdio_client`+`ClientSession`）連線：`list_tools()` 含 `ping`，`call_tool("ping")` 成功。
- `uv run ruff check src/` + `ruff format --check` 0 error；git tree clean。

### 風險
- FastMCP 匯入路徑：`mcp.server.fastmcp`，依賴裝 `mcp`/`mcp[cli]`，裝錯 import 失敗。
- `importlib.metadata.version` 需 editable install 後才讀得到，否則 `PackageNotFoundError`。
- stdio 啟動阻塞等 stdin，驗證須用 timeout / 背景 client。

---

## M2 — 核心 works

**目標**：httpx async client（polite pool / timeout / 基本 retry）+ works 四 tool，respx mock 測試，DOI 查詢可用。

### 任務
1. **config.py**（pydantic-settings 或 dataclass + os.environ）：`CROSSREF_MAILTO`(必填，缺則明確 raise)、`CROSSREF_PLUS_TOKEN`(可選)、`CROSSREF_BASE_URL`(預設 `https://api.crossref.org`)、`CROSSREF_TIMEOUT`(30.0)。`get_settings()` 用 `lru_cache`；`get_version()` fallback。
2. **errors.py**（橫切 #2 命名）：`CrossrefError`/`NotFoundError`/`BadRequestError`/`RateLimitError`/`UpstreamError`/`TimeoutError`，各帶 `status`/`message`/`detail`。`error_from_response(response)` 映射（404/400/429/5xx）。
3. **normalize.py**（橫切 #3，一次落地）：`normalize_doi`（去 `https://doi.org/` 前綴、path-escape）、`normalize_issn`、`normalize_member_id` 等，供 M2/M3/M4 共用。
4. **client.py — CrossrefClient**：`httpx.AsyncClient(base_url, timeout)`；預設 header `User-Agent: crossref-mcp/{version} (mailto:{mailto})`；有 Plus token 則**並存**加 `Crossref-Plus-API-Token`。async context manager + `aclose()`。**lifespan/單例管理生命週期**（含關閉 aclose，見審查發現）。
5. **client._get**：params 永遠注入 `mailto`；對 `TransportError`/`TimeoutException`/429/5xx 做基本退避重試（預設 3 次），404 不重試直接 raise。**預留 rate-limit 擴充點**（完整 token-bucket 屬 M4）。
6. **client works 方法**：`search_works`、`get_work(doi)`（先 normalize）、`get_work_agency(doi)`。
7. **models.py 精簡器**：`WorkSummary`（title/doi/authors/issued/container_title/url），`simplify_work` / `simplify_work_list`，全欄位 None-safe。所有 tool 帶 `raw:bool=False`。
8. **tools/works.py 四個 tool**：
   - `search_works`（query 系列 / filter / sort / order / rows≤1000 / offset / select / raw）— select 此時可先佔位，**docstring 標註 M4 才生效**（避免無聲 no-op）。
   - `get_work(doi, raw)`。
   - `get_work_references(doi, limit=50, raw)` — 讀單筆 work 的 `reference` 欄位，**硬 cap 50**（PLAN 決策 8）。
   - `get_work_quality(doi, raw)` — `/works/{doi}/agency`。
9. **server.py 註冊四 tool**（不破壞 M1 stdio）。
10. **tests**：`conftest.py`（settings/client fixture、respx base_url、`asyncio_mode="auto"`）、`test_client.py`、`test_works.py`。
11. **pyproject deps**：加 `httpx`、`pydantic>=2`、`pydantic-settings`；dev 加 `pytest`、`pytest-asyncio`、`respx`。

### 驗收
- `uv run pytest` 全綠且**全程不打真實 API**（全 respx mock）。
- 每請求帶 `mailto`；UA 形如 `crossref-mcp/<ver> (mailto:...)`；設 Plus token 後兩 header 並存。
- mock 404 → `NotFoundError`；連續 5xx 觸發 retry，耗盡 → `UpstreamError`（call count 驗重試）。
- `get_work_references(limit=100)` 實回 ≤ 50；`limit=5` 回 5。
- `raw=False` 回精簡欄位，`raw=True` 回原始 message。
- stdio `tools/list` 含 works 四 tool。

### 風險
- DOI 含斜線/特殊字元，URL 編碼不當會 404 —— 測試需含含 `/` 與大小寫案例。
- pydantic v2 的 `BaseSettings` 已移至 `pydantic-settings`，漏加依賴 import 失敗。
- `pytest-asyncio` 未設 `asyncio_mode` 會略過 async 測試（假性 passed）。
- client 生命週期不管理會洩漏連線。

---

## M3 — 其餘端點

**目標**：members/journals/funders/types/licenses/prefixes 全端點覆蓋，抽出共用查詢參數封裝，沿用 M2 的 client / 精簡器 / normalize。

### 任務
1. **盤點 M2 成果**：確認 client 方法、精簡器、tool 註冊樣式與參數命名，標記待抽出的查詢組裝邏輯。
2. **共用 QueryParams 模型**（models.py）：`query` 系列、`filter`（dict 或 `k:v,k2:v2` 字串）、`rows`(validator 1..1000)、`offset`、`cursor`、`sort`、`order`(`asc`/`desc`)、`select`(list→逗號)、`raw`。`to_query_dict()` 用 alias 對應點號 key（`query.bibliographic`）與連字號 filter key（`from-pub-date`、`has-orcid`），None 不送。
3. **共用精簡器**：works 類保留 title/DOI/author/issued/container-title/URL；list 類（member/journal/funder/type/prefix）各回關鍵欄位。`raw=True` 跳過精簡。
4. **client 通用方法**：`get_resource_list(resource, params)`、`get_resource(resource, id)`、`get_resource_works(resource, id, params)`，統一帶 polite pool，回傳 message 與（若有）`next-cursor`。
5. **tools/members.py**：`search_members` / `get_member` / `get_member_works`。
6. **tools/journals.py**：`search_journals` / `get_journal(issn)` / `get_journal_works`。
7. **tools/funders.py**：`search_funders` / `get_funder` / `get_funder_works`。
8. **tools/misc.py**：`list_types` / `get_type`；`list_licenses`（無單筆 get）；`list_prefixes` / `get_prefix(owner_prefix)`（端點僅 `/prefixes/{owner_prefix}`，docstring 註明）。
9. **server.py 註冊全部新 tool**。
10. **tests**：`test_params.py`、`test_normalize.py`、`test_members.py`、`test_journals.py`、`test_funders.py`、`test_misc.py`。

### 驗收
- `uv run pytest -q` 全綠，各 `test_*` 檔皆有案例執行。
- stdio `tools/list` 含全部 14+ 個資源 tool。
- `QueryParams(rows=1001)` 觸發 `ValidationError`；`to_query_dict()` 正確產生 `query.bibliographic` 與逗號分隔 filter/select。
- respx 斷言：命中 URL 用正規化後 id（ISSN 大寫含連字號、DOI 編碼），query string 帶 mailto。
- `raw=true` 與預設精簡兩路皆被斷言。

### 風險
- `/licenses` 無單筆 get、`/prefixes` 僅 `{owner_prefix}` —— 勿實作不存在端點。
- filter key 含連字號 + query key 含點號，alias 處理要正確。
- **cursor 邊界**：QueryParams 帶 `cursor` 欄位、`get_resource_works` 解析 `next-cursor` 屬「透傳」；完整 next_cursor 回傳與終止邏輯屬 M4（勿兩邊各做一半）。

---

## M4 — 強化穩定度

**目標**：token-bucket 速率控制 + 429 指數退避、統一結構化錯誤、cursor 無狀態深分頁、select 精簡、optional API key、**最小 HTTP transport + `/health`**（排序修正）。

### 任務
1. **config 擴充**：`MCP_API_KEY`(可選)、retry（`max_retries=3`、`backoff_base=0.5`、`backoff_max=30`）、rate-limit fallback（limit=50/interval=1s）。
2. **token-bucket 限速器**（`ratelimit.py` 或 client 內）：`asyncio.Lock` 保護，`capacity`/`tokens`/`refill_rate`/`last_refill`(monotonic)，`async acquire()`。**單 process in-memory，多 replica 不保證精準**（README 標註）。
3. **動態調速**：`parse_rate_limit_headers(headers)->(limit, interval_s)` 純函式（解析 `X-Rate-Limit-Limit` / `X-Rate-Limit-Interval` 如 `1s`），缺 header 用 fallback。
4. **429 指數退避**：`sleep=min(backoff_base*2**attempt, backoff_max)`；有 `Retry-After` 優先；重試前 `await acquire()`；耗盡 raise `RateLimitError`。
5. **統一錯誤**（橫切 #2 擴充，**非重寫**）：補 400/422→`BadRequestError`、5xx→`UpstreamError`、timeout→`TimeoutError`；404 訊息含被查 DOI。
6. **tool 層錯誤轉換**：`errors.to_tool_error` helper，捕捉 `CrossrefError` 子類轉成 `{"error":{type,message,status}}`，給 LLM 可讀訊息非 stack trace。
7. **cursor 無狀態深分頁**：搜尋/`*_works`/`search_*` tool 加 `cursor` 參數（初次 `*`），回傳結構加 `next_cursor`（取自 `next-cursor`）。cursor 與 offset 互斥。**`offset+rows>10000` 明確擋下並提示改用 cursor**。
8. **select 精簡 + raw**：tool `select` 轉 Crossref query param 透傳；**處理 select 與 raw=false 並用**（select 後欄位可能缺，精簡器需容忍）。
9. **最小 HTTP transport + `/health`**（提前自 M5）：`server.py` 依 `MCP_TRANSPORT` 切 `streamable-http`(host `0.0.0.0`, port 8000) / `stdio`；`@mcp.custom_route("/health", methods=["GET"])` 回 `{"status":"ok","version":...}` 200。
10. **optional API key 中介層**：`MCP_API_KEY` 有值才檢查 `X-API-Key`（**`secrets.compare_digest` timing-safe**），否則 401（定義 JSON body）；**`/health` 豁免**；stdio 不受影響。
11. **fail-fast 啟動驗證**：server 啟動時缺 `CROSSREF_MAILTO` 立即報錯退出（非等首次請求才爆）。
12. **tests**：429 重試、404/5xx/timeout、cursor 深分頁（兩次請求 + 終止條件）、rate-limit header 解析 + token-bucket、select + raw、API key（缺/錯/對 + `/health` 豁免）。

### 驗收
- `uv run pytest -q` 全綠，含 429/404/cursor/select/API key/header 解析測試；coverage 有輸出（不設硬門檻）。
- 連續 429 後成功可斷言重試次數與 sleep 被呼叫；耗盡 raise `RateLimitError`。
- 不存在 DOI 回 `NotFoundError`，訊息含該 DOI。
- `search_works` 回 `next_cursor`，回傳 cursor 再呼叫可取下一頁（respx 兩次請求驗）；最後一頁 `next_cursor` 空。
- 設 `MCP_API_KEY` 後缺/錯 `X-API-Key` 回 401、對的通過、`GET /health` 無需 key 回 200；未設則不擋。

### 風險
- FastMCP `streamable-http` 啟動 API（參數名/host/port）依實際 mcp SDK 版本，需查簽名；HTTP endpoint 預設路徑 `/mcp` 需實測確認。
- `X-Rate-Limit-Interval` 格式需防禦解析（避免除以零）。
- next-cursor 終止行為需確認避免無限迴圈。
- 429 退避疊 token-bucket 等待可能過久 → 設合理 `backoff_max`/`max_retries` 避免 MCP client timeout。

---

## M5 — 容器化

**目標**：多階段 Dockerfile + docker-compose（拉 Docker Hub image）+ healthcheck，本地一鍵 `compose up`。（HTTP transport 與 `/health` 已在 M4 落地，此處只打包與驗證。）

### 任務
1. **多階段 Dockerfile**：
   - builder：`python:3.12-slim` + uv，COPY `pyproject.toml`/`uv.lock`，`uv sync --frozen --no-dev`（先裝依賴再 COPY src 裝專案），venv 在 `/app/.venv`。
   - runtime：`python:3.12-slim`，建非 root 使用者，COPY `.venv` + src，`ENV PATH=/app/.venv/bin:$PATH MCP_TRANSPORT=http`，`USER app`，`EXPOSE 8000`，CMD 跑 server。
   - **確認 image 內 `importlib.metadata.version` 讀得到**（COPY .venv 需含 dist-info metadata，否則 `/health` version 爆 `PackageNotFoundError`）。
2. **.dockerignore**：排除 `.git`、`.venv`、`__pycache__`、`tests`、`.github`、`.env`、`dist`、`build`。**務必排除 `.env`**（勿把機密打進公開 image）。
3. **docker-compose.yml**：`image: heyinnaneo/crossref-mcp:latest`、`ports "8000:8000"`、`env_file: .env`、`environment: MCP_TRANSPORT=http`、healthcheck（`urllib` 探 `/health`，interval 30s/timeout 5s/retries 3）、`restart: unless-stopped`、**保留註解版 `# build: .`**。
4. **.env.example**：`CROSSREF_MAILTO`(必填)、`CROSSREF_PLUS_TOKEN`、`MCP_API_KEY`、`MCP_TRANSPORT=http`、`CROSSREF_BASE_URL`、`CROSSREF_TIMEOUT` —— 鍵名與 config.py 完全一致。
5. **本地驗證**：`docker build`、`docker run` 確認非 root + HTTP 監聽 `0.0.0.0:8000`；`curl /health` 回 200；本地驗 compose 時改 `build: .` 或 `docker tag` 騙過 pull（image 尚未 push）。

### 驗收
- `docker build` 成功，runtime 基於 `python:3.12-slim` 且非 root（`docker run --rm ... whoami` 非 root）。
- `curl -i http://localhost:8000/health` 回 200 + JSON 含 status/version。
- `docker image inspect` 顯示 `ExposedPorts` 含 `8000/tcp`、`Env` 含 `MCP_TRANSPORT=http`。
- `docker compose up -d` 後 `docker compose ps` 顯示 `(healthy)`。
- 設 `MCP_API_KEY` 後 `/health` 仍回 200（豁免）。

### 風險
- compose 預設 `image:` 在尚未 push 前無法 pull，本地驗證需 `build: .` 或 `docker tag`。
- `/health` 須在 API key middleware 之外，否則設 key 後 healthcheck 401 → 容器永遠 unhealthy。
- host 須綁 `0.0.0.0`（healthcheck 在容器內用 localhost 仍通，易誤判）。
- 多階段 build COPY 順序錯會破壞 layer cache；`uv sync --frozen` 確保依 lock 重現。

---

## M6 — CI 與文件

**目標**：GitHub Actions（lint + test + 自動 build/push 到 Docker Hub）+ 完整 README + .env.example，達成自動發佈與可交付。

### 任務
1. **.github/workflows/ci.yml 骨架**：`on: push`(branches main, tags `v*.*.*`) + `pull_request`(main)；`permissions: contents: read`；jobs `test` + `build-push`。
2. **test job**：`actions/checkout@v4` → `astral-sh/setup-uv@v5`(cache) → `uv python install 3.12` → `uv sync --all-extras --dev` → `uv run ruff check .` → `uv run ruff format --check .` → `uv run pytest --cov=src/crossref_mcp --cov-report=term-missing --cov-report=xml`。**不設 `--cov-fail-under`**（決策 10）。
3. **pyproject dev 依賴齊全**：補 `pytest-cov`；確認 ruff/pytest 設定。
4. **build-push job**：`needs: [test]` + `if: push 且 (main 或 v* tag)`（PR 不 push image）。
5. **metadata-action@v5**：`images: heyinnaneo/crossref-mcp`，tags = `latest`(default branch) + `sha`(short) + `semver`(v* tag 版本號)。
6. **login + build-push**：`docker/login-action@v3`(secrets `DOCKERHUB_USERNAME`/`DOCKERHUB_TOKEN`)、`docker/setup-buildx-action@v3`、`docker/build-push-action@v6`(push true、tags/labels 來自 metadata、gha cache)。**`platforms: linux/amd64,linux/arm64`**（開發機 Apple Silicon，見審查）。
7. **README**（完整）：簡介 + CI/License badge；安裝（uv）；**設定（環境變數表，與 .env.example 一致）**；**可用 Tools 清單**（全部 tool + 共用參數）；**MCP client 接法**（stdio claude_desktop_config 範例 + HTTP `http://localhost:8000/mcp` + `X-API-Key`）；**部署**（`docker compose pull && up -d` + `/health`）；**CI/Secrets 設定**（Web UI 設 `DOCKERHUB_USERNAME=heyinnaneo`、`DOCKERHUB_TOKEN`=Access Token）；**Crossref 資料來源/禮貌池聲明 + 非官方免責**；License 章節。
8. **LICENSE/pyproject/README License 三者一致**（MIT）。
9. **端到端驗證**：push main → Actions 兩 job 綠 → Docker Hub 出現 `latest`+`sha` tag；打 `v0.1.0` tag → 出現版本號 tag；乾淨環境 `docker pull` + compose up + `curl /health` 200。

### 驗收
- yaml 合法且 jobs 含 `test`+`build-push`。
- test job 可本機重現（`uv sync --all-extras --dev && ruff check && ruff format --check && pytest --cov`）全 exit 0。
- build-push 有 `needs: [test]` 且 if 限定 main/v* tag。
- login 用 `secrets.DOCKERHUB_USERNAME`/`DOCKERHUB_TOKEN`；build-push `push: true`、tags 來自 metadata（latest/sha/semver）、platforms 含 amd64+arm64。
- README grep 得到全部 tool 名、環境變數表、claude_desktop_config 範例、HTTP endpoint + X-API-Key、`docker compose pull && up -d`、secrets 設定說明、Crossref 聲明。
- push 後兩 job 綠、Docker Hub 三類 tag、拉下來 compose up `/health` 200。

### 風險
- 漏 `needs`/`if` → PR 或測試未過就 push 髒 image。
- `DOCKERHUB_TOKEN` 須 Access Token(Read/Write) 非密碼；secret 名稱大小寫須一致。
- semver tag 只在打 v* tag 時產生 → README 須說明「打 tag 才出版本號」發版流程。
- 本環境無 gh CLI，secrets 與最終 push 走 Web UI。
- action major 版本固定（pin）避免突然破損；`ruff format --check` 與既有風格不一致會紅燈 → M1 起就跑 format。

---

## M7 — 維運與發版

**目標**：自動 push 到 Docker Hub 的專案需要的長期維運基線。

| # | 任務 | 細節 |
|---|------|------|
| 1 | CHANGELOG.md | 採 Keep a Changelog 格式；每次發版記變更。 |
| 2 | 版本一致性檢查 | CI 加步驟：打 tag 時驗 `git tag (v0.1.0)` == `pyproject.toml` version；不一致則 fail。（橫切 #4） |
| 3 | 依賴更新 | Dependabot 或 Renovate 設定（pip/uv + GitHub Actions + Docker base image）。 |
| 4 | image 漏洞掃描 | CI 加 Trivy（或 `pip-audit`）掃 image/依賴；高風險告警。 |
| 5 | MCP 可用性打磨 | FastMCP `instructions`；每個 tool 加 `readOnlyHint=true` annotation（全為查詢）；docstring 對 LLM 友善；MCP Inspector 人工驗一輪。 |
| 6 | 真實 API smoke test | `@pytest.mark.live` 預設 skip、設 env 才跑：打真實 Crossref 取已知 DOI，驗 client/精簡器與真實結構相容（補 respx mock 看不到的結構漂移）。 |

**驗收**：CHANGELOG 存在；CI 含 tag-version 檢查與漏洞掃描；Dependabot/Renovate 設定檔存在；tool 有 annotations；live smoke test 可手動跑通。

---

# Phase 2 — 選用擴充階段（M8–M10）

PLAN.md 第 8 節定案「自用、本機環境、暫不需」的三項，展開為可執行的**選用**里程碑。
全部以「現狀不啟用、向後相容」為前提：不做這些，M0–M7 仍是完整可交付的自用部署。

> **三階段不是各自獨立的選單**——它們圍繞同一個「規模化 / 對外」決策耦合。先讀下方「跨階段協調」再決定順序。

## 建議執行順序

```
需要多副本？──是──► M9（先建跨副本限速基線）──► M8（再對外）──► M10（remote 條目可選）
            └─否──► 只要 TLS/對外單副本 ──► M8（單副本，文件註明勿 scale）──► M10（方案 B，不依賴 M8/M9）
```

- **M9 應排在 M8 之前**（若兩者都要做）：M8 把架構推向多副本，但多副本會讓 M4 的單 process 限速假設失效、超發 polite pool。先用 M9 建立跨副本限速基線再對外才安全。
- **單副本對外**：M4 假設仍成立，M8 可獨立先做，只需文件註明「勿 scale，要 scale 先做 M9」。
- **M10 排最後**，預設採方案 B（PyPI + OCI，不放 remote），不依賴 M8/M9；remote 條目（方案 C）才依賴 M8 的公開 TLS 端點。

---

## M8 — 對外公開入口層（Reverse Proxy / TLS）

**目標**：MCP HTTP server 前置反向代理，做 TLS 終結、HTTP→HTTPS 轉址、proxy 限流/連線數、可選進階認證，並**正確轉發 `/mcp` 的 Streamable HTTP(SSE) 串流**與 `/health`。

**觸發條件**（任一成立才做）：(1) 要把 port 綁公網 / 經 DNS 對外；(2) 需要 `https://` 端點；(3) 需在應用前擋限流/未授權流量；(4) 想用比 `MCP_API_KEY` 更強的認證。維持 PLAN §8「只 `127.0.0.1:8000` 自用」則不做。

**技術選型**：

| 方案 | 取捨 | |
|------|------|---|
| **Caddy v2** | 設定最簡、自動 Let's Encrypt 申請+續期、HTTP→HTTPS 內建、SSE proxy 宣告式、~30MB | ✅ 建議 |
| Traefik v3 | Docker label 自動發現、middleware 豐富，但 label 冗長、單後端殺雞用牛刀 | |
| nginx + certbot | 最成熟、SSE 控制最直接，但續期/限流全手動、組合最複雜 | |
| Caddy + oauth2-proxy | 需人類登入式 OAuth 時疊加；機器型 client 不適用 | 選配 |

**關鍵任務**：
1. **釐清認證分層**（寫入 README/PLAN）：proxy auth=邊界第一道、`MCP_API_KEY`=應用第二道。三組合：(a) 自用 IP allowlist 無 key；(b) 對外 TLS+限流+key 必填；(c) 高安全 TLS+OAuth2+key。**proxy 必須原樣透傳 `X-API-Key`**，`/health` 在 proxy 層也豁免認證。
2. **後端不直接對外**：compose 把 crossref-mcp 由 `8000:8000` 改 `expose: ["8000"]` + edge network，保留註解回退版。
3. **Caddy service**：`caddy:2-alpine`、`80:80`+`443:443`、`Caddyfile` 掛載、**具名 volume `caddy_data`**（憑證持久化，勿用匿名 volume）。
4. **Caddyfile**：`{$DOMAIN}` 自動 TLS、`reverse_proxy crossref-mcp:8000`、**`/mcp` 設 `flush_interval -1` + 長 timeout**（否則 SSE 串流被緩衝/切斷）、`/health` 直穿、HSTS 等安全標頭。
5. **限流/連線數** + **可選 IP allowlist / Basic auth**（`caddy hash-password` bcrypt）範本。
6. **`.env.example`/README**：`DOMAIN`/`ACME_EMAIL`/`PROXY_BASIC_AUTH_*`/`ALLOWED_IPS`；對外模式 `MCP_API_KEY` 升為**建議必填**；架構圖、連線 URL 改 `https://<DOMAIN>/mcp`、回退步驟。

**驗收重點**：後端不再綁 host 8000（只 proxy 443 對外）；HTTP→HTTPS 轉址；`/health` 經 LE 憑證回 200；**MCP client 經 `https://<DOMAIN>/mcp` 長串流不被中途切斷**（flush_interval 生效）；`X-API-Key` 透傳後端仍生效；容器重建後憑證仍在（不重撞 LE rate limit）。

**依賴**：M4（HTTP transport + `/health` + `MCP_API_KEY`）、M5（compose/Dockerfile）、M6（README/.env）。前置：對外可解析網域 + DNS 指向 + 80/443 對外（HTTP-01；或 DNS-01）。

**關鍵風險**：
- ⚠️ **SSE 緩衝陷阱**（最隱蔽）：未停用回應緩衝或讀取 timeout 太短 → `/mcp` 連得上卻收不到串流。必須實測長連線。
- ⚠️ **`/health` 認證誤套**：proxy auth/限流或後端 key 套到 `/health` → 容器永遠 unhealthy。三層一致豁免。
- LE rate limit：測試用 staging（`acme_ca`）；`caddy_data` 勿清除。
- **Caddy `rate_limit` 非內建**（需 `caddy-ratelimit` 模組 → 自 build image，與 `caddy:2-alpine` 矛盾）；DNS-01 也需含 provider plugin 的自 build image。落地前先收斂：自 build / 或限流改用 Traefik/nginx。

---

## M9 — Redis 快取 + 跨副本共享限速

**目標**：引入 Redis 同時解決兩事——(1) 快取 Crossref GET 回應降低重複請求/延遲；(2) 把 M4 單 process token-bucket 升級為**跨副本共享分散式限速**，使多副本不超發 polite pool。

**觸發條件**：(1) 開始多副本（compose scale / 多主機）→ M4 單 process 假設失效、頻繁吃 429；(2) 大量重複查詢想降上游請求量；(3) 預建高流量基線。單副本/自用/無 429 困擾則維持 M4 in-memory。

**技術選型**：

| 方案 | 取捨 | |
|------|------|---|
| **hishel 掛 httpx + Redis storage** | 改動最小（掛 M2 的 AsyncClient）、快取上游 raw 回應 raw/精簡天然一致、可多副本共享 | ✅ 建議（需 PoC 驗 Crossref 無 Cache-Control 下能強制快取） |
| 應用層手動 Redis cache-aside | key 正規化/分型別 TTL/stampede 鎖完全可控，但程式量大 | |
| 純記憶體 LRU（cachetools） | 零依賴但無法跨副本、解決不了核心限速問題 | |

**關鍵任務**：
1. **config**：`REDIS_URL`（未設則完全回退 M4 + 不快取，**向後相容預設**）、`CACHE_ENABLED`/`CACHE_TTL_*`（預設 24h，Crossref metadata 更新頻率低）、`CACHE_NAMESPACE`、`RATELIMIT_BACKEND`(in-memory|redis)。
2. **cache.py**：redis.asyncio 連線單例（納入 lifespan + aclose）、**Redis 不可用降級**（記 stderr warning 不讓 tool 失敗）。
3. **回應快取**（hishel）：只快取 200、自訂 key generator（**排除 mailto/UA/Plus token/X-API-Key**、排序 query）、**一律存上游 raw，精簡在本地做**（raw=true/false 命中同一份）。
4. **`fresh`/`no_cache` 參數**（bypass）+ **cache stampede 防護**（TTL jitter + miss 時分散式鎖，鎖 TTL < 請求 timeout）。
5. **`RedisTokenBucket`**：抽 `RateLimiter` 介面、保留 `InMemoryTokenBucket`、用**單一 Lua 腳本原子化** token-bucket 跨副本共享；refill_rate 由 `parse_rate_limit_headers` 帶入；Redis 失敗降級 in-memory。
6. **`/health` 加 redis 狀態**（redis down 仍回 200 標 `redis:down`，不誤殺容器）。
7. **compose**：redis service（`redis:7-alpine`、healthcheck、**`maxmemory`+`allkeys-lru` 逐出**，cache 與 ratelimit 分 namespace）、`depends_on: redis healthy`、多副本 scale 範例。
8. **測試**（fakeredis + respx）：key 正規化、raw 一致性、fresh bypass、只快取 200、**多「副本」共用 bucket 限速收斂 + Lua 並發無 race**、降級。

**驗收重點**：未設 `REDIS_URL` 行為與 M4 完全一致（既有測試全綠）；同請求兩次上游只打一次；raw=true/false 命中同份；fresh 觸發 bypass；5xx 不入快取；兩副本共用 bucket 合計受限；停 redis 後 `/health` 仍 200 標 down 且不崩。

**依賴**：M4（token-bucket/parse headers/結構化錯誤/`/health`）、M2（client/normalize/精簡器/lifespan）、M5（compose/.env）。前置：已出現多副本或重複查詢/429。

**關鍵風險**：快取一致性（一律存 raw）；機密入 key（排除 header）；cursor 深分頁 TTL 宜短或不快取；分散式限速 race（Lua 原子）；Redis 單點（全降級）；多副本 host port 衝突（移除逐一映射）；hishel 對無 Cache-Control 的 Crossref 能否強制快取（**先 PoC**）；Redis OOM（設 maxmemory 逐出）。

---

## M10 — 發佈到官方 MCP Registry 與社群清單

**目標**：以合規 `server.json` manifest 發佈到官方 MCP Registry（`registry.modelcontextprotocol.io`），提供 stdio（uvx/Docker）與（選用）remote HTTP 安裝指引，並列入社群清單。

**觸發條件**：決定對外公開給他人用時。(1) 想被 Claude Desktop/Cursor/VS Code 內建 registry 搜到；(2) 有外部使用者；(3) 已穩定發過 ≥1 個有版本號 release（M7 就緒）。僅自用則不做。

**技術選型**：**方案 B（PyPI + OCI 兩 package，先不放 remote）= 建議**。涵蓋最廣（`uvx crossref-mcp` + `docker run`），皆本機 stdio/容器不需公開 URL，符合自用現況。方案 C（加 remote 條目）才依賴 M8 公開 TLS 端點 + 常駐主機。

**關鍵任務**：
1. **⚠️ 前置阻塞（先做）**：定**實際 GitHub owner**（命名空間 `io.github.<owner>`，注意 Docker Hub 是 `heyinnaneo`、GitHub owner 可能不同）；**查 PyPI 名 `crossref-mcp` 是否被占用**（占用則改名並同步所有 identifier）。三處 placeholder 定稿前無法發版。
2. **PyPI 前置**：pyproject 補 metadata（description/urls/classifiers/keywords mcp+crossref）；設 GitHub Actions **Trusted Publisher（OIDC）**；testpypi 先驗。
3. **ownership 驗證**：README 加 `<!-- mcp-name: io.github.<owner>/crossref-mcp -->`；Dockerfile 加 `LABEL io.modelcontextprotocol.server.name=...` + OCI labels。
4. **server.json**：`$schema` 2025-12-11、name、version（=pyproject）、repository、packages 兩條（pypi stdio + oci stdio 用**版本 tag 非 latest**）、environmentVariables（`CROSSREF_MAILTO` required、`CROSSREF_PLUS_TOKEN`/`MCP_API_KEY` isSecret）。
5. **CI**：`publish-pypi`（OIDC）+ `publish-registry`（官方 Publish Action / mcp-publisher），於 `v*` tag 觸發，`needs: [publish-pypi, build-push]`，**先過版本一致性 gate**。
6. **README**：三種安裝範例（uvx / docker stdio / remote 自架）+ **Security/Trust 段**（read-only + readOnlyHint、限速單 process 警告、polite pool 自備 mailto、remote 須設 key）。
7. 投稿 awesome-mcp-servers（含非官方/資料來源聲明）。

**驗收重點**：`mcp-publisher publish --dry-run` schema+ownership 全綠；registry 查得到條目且版本相符；PyPI description 含 mcp-name；image annotation == server.json name；`uvx crossref-mcp` 可起 stdio；打 tag 後 CI 三段（pypi→docker→registry）皆綠且版本不一致會被 gate fail。

**依賴**：M7（CHANGELOG/版本一致性/annotations/instructions）、M6（CI/Docker Hub/tag 規則）、M5（Dockerfile 需加 OCI LABEL）。remote 條目額外依賴 M8。前置：GitHub repo 公開可 OIDC、PyPI 帳號 + Trusted Publisher。

**關鍵風險**：MCP Registry 為 preview（schema/API 可能 breaking）；命名空間權限（owner 須擁有 repo）；**版本七方同步**（pyproject/server.json/git tag/image tag/PyPI）；OCI 驗證需重建帶 LABEL 的 image（M5/M6 舊 image 不相容）；公開暴露濫用（限速單 process 警告）。

---

## 跨階段協調與須回頭修改的既有決策

Phase 2 三階段共用 `docker-compose.yml` / `.env.example` / `README.md` 三檔並互相耦合，且 **M9 會推翻 PLAN §9 決策 6**。開工前須注意：

**1. M9 推翻「單 process 限速假設」→ 連鎖修訂 5 處**（M9 規劃只改 README 一處，不足）：
- PLAN.md 決策 6 加註「M9 起多副本改用 `RATELIMIT_BACKEND=redis` 收斂」。
- Roadmap M4 task 2 / risk 的「多副本不保證精準」README 標註改為條件式（單副本 in-memory / 多副本 redis）。
- M7 #5 與 M10 的「公開 server 限速單 process 警告」文字同步修正。
- **為此，M4 落地時就須把限速器放 `ratelimit.py` 並用介面**（橫切 #2 演進非重寫），否則 M9 抽介面變成動到 client 的重構。

**2. `/health` 契約跨 M4/M5/M8/M9 一致**：永遠 200、免認證、不限流。M9 加 redis 狀態欄位後，M8 proxy 仍須讓 `/health` 直穿、M5 healthcheck（urllib 只看能否開啟、不解析 body）仍須綠。

**3. `X-API-Key` 認證鏈契約 M8↔M10**：M8 要求 proxy 原樣透傳、M10 remote 區塊宣告同名 header；同一條 client→proxy→backend 鏈，header 名與 timing-safe 後端比對須一致。

**4. docker-compose host port 改動 M8↔M9 是同一區塊**：M8 後端改 expose、M9 多副本移除逐一 host 映射——必須一起設計，勿互相覆蓋。對外模式下 M5/M6 的 `curl localhost:8000/health` 驗收步驟失效，改經 proxy，需文件標註兩種模式驗證差異。

**5. M10 OCI label 回溯改 M5/M6**：M5/M6 產出的 image 不含 `io.modelcontextprotocol.server.name` LABEL，M10 publish-registry 依賴帶 label 的 image → 須回頭補 M5 Dockerfile + M6 metadata-action 的 OCI labels 並重出 tag。

**6. 三階段共漏（補進對應里程碑）**：
- **多副本 + MCP Streamable HTTP session 親和性**：`Mcp-Session-Id` 若有 per-session in-memory 狀態，跨副本負載均衡會話會斷。M9 多副本前須釐清 mcp SDK 的 session 模型（需 sticky 或共享）。
- **cursor 深分頁跨副本**：決策 11 cursor 無狀態理論上多副本安全，但須驗證 Caddy 輪流打不同副本時 `next_cursor` 仍正確續抓；M8 也須講清 compose scale 下 Caddy 如何發現 N 個副本（DNS round-robin）。
- **壓測/並發工具基線**：M8 限流驗收（ab/hey）、M9 並發無 race，須把工具與基線數據列為產出，否則驗收主觀。
