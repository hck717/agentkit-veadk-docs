# FIN-MATE — 總結（OVERALL SUMMARY）

> 一個 project 包晒 `references/veadk-agentkit-all.html` 嘅 24 個 Tab 概念：base agent → KB/RAG → 新聞情緒 → tool calling → eval → engine bench → observability → 安全 → multi-agent → structured output，全部用**官方 AgentKit SDK（veadk-python）** 砌出嚟、可量度、可重現。
> 呢份係最終整合：階段／產物／結果／決策／成本／點樣行，一頁睇晒。
> 其他文件係詳細版：`IMPLEMENTATION_PLAN.md`（計劃同排期）、`eval.md`、`observability.md`、`agentkit_studio.md`、`D7_SECURITY.md`、`experiments/METHODOLOGY.md`＋`RESULTS.md`＋`rag_bench/RAG_LAB.md`。

---

## 0. 一句話

**你問金融嘢 → Agent 用工具查新聞/計數 → KnowledgeBase RAG 查研報 → 情緒分析 → 出有根據嘅分析；每一層都有量度、有 gate、有 trace、有安全校驗。**

```
User 問題
  │  (injection input filter)
  ▼
Agent (veadk.LlmAgent, Ark seed-1-6-flash, model fallback)
  ├─ tools     read_news_file / fetch_news / calc        (role gate + HITL)
  ├─ KB RAG    OpenViking hybrid RRF → knowledgebase_query 【KB:uri】→ 范文
  ├─ 輸出      出分析＋【KB:】citation＋出碼
  │            (PII/secret output redact)
  ▼
Eval gate (34 golden) / Engine bench / OTel→Jaeger / 紅隊 sec-eval
```

---

## 1. 邊個階段做咗咩（work products）

| 階段 | 內容 | Artifact / 證明 | 核心結果 |
|---|---|---|---|
| **D1–D3 地基** | veadk agent build（`agent_build.py`）、KB（OpenViking `fin_kb`，auto-seed `data/kb/`）、STM sqlite（`data/stores/fin_mate.db`）、新聞工具（`tools/news_tools.py`：RSS/CSV＋情感字典）、`calc`、hybrid 生成 pipeline | `agent_build.py`（10 tools＋3 callbacks）、`tools/`、`data/` | agent 常規 build 成功、hybrid answer 帶 `【KB:】`＋`【CALC】` marker |
| **D4–D5 RAG 實驗室** | 6→7 種檢索策略（naive/advanced/hybrid/corrective/adaptive/agentic†/hyde/hyde_rrf）×16→15 題，全 trace＋log＋`eval_metrics.py`；Rerank Lab（none/RRF/Qwen3-4B pointwise/cross-encoder/LLM listwise）；HyDE；新方法 | `experiments/rag_bench/`（strategies.py／rerank.py／eval_set.py／REPORT_...md）、`experiments/runs/`（每個 strategy 有 events.jsonl＋transcript.jsonl） | 見 §3.1；「檢索已到天花板，樽頸喺答」 |
| **D6 Eval + Engine** | 34 條 golden（6 sets）× deterministic evaluator（exact/f1/trap/tool_call/sentiment）＋ 1 個本地 LLM judge；regression gate vs baseline（跌 3% → FAIL）；engine bench（Ark vs Ollama） | `eval/`（run_eval.py／gate.py／baseline.json／reports）、`eval.md`、`experiments/engine_bench/` | 26/34（0.713 exact）；baseline lock 260909_2254；bench 見 §3.3 |
| **工具／外圍** | Studio 本地 runbook＋local patch；budget 計數；docker 全套（web/openviking/otel/jaeger） | `agentkit_studio.md`、`studio_local_patch.py`（冚冚全 7 endpoint 200）、`budget.py`、`docker-compose.yml` | Studio 8001 起樹 |
| **Observability** | 三層 trace（stage events / transcript / OTLP span）+ OpenViking observer + `scripts/trace_all.py` 一鍵打包 | `observability.md`、`observability/observability-<ts>/` | `make obs` 收 7 個源 |
| **D7 安全＋多 agent** | `security/`（filters/auth/gate/hooks/self_test）＋ `make sec-eval`（42/42）；`multi_agent.py`（SequentialAgent research→risk）＋ `demo/`；`schema_bench`（有無 output_schema 對比） | `D7_SECURITY.md`、`SECURITY_GATEWAYS_METHODOLOGY.md`（root）、`experiments/schema_bench/`、`eval/golden_datasets/security/` | security 42/42＋block-policy OK；schema 100%/100%；risk JSON 驗證 PASS |

† agentic 戰略：評測後**退役**（§3.1 點解），但結果有保留喺 REPORT 做對照。

---

## 2. 架構同關鍵選型

| 啲咩 | 揀咗 | 點解 |
|---|---|---|
| 框架 | **veadk-python**（AgentKit 官方 SDK，1.1.9；LiteLLM 底） | 一次過包 Agent/Runner/Tools/Memory/KB/Structured/多 Agent/Tracing/CLI/Studio——唔自建 framework |
| 主模型 | Ark **`seed-1-6-flash-250715`**（`MODEL_PRIMARY`）＋`MODEL_BACKUP=250615` fallback | tool-calling 可靠；全部實驗同一模型，結果可比 |
| KB | 自架 **OpenViking** `:1933`（docker，fin_kb，`nomic-embed-text` dim 768，server 端 parse→L0/1/2→embed→search） | 零 cloud 帳單；取代 Milvus/VikingDB-cloud |
| 記憶 | STM=sqlite；LTM=OpenViking（session+長期） | veadk builtin |
| 工具 | 純 function（type hint+docstring 自動 FunctionTool）＋ builtin web/run_code/coding ＋自建 `fetch_news/read_news_file/calc` | 唔寫 registry |
| RAG production pick | **hybrid（dense k=15 + sparse grep → RRF k=60）**，`read_limit` instance 級，GATE=0.35 | 世界上最好 MRR@5 0.929 同最高 answer-F1 |
| 安全 | rules-only filter（零 LLM）＋token auth＋3 級 role allowlist＋3 個 ADK callback hook | deterministic、可測攔截率、零成本 |
| Observability | OTel→Jaeger＋OpenViking observer＋transcript | `make obs` 一鍵 |

---

## 3. 結果（全部係真 model live run）

### 3.1 RAG 實驗室（D4：6 pipes × 16 題；D5：new methods ×15 題）

| pipe | recall@5 | prec@5 | MRR@5 | answer-F1 | trap | ms/題 |
|---|---|---|---|---|---|---|
| naive（prod baseline） | 0.964 | 0.418 | 0.762 | 0.109 | 2/2 | 1,576 |
| advanced | 0.964 | 0.214 | 0.762 | 0.105 | 1/2 | 1,814 |
| **hybrid（production pick）** | **0.964** | 0.214 | **0.929** | **0.127** | 2/2 | 1,754 |
| corrective | 0.607 | 0.287 | 0.524 | 0.077 | 1/2 | 1,354 |
| adaptive | 0.964 | 0.418 | 0.762 | 0.112 | 2/2 | 2,079 |
| agentic（已退役） | 0.750 | 0.500 | 0.494 | 0.056 | 2/2 | 11,810 |

- **Rerank Lab（D5）**：RRF 同 Qwen3-4B pointwise / cross-encoder / LLM listwise 喺呢個細枯 KB **冇實證幫助**（rerank 3 variant 各 ~30K token budget、0 error）。
- **HyDE**：recall↔answer-F1 trade-off（提升 recall 但 F1 唔升），最終都係 hybrid 收復尾。

### 3.2 關鍵結論（點解揀 hybrid）

1. 檢索已到天花板——naive/advanced/hybrid/adaptive 全部 recall@5=0.964，唯一缺嘅係 m1 跨兩份 doc；樽頸喺「**答**」，唔喺「搵」。
2. Corrective 反而拖矮（recall 0.964→0.607）——LLM 自評「無料」→re-write 走錯方向。**「檢測唔到」等於倒頭虧**。
3. Agentic prec@5 最高（0.5）但 recall 0.75、11.8s/題（~7×）、最貴、citation 有 falsified 3 個——**細 KB 冇 routing/多源價值**→退役。

### 3.3 Engine Bench（D6：12 prompts × iter 10，concurrency 1，全 live）

| engine | TTFT p50 | TTFT p95 | mean total | tok/s | usd |
|---|---|---|---|---|---|
| Ollama qwen3:4b（local，$0） | 49 ms | 65 ms | 4,846 ms | 27.2 | $0.0024 | 
| Ark seed-1-6-flash | 172 ms | 479 ms | 932 ms | 121.4 | $0.0015 |

→ **雲勝**：TTFT 慢 3.5× 但吞吐 4.5×、總時間 ~5× 快、p95 可控；成本其實同級或更低。本地引擎留做 fallback／延伸（vLLM/SGLang + LoRA）。

### 3.4 Eval 回歸 gate（D6，34 records，baseline lock `260909_2254`，margin 3%）

| set | n | score | pass | 備註 |
|---|---|---|---|---|
| fact_single | 11 | 0.164 | 3/11 | **已知最弱**：單事實 F1 低（屬「答」樽頸，見 §3.2） |
| fact_multi | 4 | 1.000 | 4/4 | 多跳＋trap（「無資料」）全 PASS |
| calc_expr | 5 | 1.000 | 5/5 | tool call 真執行 |
| news_extract | 3 | 1.000 | 3/3 | read_news_file 抽 row |
| sent_3way / sent_score | 6 / 5 | 1.000 | 11/11 | 情感字典 |
| **overall** | 34 | **0.729** | **26/34** | exact_mean 0.713；judge 1/1；$0.0020/run |

> `make eval` 係 CI：跑完對 baseline，跌 3% 即 exit 1。

### 3.5 Structured output（D7 schema_bench：8 題 × 3 iter × plain/schema）

| variant | n | valid | parse | field_rate | usd |
|---|---|---|---|---|---|
| plain（淨 prompt） | 24 | 100% | 100% | 100% | $0.0008 |
| **schema（Ark json_schema strict）** | 24 | 100% | 100% | 100% | $0.0007 |

> 呢個 task 兩邊都已經 100%——證明 schema 唔會累贅、仲平啲；對弱 model 或者合約界線重要（risk_agent 用佢迫樣 `{company, risk_level, score, reasons[], sources[]}`）。

### 3.6 安全紅隊（D7 sec-eval，全 deterministic）

| set | n | 攔截率 |
|---|---|---|
| injection | 15 | 100%（6 families） |
| pii | 10 | 100% |
| secrets | 7 | 100% |
| authz | 10 | 100%（role×tool 越權矩陣） |
| **block-policy** | — | **所有越權 call 全 block：OK** |

---

## 4. D7 安全 + Multi-agent

- **安全層**：`security/`（39 條 regex：injection 6 families＋PII 5＋secret 9）。
  三條 hook 全掛到 `agent_build.py`：`before_model_callback=input_injection_filter`、
  `after_model_callback=output_pii_filter`、`before_tool_callback=[tool_security_gate, human_gate]`；
  身份用 `.env` `FINMATE_TOKENS` → `authenticate()` → role contextvar → default-deny 矩陣。
  完整方法論：`projects/../SECURITY_GATEWAYS_METHODOLOGY.md`（root）。
- **Multi-agent**：`multi_agent.py` 用 `veadk.agents.SequentialAgent` 串 **research_agent（真實工具：read_news_file/calc/KB）→ risk_agent（output_schema）**，
  `google.adk.runners.Runner`＋InMemorySessionService；`make demo` 一條龍出到**已驗證嘅風險 JSON**；
  `--role viewer` 實測會啱新聞 tool，正確墮 KB fallback（role gate 生效）。
- **A2A 概念**：而家版 sub-agent 用本地 `SequentialAgent`（共享 session 已做到「委派」）；
  要變真 A2A 只要將 sub-agents 換做 `veadk.a2a.RemoteVeAgent`＋`ve_a2a_server`＋`A2AAuthMiddleware`（reference `veadk-agentkit-gateway.md` §B.3 有決策樹）。

---

## 5. Observability / Studio / 成本

- **Observability**：三層 trace 全有——stage events（`runs/*/events.jsonl`）、full transcript（`transcript.jsonl`，逐 LLM call replay）、OTLP span（Jaeger `:16686`）；`make obs` 打包 7 個源（OpenViking `/api/v1/observer/*`＋containers 等）。
- **Studio**：本機 `veadk studio`（:8001）runbook＋`studio_local_patch.py`（冚冚全 7 endpoint→200）；cloud tab 用 `.env` ACCESS/SECRET。
- **成本意識**：`budget.py`；RAG Lab 受 token budget（≤500K，D4 實耗 408,174，$0.011）、engine/eval/schema 各 ~$0.002/run。**真實成本全計 $0 開機器錢**（自架 OpenViking＋本地 Ollama＋Ark pay-per-token，最貴 agentic 都係 $0.0023/題）。

---

## 6. 點樣行（cheatsheet）

```bash
cd projects/fin_mate
make eval          # 34 golden 回歸 gate（exit 0/1）
make eval-lock     # 錄 baseline（大改 prompt 先做）
make eval-qa       # 只 QA、no judge
make bench         # Ark vs Ollama engine bench → report.md
make sec-eval      # security self-test + 42/42 紅隊（越權全 block 先綠）
make schema-bench  # plain vs output_schema → report.md
make demo          # SequentialAgent research→risk demo（admin role）
make obs           # 一鍵收 trace/log/observability bundle
```

逐份 doc 對應：`IMPLEMENTATION_PLAN.md`（計劃）／`eval.md`（結果面 gate）／
`experiments/METHODOLOGY.md`（方法論）＋`RESULTS.md`（結果）＋`rag_bench/RAG_LAB.md`（檢索面 bench）／
`observability.md`／`agentkit_studio.md`／`D7_SECURITY.md`＋root `SECURITY_GATEWAYS_METHODOLOGY.md`。

---

## 7. 已知弱點／後續

1. **fact_single answer-F1 低（3/11）**：檢索已逼頂，樽頸喺「答」——下一步係答題 prompt／檢證（不用再堆 retrieval strategies）。
2. **corrective / agentic 喺細 KB 冇價值**——要再試先要更大、多源 KB（multi-source 先有 routing 意義）。
3. **A2A 只到「概念」**：真跨進程／跨語言 agent card＋auth middleware 未開。
4. **Security auth 係 demo token**：上線要 hash/store/JWT（見 root SECURITY_GATEWAYS_METHODOLOGY.md §A.4）。
5. **延伸（E1–E3 未做）**：LoRA/QLoRA fine-tune＋vLLM/SGLang serve＋請求排隊／路由——接口已留（`experiments/_lib.py`、`engine_bench` adapter pattern）。