---
name: byteplus-veadk-docs
description: >-
  Real-time, current-source answers for the BytePlus / Volcengine Agent ecosystem. USE FOR any question about
  AgentKit, VeADK (veadk-python), ModelArk / ModelArk API (Chat/Responses/Messages, reasoning, modes), 
  agentkit-sdk-python, AgentKit CLI (agentkit/ak init config build deploy launch invoke runtime kb mem eval),
  deploying/hosting agents, MCP, sessions, memory & knowledge base, model-gateway (mgw), A2A, harness,
  evaluations, billing/quota, IAM, and anything referencing docs.byteplus.com, the AgentKit/VeADK Mintlify
  mirrors, or volcengine/* GitHub repos. Fetch the live docs first (with local references/ as fallback) and
  answer from current source with citations. Also triggers on "check the docs", "最新文檔", "source says",
  "confirm against doc", and product keywords like doubao, seed, dola, flex, vikingdb, mem0, arkruntime,
  Viking AI Search / viking-aisearch / AI Search / SearchCLI, and ArkClaw / ArkClaw Enterprise / Claw
  (admin console, seats, templates, observability, network config, release notes).
  Also triggers on "all options" / "全部後端" / "全部 backend" / "全部 span" / "can I trace" / "可以 trace 啲乜" /
  "list all DB/記憶/RAG/可觀測/environment variable" / "全部子頁" / "文檔索引" / "all sub-pages" queries:
  the exhaustive option tables (STM/LTM/KB backends, span attributes, CLI logging, env vars) live in §2b
  with exact upstream file paths to fetch, and full per-product page trees live in §2c.
  DO NOT USE for the user's own application code, unrelated products, or for a plain recap of the local
  comprehensive guide when the user explicitly wants current/upstream docs.
---

# BytePlus / Volcengine Agent — Live-Docs Lookup

這個 skill 令你**實時查上游文檔**先答問題，唔好淨係靠記住或靠本地 cache。每次答 AgentKit / VeADK /
ModelArk / SDK / CLI 相關問題，流程如下：

1. **路由話題 → 揀 source（見下表）**
2. **照「Fetching Playbooks」攞最新內容**
3. **帶 citation 作答**；來源衝突時以最新官方為準並註明。

## 0. 兩個市場（先認清，模型名/endpoint/憑證都唔同）

| | BytePlus（國際） | Volcengine（內地） |
|---|---|---|
| 模型 | `seed-*`, `dola-*`, `deepseek-*` | `doubao-*`, `doubao-seed-*` |
| Ark endpoint | `ark.ap-southeast.bytepluses.com/api/v3` | `ark.cn-beijing.volces.com/api/v3/` |
| 憑證 | `BYTEPLUS_ACCESS_KEY` / `BYTEPLUS_SECRET_KEY` | `VOLCENGINE_ACCESS_KEY` / `VOLCENGINE_SECRET_KEY` |
| 預設 region | `ap-southeast-1` | `cn-beijing` |

## 1. Source 排序（優先次序）

| Priority | Source | 點樣讀 |
|---|---|---|
| 1 | Mintlify mirror（VeADK + AgentKit CLI） | `webfetch` 直接攞到 markdown，`https://agentkit-f14c9eb5.mintlify.site/productions/<product>/<path>` |
| 2 | docs.byteplus.com（AgentKit / ModelArk / Viking AI Search / ArkClaw） | JS-rendered，`webfetch` 多數攞到空壳 → 見 Playbook B（**B0 用 `www.byteplus.com/api/doc/getDocList|getDocDetail` 攞 JSON**，最可靠） |
| 3 | GitHub（volcengine/agentkit-sdk-python, volcengine/veadk-python） | 用 `raw.githubusercontent.com/volcengine/<repo>/main/<path>` 或 repo 頁 |
| 4 | local `references/`（指南 + source note） | HTML guide 係簡練精華，topic md 係逐頁抄底稿；標明「可能過時」 |
| 5 | `websearch` | 搵新 doc ID / 未有 registry 嘅頁面 |

## 2. Topic → URL Registry（已確認）

### VeADK（mintlify mirror — 用 `.site`；`.app` 亦可；`/preview/zh` 中綴可有可無）
`https://agentkit-f14c9eb5.mintlify.site/productions/veadk/`

| Topic | Path 後綴 |
|---|---|
| 模型配置 / Agent 參數 | `components/agent/model` |
| Prompt 管理 | `components/agent/prompt-management` |
| 知識庫 (KB) | `components/knowledge` · `components/knowledge/context-search` |
| 記憶 (STM/LTM) | `components/memory` · `components/memory/mem0` · `components/memory/vikingdb` |
| 可觀測 | `components/observability` · `…/apmplus` · `…/inmemory` · `…/logging` |
| 內容安全 | `components/security/content-safety` · `…/inbound` · `…/outbound` |
| 工具 | `components/tools/load-memory`（+同層 `tools/*`, `builtin-tools/*`） |
| 前端 / Studio | `components/frontend/studio` |
| 部署到 AgentKit | `deploy/agentkit` |

### AgentKit CLI（mintlify mirror）
`https://agentkit-f14c9eb5.mintlify.site/productions/agentkit-cli/`
已知例句：`commands/eval` · `commands/runtime/update` · `commands/docs`。其他 commands 用同一模式
（`commands/init`, `config`, `launch`, `runtime/*`, `knowledge`, `memory`, `model-gateway`, `harness`…）。

### docs.byteplus.com（AgentKit & ModelArk）
- AgentKit 中心: `https://docs.byteplus.com/en/docs/agentkit/`（如 `Billing_instructions_during_public_preview`, `Gateway_FAQ`）
- API 文檔: `https://docs.byteplus.com/api/docs/agentkit/MCP_Overview`（呢個路徑有時 server-render，可先試）
- ModelArk: `https://docs.byteplus.com/en/docs/ModelArk/<docID>` or `/docs/modelark/<docID>`（大小寫有時唔同）
  已知 ID：`2636748` = 模型調用最佳實踐（Agent 專用）· `1824121/2222480/2291680/2582774/2582775/2607688/2607689/2608626/2288086/2516283/2608010` = 見 local refs，標題以 fetch 為準

### docs.byteplus.com — 其他產品庫（Viking AI Search / ArkClaw）
- Viking AI Search: LibraryCode `viking-aisearch`，入口 `https://docs.byteplus.com/en/docs/viking-aisearch/Viking_AI_Search_Product_Introduction`（API reference / dataset / recommendation / conversational search 全部子頁見 §2c）
- ArkClaw: LibraryCode `ArkClaw`，入口 `https://docs.byteplus.com/en/docs/ArkClaw/Feature_release_notes_for_administrators`（ArkClaw Enterprise 管理員 + 標準版全部子頁見 §2c）
- URL 模式一律 `https://docs.byteplus.com/en/docs/<LibraryCode>/<DocumentCode>`（**唔係** LibraryID；兩個庫嘅 LibraryCode 就係上面嘅 `viking-aisearch` / `ArkClaw`）

### GitHub
- 平台 SDK: `https://github.com/volcengine/agentkit-sdk-python`（`tree/main/docs/content/…` 係官方內容）
- 框架: `https://github.com/volcengine/veadk-python`（`main` branch）

### Local fallback（references/ 目錄）
- `references/veadk-agentkit-comprehensive-guide.html` — 10 Part 精華（Part 0 前置 → 1 ModelArk → 2 AgentKit → 3 VeADK → 4 SDK → 5 CLI → 6 實戰 → 7 Viking AI Search → 8 ArkClaw → 9 附錄），索引齊全；而家已含「全部選項」大全表（176 張表：model 參數 / 全部 tool / STM、LTM、KB 全部 backend / 全部 span 屬性 / CLI logging）＋ Part 7 Viking AI Search（全深度：Dataset schema / Search 配置 / Filter 語法 / Recommendation / Conversational Search / 鑑權 / 檢索 API 大全 / Data API / SearchCLI / Agent Skill / 計費 / 錯誤 + 全部子頁索引 130 節點）＋ Part 8 ArkClaw（全深度：定位 / 計費 / 鑑權 / 管理員能力 / 實例 / 模型 / 模板 / 圖片 / Skills / Application Center / 用戶權限 / 網絡 / 安全 / 可觀測 / Credential / IAM / 最佳實踐 + 管理員 release notes 逐月表 + 全部子頁索引 387 節點）
- `references/veadk-agentkit-comprehensive-guide.md` — 同一份嘅 markdown 版
- `references/veadk-agentkit-*.md` — 逐主題底稿（pricing / evaluation / memory-context / rbac-observability / gateway / rag-guide / tools-capabilities / database-management / cache-management / finetune-optimize / training-kit / serving-kit / seedream / seedance / vector-cache / performance / hardware / uniqueness / vendor-cost-comparison / ai-concepts）
- `references/agentkit-cli.md` · `references/agentkit-sdk.md` · `references/veadk-api.md`

## 2b. 檔案級 Deep-Lookup（「所有選項」嘅上游）｜唔好靠記憶，冇把握就 fetch 呢啲檔

> 全部 GitHub raw base：`https://raw.githubusercontent.com/volcengine/veadk-python/main/docs/content/docs/<下面路徑>`
> 用戶問「全部 backend / 全部 span / 全部 env / 全部 tool」時，照呢度嘅表逐個 fetch，再帶 citation 作答。

### Observability / Tracing（一個例子 + 可以 trace/show 嘅全部選項）
| 想知 | 檔案（`.en.mdx`） |
|---|---|
| 點起 exporter + `config.yaml` | `framework/observability.en.mdx` |
| 完整例子 + span 種類 | `framework/tracing.en.mdx` |
| 全部 span 屬性（Common / LLM / Tool 三張大全表） | `framework/span-attributes.en.mdx` |
| APMPlus / CozeLoop / TLS / Prometheus endpoint 速查 | `framework/ve-tracing.en.mdx` |

- **可 trace 嘅 span 種類（4 個插樁點）**：`invocation`（agent 最外層）→ `invoke_agent {name}`（子 agent，用 `parent_span_id` 串埋跨 agent 鏈）→ `call_llm` → `execute_tool {name}`。
- **可以「show」嘅全部 span 屬性（精華）**：Common（9 個）＝ `gen_ai.system` / `gen_ai.request.model` / `gen_ai.response.model` / `gen_ai.operation.name` / `gen_ai.thread.id` / `gen_ai.usage.*`（input/output tokens、cache 相關）等等 + `openinference.*`；LLM（17 個）＝ request/response 內容、temperature、top_p、max_tokens、stop、finish reason、usage prompt/completion/cache tokens（有 `#` 記號嘅要 `trace_content=True` 先有）；Tool（6 個）＝ tool 名 + input/output（`trace_content` 控制）。
- **最少例子**：
  ```python
  from veadk.tracing.telemetry import Telemetry
  telemetry = Telemetry(completion_exporter="APMPlus", trace_content=True)
  ```
  ```yaml
  # config.yaml
  observability:
    opentelemetry:
      apmplus:
        endpoint: "apmplus.ines.bcen.volces.com:4317"
  ```
- exporter：`CozeLoop` · `APMPlus`（OTLP gRPC `:4317`）· `TLS`（HTTP `:4318`）· `InMemory` · `Prometheus`（pushgateway）；想埋 model output / thinking / tool arg 就 `LOGGING_LEVEL=DEBUG`。

### Memory — 全部 DB backend
| 想知 | 檔案 |
|---|---|
| STM 總覽 + 揀法 | `framework/memory/short-term/index.en.mdx` |
| STM 每個 backend | `framework/memory/short-term/{sqlite,mysql,postgresql,local}.en.mdx` |
| LTM 總覽 + 揀法 + 自動保存 | `framework/memory/long-term/index.en.mdx` |
| LTM 每個 backend | `framework/memory/long-term/{vikingdb,mem0,opensearch,redis,tos-context,local}.en.mdx` |

- **STM backend 全集**：`local`（內存）· `sqlite`（本地檔）· `mysql` · `postgresql` · `database`（deprecated → `sqlite`）。統一入口 `ShortTermMemory`；一設 `db_url` 就忽略 `backend`。
- **LTM backend 全集**：`local` · `opensearch`（預設）· `redis` · `viking`（生產推薦，唯一支援 `get_user_profile(user_id)`）· `mem0`（托管，免本機 embedding）· `openviking` · `tos_context`（要 `tos>=2.9.4b1`）；`viking_mem` deprecated → `viking`。統一入口 `LongTermMemory`（實作 ADK `BaseMemoryService`）；自動保存 = 10 個 events 或 60 秒。

### Knowledge Base / RAG — 全部 backend + 點放入 + 點攞返
| 想知 | 檔案 |
|---|---|
| KB 總覽 + backend 矩陣 | `framework/knowledgebase/overview.en.mdx`（源碼對照：`veadk/knowledgebase/backends/*.py`） |

- **KB backend 全集**：`local` · `viking` · `context_search` · `openviking` · `opensearch` · `redis` · `milvus` · `tos_vector`。
- 放入：`add_from_files(paths)` / `add_from_directory(dir)` / `add_from_text(text, splitter=...)`，之後用 `knowledgebase.build()`。
- 攞返：① 開 app 自動掛 `load_knowledgebase` tool；② 手動 `kb.search(queries, top_k, rerank, metadata_filter)`；③ 疊 web tools。
- 範例（Viking 後端）：`KBConfig(veadk_config='viking')`，自動 `create_collection()`；`KnowledgeIndex` / `Knowledgebase` 二選一。

### Tools — 全部內建 / MCP / 系統
| 想知 | 檔案 |
|---|---|
| 全部內建 function tools 表 + import 路徑 + 要嘅 key | `framework/tools/builtin.en.mdx` |
| MCP 工具（mcp_router / lark_tools / las / vod_tools / TrustedMcpToolset …） | `framework/tools/builtin-mcp.en.mdx` |
| 系統工具（load_knowledgebase / load_memory） | `framework/tools/system-tools.en.mdx` |
| 自訂 function tool（`@tool` / return type contract） | `framework/tools/custom-function.en.mdx` |
| Guardrail / Inbound / Outbound | `framework/tools/guardrail.en.mdx` |

- 內建全集精華：`web_search` · `parallel_web_search` · `web_scraper` · `link_reader` · `web_fetch` · `vesearch` · `image_generate` / `image_edit` / `video_generate` / `text_to_speech` · `run_code` · `execute_skills` / `coding` / `run_sandbox_agent` · `create_mobile_use_tool`；sandbox 相關 env：`AGENTKIT_TOOL_ID*` / `AGENTKIT_TOOL_HOST` 等。

### Agent / Runner / 配置
| 想知 | 檔案 |
|---|---|
| Agent 參數全集（model_name / model / enable_responses / 補 pinned/overrides …） | `framework/agent/index.en.mdx` · `framework/agent/model.en.mdx` |
| Runner 事件流 + `on_*` callbacks | `framework/runner.en.mdx` |
| Skills / 多 agent / Responses API | `framework/agent/skills.en.mdx` · `framework/agent/advanced.en.mdx` · `framework/agent/responses-api.en.mdx` |
| 全部 env var（`MODEL_*` / `DATABASE_*` / `AGENTKIT_*` / `OTEL_*` / `LOGGING_*`） | `references/configuration/environment-variables.en.mdx` |
| config.yaml schema（index / runtime / constants） | `references/configuration/{index,runtime,constants}.en.mdx` |

- 模型常用 env：`MODEL_AGENT_MODEL_NAME` / `MODEL_AGENT_API_KEY` / `MODEL_EMBEDDING_MODEL_NAME` / `MODEL_EMBEDDING_API_KEY` / `MODEL_JUDGE_MODEL_NAME`；推理 `MODEL_AGENT_*`。

### CLI logging（agentkit-sdk-python 另邊）
- `https://github.com/volcengine/agentkit-sdk-python/blob/main/docs/en/content/2.agentkit-cli/4.logging.md`
- env：`AGENTKIT_LOG_CONSOLE` / `AGENTKIT_FILE_ENABLED`（bool）· `AGENTKIT_LOG_LEVEL`（預設 INFO）· `AGENTKIT_CONSOLE_LOG_LEVEL` / `AGENTKIT_FILE_LOG_LEVEL` · `AGENTKIT_LOG_FILE`；5 級：`DEBUG < INFO < WARNING < ERROR < CRITICAL`；專用 env 優先過通用，通用優先過預設 INFO。

### 源碼 ground truth（docs 唔夠細時先落去睇）
- Tracing exporters：`veadk/tracing/telemetry/exporters/{apmplus,cozeloop,tls,inmemory}_exporter.py`
- Span attributes 提取器：`veadk/tracing/telemetry/attributes/extractors/common_attributes_extractors.py`（LLM / Tool 同層）
- LTM backends：`veadk/memory/long_term_memory_backends/*.py`；STM backends：`veadk/memory/short_term_memory_backends/*.py`
- KB backends：`veadk/knowledgebase/backends/*.py`；內建工具：`veadk/tools/builtin_tools/*.py`

## 2c. 其他產品庫嘅完整頁面樹（Viking AI Search / ArkClaw）

> 呢兩個庫唔喺 Mintlify mirror，用 Playbook B0 嘅 `getDocList` 攞實時樹；本地快照（2026-09）已經將
> **全部子頁索引** 寫入指南 Part 7（Viking，130 個節點）/ Part 8（ArkClaw，387 個節點），可直接引用。

| 庫 | LibraryCode | 節點數 | 主要目錄（頂層） |
|---|---|---|---|
| Viking AI Search | `viking-aisearch` | 130 | Product Introduction · Pricing · Quick Start · User Guide（Dataset / App Mgmt / Configure AI Search / Recommendation / Conversational Search / Monitoring / API Key）· Best practices · API reference（Data API / Search / ChatSearch / Recommend / Rerank…）· Troubleshooting · Terms |
| ArkClaw（含 Enterprise + 標準版） | `ArkClaw` | 387 | What's New（release notes）· Product overview · Billing · Getting Started（Feishu/Lark/Slack/Teams/OAuth/OIDC/SAML）· Employee use · Managing ArkClaw（admin）· Observability · Batch O&M · Access Control · Network Management · Security · Credential · Application Center · Best Practices · Troubleshooting |

- 想攞實時完整樹：Playbook B0 step 1（`getDocList?LibraryCode=<code>&type=1&DataSchema=all_second_nav`）。
- 頁面 URL = `https://docs.byteplus.com/en/docs/<LibraryCode>/<DocumentCode>`。
- 常見關鍵頁：Viking 產品介紹 `viking-aisearch/Viking_AI_Search_Product_Introduction`；ArkClaw 管理員更新日誌 `ArkClaw/Feature_release_notes_for_administrators`；ArkClaw 可觀測 `ArkClaw/ArkClaw_observability_for_administrators`。

## 3. Fetching Playbooks

### Playbook A — Mintlify（最順）
```text
webfetch https://agentkit-f14c9eb5.mintlify.site/productions/veadk/components/memory
```
- 攞到 markdown 直接用。
- 若想攞原始 md：試喺路徑尾加 `.md`。
- 若 404 / 空壳：改試 `.app` host、加 `/preview/zh` 中綴、或去上層目錄頁(`productions/veadk/`)搵 link 再進入。
- 唔知確切 path：`webfetch` 上層頁 → 順住 sidebar link 爬；或 `websearch site:agentkit-f14c9eb5.mintlify.site <topic>`。

### Playbook B — docs.byteplus.com（JS-rendered 陷阱）
`webfetch` 對呢啲頁通常淨係攞到 nav 空壳。處理順序：

**B0（最可靠，攞到成個庫嘅頁面樹 + 正文 JSON）— doccenter JSON API**
文檔站係 ByteDance「doccenter」SPA，正文用 JSON API 攞。真實 API host 係 **`www.byteplus.com`**（唔係 `docs.byteplus.com`；後者嘅 `/api/doc/*` 會 301 去 `/api/docs/doc` 空壳）。要帶 `Origin`/`Referer`：
```bash
# 1) 攞成個庫嘅頁面清單（DocumentCode / Title / ParentCode / Type；Type=1 係目錄、0 係正文頁）
curl -s "https://www.byteplus.com/api/doc/getDocList?LibraryCode=viking-aisearch&type=1&DataSchema=all_second_nav" \
  -H "Origin: https://docs.byteplus.com" -H "Referer: https://docs.byteplus.com/" -o /tmp/list.json
# 2) 攞某一頁正文（回傳 lake/Quill JSON，Content 欄位係 JSON 字串）
curl -s "https://www.byteplus.com/api/doc/getDocDetail?LibraryCode=ArkClaw&DocumentCode=Feature_release_notes_for_administrators&type=1" \
  -H "Origin: https://docs.byteplus.com" -H "Referer: https://docs.byteplus.com/" -o /tmp/detail.json
```
`LibraryCode` 例：`agentkit` · `ModelArk` · `viking-aisearch` · `ArkClaw`。`getDocList` 嘅 Result 係 `{ "<key>": [ {DocumentCode,Title,ParentCode,ParentID,Type,LibraryCode,…}, … ] }`，用 `ParentCode` 砌返完整頁面樹（見 §2c）。`getDocDetail` 正文係「lake」Quill JSON（`{"data":{"0":{"ops":[…]},"rs…/cs…/xr…":表格}}`），表格 cell 文字喺 `zoneType:"Z"` 嘅 `xr…xc<cellId>` block。

**B1（要最像真 DOM / 想直接抄 HTML）— headless Chrome，用大 virtual-time-budget**
```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --no-sandbox --window-size=1440,1000 --virtual-time-budget=30000 \
  --dump-dom "https://docs.byteplus.com/en/docs/viking-aisearch/Viking_AI_Search_Product_Introduction" > /tmp/doc.html
```
⚠️ budget 太細（如 9000）淨係攞到 sidebar nav；正文要 ~30000ms 先 render 到。正文喺 `data-slate-editor="true"` 容器內（`div.ace-line` 逐行、`table.ace-table` 係真 HTML 表、`<a href>` 係真 link），可以直接切出嚟再 pandoc 轉 GFM。

**B2** — 都唔得先試 `/api/docs/<product>/<page>` 變體（有時 server-render 出文章）；再唔得先自己 strip tags。
3. 唔好淨係引 regression — 要以實際抓返嚟嘅字句為準。

### Playbook C — GitHub
- 睇檔案原始內容：`webfetch https://raw.githubusercontent.com/volcengine/veadk-python/main/README.md`
  （branch 用 `main`；錯就試 `master` 或 GitHub 頁面確認。）
- 睇目錄：`webfetch https://github.com/volcengine/agentkit-sdk-python` 然後入 `docs/content/…`。
- 官方 SDK 簽名/預設值以源碼 `*.py`（`*.pyi`）為準：搵 `packages/` 或 `src/` 路徑。

### Playbook D — Local fallback（離線 / fetch 失敗）
- 直接讀 `references/*`。作答時標明「以下係本地 cache（YYYY-MM-…），可能滯後於上游」。
- 本地版同上游有衝突時，話俾用戶知邊度唔同，並指向上游 URL。

## 4. Answer Protocol

- **引言一句講晒答案**，然後先揭細節；Cantonese 為主（跟用戶語言）。
- **一定帶 citation**：`來源: <URL>（由 <方法> 讀取，<日期>）`。無 URL 引用嘅嘢唔好當官方講。
- **頁面唔存在 / 404 / 內容唔對**：照講，唔好估；改行 fallback。
- **衝突**：以最新官方為準；列出兩邊理據。本地 guide 係 2026-09 快照，ModelArk best-practices 適用版本見正文。
- **答問題唔夠料 → 擴展搜**：一種途徑攞唔到就換 Playbook（Mintlify → byteplus → raw github → websearch），唔好停喺第一跳。
- **模型名/參數**：要喺 arkruntime 最佳實踐正文、config.yaml schema、SDK source 實讀實引，唔准憑記憶填 `max_tokens`/mode 值。
- **示例保持可跑**：Python + `veadk-python` / `agentkit-sdk-python`；部署步驟用 `agentkit` CLI。

## 5. 唔准做

- ❌ 唔好因為「大概記得」就寫 API 簽名、doc ID、endpoint、region、env var —— 全部以 fetch 到嘅原文為準。
- ❌ 唔好編造本 registry 無嘅 URL（尤其 `docs.byteplus.com/en/docs/…/Some_Slug`）；要經 sitemap/上層/search 搵真 link。
- ❌ 唔好將本地 cache 當「最新」；只喺 fetch 唔到時先高速落嚟用。
- ✅ 想 update 本地 references/ 嘅話，先 fetch 原文對照，再回寫。

## 6. 快速 routing 表（用戶關鍵字 → 一行指示）

| 用戶講 | 即刻做 |
|---|---|
| VeADK / veadk-python / Agent / Runner / config.yaml / tools / callbacks | Playbook A 攞 `productions/veadk/…` |
| AgentKit CLI / ak / deploy / launch / agentkit.yaml / runtime | Playbook A 攞 `productions/agentkit-cli/…` |
| ModelArk / 推理 / reasoning / Flex / cache / max_tokens | Playbook B 攞 ModelArk doc（best-practices 2636748 起） |
| agentkit-sdk-python / A2aApp / AgentServerApp / Tool / Memory / MCP client | Playbook C 攞 repo + `docs/content/…` |
| 平台 / Gateway / MCP / A2A / Skills / Sessions / Knowledge | Playbook B 攞 `docs.byteplus.com/en/docs/agentkit/…` |
| Viking AI Search / viking-aisearch / AI Search / 多模態搜尋 / 推薦 / 對話式搜尋 / SearchCLI | Playbook B0 攞 `LibraryCode=viking-aisearch`；產品介紹睇 `viking-aisearch/Viking_AI_Search_Product_Introduction`；全部子頁見 §2c / 指南 Part 7 |
| ArkClaw / ArkClaw Enterprise / Claw / 管理員控制台 / seat / template / release notes | Playbook B0 攞 `LibraryCode=ArkClaw`；管理員更新日誌睇 `ArkClaw/Feature_release_notes_for_administrators`；全部子頁見 §2c / 指南 Part 8 |
| 全部 backend / span / env / tool / 檢索選項（STM、LTM、KB、Observability、CLI logging） | 先睇 §2b → fetch 對應檔案；精華對照 `references/veadk-agentkit-comprehensive-guide.html`（176 張大全表） |
| 全部子頁 / 文檔索引 / all sub-pages（Viking、ArkClaw） | 睇 §2c，或 Playbook B0 `getDocList` 攞實時樹；本地快照喺指南 Part 7 / Part 8 |
| 任何 topic 想先對照精華 | 讀 `references/veadk-agentkit-comprehensive-guide.html` 對應 Part |