# FIN-MATE RAG 實驗室（D4 · 第一部分）

目的：用 **agentkit / veadk builtin RAG code** 為主（少寫自訂），比較 RAG pipeline 喺同一份 fin_kb 上嘅
**準確度（retrieval + answer-F1）、成本（USD）、latency（ms）**，全部可完整追蹤、可重現。

- 程式：`experiments/_lib.py`、`experiments/eval_metrics.py`、`experiments/rag_bench/strategies.py`、`experiments/rag_bench/run.py`、`experiments/rag_bench/rerank.py`（D5）
- 試題：`experiments/rag_bench/eval_set.py`（16 題 = 12 fact + 2 trap + 2 multi-hop，gold 直接對應 9 docs → **corpus reseed 後 `msft_overview` 冇咗 → D5 起用 `CURRENT_ITEMS` = 15 題**，f12 剔出）
- 跑法：`.venv/bin/python -m experiments.rag_bench.run --smoke`（4 題快試）；full run 去 `--out experiments/runs/<tag>`
- **agentic 已退役**（2026-09-08 決定，**結果保留**）：run set 唔再包含 agentic；單一細 KB 下 agent 冇 routing/多源價值，只燒 tokens+latency（見 §4 末同 REPORT §8）。新入 **hyde**。

---

## 0. 用咗幾多自己 code？

| 層面 | 用 veadk/agentkit builtin | 自訂（最少） |
|---|---|---|
| 連線 + KB | `KnowledgeBase(backend="openviking")`、`kb.search()`、`LoadKnowledgebaseTool` | `load_env()` / `build_kb(read_limit)`（每 pipe 各一 KB instance） |
| Agentic | `veadk.Agent(...)`、`google.adk.runners.Runner.run(...)`、`Event.usage_metadata`（真實 token）、OTLP tracer → Jaeger | `_build_agent()`（lean agent）＋ citation verifier |
| Retrieval | find = dense（L1 chunk embeddings）＋ L2 hydrate | `_terms()`（keyword 抽取）、`_sparse()`（OpenViking grep）、`_rrf()`、`_dedupe()`/`_pref()` |
| LLM | `AsyncArk responses.create`（`_lib.ark_complete`） | 個別 prompt（answer / judge / rewrite / router） |
| 平分 | — | `eval_metrics.py` + `run.py` reporter |

成個 lab 自訂 code ~3 個檔案，核心邏輯集中喺 `strategies.py`。

---

## 1. 模型同成本

- 六條 pipe **全部**用同一 `MODEL_PRIMARY`（seed-1-6-flash-250715）做 answer / judge / rewrite / router / agent — 一致先有得比。
- 價（官方依每 1M tokens）：**input ¥0.15 ≈ $0.021、output ¥1.5 ≈ $0.211、cached ¥0.03 ≈ $0.004**（`_lib.PRICES`）。
- agentic 嘅 token 數嚟自 `Event.usage_metadata`（真實數）；其他 pipe 嚟自 Responses API `usage`。

## 2. 六條 pipe

所有 pipe 共享嘅 retrieval channel 得兩款：
- **dense**：`kb.search(q, top_k)` → OpenViking find（over L1 chunk embeddings）＋ L2 hydrate（讀全文，`read_limit` 截斷）。
- **sparse**：`_sparse(kb, "kw1|kw2|kw3")` → OpenViking grep（keyword，掃全套 doc subtree），攞 `{uri, content}`。

每 pipe 用唔同 `read_limit` =「hydration 深度」（粗 vs 細，見 §3）。

| # | 名 | 流 | read_limit | k | 模型 stage |
|---|---|---|---|---|---|
| 1 | **naive** | find k=5 → 全量注入 → answer | 200（粗）| 5 | answer |
| 2 | **advanced** | find k=15 + grep 擴 query → dedupe → **score gate**（<0.35 就當無料注入） | 2000（細）| 15 | answer |
| 3 | **hybrid** | find k=15 + sparse grep → **RRF(k=60)** 融合 → 注入 top | 200 | 15 | answer |
| 4 | **corrective** | find k=5 → **LLM self-check** → 唔夠就 **rewrite** → re-find → 再唔得就 **skip 注入** | 1000 | 5 | judge + rewrite + judge2 + answer |
| 5 | **adaptive** | **LLM router**（SEARCH/SKIP）→ SKIP 就唔查 | 200 | 5 | router + answer |
| 6 | **agentic** 🚫退役 | veadk **Agent + Runner** + `LoadKnowledgebaseTool`（agent 自己決定捽幾多次、用邊 tool）＋ calc | 200 | 5 | agent loop（每次調用真實 usage） |
| 7 | **hyde** | **LLM 生成 hypothetical doc** → 用嗰段當 query 做 dense find → answer | 200 | 5 | hyde(生成) + answer |

> agentic 由 run set 移除（結果保留喺 REPORT）；**唔會再跑**。hyde 係新 type（D5），喺「唔 retest 舊 pipe」原則下單獨 run。

### 1）naive —— 生產 baseline
```
q ──> kb.search(q, top_k=5) ──> dense entries (find + hydrate@L2, read_limit=200)
        ──> context 全量注入 ──> MODEL_PRIMARY answer（要求 inline【KB:檔案名】+ ## 來源）
```
- 用 builtin 一條龍：`knowledgebase.search`。同 prod 個 agent 一個 retrieval 樣。
- 弱點：context 粗、冇去重（overview + 正文同一檔案可能同時出現）、冇 gate。

### 2）advanced —— 粗改細 + 擴 query + gate
```
q ──> kb.search(q, top_k=15)@read_limit=2000（細水化，多料）
   ──> grep(kw from q) 加 sparse 證據（grep_hits）──> dedupe by doc-prefix
   ──> gate: max dense score >= 0.35 或 有 grep hit 先注入，否則 context=""（答「KB 無資料」）
   ──> answer
```
- 新增咗：`read_limit=2000`（2000 字內 chapter 全文）、grep 擴展、score gate（防低分噪音入腦）。

### 3）hybrid —— dense + sparse 融合（RRF）
```
q ──> kb.search(q, top_k=15) （dense ranked list）
   ──> grep(kw) （sparse ranked list）
   ──> RRF: score(doc) = Σ 1/(RRF_K + rank)      (RRF_K=60)
   ──> top 去 dedupe ──> dense entries + 最高 RRF 嘅 grep snippets 注入 ──> answer
```
- 經典 lexical+dense 融合，唔使 train；trap 題 sparse 會搵到「dividend」等 keyword → 都有料可證「無資料」。

### 4）corrective —— 自己檢查、出錯重試
```
q ──> find k=5 ──> judge(q, ctx)  ──PASS──> inject ──> answer
                          └─CORRECT/FAIL─> rewrite(q)──> re-find(k=5)──> judge2
                                                    └─PASS─> inject
                                                    └─FAIL─> 唔注入 context（答「KB 無資料」，唔作）
```
- judge/rewrite 都係 `MODEL_PRIMARY`（統一）。最多 retry 一次，成本可控。

### 5）adaptive —— 先諗查唔查
```
q ──> router(q): SEARCH/SKIP ──SEARCH──> find k=5 ──> inject ──> answer
                         └────SKIP────> 無 retrieval ──> answer（純 model 答，無料）
```
- trap/dividend 類 router 應 SKIP；答 fact 時唔會 waste retrieval。

### 6）agentic 🚫 已退役（結果保留，唔再跑）

> **點解唔跑**：單一細 `fin_kb` 淨係得 `LoadKnowledgebaseTool` 一個 retrieval 動作，agentic 加嘅「自己決定查幾多次」
> 只係多咗 LLM 往返開銷，冇擴大 search action space → 實測 fact recall 0.75（低過 naive 0.964）＋每題 11.8s＋最貴。
> 只有「多源異構（多 KB / RDBMS / web / 工具 chain）」先 justify agent。以下方法論保留作記錄。

```
q ──> veadk.Agent(instruction=「每句 claim 標【KB:檔案名】/【CALC】，結尾 ## 來源」,
                  knowledgebase=fin_kb,  # → 自動掛 LoadKnowledgebaseTool
                  tools=[calc],
                  tracers=[OTLP → Jaeger])
   ──> google.adk.runners.Runner(agent).run(user_id, session_id, new_message=Content(parts=[Part(text=q)]))
         loop: agent 自己決定 → load_knowledgebase(...) / calc(...) → 再答
   ──> 每 event: is_final_response / get_function_calls / get_function_responses
        + 真實 usage_metadata（agentic 成本唔係估，係秤）
   ──> citation verifier：function_response 入面嘅 viking:// URI =「agent 實際睇過嘅 source」
        對返 answer 嘅【KB:…】markers → precision / falsified / coverage
```
- 冇 HITL、冇 web search（用戶決定暫緩），得 KB + calc 兩類 tool → 唔會亂上網。
- 出處自動帶埋：`LoadKnowledgebaseResponse` 會 serialize `metadata.uri` 畀 model → agent 有得引來源。

### 7）hyde —— HyDE（Hypothetical Document Embeddings）

```
q ──> LLM 生成一段「假設呢份報告點答呢條問題」嘅第 3 身研究段落（60–120 tokens）＝ hypothesis h
   ──> kb.search(h, top_k=5) @read_limit=200   （用 h 當 query 去 embed 返層搵）
   ──> dedupe ──> 全量注入 ──> answer
```
- **原理**：直接 query（keyword 少／同語料用詞唔近）embed 落去搵唔中；假設文句「像真報告」咁 embed，
  啱啱好撳中語料語境 → 改善 **query-document 語義 gap**（尤其多字合併表述、問題名詞同報告名詞唔同）。
- 純 **dense 單通道**（冇 grep/RRF），k=5、read_limit=200 同 naive 對齊 → 睇嘅就係「換 query」單一變數。
- 生成 stage 係 Ark 一個 call（max_tokens≈140）；定死 `思考/無來源標註`，唔好出埋 citation，分心。
- latency：+1 個 LLM 往返（~0.3–0.5s/題）。fail-safe：生成空 → fallback 原 query。

## 3. OpenViking L0/L1/L2 同「粗/細」

OpenViking 三層都係 **server-side parse + embed**，client 冇得自己揀 level：
| L | 用途 | 邊度 | pipe 用法 |
|---|---|---|---|
| L0 | abstract | `/content/abstract` | —（唔用） |
| L1 | overview chunk | `/content/overview` | `find` dense 檢索層（嵌入呢層） |
| L2 | 全文 read | `/content/read` | `hydrate`＝讀全文；`read_limit` 截斷 = 「粗/細」 |

所以：
- `read_limit=200` = 「粗」→ 每 chunk 最多 200 字（成本低、夠快、快答）。
- `read_limit=2000` = 「細」→ 章節全文（answer-F1 上限高、token 貴）。

## 4. Full trace 點讀（人肉 replay 每一步）

每次 run 出三層 artifact（`--out` 目錄）：

```
experiments/runs/<tag>/
├── run_meta.json            # model / prices / gate / rrf_k / items / 時間戳（重現 config）
├── <strategy>/info.json     # 嗰條 pipe 嘅 read_limit.k.desc
├── <strategy>/events.jsonl  # 全 item × 全 stage（每行一個事件）：
│                             {strategy,eid,category,stage,ts,ms,tokens{...},score,uris[],detail}
│                             stage = retrieve / gate / router / judge / rewrite / retry / answer / agent
├── <strategy>/<eid>/transcript.jsonl   # 逐 call replay：
│                             • 非 agentic：全 LLM call{msgs,text,prompt/completion/cached_tokens,ms}
│                             • agentic：Runner events{kind,final|function_call|function_response|llm,
│                                          parts,calls[{name,args}],responses[{name,response}],usage{}}
├── <strategy>/<eid>/answer.txt          # final answer（連【KB:…】markers + ## 來源）
└── <strategy>/report.md + SUMMARY.md    # 表：recall/prec/MRR/nDCG/F1/trap/cost/ms
```

**agentic 額外兩條線**（`agent` event 嘅 `detail.observer_delta`）：
1. `/api/v1/observer/retrieval` + `/api/v1/debug/vector/count`：跑前後快照 → 睇 agent 有冇真係捽過 verbose。
2. OTLP tracer → **Jaeger**（用 agent_build 同款），events 有 timestamp，可對返 Jaeger trace 時間窗。
3. 最後 `Agent` 自己有 session memory → `session_id=rag-<eid>`，可以跟返個 session 狀態。

### agentic pipe 實作注意（實測，2026-09-08）
- **每題一個 fresh subprocess**：veadk Agent + ADK Runner 喺同一進程連續跑多題會 hang / litellm
  「cannot schedule new futures after shutdown」；所以 run.py spawn `python -c`（內嵌已實證體）per item，
  `--agent-timeout`（預設 240s）硬殺。**Runner 嘅 sync generator 一定要喺無 active event loop 嘅環境行**
  （除 `asyncio.run(create_session)` 嗰下）；唔好用 `python -m agent_worker` 入口（實測會甩 litellm threadpool）。
- **`tracers=[]`**：`_build_agent` 唔用 `_build_local_otlp_tracer()`，OTel tracer 同 litellm 相撞甩 threadpool
  （對比舊規劃 tracers=OTLP，依實測為準）。
- **tokens budget 機制**：run.py `EST_TOKENS_PER_ITEM` 做跑前預查（over 500K → `BUDGET_SKIP` event），
  每題後用真實 usage 校正 `used_tokens`；agentic 排最後，食剩餘預算。
- **`seed-1-6-flash-250715` 兩坑**：(1) 預設 thinking=True 會燃燒 output 預算 →
  `ark_complete` 已加 `"thinking": {"type": "disabled"}`；(2) 答案 text 喺 `output[].content[].text`（part），
  唔係 `output_text` attribute → `_extract_text()` 讀。
- **agentic 嘅 uris 用 raw `viking://`**（由 load_knowledgebase function_response 抽出）先計到 recall/prec；
  `_cite` 驗證用 normalized 版，metric 用 raw 版。

## 5. Evaluation（算式）

Per item（resolve_gold 轉 URI prefix set 做 gold）：
- **recall@k / precision@k / MRR@k / nDCG@k**（k=5）：`eval_metrics.py`，全 prefix match。
- **answer-F1**：token overlap（`answer_f1(gold_text, answer)`）。
- **trap**：唔計 F1；評「有冇作」→ PASS 條件係答案出「KB 無資料 / 没有 / not found / 唔知」。
- **agentic citation verifier**：`cited`（markers 數）→ 對 accountant observed KB URIs（load_knowledgebase 返嚟嘅 viking://）match → `precision`、`falsified`（引用咗但 agent 無實際睇過 = **當 fail**）、`coverage`（有幾多句有標）、`calc_called`。

判別規則：
- **falsified citation 一票當 fail**（用戶定案）——即使 answer-F1 幾高。
- trap 唔肯講「無資料」= 當 fail（generate 出嚟）。

預期同 compare：
- naive baseline；advanced 應漲 F1（細資料）；hybrid 主要幫 trap（sparse 有據）+ 穩 recall；corrective 專救 query 差；adaptive 慳錢（SKIP 零 retrieval）；agentic 有真 tool-loop 成本同 citation 指標（其他 pipe 冇得睇）。

## 6. 點跑

```bash
cd projects/fin_mate
# 要嘅 env：MODEL_AGENT_API_KEY / MODEL_AGENT_API_BASE / MODEL_PRIMARY / DATABASE_OPENVIKING_API_KEY（.env 有）
# 快試（4 題）：
.venv/bin/python -m experiments.rag_bench.run --smoke
# 可 run 15 題（f12 剔出，見 REPORT caveat #8）×（現役 pipe）＝ naive,advanced,hybrid,corrective,adaptive,hyde：
.venv/bin/python -m experiments.rag_bench.run
# 淨單挑新 type（唔 retest 舊 pipe）：
.venv/bin/python -m experiments.rag_bench.run --only hyde --out experiments/runs/hyde_$(date +%y%m%d_%H%M) --max-tokens 150000
# D5 rerank lab（none/RRF/Qwen3 pointwise）＋ k×w sweep：
.venv/bin/python -m experiments.rag_bench.rerank --out experiments/runs/rerank_$(date +%y%m%d_%H%M) --max-tokens 150000
.venv/bin/python -m experiments.rag_bench.rerank --rrf-sweep
```
> `MODEL_AGENT_API_KEY` 已填（`.env`）；直接跑就係真 model（`seed-1-6-flash-250715`）。agentic 已退役唔會行；`--only agentic` 會 KeyError（已由 STRATS/dispatch 移除）。

## 7. 已知限制
- `read_limit`/`top_k` 每 pipe 分開 KB instance（compromise，因為 OpenViking read_limit 係 instance 級）。
- RRF 無 score scaling（統一 k=60）——已係最簡、可接受。
- agentic 已退役（結果保留）；相關注意（fresh subprocess、tracers=[]、raw uris）只係歷史記錄，唔再行。
- Local Rerank（D5）**已跑完**——`rerank.py` + `--rrf-sweep`；結論：冇幫助（REPORT §9）。
- **Token 計數陷阱**：`_emit()` 對 judge/rewrite/judge2/router 冇帶 `tokens` → 呢啲 stage 嘅用量淨係喺 `<eid>/transcript.jsonl`（trace），events.jsonl / `run.py used_tokens` 計唔到。REPORT §6 已由 transcript 全 call 修正：corrective 真係 **74,927**（唔係 events 淨計嘅 20,269）、adaptive **33,813**。寫喺 code 時注意 `_emit` 要帶 tokens。

## 8. 下一步

- **D5 rerank（✅ 已跑完，結果見 REPORT §9）**：固定 pool × {none, RRF(k=60), 本地 LLM-as-reranker}——**冇幫助**（none MRR@3=0.923 最高；RRF 0.910；Qwen3-4B 0.872）；只 run 新 type，冇 retest 舊 pipe。
- **HyDE（✅ 已跑，結果見 REPORT §10 vs naive 對照）**：recall 跌 0.077、answer-F1 升 0.026。
- 用 `events.jsonl` `ms` 去睇有冇 pipe 慢到唔合理（例：hybrid grep limit 大）。

## 9. D5 · Rerank Lab（rerank.py · 方法論）

目的：同一 **fixed candidate pool** 上比較 3 種「排序」，睇 top-of-list 質素有冇改善、代價幾多。程式 `experiments/rag_bench/rerank.py`。**✅ 已完成（2026-09-09）——結果數字同閱讀放 REPORT §9.1；下面方法論保留，加入實作筆記。**

> **實作筆記（跑嘅時候先發現）**：
> 1. **`strategies._rrf` 返 doc-prefix**（`_pref(u)` 為 key）——rerank「rrf」variant 如果照直用，`_ctx_selected` exact-match 唔上 chunk → ctx 空 → 全「KB 無資料」假答案（ansF1 0.039）。修正：`_pref_to_chunk()` 將每個 pref 展開返做 pool 入面該 doc 嘅真實 chunk uri → answer ctx 先有料（0.114）。main run hybrid 無呢個問題（佢嘅 ctx 唔係靠 rerank 單返回 list，係 `_ctx(entries, extra=grep-content)`）。
> 2. **corpus reseed**（REPORT caveat #8）：`msft_txt/` → `fin_kb/` 直出；`msft_overview` 消失 → **f12 剔出，`CURRENT_ITEMS` = 15 題**；`eval_set.TXT` 已更新。rerank / hyde 全部行 `CURRENT_ITEMS`。

### 9.1 Candidate pool（3 variant 共用同一 pool，淨係排序唔同）

```
per item:
  dense  = kb.search(q, top_k=15)          # find(L1 embeddings) + L2 hydrate@read_limit=200
  grep   = _sparse(kb, "kw1|kw2|kw3", limit≤20)       # OpenViking grep（keyword，掃全套 doc subtree）→ {uri, content}
  pool   = _dedupe(dense_uris + grep_uris) # doc-prefix 去重（同 eval metric 一致）→ ~15–25 件
```

### 9.2 三個 ranking variant

| variant | 排序做法 | 額外成本 |
|---|---|---|
| **none** | pool 原序（dense 15 先行、grep 補足）＝ rerank 前 baseline | $0 |
| **RRF** | **RRF(k=60)** 融合 dense+grep 兩個 ranked list（`strategies._rrf`）| $0 |
| **LLM** | **Qwen3-4B pointwise**：每個 candidate 獨立 score 0–3 → desc sort（tie 用原序）| $0（Ollama 本機）|

Rank ordering 只由以上方法決定；三條 variant 嘅「候選集合」完全一樣。

### 9.3 RRF —— 底層邏輯（揾最好權重）

$$Score(d)=\sum_{j\in\{\text{dense},\text{grep}\}} \frac{w_j}{k+r_j(d)}$$

- rank-based fusion：唔使 score normalization／calibration，dense score 同 grep hit 直接並排。
- **k 係投票曲線平滑常數**，唔係 channel 權重：細 k（1–10）極度偏袒榜首（#1 票超大）；大 k（60–100）拉平、深排位都有票（ensemble 味；classic RRF paper + Google 2024 RAG blog 都推 k=60）。
- 真正可 tune 嘅係 **每 list 權重 `w_j`**（sparse vs dense 信任度）同 **各列表 truncate 位**（我哋 dense=15 / grep≤20）。
- 揾最好權重（RRF 確定性、retrieve-only 即計、$0）：目標 **MRR@3 為主** + recall@5 做 constraint（唔准跌）；dev set 上掃 `k ∈ {1,10,20,40,60,80,100,200}` × `w ∈ {0.5,1,1.5,2}`；RRF 對 k 出名「鈍感」→ 攞 plateau 最細 k；grep 高 precision 低 recall ⇒ sparse 條 list 加權高啲係合理起點。`rerank.py --rrf-sweep` 出暖靴表。

### 9.4 本地 LLM-as-reranker（Qwen3-4B via Ollama）

- backend：**Ollama `qwen3:4b-instruct-2507-q4_K_M`**（已裝已 running，port 11434）；唔用 Ark（$0 本機）。
- 行 **native `/api/chat`**（唔係 `/v1/chat/completions`）：`{"model":..., "messages":[...], "stream":false, "think":false, "temperature":0, "options":{"num_predict":8}}`——`think:false` 係要緊嘅（Qwen3 預設 thinking 會出 reasoning，同 Ark seed-1-6 個坑同源）。
- prompt：「只回一個整數 0–3：0=無關 / 1=相關 / 2=間接關鍵 / 3=直接答到」+ query + candidate content（截 ~400 chars）。regex 抽 `\b[0-3]\b`，抽唔到 fallback 0；temp 0 → 可重現。
- 每題 ~pool 大小次 call（~15–25），sequential 每題 ~10–40s；token/latency 另計 `local_*` 欄，$ = 0。

### 9.5 metric 同 generate

- Ranking：**recall@3 / prec@3 / MRR@3 / nDCG@3（主）**＋ **@5（參考**，直接同 main run §4 表比；RRF 路徑 ≈ hybrid）。
- answer-F1：揀中嘅 **top-5** 組 ctx → `_ans_msgs` → Ark answer（multi-hop 要兩份 doc，top-3 會斷料）；trap 照行、照 `_trap_pass`。
- Latency：分「**local**（retrieve+rerank）」同「**Ark**（answer）」兩欄；LLM-variant 嘅 +Xs 就係 rerank 嘅時間懲罰。

### 9.6 Budget 同局部驗證

- scoring 全 $0（Ollama）；只有 answer 經 Ark ≈ 每題 1.2–1.5K → **獨立 budget 150K**（`--max-tokens 150000`，48 次 answer ≈ 75K 還有頭），唔扣 main run 嗰 500K。
- `--llm-stub`：mock reranker（確定性）驗 plumbing/metrics，唔打 Ollama；`--retrieve-only`：stub Ark，只驗 retrieval+scoring。

```bash
cd projects/fin_mate
.venv/bin/python -m experiments.rag_bench.rerank --smoke --llm-stub --retrieve-only   # plumbing（$0）
.venv/bin/python -m experiments.rag_bench.rerank --smoke                             # 4 題真跑
.venv/bin/python -m experiments.rag_bench.rerank --out experiments/runs/rerank_$(date +%y%m%d_%H%M) --max-tokens 150000
.venv/bin/python -m experiments.rag_bench.rerank --rrf-sweep                        # k×w 暖靴表（retrieve-only、$0）
```

### 9.7 結果（2026-09-09，15 題）

| variant | recall@3 | MRR@3 | answer-F1 | trap |
|---|---|---|---|---|
| none（pool 原序）| **0.962** | **0.923** | 0.111 | 2/2 |
| RRF（k=60，pref→chunk 修正後）| 0.923 | 0.910 | 0.114 | 2/2 |
| LLM（Qwen3-4B pointwise）| 0.923 | 0.872 | 0.108 | 2/2 |
| 對照 hybrid（main-run 重算）| 0.923 | 0.923 | 0.118 | 2/2 |

- **Rerank 冇輸贏過「唔 rerank」**；LLM-as-reranker 反而最差（+2.7s/題 local、$0，但 ranking 跌）。
- **RRF sweep** `k∈{10..200}×w∈{0.5..2}` 24 格全 plateau（MRR@3=0.910 / recall@5=0.962）→ 現行 k=60/w=1 已喺 plateau；細 pool（≤30 分片、8 doc）之下權重唔敏感。
- 詳細 + 對照表：REPORT §9.1。

## 10. D5 · HyDE（strategies.py `run_hyde` · 設計同狀態）

**狀態：✅ 已完成（2026-09-09）——15 題、49,974 Ark tokens（$0.0016）、0 err。結果：recall@5 0.962→0.885、MRR@5 0.744→0.769、answer-F1 0.112→**0.138**（同 naive 對照）。詳見 REPORT §10.1。**

| 設定 | 值 |
|---|---|
| 流程 | `q → LLM 生成 hypothesis h（60–120 tokens）→ kb.search(h, k=5)@read_limit=200 → dedupe → answer` |
| k / read_limit | 5 / 200 —— **同 naive 對齊**，變數淨係「換 query」 |
| 生成 LLM | `MODEL_PRIMARY` seed-1-6-flash（Ark），max_tokens≈140，trace 入 transcript；空 → fallback 原 query |
| 成本 | +1 個 Ark call/題（~0.3–0.5s）；est 每題 ~2.2K tokens |
| 預期 | 短 query／名詞唔對（如「Microsoft Cloud 突破 50B」）靠假設文补語境 → 睇 recall@5/F1 有冇升；trap 唔應該變差（假設文唔會突然有料） |

```bash
.venv/bin/python -m experiments.rag_bench.run --smoke --only hyde   # 快試 4 題
.venv/bin/python -m experiments.rag_bench.run --only hyde --out experiments/runs/hyde_$(date +%y%m%d_%H%M) --max-tokens 150000
```

## 11. D5 · 新 RAG 方法（HyDE+RRF / cross-encoder / LLM listwise · 方法論）

**狀態：✅ 已完成（2026-09-09）——三條各 15 題、各自獨立 ≤150K budget、0 err。詳見 REPORT §11.1。**
（env：`.venv` 補裝 `torch`(CPU) + `sentence-transformers` + `bge-reranker-v2-m3` ~2.2GB，先行到 `ce`。）

### 11.1 hyde_rrf（strategies.py `run_hyde_rrf`）——融合 hyde 召回 + RRF 排序

| 設定 | 值 |
|---|---|
| 流程 | `q → h=LLM hypothesis（跑法同 §10）→ 3-channel RRF([dense(q,15), dense(h,15), grep≤20], k=60)` → **top-5 RRF doc 各取 1 最佳分開** 組成 answer ctx → Ark answer |
| 同 §10 hyde 分別 | hyde 淨係 `dense(h, k=5)`，每回 h-lane；hyde_rrf 加返 q-lane + grep，並行融合三條 ranked list |
| ctx 修 BK（實測） | 初版把 q+h 兩 lane 共 ~30 個 dense entries 全文入 ctx → **11K tokens/題** 爆獨立 150K budget；改成「top-5 RRF prefix 各取 1 score 最高 integral entry」→ **3.2K/題**（48,702/15） |
| 同 hybrid 分別 | §9 hybrid ctx 係 `_ctx(entries_q, extra=grep)`（q-lane 全文）；hyde_rrf ctx 係 fused top-5 doc 各 1 段 |
| 結果 | recall@3 0.846→**0.923**（q-lane 救返），MRR@3 0.821（**低過 hybrid 0.923**），answer-F1 0.125（低過 hyde 0.138）。見 REPORT §11.1 |

```bash
.venv/bin/python -m experiments.rag_bench.run --smoke --only hyde_rrf
.venv/bin/python -m experiments.rag_bench.run --only hyde_rrf --out experiments/runs/hyde_rrf_$(date +%y%m%d_%H%M) --max-tokens 150000
```

### 11.2 ce（rerank.py `_rerank_order` → `_cross_encoder`）——cross-encoder pointwise

| 設定 | 值 |
|---|---|
| 模型 | 預設 `BAAI/bge-reranker-v2-m3`（multilingual，啱中英夾雜；`RERANK_CE_MODEL` env 可改）；CPU、lazy singleton（唔 run 就唔 load） |
| 入 | 同 §9 fixed pool（dense top-15 + grep ≤20 doc-prefix 去重），每 candidate 同 q 組 pair，`content[:400]` |
| 出 | `ce.predict(pairs, batch_size=16)` sigmoid 機率 → desc、tie 原序；**本機 CPU，無 token、$0、deterministic** |
| latency | 每題 ~2.2s（args run 實測 2,230 ms/題） |
| 結果 | MRR@3 0.872 **=點对 同 §9 LLM pointwise（0.872）**、快過佢（2,230 vs 2,855 ms）、無 prompt 風險；answer-F1 0.101（略低）。見 REPORT §11.1 |

```bash
.venv/bin/python -m experiments.rag_bench.rerank --smoke --only ce
.venv/bin/python -m experiments.rag_bench.rerank --only ce --out experiments/runs/rerank_ce_$(date +%y%m%d_%H%M) --max-tokens 150000
```

### 11.3 llm_listwise（rerank.py `_qwen_listwise`）——LLM 一次過排晒

| 設定 | 值 |
|---|---|
| 入 | 同一 pool；msg 列出 `[i] pref — content[:150]`，一次俾晒 |
| 出 | 要求模型輸出重新排序後嘅編號序列；parse `\d+` → 去重 → 未列出嘅按原序補尾；**parse fail → 原 pool 序 fallback** |
| 記分 | 唔行 pointwise——**每題 1 次 Ollama call**（實測 1,872 ms/題、8,665 local tokens）；scores 冇 calibrate |
| 結果 | MRR@3 0.833 **< pointwise 0.872**——~20 候選一次過排對 4B 模型太散；latency 換唔返排序質素。見 REPORT §11.1 |

```bash
.venv/bin/python -m experiments.rag_bench.rerank --smoke --only llm_listwise
.venv/bin/python -m experiments.rag_bench.rerank --only llm_listwise --out experiments/runs/rerank_llmlist_$(date +%y%m%d_%H%M) --max-tokens 150000
```