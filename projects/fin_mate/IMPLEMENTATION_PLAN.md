# FIN-MATE 金融研究 Agent — AgentKit (VeADK) 實作計劃 + 排期（v2.2）

> 一個 project 包辦 `references/veadk-agentkit-all.html` 全部 24 個 Tab 嘅概念。
> 輸入：**yfinance 行情/基本面 + 金融新聞情緒**（用戶提供 news 檔案，未到先用 RSS + 合成數據）。
> 輸出：一個**直接用人哋官方 AgentKit SDK（VeADK）** 建成嘅 agent + 每個 Tab 對應嘅實驗 + 端到端 demo。
>
> **v1 → v2 轉變**：之前自建咗一套「微型框架」去重造 VeADK 概念（llm/gateway/memory/rag/safety……約 80 個檔案），已全部移除。既然目標係**成功實作 + 最少 code**，而 AgentKit 本身正正就係官方 framework（`veadk-python`），直接攞嚟用——**24 個 Tab 嘅概念全部透過 VeADK 功能去攞驗**，唔再造一次車輪。
>
> **v2.0 → v2.1 轉變（實作後）**：
> - **KnowledgeBase / LTM 由 Milvus+Redis / VikingDB cloud 改為自架 OpenViking**（`docker compose up -d`，local vector，零 cloud 帳單）；VLM 移除（KB 純文字）。→ 對應 `vc/db/rag` tab。
> - **Observability 落地為本地 OTel → Jaeger**（輕量，唔用 Volcengine TLS/APM+ cloud）：`veadk` 內建 OTel 追蹤 + OTLP collector + Jaeger UI；OpenViking 內建 `/api/v1/observer/*` + `ov` CLI 透明度；`scripts/trace_all.py` 一鍵打包。→ 對應 `obs/arch` tab。
> - **新增兩大實驗線**：①高吞吐推理引擎（**vLLM / SGLang**）+ **LoRA / QLoRA 精調**（pre/post training）；②**用戶請求排隊（queueing）與路由（routing）**。
>
> **v2.1 → v2.2 轉變（D4/D5 RAG 實驗室）**：
> - **RAG + Cache 由「兩場仗」升級為「三邦」**：①**策略邦**——六種 RAG（naive / advanced / hybrid / corrective / adaptive / agentic）全部 stage 級 **trace + log**，recall/precision/MRR/nDCG 用**自己寫嘅 `eval_metrics.py`**；②**Rerank 邦**——無 / **RRF** / **本地 LLM-as-reranker**（Qwen3-4B：vllm-mlx 或 Ollama）對照；③**Cache 邦**——Ark（`cached_input`）+ 本地 **vllm-mlx**（prefix cache + `/metrics` + warm-prompts）cold vs warm TTFT、開/關成本差；vLLM/SGLang adapter 預寫、等 E2/GPU。
> - **排期由 8 日變 9 日**：RAG 實驗室佔 **D4 + D5** 兩日，之後 **D6–D9 對返原本 D5–D8** 內容（Eval+引擎 → 安全 → Perf/KV/Seed → 打磨）。

- **場景**：Mac（Apple Silicon）為主 + Docker Desktop；本地（Ollama / **vllm-mlx** / vLLM / SGLang）或 BytePlus/Ark key 做雲版對照。
- **時限**：9 個工作日核心（D1–D9；RAG 實驗室佔 **D4+D5**，之後 D6–D9 對返原本 D5–D8）＋接住嘅**延伸階段（E1–E3：LoRA/QLoRA 精調 + vLLM/SGLang 服務 + 請求排隊/路由）**。
- **語言**：Python 3.11+；框架 = **`veadk-python`**（AgentKit 官方 Python SDK，LiteLLM 底 → 一個 config 可同時 switch 本地引擎同 BytePlus ModelArk）。
- **主模型（現行）**：BytePlus Ark **`seed-1-6-flash-250715`**（`MODEL_AGENT_API_BASE=https://ark.ap-southeast.bytepluses.com/api/v3`）。延伸階段再落本地 vLLM/SGLang 起 open-weight 模型（如 Qwen 系列）做對照。
- **Observability**：本地 **Jaeger**（OTLP collector）＋ OpenViking 內建 observer + `scripts/trace_all.py`。

---

## 0. 一句話目標

整一個「你問金融嘢 → Agent 用工具查行情/基本面 → KnowledgeBase RAG 查文檔 → 情緒分析新聞 → 出有根據嘅分析」嘅系統，**code 量最少、最先跑通**，而每個 docs 概念都有一個用 VeADK 功能砌出嚟嘅可量度實驗，唔係淨係讀完個概念。

---

## 1. 技術決策（含理由）

| 項目 | 揀咩 | 點解 |
|---|---|---|
| 框架 | **`veadk-python`**（AgentKit 官方 SDK） | 一次過包晒 Agent / Runner / Tools / Memory（STM+LTM）/ KnowledgeBase RAG / Structured output / 多 Agent / Tracing / API harness / CLI / 雲部署——就係我哋 v1 想自建嗰套，而家直接用 |
| 模型接入 | **LiteLLM**（VeADK 底層） | 現行 `provider="openai"` + Ark `seed-1-6-flash-250715`（`cmp` tab）；延伸階段加本地 `vllm`/`sglang`/`ollama` endpoint 對照 |
| 主模型（現行） | BytePlus Ark **Seed-1.6-Flash-250715**（`MODEL_AGENT_NAME`） | 已跑通；tool-calling 可靠；`MODEL_BACKUP=seed-1-6-flash-250615` 做 fallback |
| 主模型（延伸/本地） | open-weight（如 **Qwen3** 系列）經 **vLLM / SGLang** 起 OpenAI 相容 endpoint | LoRA/QLoRA 精調後 serve；同 Ark 對照吞吐/成本 |
| Embedding | **Ollama `nomic-embed-text`**（dim 768；OpenViking server 端自動 embed） | embedding 由 OpenViking 全權處理，config 標定 ollama `api_base=http://host.docker.internal:11434/v1` |
| KnowledgeBase 後端 | **OpenViking（自架開源，`docker compose up -d`，port 1933，local vector）** | AGPLv3 自架，零 cloud 帳單；server 端自動 parse→L0/L1/L2→embed→search；取代 Milvus+Redis / VikingDB cloud（`vc/db` tab） |
| Memory | STM = **sqlite**（`data/stores/fin_mate.db`）；LTM = **OpenViking**（`backend="openviking"`，session + 長期記憶一條龍） | 對應 `mem` tab；VeADK 一造就有 |
| 工具 | **純 Python function**（type hint + docstring → 自動變 tool）+ builtin `web_search`/`web_fetch`/`link_reader`/`run_code`/`coding` + 自建 `fetch_news`/`read_news_file`/`calc` | 對應 `tools` tab；唔使自己寫 registry |
| API / CLI | `veadk web`（ASGI，`/run`、`/apps/.../sessions`）+ `veadk agentkit` CLI（可選上雲） | 對應 `api`/`cli` tab；Docker compose 統一管理 |
| Observability | 本地 **OTel → OTLP collector → Jaeger**（`veadk` 內建 OTel tracer + 自加 `LocalOtlpExporter`）+ **OpenViking `/api/v1/observer/*` + `ov` CLI** + **`scripts/trace_all.py`** 一鍵打包 | 對應 `obs`/`arch` tab；唔用 Volcengine TLS/APM+ cloud（零帳單） |
| 安全 | 入/出 filter function + simple token auth + role allowlist + `before_tool_callback` HITL | 對應 `sec` tab（薄薄一層，唔自建 framework） |
| 精調（延伸） | **LoRA / QLoRA**（`unsloth`/`peft`）pre/post training + **vLLM / SGLang** serve adapter | 對應 `ft`/`serv` tab；本地 GPU/Apple Silicon 原生 |
| 排隊/路由（延伸） | **請求佇列（queueing）+ 路由（routing）**：優先級佇列、負載均衡、模型路由、多 worker 消費 | 對應 `serv`/`gw`/`perf` tab；多用戶並發落地 |
| 生圖/生片 | `image_generation` / `video_generation` tool + **Mock provider（PIL）**，真 BytePlus endpoint 留接口 | 對應 `seedream`/`seedance` tab；一有 key 即轉 |

**選型深潛（hard 對照）**：現行主模型為 Ark **Seed-1.6-Flash**（雲，零本地 VRAM）。延伸階段本地 open-weight（如 Qwen3-4B Q4_K_M ≈ 3–4 GB，加 KV cache 約 3–5 GB，8 GB Mac 已跑得）經 **vLLM / SGLang** 起；默認 8k ctx、細 top_k，16GB+ 先開長 context 實驗。vLLM（vLLM 本身支援較好 tool-calling / OpenAI 相容）vs SGLang（優勢喺 RadixAttention 前綴快取）做對照。

---

## 2. Repo 佈局（`projects/fin-mate/`，精簡版 ~20 個檔）

```
projects/fin_mate/
├── IMPLEMENTATION_PLAN.md        # 呢份
├── README.md                     # 快速起動 + 概念→檔案對應
├── agent.py                      # `veadk web` app 入口（expose root_agent）
├── agent_build.py                # 共享建構：Agent + KB(OpenViking) + STM/LTM + tools + HITL + OTel tracer
├── agentkit.yaml                 # AgentKit CLI 慣例（entry_point、runtime_envs、hybrid 雲部署位）
├── docker-compose.yml            # openviking + web + otel-collector + jaeger（統一 up）
├── otel-collector-config.yaml    # OTLP receiver(4318) → Jaeger
├── requirements.txt              # deps：veadk-python[extensions] + openviking-sdk==0.1.8 + yfinance + ...
├── .env                          # 環境變數（gitignore；含 DATABASE_OPENVIKING_* + OBSERVABILITY_OTLP_ENDPOINT）
├── Dockerfile.web                # web 容器 base（graphviz + requirements）
├── tools/
│   ├── news_tools.py             # fetch_news/read_news_file（情緒）
│   └── calc.py                   # 數值計算
├── data/
│   ├── kb/                       # KB 文檔（msft_txt 等研報/財報）
│   ├── news/                     # sample news
│   └── stores/fin_mate.db        # STM（sqlite）
├── scripts/
│   ├── trace_all.py              # 一鍵打包 observability（OpenViking observer + logs + Jaeger 提示）
│   └── trace_run.py              # per-run 快照：observer/retrieval + vector/count + Jaeger invocation（策略邦用）
├── eval/                         # （延伸）eval datasets + evaluators + gate
├── experiments/                  # （延伸）每個對比實驗
│   ├── _lib.py                   # 共享：env、KB builder（+ hydration patch）、Ark/本地 LLM client、timing、token/$ 計
│   ├── eval_metrics.py           # 自己寫：recall@k / precision@k / MRR@k / nDCG@k / answer-F1
│   ├── rag_bench/                # D4/D5 RAG 實驗室
│   │   ├── eval_set.py           # 12 fact-QA（gold answer + gold leaf URIs）+ 2 trap + 2 multi-hop
│   │   ├── strategies.py         # 6 條 RAG pipe（naive/advanced/hybrid/corrective/adaptive/agentic）＋ events.jsonl
│   │   ├── run.py                # 策略邦 → report.md
│   │   └── rerank.py             # Rerank 邦：none / RRF / 本地 LLM-rerank → report.md
│   ├── cache_bench/              # D5 Cache 邦
│   │   ├── prompts.py            # shared-prefix prompt（stable vs 亂排）
│   │   ├── ark_cache.py          # Ark multi-turn + prefix-probe（cached_input）
│   │   ├── server_cache.py       # vllm-mlx / vLLM / SGLang adapter（TTFT + cached_tokens + /metrics）
│   │   └── run.py                # → report.md
│   ├── kvlab/  engine_bench/  lora_bench/  queue_bench/  perf/  safety/
├── finetune/                     # （延伸 E1–E2）LoRA/QLoRA 精調管線
│   ├── datasets/                 # 指令/SFT 數據（金融 QA / 工具 call / 情緒）
│   ├── train_lora.py  train_qlora.py  eval_ft.py
├── serving/                      # （延伸 E2–E3）vLLM/SGLang 起本地 model endpoint
│   ├── vllm_serve.sh  sglang_serve.sh  adapter_config
├── router/                       # （延伸 E3）請求排隊/路由
│   ├── queue.py  router.py  workers.py
└── tests/                        # 輕量 pytest
```

compare v1：由 ~80 檔縮到 ~20 檔；「框架」由自建變做一支 `veadk-python` dependency。v2.1 加 `serving/`、`finetune/`、`router/`、`scripts/` 四組延伸。

---

## 3. 端到端架構（對應 VeADK 一個 request 由頭到尾 + site 邊個 tab）

```
[User / curl / `veadk web` (/run) 或 agentkit CLI]
   │  auth + role allowlist（薄）
   ├─[E3 router/queue]  優先級佇列 → 路由 → worker   → serv/gw/perf tab（延伸）
   ▼
[Runner.run(messages, session_id)]
   ├─ Agent(instruction, tools=[...], knowledgebase=kb, tracers=[...])
   │    ├─ LiteLLM → Ark(seed-1-6-flash) 或 [E2] vLLM/SGLang 本地      → serv/gw/cmp tab
   │    ├─ KnowledgeBase（OpenViking `load_knowledgebase`）             → rag/vc/db tab
   │    ├─ STM（sqlite session）/ LTM（OpenViking 跨 session）           → mem tab
   │    ├─ Tools：web_search/fetch_news/read_news_file/calc/run_code    → tools tab
   │    └─ before_tool_callback HITL（寫/副作用工具審批）                → sec tab
   ▼
[Trace：OTel → otel-collector → Jaeger]（每 request：LLM/tool/agent spans）
   ▼
[OpenViking observer /api/v1/* + /metrics]（KB 內部透明度）
   ▼
[`scripts/trace_all.py` 一鍵打包] → [Jaeger UI / eval experiment / CI gate]  → obs/arch/perf tab
```

Request flow（docs ai-concepts §0.2 對照）：認證 → 組 context（system+KB top_k+歷史）→ 模型/引擎選擇 → 工具 loop → 結構化輸出 → 用量記帳 →（可選 shadow eval）。

Request flow（docs ai-concepts §0.2 對照）：認證 → 組 context（system+KB top_k+歷史）→ 模型/引擎選擇 → 工具 loop → 結構化輸出 → 用量記帳 →（可選 shadow eval）。

---

## 4. Tab → VeADK 功能 → 實作產物 → 可量度實驗（覆蓋矩陣）

| # | Tab | 核心概念 | 用 VeADK 邊舊功能做 | 可量度實驗 / 產出 | 邊日 |
|---|---|---|---|---|---|
| 1 | overview | 全站導覽 | README + ARCH.md + `make demo` | 一條 demo run 由頭到尾 | D9 |
| 2 | concepts | 全字典 | `.env`（sampling 參數）+ `output_schema` + Runner 參數 | 結構化輸出成功率先 vs 後；sampling 穩 vs 創意表 | D1, D7 |
| 3 | cli | init/configure/invoke/logs | `veadk agentkit` CLI + `veadk web` | `curl /run` 一頁跑通 + agentkit invoke | D1 |
| 4 | api | Agent/Responses/Runner | `veadk web`（ASGI，`/apps/.../sessions` + `/run`） | curl `/run` 收 events；usage 欄位出到 | D1 |
| 5 | tools | Function/MCP/Skills/A2A | function tools + builtin `web_search` + MCP + sub-agent/A2A | 工具 loop 全程 log；research→risk 委派 | D2, D7 |
| 6 | vc | KB 後端矩陣 | `KnowledgeBase(backend="openviking")`（自架）；原生 vs 其他後端一表 | 切後端建/檢索時間對照 | D2, D4 |
| 7 | rag | RAG 策略（檢索/治癒/自適應/agentic） | `KnowledgeBase`（openviking，L0/L1/L2 auto-parse）+ `_patch_openviking_hydrate()` + `grep` sparse 通道 | ⭐**實驗 1/2：六 RAG 策略邦 + rerank 邦**（自寫 recall/precision/MRR/nDCG） | D4, D5 |
| 8 | db | SQL/Vector/記憶三層 | OpenViking local vector（SQLite STM）+ `debug/vector/*` observer | 「一個 interface 多後端」實測 | D2 |
| 9 | mem | STM/LTM/compaction | STM(session_id sqlite) + LTM(openviking auto_save_session) | 第二輪自動帶返偏好；usage 前後表 | D3 |
| 10 | cache | prefix/上下文/隱式 | Ark `cached_input` / vllm-mlx `cached_tokens` + `/metrics`（VeADK usage 透出） | ⭐**實驗 3：Cache 邦**（Ark + vllm-mlx，三層）；**實驗 4：KV 公式 vs 實測** | D5, D8 |
| 11 | price | Plan/per-token | VeADK usage dump（Jaeger span usage 欄位）+ 成本表 script | 每 request USD/¥ 記帳（+ 可選 console 面板） | D3 |
| 12 | cmp | 跨廠商 | model_provider：ollama vs ark（同一 agent） | 本地 vs 雲（每 1M token）比較表 | D6 |
| 13 | ft | LoRA/SFT | **LoRA / QLoRA**（peft/unsloth）pre/post training + vLLM/SGLang serve adapter | ⭐**實驗 6：精調前/後 eval 分數**（延伸相 E1） | E1 |
| 14 | val | dataset/evaluator/CI | `eval/` 三類 dataset + LLM-judge + gate | `make eval` gate；改 prompt 分數升跌 | D6 |
| 15 | hard | GPU/VRAM/量化 | 公式 + 實測（Ollama verbose / activity monitor） | 3 模型大小 × 精度 × 長度 → VRAM 表 | D8 |
| 16 | serv | 引擎 | **vLLM / SGLang**（本地 open-weight）vs Ollama vs Ark vs mock-cloud | ⭐**實驗 5：吞吐/TTFT/前綴命中**（延伸相 E2） | E2 |
| 17 | gw | 統一入口/fallback/緩存 | veadk LiteLLM `model_fallbacks` + retry；**router/ 請求路由** | 主 provider 死 → 自動降級 demo（有 log 證明） | D2, E3 |
| 18 | sec | RBAC/PII/Audit | request filter + token auth + role allowlist（薄層） | ⭐**實驗 8：injection × 攔截率；越權全 block** | D7 |
| 19 | uniq | 默認上下文緩存 | Ark cached_input / vllm-mlx cached_tokens（usage 欄位）+ stable prefix 排位 | ⭐**實驗 3 cache 邦：開/關 cache 成本差（USD/¥）** | D5 |
| 20 | perf | latency/throughput/cost/eval | VeADK usage + eval 守門 | ⭐**實驗 7：優化前後延遲/成本 + eval 唔跌** | D8 |
| 21 | seedream | 生圖家族 + prompt skills | image_generation tool（Mock→真 API） | 五元素 prompt 對照 5 張 sample 圖 | D8 |
| 22 | seedance | 生片家族 + task/poll | video_generation tool（異步 task + poll） | task 狀態流轉 log（queued→rendering→done） | D8 |
| 23 | arch | 端到端 | ARCH.md + 最終 trace（Jaeger + OpenViking observer + `trace_all.py`） | 全鏈路 trace 一次 | D9 |
| 24 | links | 實用連結 | README 引用返 docs tabs | 每概念對應返 `veadk-agentkit-all.html` | 全程 |

---

## 5. 精簡排期（9 個工作日；原則：**先跑通，後靚**）

> 每日分 AM（實作）/ PM（實驗、驗證）。最大原則：**D1 尾已有一個行得嘅 agent**，之後每日都喺一個「已 work」嘅基礎上加嘢。

#### D1 — 骨架 + 第一個跑通 agent（concepts/cli/api/gw 起步）

- 寫 `requirements.txt`（`veadk-python[extensions]` + `openviking-sdk==0.1.8` + `yfinance` + ...）＋ `uv pip install -r requirements.txt`；`agentkit.yaml` 生成（`common.dependencies_file: requirements.txt`）＋ `.dockerignore`。Ollama 只需 `nomic-embed-text`（OpenViking server 端 embed 用）。
- `agent.py`（`veadk web` 入口）+ `agent_build.py` 最小版：`Agent(name="fin_mate", instruction=…, model=[MODEL_PRIMARY, MODEL_BACKUP], tools=[...])`；`docker compose up -d` 得出第一句答案 + 一次 tool call。
- `veadk web .. --host 0.0.0.0 --port 8000` 起 ASGI，`curl /apps/fin_mate/users/{u}/sessions/{s}` + `curl /run` 收到 response。
- **驗證**：`curl /run`「MSFT 而家股價幾多」出到數字 + tool call log；usage 有 tokens。

#### D2 — Tools 全套 + KnowledgeBase + memory + fallback（tools/vc/db/gw 主力）

- `tools/news_tools.py`、`calc.py` 補齊；tools 變純 function 自動成為 VeADK tools。
- `KnowledgeBase(backend="openviking", index="fin_kb")`——server 端自動 parse+embed；agent `knowledgebase=kb` 自動有 `load_knowledgebase` 工具（idempotent 用 `_openviking_has_data()`）。
- STM（`session_id` 續談）+ LTM（`auto_save_session=True`）接上 runner。
- LiteLLM `model_fallbacks`：主 model 死 → 降級 backup（`MODEL_PRIMARY=seed-1-6-flash-250715` → `MODEL_BACKUP=seed-1-6-flash-250615`，同一 api_base）。
- **驗證**：`「睇吓 MSFT 近況，總結報告」`用到 kb+news+sentiment tool；第二輪對話帶返上一輪偏好。

#### D3 — Observability + usage/cost（obs/price 主力）✅ 已落地

- VeADK 每 request usage dump（prompt/completion/cached_input tokens）寫 SQLite ledger；成本表 script。
- **新增已完成實作**：本地 OTel trace → OTLP collector → **Jaeger**（`docker compose up -d` 起埋 otel-collector + jaeger；`veadk web` 透過 `OBSERVABILITY_OTLP_ENDPOINT` 指過去）；OpenViking 內建 `/api/v1/observer/*` + `ov` CLI 透明度；**`scripts/trace_all.py`** 一鍵打包（observer JSON + 容器 logs + session DB 摘要 + Jaeger 提示）。
- **驗證**：`curl /run` hello → Jaeger 睇到 `fin_mate` service 3-span trace（invocation → invoke_agent → call_llm）。

#### D4 — ⭐ RAG 實驗室（上）：策略邦 + 自有評分（rag/val 主力）

> RAG 由一場仗升做「三邦」，佔 **D4 + D5** 兩日（之後 D6–D9 對返原本 D5–D8 內容）。

- `experiments/_lib.py`：.env loader、KB builder（reuse `build_knowledgebase` + `_patch_openviking_hydrate`）、Ark 同本地 LLM client、stage timing、chars→tokens、USD 計（§8 表）。
- `experiments/eval_metrics.py`——**自己寫** recall@k / precision@k / MRR@k / nDCG@k / answer-F1（token overlap；金標準 = `eval_set.py` 每題標 gold leaf URIs + gold answer）。
- `experiments/rag_bench/eval_set.py`：12 條 fact-QA（8 份 MSFT 研報 + overview）+ 2 條 KB 無答案 trap（量度唔亂講）+ 2 條 multi-hop。
- `rag_bench/strategies.py` 六條 pipe，每 stage 記 `runs/<strategy>/events.jsonl`（stage, ts, latency, tokens, cached, score, uris）：
  - **naive**：`find` top_k=5 注入（= 現 prod baseline）。
  - **advanced**：`find` k=15 + read_limit 2000 + dedupe + `grep` 擴 query + score gate。
  - **hybrid**：dense `find` + sparse `grep` terms → RRF merge。
  - **corrective**：retrieve → self-check（分數/一致性）→ 差則 query rewrite + re-retrieve；再差 skip 注入直接答（log correction）。
  - **adaptive**：router 決定查唔查（trap / 閒談 skip retrieval）。
  - **agentic**：真 agent（veadk `Runner` + `LoadKnowledgebaseTool` loop）→ OTel/Jaeger span + observer/retrieval delta 快照。
- **trace + log**：`scripts/trace_run.py` per-run 快照（observer/system + retrieval + debug/vector/count + Jaeger invocation 提示）。
- **驗證**：6×12 = 72 runs → `experiments/rag_bench/report.md`：每 strategy 有 recall/precision/F1/MRR/nDCG@k + answer-F1 + 分 stage latency + tokens + USD + efficiency（F1/$/token）；recommend 格已揀。
- `rag_bench/rerank.py`（Rerank 邦）：固定 candidate pool（top15 dense + grep）× {**none**, **RRF**, **本地 LLM-as-reranker**}。
  - **RRF**：k=60 融合 dense+grep 排序，免費、確定性。
  - **本地 LLM-as-reranker**：**Qwen3-4B**（vllm-mlx serve 或 Ollama）pointwise score 0–3 → sort 取 top-k（唔用 Ark，本地≈$0）；對照 recall@3/MRR/answer-F1 升跌 + latency/$ penalty。


#### D6 — Eval 體系 + 引擎對比（val/serv/hard 主力）
- please test 6 very different prompts sets that with rag, tools call + output expectation + local_llm_as_a_judge
- `eval/golden_datasets/` 三類（QA / tool_call / sentiment）+ `evaluators.py`（exact / F1 / LLM-judge）+ `gate.py`；`make eval` 一鍵 + CI gate（改壞 prompt → fail）。
- `experiments/engine_bench/run.py`：同一 prompt 集 → Ollama vs Ark（冇 key 就註明 + mock-cloud 對照）吞吐/TTFT/usage。
- **驗證**：`make eval && echo $?` 出 0/1；bench report 有數。



#### D7 — 安全 + 多 Agent + 結構化輸出（sec/tools/cmp 主力）

- 薄安全層：request input filter（injection 偵測）+ simple token auth + role allowlist（viewer/analyst/admin）。
- `SequentialAgent`：research_agent（數據+新聞）→ risk_agent（風險結論）委派 demo；A2A 概念點到即止。
- `output_schema`：分析結果出結構化 JSON（rate/score/理由）；比較「有無 schema」輸出正確率。
- PII detection filter at input and output
- Protect Prompt injestion 
- Sensitive Data Disclosure Project 
- **驗證**：red_team_attack_evaluation_set x injection 集 × 攔截率表；越權 call 全 block；schema 輸出演到。

#### D8 — ⭐ Perf Playbook  + Seed demos（perf/hard/serv/seedream/seedance 主力）

- `experiments/perf/`：優化前後對照（top_k 收窄 → 少 tools → compaction/summarization → 並行工具）每格 latency/cost + **eval 分數唔跌先收貨**。
- `seed/image_gen.py` + `video_gen.py`：Mock（PIL）→ 真 BytePlus 接口留位；五元素 prompt 對照 + 異步 task/poll log。
- **驗證**：perf report 有前後兩欄；KV 實測 vs 公式 < ±20%；生圖/生片 artifacts + status log。

#### D9 — 打磨 + buffer（arch/overview/links 主力）

- AI gateway of MCP/ agentkit/ VeADK
- `README.md`（起動 + 概念→檔案對應）、`ARCH.md`、全套 eval 重跑、`make demo` 由頭到尾。
- **驗證**：24 tab 覆蓋 check 表 + `make demo` 可重現 + 全部實驗 report 存在。

---

### 延伸階段（D9 之後，三炮，每炮 ~1–2 日）

> 目標：由「單一雲模型 + 單用戶順序請求」升級做「本地自己訓 + 自己 serve + 多用戶排隊/路由」，全程量度對照。

#### E1 — LoRA / QLoRA 精調（pre/post training；ft tab）

- **數據**：`finetune/datasets/`——金融 QA（KB 相關）、工具 call 範例、情緒分類；小（100–1k 條）但高質。可先用 `eval/` + 合成 pipeline 造。
- **訓練**：`peft`/`unsloth`。**LoRA**：全精度 adapter（r=8/16，`target_modules` 揀 attention + MLP）；**QLoRA**：4-bit NF4 base（bnb）+ 相同 adapter（對無 GPU 的 Mac 或卡 budget 場景）。base 揀 open-weight（Qwen3 或者 BytePlus/open 出嘅可下載權重如有）。
- **Pre/post training 對照**：pre（僅 instruct 微調）+ post（繼續用金融數據 SFT）兩階段，跑同一 eval set。
- **驗證**：`experiments/lora_bench/report.md`——精調前/後 eval 分數（F1/LLM-judge）、訓練步數/cost、adapter 體積。

### E2 - Pre-training vs fine-tuning -- SFT/RFL

### E3 - Redis vs OpenViking on LTM & Vector DB 
- add Semantic Cache + Working Memory with Redis in layer 1 search 
- else layer two openviking
- compare what if wholely Redis only vs. OpenViking only

(1) 查詢與檢索流程（Read Path）
Semantic Cache Check：
用戶發送請求，先在 Redis 中計算問題向量並執行範圍檢索（Cosine Distance < 0.15）。若命中，直接返回答案。

OpenViking 意圖與目錄導航：
若快取未命中，請求轉入 OpenViking。系統不是在全量資料集暴力搜索，而是先透過意圖分析，用向量檢索找到最相關的目錄（如 viking://memory/ho_brian/preferences/）。

分級上下文注入（Tiered Hydration）：

優先讀取該目錄下節點的 L0 摘要 與 L1 結構 拼裝進 System Prompt 。

只有當 Agent 判定需要精確文檔或程式碼實作時，才發動 read_details 加載特定節點的 L2 原文 。

LLM 生成與回傳：
LLM 生成回答並輸出給使用者。

(2) 記憶沉澱與整合流程（Write / Consolidation Path）
即時寫入：對話訊息即時 append 到 Redis Session List 中，維持實時多輪流暢度。

會話結束異步壓縮：當會話結束（或對話超過 5 輪），後台 Celery / Worker 異步提取該對話的核心實體與事實（Fact Extraction）。

OpenViking 歸檔與更新：

將新萃取的事實寫入 viking://memory/{user_id}/，並更新或覆蓋舊有矛盾知識（Self-evolving Memory）。

計算該記憶的向量並同步寫入 VikingDB / Milvus，同時生成對應的 L0 摘要 。

若為高頻精確問答，同步寫入 Redis 語義快取並配置 7 天 TTL 。



#### E4 — vLLM-metal  本地 serve（serv tab）

- **vLLM**：`vllm serve <model> --served-model-name <name> --enable-auto-tool-choice`（OpenAI 相容，LiteLLM 直接用）；**SGLang**：`python -m sglang.launch_server`（對照）。
- 用 **E1 訓好嘅 LoRA/QLoRA adapter** 合併或掛載 serve；agent 模型 switch 去本地 endpoint。
- **驗證**：⭐實驗 5 `experiments/engine_bench/report.md`——vLLM vs SGLang vs Ollama vs Ark：吞吐（tok/s）、TTFT、併發 1/8/32、前綴命中；LoRA on/off 對比。

- `cache_bench/`（Cache 邦，三層）：
  - `prompts.py`：shared-prefix prompt 生成（system+skills+KB 排頭 stable vs 亂排）。
  - `ark_cache.py`（今日）：multi-turn chat cache（`previous_response_id` chaining）+ prefix-probe（`caching:{"type":"enabled"}` + `store`）；`cached_tokens/prompt` → `cached_input%`；開/關 cache 成本差（USD/¥）。
  - `server_cache.py`（今日）：**vllm-mlx** 獨立 venv + MLX **Qwen3-4B**（`--enable-prefix-caching --metrics --warm-prompts`）cold vs warm TTFT + `usage.prompt_tokens_details.cached_tokens` + `/metrics` `prefix_cache_hits`；內建 `bench-serve`。
  - vLLM-metal （`--enable-prefix-caching --enable-prompt-tokens-details`)

- `experiments/kvlab/run.py`：KV cache 公式（`2×layers×kv_heads×head_dim×seq×bytes`，Qwen3-4B: 36層/8 head/128 dim）vs 實測（長度 2k/4k/8k）→ VRAM 表。


- **驗證**：cache `report.md` 有 Ark + 本地 cached_input%、TTFT speedup、開/關成本差；rerank `report.md` 有 effectiveness + recommend。

#### E4 — 用戶請求排隊 + 路由（serv/gw/perf tab）

- **`router/queue.py`**：多用戶請求入優先級佇列（FIFO + queue priority）；**`router/router.py`**：路由策略——按 負載/併發 → 派去 idle worker（模型 endpoint / GPU），重負載落額外隊列，超時 fallback 降級模型（本地→Ark）。
- **`router/workers.py`**：N 個 worker 消費佇列（asyncio + queue），接返 `veadk` Runner。
- 加 queueing 指標去 observability（enqueue→dequeue→complete 延遲，入 Jaeger span / observer）。
- **驗證**：⭐`experiments/queue_bench/report.md`——併發 1/5/20 下 P50/P95 延遲、吞吐、丟失率；優先級是否有效；fallback 觸發 log。



---

## 6. 核心實驗清單（九場仗，全部有量度）

| # | 實驗 | 對照維度 | 對應 tab | 產出 report | 邊日 |
|---|---|---|---|---|---|
| 1 | **RAG 策略邦** | 6 種 RAG（naive/advanced/hybrid/corrective/adaptive/agentic）→ recall/precision/MRR/nDCG@k（自寫）+ answer-F1 + stage latency/tokens/$ + trace/log | rag/val | `experiments/rag_bench/report.md` | D4 |
| 2 | **Rerank 邦** | none vs RRF vs 本地 LLM-rerank（Qwen3-4B）→ recall@3/MRR/answer-F1/latency/$ | rag | `experiments/rag_bench/report.md` | D5 |
| 3 | **Cache 邦** | stable vs 亂排 → cached_input%（Ark `cached_input` / vllm-mlx `cached_tokens` + `/metrics`）；cold vs warm TTFT；開/關成本差 | cache/uniq | `experiments/cache_bench/report.md` | D5 |
| 4 | **KV Cache 公式 vs 實測** | 長度 × 量化 × memory | hard/serv | `experiments/kvlab/report.md` | D8 |
| 5 | **Engine 對比（E2）** | vLLM vs SGLang vs Ollama vs Ark：吞吐/TTFT/併發/前綴命中 | serv/cmp | `experiments/engine_bench/report.md` | E2 |
| 6 | **LoRA/QLoRA 前後（E1）** | 精調前 vs 後（LoRA / QLoRA 各一）eval | ft | `experiments/lora_bench/report.md` | E1 |
| 7 | **Perf Playbook** | 優化前後 latency/cost + eval 守門 | perf | `experiments/perf/report.md` | D8 |
| 8 | **Safety 攻防** | injection 攔截 / RBAC 越權 | sec | `experiments/safety/report.md` | D7 |
| 9 | **排隊/路由（E3）** | 併發 1/5/20 下 P50/P95/吞吐/優先級/fallback | serv/gw/perf | `experiments/queue_bench/report.md` | E3 |

---

## 7. 每 Request 記住嘅「度量骨骼」（對應 perf/pricing）

```
request_id, provider, model, session_id,
prompt_tokens, completion_tokens, cached_input_tokens,
cache_hit_rate, ttft_ms, total_ms, tok_s,
cost_usd / cost_cny, guardrail(block/allow), audit_hash,
tool_calls[], steps_count, eval_score(shadow)
# D4/D5 RAG 實驗室（策略邦 / rerank 邦 / cache 邦）
strategy(naive|advanced|hybrid|corrective|adaptive|agentic),
stage_timings{retrieval_ms, rerank_ms, llm_ms}, rerank(none|rrf|local_llm),
recall@k, precision@k, mrr@k, ndcg@k, answer_f1,
gold_uris[], retrieved_uris[], injected_tokens,
events_log(runs/<strategy>/events.jsonl), observer_delta
# E3 排隊/路由（queue 指標入 Jaeger span / observer）
enqueue_ts, dequeue_ts, complete_ts, queue_depth, priority,
routed_worker, fallback(primary_dead -> backup)
```

D1 由 VeADK usage 落地；**D4/D5 RAG 實驗室**加 strategy/stage/recall-precision/rerank/cached_input 指標；D6 加 `eval_score`；E3 加 queue/route 指標；全程入 SQLite —— 九場仗全部有底數。

---

## 8. 成本估算（現行自架 + BytePlus 實招對照）

| 項目 | 現行本地（自架） | BytePlus 雲 | 備註 |
|---|---|---|---|
| 主模型 | **Ark Seed-1.6-Flash-250715**（token 計） | Seed-2.0-mini $0.10/$0.40 | 依家實際上緊雲；E2 起本地 vLLM/SGLang 對照 |
| 本地推理（E2） | **$0**（vLLM/SGLang + Mac 電費） | — | LoRA/QLoRA adapter 都係本地$ |
| Rerank（D5） | **$0**（本地 Qwen3-4B：vllm-mlx / Ollama） | Ark-rerank 按 token | LLM-as-reranker 行本地；RRF 免費 |
| Cache 邦（D5） | **$0**（vllm-mlx prefix cache，本地） | — | cold vs warm TTFT 全本地 |
| KB / LTM | **OpenViking 自架 $0**（docker + 本地 disk） | VikingDB $0.25/CU·hr ⚠️ | 取代 Milvus+Redis，零帳單 |
| Embedding | **Ollama nomic-embed-text $0** | doubao-embedding $0.15/M | OpenViking server 端自動 embed |
| Tracing | **Jaeger + OTLP collector $0**（本地 docker） | TLS / APM+ 按量 | 取代 cloud observability |
| 精調（E1） | **$0**（peft/unsloth 本地） | Ark 精調按時收費 | QLoRA 得先落 4-bit |
| 請求路由（E3） | **$0**（自寫 router/） | — | 排隊指標入 Jaeger |

**結論**：核心架構已完全自架（OpenViking + Jaeger + Ollama），**除咗主模型 token 外基本 $0**。主模型可全程用 Ark Seed-1.6-Flash（最平），E2 起用本地 open-weight 對照再慳。雲方案全部保留接口做對照/伸延。

---

## 9. 風險 / 注意 / 前置

| 風險 | 影響 | 應對 |
|---|---|---|
| **VeADK API 細節有機會改**（config key / 參數名） | 卡實作 | 每日對返 `github.com/volcengine/veadk-python` examples（01–11）照抄再改；GitBook docs 用 `.md` URL 查 |
| **openviking-sdk 版本要夾 veadk** | 參數 mismatch → TypeError | pin `openviking-sdk==0.1.8`（0.1.9 改咗 lean options dict API，veadk 1.1.9 用 rich kwargs） |
| **OpenViking hydration 攞唔到正文** | RAG 冇料 | `agent_build.py` `_patch_openviking_hydrate()` monkeypatch 優先 `read()`（已解決） |
| **OpenViking 唔係黑 box 浪唔到** | 觀察唔到 | 內建 REST `/api/v1/observer/*` + `/metrics` + `ov` CLI + `/openapi.json`；`scripts/trace_all.py` 打包 |
| **無 BytePlus key / 主模型不可用** | agent 出唔到 | 已設 MODEL_BACKUP fallback；E2 本地 vLLM/SGLang 起 open-weight 完全脫離雲 |
| **Mac RAM/VRAM 限制** | 大 context + 並發爆 | 默認 8k ctx、Q4/QLoRA 4-bit；vLLM 設 `--max-model-len` / `--gpu-memory-utilization` |
| **真 vLLM/SGLang 要 CUDA/Linux GPU** | 本地 cache/engine 實測做唔到 | **vllm-mlx**（Apple Silicon 原生 vLLM 式）今日出數；vLLM/SGLang adapter 等 E2/GPU box |
| **vllm-mlx 同 veadk dep 撞** | env 污染 | cache 邦用獨立 venv；port 30000 同 web(8000)/openviking(1933) 分開；Qwen3-4B ~4GB download（1.7B lighter fallback） |
| **本地細模型做 LLM-rerank 質素** | rerank 邦準確度受限 | pointwise score 0–3 比 listwise 穩陣；report 列明 model；E1 精調後可升級 |
| **LoRA/QLoRA 時間太耐（CPU）** | 精調唔收貨 | 細數據（100–1k）+ 短 epoch；QLoRA 4-bit 減 memory；用 vLLM/SGLang 但冇 NVIDIA GPU 就 fallback MLX/llama.cpp |
| **veadk web 對「hello」空 tool call** | 偶發模型幻覺 | 無關 tracing；指令加「僅在需要時先 call tool」；E1 精調可改善 |
| **yfinance 限流/轉變** | 拉數據失敗 | `data/stores` 快取 + retry；或 switched 用讀 raw files |

**前置**：Docker Desktop（openviking/jaeger/otel-collector 容器）；Ollama（`nomic-embed-text`）；Python 3.11+ + `uv`；BytePlus/Ark key 放 `.env`（`MODEL_AGENT_API_KEY`）；（D5）vllm-mlx + MLX Qwen3-4B；（延伸 E1/E2）peft/unsloth/bnb + vLLM/SGLang。

---

## 10. Definition of Done

- [x] `docker compose up -d`（openviking + web + otel-collector + jaeger）一條尾出到答案 + tool call（D1 已達成）。
- [x] **Observability 端到端**：hello → Jaeger 見到 `fin_mate` service 3-span trace；`trace_all.py` 出到完整 bundle。
- [x] KnowledgeBase/LTM 全用 **OpenViking**（無 milvus/redis 引用，grep 驗證過）。
- [ ] 24 個 Tab 每個都有一項「用 VeADK 功能造嘅實作 / 實驗」可指（見 §4）。
- [ ] 九場仗：`experiments/*/report.md` 齊 + 有真實數字（見 §6，E1–E3 延伸）。
- [ ] **RAG 實驗室（D4/D5）**：策略邦 6 種 RAG + 自寫 recall/precision report；rerank 邦 RRF + 本地 LLM-rerank；cache 邦 Ark + vllm-mlx cached_input%/TTFT；三份都有 recommend。
- [ ] LoRA/QLoRA（E1）精調前/後 eval 分數 report；vLLM/SGLang（E2）引擎對照 report。
- [ ] 請求排隊/路由（E3）併發 1/5/20 下 P50/P95/吞吐 report + fallback 有 log。
- [ ] `make eval` gate 有效（改壞 prompt → fail）；`pytest` 全綠。
- [ ] `make demo` 由頭到尾可重現；`README.md` 有概念 → 檔案對應表。

---

*Last audit date: 2026-09-08 · 計劃 v2.2（RAG 實驗室三邦落地 D4/D5：6 RAG 策略邦 + RRF/本地 LLM-rerank 邦 + Ark/vllm-mlx cache 邦；排期 8→9 日，D6–D9 對返原 D5–D8）· 微調於實作中按實際情況更新。*