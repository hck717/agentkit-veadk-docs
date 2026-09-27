# AgentKit Studio 本機啟動 runbook（agent + db + docker 一條龍）

> 參考官網：https://docs.byteplus.com/zh-CN/docs/agentkit/Building_and_deploying_agents_using_AgentKit_Studio
> 驗證時點：2026-09-09（fin_mate，veadk 1.1.9，studio server 用 `--dev` 行 local agents）。

## 1. 呢個 doc 係咩

`veadk studio` 係 AgentKit Studio 嘅本機版（同 `veadk web` 同一個 server，只係 landing page 唔同）。
呢個 runbook 講點樣重新開番成 set 本機嘢：

### Quickstart（一鍵）

```bash
cd /Users/brianho/agentkit-veadk-docs/projects/fin_mate
source .venv/bin/activate
make web       # chat-first UI → http://127.0.0.1:8000（先起 db + observability）
make studio    # AgentKit Studio landing → http://127.0.0.1:8001
make web-stop  # 或者 make studio-stop
```

- `make web` / `make studio` 會先 `docker compose up -d openviking otel-collector jaeger`（**唔會**起 `web` container，避免霸 8000），再行 host 嘅 `veadk`。
- 需要 **Docker Desktop 開住**；唔想經 Docker 就照下面 §3 手動起。
- 兩個 UI 同一個 server，唔可以同時用同一 port；`web` 用 8000、`studio` 用 8001，可以並存。

### 用本地模型（可選；預設 Ark）

預設行 Ark cloud（`MODEL_PRIMARY` → `MODEL_BACKUP`）。想 UI 離線／免費行本地（E4 `vllm-mlx`），設兩個 env 就成個 agent 轉去本地 OpenAI-compatible endpoint：

```bash
MODEL_LOCAL_BASE=http://127.0.0.1:8203/v1 MODEL_LOCAL_NAME=fin-mate-local make web
```

- 有 `MODEL_LOCAL_BASE` → `agent_build._model_kwargs()` 回本地（provider `openai`、唔使 key，`MODEL_LOCAL_API_KEY` 預設 `not-needed`）。
- 冇設 → 照舊 Ark primary→backup，行為不變。
- `MODEL_PRIMARY` / `MODEL_BACKUP` 本身都可以用 env 覆寫。

| 組件 | 係咩 | 邊度 |
|---|---|---|
| **Local Agent** | `fin_mate`（`agent.py` → `root_agent`） | `projects/fin_mate/`（`agent_build.py` 砌） |
| **Local DB (KB)** | OpenViking `fin_kb`（local vector index，auto seed `data/kb/`） | Docker `fin-mate-openviking` (`:1933`) |
| **Local DB (STM)** | sqlite `data/stores/fin_mate.db` | STM backend = sqlite |
| **Local DB (LTM)** | OpenViking（同一個 container，session + 長期記憶） | `fin-mate-openviking` |
| **Local Model** | Ollama `:11434`（OpenViking embed `nomic-embed-text`；本地 LLM fallback `qwen3:4b`） | host，非 Docker |
| **Model (main)** | Ark cloud `seed-1-6-flash-250715`（`MODEL_AGENT_API_KEY`） | `.env` |
| **Observability** | otel-collector `:4318` → Jaeger UI `:16686` | Docker |

## 2. 前置條件

1. **用啱 venv**：`projects/fin_mate/.venv`（有 `veadk` + `openviking-sdk==0.1.8` + `google.adk` + `volcengine`）。
   ⚠️ 唔好 source `invoice-pipeline/.venv` —— 嗰個係第二個 project，agent 啲 dep 未必齊，出錯會好蝦人。
   ```bash
   cd /Users/brianho/agentkit-veadk-docs/projects/fin_mate
   source .venv/bin/activate
   ```
2. **Docker Desktop** 開住（OpenViking / otel-collector / Jaeger 係 container）。
3. **Ollama** host 起咗 `:11434`，有 `nomic-embed-text`（OpenViking server 端 embed 用）。
4. **`.env`** 已經有：
   - `DATABASE_OPENVIKING_URL=http://localhost:1933`（本機行；容器入面先係 `http://openviking:1933`）
   - `DATABASE_OPENVIKING_API_KEY` / `ACCOUNT` / `USER` / `USER_ID`
   - `MODEL_AGENT_API_KEY` / `MODEL_AGENT_NAME` / `MODEL_AGENT_PROVIDER`
   - `OBSERVABILITY_OTLP_ENDPOINT`

## 3. 起機步驟

### Step 1 — 起 Docker stack（db）
```bash
cd /Users/brianho/agentkit-veadk-docs/projects/fin_mate
docker compose up -d        # openviking + web(8000) + otel-collector(4318) + jaeger(16686)
docker compose ps           # fin-mate-openviking 應該 (healthy)
```

> 如果淨係想留 db + observability、唔用容器入面嗰個 web（佢霸咗 port 8000），可以：
> `docker compose stop web`

### Step 2 — 確認 DB 有料（fin_kb seeded）
```bash
set -a && source .env && set +a
.venv/bin/python -c "import agent_build; print(agent_build._openviking_has_data(index='fin_kb'))"
# -> True  係有料；False 的話，agent 起嗰陣 build_knowledgebase() 會自動 seed data/kb/
```

> **仲要加 cloud 控制台 creds**（令「智能體」「技能庫」tab 唔再報 HTTP 400/409，返回 200 空 list）：
> 喺 `fin_mate/.env` 加兩行（值同 `BYTEPLUS_ACCESS_KEY` / `BYTEPLUS_SECRET_KEY` 一樣，2026-09-09 已加咗）：
> ```
> VOLCENGINE_ACCESS_KEY=...
> VOLCENGINE_SECRET_KEY=...
> ```
> 唔加嘅話 `/web/runtimes`、`/web/skill-management/spaces` 會話 "credentials not found"。

### Step 3 — 起 local Studio（agent）
喺 `projects/fin_mate` 度（**`--agents-dir ..` 好緊要**）：
```bash
veadk studio --agents-dir .. --dev --host 127.0.0.1 --port 8001
```
睇 log 見到：
```
A2UI UI + API serving on http://127.0.0.1:8001 (agents: .../projects)
```
然後開 **http://127.0.0.1:8001**：

- Agent picker 揀到 **fin_mate**（因為 `--dev` → `agentsSource: local`，用 `/list-apps`）。
- Agent 詳情見到 model `seed-1-6-flash-250715`、tools（`load_knowledgebase` / `load_memory` / `calc` / `fetch_news` …）、
  components：**KB `fin_kb` (openviking)** + STM (sqlite) + LTM (openviking)。
- Search → knowledge 會查**本機 OpenViking**。

**三個位最容易錯：**
1. `--agents-dir ..` —— 由 `projects/fin_mate` 起嘅話 agents 喺 parent；如果就咁 `veadk studio`（agents-dir = 而家目錄）`/list-apps` 會係空。
2. `--dev` —— 冇 `--dev` 嘅話 picker 會去 **cloud AgentKit runtimes**，淨係會撞 DNS（見 §4）。
3. port —— 8000 俾 `fin-mate-web` container 霸咗，用 8001（或者先 `docker compose stop web`）。

> 想要 chat-first UI（唔係 add-agent landing）：同一個 command 換 `veadk web` 就得。

## 4. 邊啲頁面會 502 / network error —— 唔使理

以下係 **cloud-only** 頁面，雙手請放開：

| 頁面 / endpoint | 佢 call 咩 |
|---|---|
| Runtimes / 管理 Agent（`/web/runtimes`、`/web/my-runtimes`、`/web/runtime-detail`） | cloud control-plane `agentkit.cn-beijing` / `agentkit.cn-shanghai` `.byteplusapi.com` |
| Skill Center（`/web/skill-spaces`） | 同上（`list_skill_spaces`） |
| VikingDB KB listing（`/web/viking-knowledgebases`） | `api-knowledgebase.mlp.cn-beijing...volces.com` |

今日（2026-09-09）呢部機 `nslookup` 呢啲 hostname 係 **NXDOMAIN**（DNS 直接話唔存在），所以 `Failed to ListRuntimes: network error` / 502 —— 呢個係**環境 / 區域**問題，**唔係 code bug**，local dev 根本唔經呢啲嘢。
Local chat / add-agent / manage local agent 全部行 local，唔受影響。

⚠️ **`--dev` 只改 agent picker（用 local `/list-apps`），唔會令「管理 Agent」/ Skill Center / VikingDB 呢啲 tab 唔再 call cloud** —— 開住嗰個 tab 照樣會 502。用嚟 chat 就開 Chat ／裝 嗰啲，管理 Agent tab 唔好理。

> **想原裝 tab 直接管本地嘢？** → 見下面 §4.5「本地管理 patch」，一個 script 令呢啲 cloud tab 喺 `--dev` 時改食本地資料。

### Cloud tab 實際狀態（2026-09-09，已加 `VOLCENGINE_ACCESS_KEY/SECRET_KEY` 之後）

| Tab | endpoint | 結果 | 原因 / 有冇得搞 |
|---|---|---|---|
| 智能體 列表 | `/web/runtimes`、`/web/my-runtimes` | ✅ **200** `{"runtimes":[]}` | 有 creds 就唔再報錯；空 = 呢個帳戶冇 cloud runtime（本地 agent 唔喺呢度，喺 picker） |
| 技能庫（技能空間） | `/web/skill-management/spaces` | ✅ **200** `{"items":[]}` | 同上 |
| 知識庫 | `/web/viking-knowledgebases` | ❌ 502 | 呢個係 **cloud VikingDB**（同本地 OpenViking `fin_kb` 唔同產品）；呢個帳戶 Viking 響應冇 `collection_list`；本地 fin_kb 喺 Chat 嘅 knowledge search / `load_knowledgebase` |
| 工作區 / 環境 | `/web/workspaces`、`/web/environments` | ❌ 503「管理員未配置持久化儲存」 | 要 `VEADK_STUDIO_TOS_BUCKET/REGION` + cloud TOS bucket（cloud object storage）；本地唔使搞 |
| 定時任務 | `/web/cronjobs` | ❌ 200（HTML）→ 前端 JSON parse 爆 | route 要 TOS storage 先 mount（cli_frontend 只喺 `cronjob_storage.configured` 時 mount）；冇 storage → SPA catch-all 回 index.html。veadk 本地 mode 行為，唔係 bug 喺你度 |

### 4.5 本地管理 patch（原裝 tab 直接管本地 agent / KB / memory）

一個可逆、冪等嘅 script：`projects/fin_mate/studio_local_patch.py`。佢 patch 咗 venv 嘅
`veadk/cli/cli_frontend.py`，令 **`--dev` 時**下列 cloud tab 改食本地資料（非 `--dev` 照舊行 cloud）：

| endpoint | `--dev` 後返回 |
|---|---|
| `/web/runtimes`、`/web/my-runtimes` | 本地 agents（e.g. `local:fin_mate`，status RUNNING） |
| `/web/runtime-detail?runtimeId=local:fin_mate` | 本地 agent 詳情；env list 係 `.env` keys（secrets 全部 `[masked]`） |
| `/web/viking-knowledgebases` | 本地 openviking KB components（`fin_kb`） |
| `/web/viking-memories` | 本地 LTM components（`default_app`） |
| `/web/cronjobs` | 空 list `{"items":[]}`（唔再 200 HTML 爆 JSON parse） |

用：

```bash
cd /Users/brianho/agentkit-veadk-docs/projects/fin_mate
.venv/bin/python studio_local_patch.py apply    # patch（首次會 .bak）
.venv/bin/python studio_local_patch.py revert   # 完好還原
.venv/bin/python studio_local_patch.py apply    # 冧返再 apply（idempotent）
# apply/revert 之後記住重啟 studio：
.venv/bin/veadk studio --agents-dir .. --dev --host 127.0.0.1 --port 8001
```

⚠️ 呢個係 patch `site-packages` 入面嘅 file —— **veadk 升級之後要重新 apply**；亦都唔會令
真正嘅 runtime 部署變成立喺度，管理 tab 係「睇/管本地」用。`/web/workspaces`、`/web/environments`、
`/web/knowledge-bases` 仍然係 cloud-only（後者而家返 200 空 list，唔 crash）。

## 5. Headless 驗證（optional）

```bash
B=http://127.0.0.1:8001
curl -s $B/web/ui-config | python -m json.tool        # "agentsSource": "local"
curl -s $B/list-apps                                    # ["fin_mate"]
curl -s $B/web/agent-info/fin_mate | python -m json.tool
curl -s "$B/web/search?source=knowledge&app_name=fin_mate&q=Microsoft%20cloud%20revenue%20growth"
# -> results 有 5-10 條（嚟自本機 OpenViking fin_kb）
```

Chat（`run_sse` 需要 `X-VeADK-Local-User` header + 先 create session；`newMessage` 用 `parts[].text`）：
```bash
SID=$(curl -s -X POST $B/apps/fin_mate/users/brianho/sessions \
      -H "X-VeADK-Local-User: brianho" -H "Content-Type: application/json" -d '{}' \
      | python -c "import json,sys; print(json.load(sys.stdin)['id'])")
curl -s -N -X POST $B/run_sse \
  -H "Content-Type: application/json" -H "X-VeADK-Local-User: brianho" \
  -d "{\"appName\":\"fin_mate\",\"userId\":\"brianho\",\"sessionId\":\"$SID\",\"newMessage\":{\"role\":\"user\",\"parts\":[{\"text\":\"你叫咩名？\"}]}}"
```

## 6. Troubleshooting

| 症狀 | 原因 / 解決 |
|---|---|
| `Failed to ListRuntimes: network error` / 502 / `NameResolutionError` | cloud-only 頁面撞 DNS（`agentkit.cn-*byteplusapi.com` NXDOMAIN）；用 `--dev` 行 local，忽略呢啲 tab |
| `/list-apps` 空 | `--agents-dir` 唔唔啱；喺 `projects/fin_mate` 用 `--agents-dir ..`，或者直接 `cd projects && veadk studio --dev ...` |
| port 8000 already in use | `fin-mate-web` container 霸住；`--port 8001` 或者 `docker compose stop web` |
| `.venv/bin/veadk studio` 話 `[Errno 48] address already in use` | 之前嗰個 instance 未死；`lsof -iTCP:8001 -sTCP:LISTEN` 睇 PID，`kill <pid>`（或 `pkill -f "veadk studio"`） |
| `/web/runtimes` 400「Volcengine credentials not found」| fin_mate `.env` 缺 `VOLCENGINE_ACCESS_KEY/SECRET_KEY`；加佢（值 = `BYTEPLUS_*`）。**或者**直接上 §4.5 local patch，就唔再掂 cloud creds |
| 想管理 tab 直接睇本地 agent/KB/memory | 跑 `studio_local_patch.py apply`（§4.5），`--dev` 之下呢啲 tab 會列出本地嘢；veadk 升級後要重跑 |
| `which veadk` 指向 `~/Agent-skills-POC/.venv/bin/veadk` | `~/.zshrc` 而家已經 comment 咗嗰兩行自動 activate（backup `~/.zshrc.bak-20260909`）；開新 terminal 就冇事。永遠最穩陣：用絕對路徑 `.venv/bin/veadk` |
| KB search 冇料 / `_openviking_has_data` = False | OpenViking container 未 healthy / 未 seed；`docker compose ps`，等下再試；agent 起機會 auto-seed |
| import 錯（`openviking_sdk` / `veadk` / `google.adk` 缺） | 用錯 venv；用 `fin_mate/.venv` |
| log 顯示 `Loaded .env file from ~/Agent-skills-POC/.env` 或 `UI: .../Agent-skills-POC/.venv/...` | shell **hash cache** 食咗舊 venv（`~/Agent-skills-POC/.venv` 或其他 project）；開新 terminal，或 `hash -r`/`rehash` 之後行 `.venv/bin/veadk`（絕對路徑，唔好靠 activate） |
| `No config.yaml file found` warning | 正常；呢個 project 用 `.env` |
| Studio 無「Chat」頁 | 用咗 `veadk studio`（landing 係 add-agent）；要 chat-first 就 `veadk web`（同參數） |

## 7. 全文 checklist

```bash
cd /Users/brianho/agentkit-veadk-docs/projects/fin_mate
source .venv/bin/activate
docker compose up -d            # db + observability
docker compose ps               # openviking healthy
set -a && source .env && set +a
.venv/bin/python -c "import agent_build; print(agent_build._openviking_has_data('fin_kb'))"  # True
veadk studio --agents-dir .. --dev --host 127.0.0.1 --port 8001
# 開 http://127.0.0.1:8001 → 揀 fin_mate → chat
```