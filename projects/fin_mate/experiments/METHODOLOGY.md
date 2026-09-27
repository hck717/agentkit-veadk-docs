# FIN-MATE 研究方法論總覽（METHODOLOGY.md）

> 本文件係 **RAG 實驗室＋Rerank Lab＋Engine Bench＋Eval/Regression Gate** 全部方法論嘅單一權威來源。
> 對應結果數字統一放喺 [RESULTS.md](RESULTS.md)。逐單實驗嘅執行細節保留喺 `rag_bench/RAG_LAB.md`、`rag_bench/REPORT_full_260908_1551.md`、`engine_bench/`、`eval.md`。
> 核心原則（D4 定案）：**少自己 code、多用 veadk/agentkit builtin**；全部 run 可完整追蹤、可重現、受 token 預算約束。

---

## 0. 總體框架（三層）

```
[1] RAG 實驗室（D4-D5）         比較 7 種「檢索策略」（retrieval/查詢策略）   → recall/MRR/nDCG/answer-F1/成本/時延
       └─ 發現：retrieval 已到頂、樽頸喺「答」→
[2] Rerank Lab + 新 RAG 方法（D5）比較「排序」同一 pool（RRF/LLM pointwise/cross-encoder/LLM listwise）
                                        ＋「換 query」（HyDE、HyDE+RRF）
       └─ 發現：排序冇幫助、HyDE 係 trade-off → 收窄到 hybrid 做 production pick
[3] Engine + Regression（D6）    benchmark 引擎（Ollama vs Ark）＋ 用 34 條 golden 做全 pipeline 回歸 gate
       → make eval / make bench 一鍵
```

每層嘅「被測物」唔同，但**共享**：同一 KB（OpenViking `fin_kb`）、同一模型（`seed-1-6-flash-250715`）、同一套 metric（`eval_metrics.py`）、同一成本模型（`_lib.PRICES`）。

---

## 1. 測試集（`experiments/rag_bench/eval_set.py`）

### 1.1 構成（16 → 15 題）

| 類別 | 數 | eid | 結構 |
|---|---|---|---|
| fact | 12 | f1–f12 | 單一問題對應 1 份 doc（SR 研報 / 財報 call） |
| trap | 2 | t1/t2 | **KB 無據**（股息歷史、日本搜尋份額），gold =「KB 無資料」，評「有冇作」 |
| multi_hop | 2 | m1/m2 | 要**跨兩份 doc**（m1＝Barclays+Deutsche）先答到 |

- 題庫對應 **8 份文件**（Deutsche F2Q / Mizuho / China Renaissance / DeMatteo / Barclays E7 / Wells Fargo E7 / EC1 舊 call / EC2 F2Q26 call）。
- **corpus reseed（2026-09-08 run 期間）**：`msft_txt/` 路由剷走、`msft_overview` 消失 → `msft_overview` 題 f12 再冇 gold 對應 → **D5 起 `CURRENT_ITEMS` = 15 題**（f12 剔出），`eval_set.TXT` 已更新。RAG main run（D4）16 題數字保留（當時 overview 仍存在）。

### 1.2 Gold 格式（唔 hardcode URI）

每題 gold 兩部分：
1. **gold_docs**（filename list）→ `resolve_gold()` 對 `all_doc_uris()`（跑時用 OpenViking fs/tree probe 一次 map filename → doc folder URI prefix）轉成 **URI-prefix set**。
2. **gold 文字答案**（一句）。

> `all_doc_uris()` 唔 hardcode：DB folder 名帶 hash，reseed 會變；每一 run 開頭 probe 一次，之後整個 run 共用以保持自洽。

### 1.3 相關判定

相關 = **prefix match**：`rel(u) = u.startswith(任一 gold prefix)`。同一 doc 嘅唔同分片全部算相關（呢個特性令本試行 nDCG 可 >1，見 §6.6）。

---

## 2. 語料後端（OpenViking）同「粗/細」

點樣同 OpenViking 交收（全部 server-side parse + embed，client 唔可以自揀 level）：

| L | 用途 | endpoint | RAG 用法 |
|---|---|---|---|
| L0 | abstract | `/content/abstract` | 唔用 |
| L1 | overview chunk | `/content/overview` | `find` dense 檢索層（嵌入呢層） |
| L2 | 全文 read | `/content/read` | `hydrate`＝讀全文；`read_limit` 截斷＝「粗/細」 |

- `read_limit=200` = 粗（快、平、快答）；`read_limit=2000` = 細（章節全文、answer-F1 上限高、token 貴）。
- **`read_limit` 係 instance 級** → 每條 pipe 各自 `_kb(read_limit)` 一個 KB instance（`strategies._kb` 按 read_limit cache）。
- 兩個 retrieval channel：
  - **dense**：`kb.search(q, top_k)` → OpenViking find（L1 chunk embeddings）＋ L2 hydrate。
  - **sparse**：`_sparse(kb, "kw1|kw2|kw3", limit)` → OpenViking grep（關鍵字，掃全套 doc subtree）→ `{uri, content}`。
- `_dedupe()`：按 **doc-prefix**（`_pref(u)`）去重，同 eval metric 一致。

---

## 3. RAG strategies（`strategies.py`）

### 3.1 config 總表

| # | pipe | flow 摘要 | read_limit | k | 額外 LLM stage |
|---|---|---|---|---|---|
| 1 | naive | find k=5 → 全量注入 → answer | 200 | 5 | answer |
| 2 | advanced | find k=15 + grep 擴 query → dedupe → **score gate 0.35**（低→當無料） | 2000 | 15 | answer |
| 3 | **hybrid** | find k=15 + sparse grep → **RRF(k=60)** 融合 → 注入 top | 200 | 15 | answer |
| 4 | corrective | find k=5 → LLM self-check → rewrite → re-find → 再差 **skip 注入** | 1000 | 5 | judge + rewrite + judge2 + answer |
| 5 | adaptive | LLM router（SEARCH/SKIP）→ SKIP 唔查 | 200 | 5 | router + answer |
| 6 | agentic 🚫退役 | veadk Agent + Runner + `LoadKnowledgebaseTool`（agent 自己捽 retrieval）＋ calc | 200 | 5 | agent loop（真 usage） |
| 7 | hyde | LLM 生成 hypothesis → 當 query dense find → answer | 200 | 5 | hyde(生成) + answer |
| 8 | hyde_rrf | hypothesis → **3-channel RRF**(dense_q + dense_h + grep) → top-5 各取 1 → answer | 200 | 15 | hyde(生成) + answer |

**退役決定（用戶定案，2026-09-08）**：agentic 由 run set 移除（新 pipe = hyde）。理由：單一細 `fin_kb` 淨係得 `LoadKnowledgebaseTool` 一個 retrieval 動作，agentic 加嘅「自己決定查幾多次」只係多 LLM 往返開銷，冇擴大 search action space → 實測唔值（見 RESULTS §2.3）。當多源異構（多 KB / RDBMS / web / 工具 chain）先重新上。

### 3.2 每條 pipe 嘅 method

**1）naive —— 生產 baseline**
```
q → kb.search(q, top_k=5) [dense L1 find + L2 hydrate@200] → 全量注入 → MODEL_PRIMARY answer
```
- 同 prod agent 一個 retrieval 樣；弱點：context 粗、冇去重、冇 gate。

**2）advanced —— 粗改細 + 擴 + gate**
```
q → kb.search(k=15)@read_limit=2000 → grep(kw) 加 sparse evidence → dedupe
   → gate: max dense score ≥ 0.35 或有 grep hit 先注入，否則 context="" → answer
```

**3）hybrid —— dense+sparse RRF 融合**
```
q → kb.search(k=15) [dense] + grep(kw≤3) [sparse]
   → RRF: score(doc) = Σ_j 1/(RRF_K + rank_j), RRF_K=60
   → top dedupe → dense entries + 最高 RRF 嘅 grep snippets 注入 → answer
```
- rank-based fusion，唔使 score normalization；`GATE=0.35` 低過 threshold 唔入 answer。

**4）corrective —— 自檢重試**
```
q → find k=5 → judge(q, ctx) ─PASS─→ inject → answer
                       └CORRECT/FAIL→ rewrite(q) → re-find(k=5) → judge2
                                                └PASS→ inject
                                                └FAIL→ skip 注入（答「KB 無資料」）
```

**5）adaptive —— 先諗查唔查**
```
q → router(q): SEARCH/SKIP ─SEARCH─→ find k=5 → inject → answer
                            └SKIP─→ 無 retrieval → answer（純 model 答）
```

**6）agentic ——（退役，method 保留）**
```
q → veadk.Agent(instruction=「每句 claim 標【KB:檔名】/【CALC】, 結尾 ## 來源」, knowledgebase=fin_kb,
               tools=[calc], tracers=[])
   → google.adk.runners.Runner(agent).run(user_id, session_id, new_message=...)
   → 每 event: is_final_response / get_function_calls / get_function_responses + 真 usage_metadata
   → citation verifier: 對 load_knowledgebase 實際返過嘅 viking:// URI
```
執行注意（實測）：每題 **fresh subprocess**（`python -c` 內嵌體，`--agent-timeout 240s` 硬殺）；`tracers=[]`（OTel 同 litellm 相撞）；sync Runner generator 要喺無 active event loop 環境行。

**7）hyde（D5）**
```
q → LLM 生成 hypothesis h（60–120 tokens，MODEL_PRIMARY，max_tokens≈140）+ 1 Ark call
   → kb.search(h, k=5)@read_limit=200 → dedupe → 全量注入 → answer
```
- 與 naive **同 k / read_limit**（5/200）→ 單一變數＝「換 query」。生成空 → fallback 原 query（fail-safe）。

**8）hyde_rrf（D5 §11）**
```
q → h=LLM hypothesis → 3-channel RRF([dense(q,15), dense(h,15), grep≤20], k=60)
   → top-5 RRF doc 各取 1 最佳分片 → answer
```
- ctx 限制（實測）：初版兩 lane 全文直塞 → 11K tokens/題爆預算；改「top-5 RRF prefix 各取 1 score 最高 integral entry」→ 3.2K/題。

---

## 4. Rerank Lab（`rerank.py`）

### 4.1 Fixed pool（3+ variant 共用，淨係排序唔同）

```
per item:
  dense = kb.search(q, top_k=15)  # find(L1) + hydrate@200
  grep  = _sparse(kb, "kw1|kw2|kw3", limit≤20)
  pool  = _dedupe(dense_uris + grep_uris)   # doc-prefix 去重 → ~15–25 候選
```

### 4.2 Ranking variant

| variant | 做法 | 額外成本 |
|---|---|---|
| none | pool 原序（dense 15 先行、grep 補）＝ rerank 前 baseline | $0 |
| RRF | `_rrf([dense, grep], k=60)` | $0 |
| llm（pointwise） | **Qwen3-4B** 每個 candidate 獨立 score 0–3 → desc sort（tie 原序） | $0（Ollama 本機）|
| ce（§11） | **cross-encoder** `BAAI/bge-reranker-v2-m3` sigmoid → desc | $0（CPU 本機）|
| llm_listwise（§11） | Qwen3-4B 一次過排晒（`[i] pref — content[:150]`）→ 編號序；parse fail → 原序 | $0（Ollama 本機）|

### 4.3 RRF 底層

$$Score(d)=\sum_{j\in\{\text{dense},\text{grep}\}} \frac{w_j}{k+r_j(d)}$$

- k 係投票平滑常數（細 k 偏袒榜首、大 k 拉平），唔係 channel 權重；真正可 tune 係 `w_j` 同列表 truncate 位。
- `--rrf-sweep` 掃 `k∈{10,20,40,60,100,200} × w∈{0.5,1,1.5,2}`（retrieve-only、$0），以 **MRR@3 主 + recall@5 constraint** 揾 plateau 最細 k。

### 4.4 本地 LLM-as-reranker（Qwen3-4B via Ollama）

- Ollama `qwen3:4b-instruct-2507-q4_K_M`（port 11434）；**native `/api/chat`**（非 OpenAI compat）：`{"model":…,"messages":[…],"stream":false,"think":false,"temperature":0,"options":{"num_predict":8}}`。
- `think:false` 係要緊（Qwen3 預設 thinking 出 reasoning，同 Ark seed-1-6 個坑同源）。
- prompt：「只回一個整數 0–3：0=無關 /1=相關 /2=間接關鍵 /3=直接答到」+ query + candidate content[:400]；regex 抽 `\b[0-3]\b`，抽唔到 fallback 0；temp 0 → 可重現。
- 每題 ~pool 大小次 call（~15–25），sequential。

### 4.5 ce（cross-encoder）

- `bge-reranker-v2-m3`（multilingual，啱中英夾雜）、CPU、lazy singleton（唔 run 唔 load）；`predict(pairs, batch_size=16)` sigmoid → desc、tie 原序。
- 無 token、$0、deterministic；每題 ~2.2s。

### 4.6 llm_listwise

- 每題 **1 次** Ollama call（vs pointwise ~25 次）；輸出編號序 parse `\d+` → 去重 → 未列出補尾；parse fail → 原 pool 序。
- 唔行 pointwise——scores 冇 calibrate。

### 4.7 評測設定

- Ranking：**@3 主（recall/prec/MRR/nDCG）**＋ **@5 參考**（同 main run 表比；RRF 路徑 ≈ hybrid）。
- answer-F1：揀中嘅 **top-5** 組 ctx → Ark answer（multi-hop 要兩份 doc）；trap 照行。
- Latency 分「**local**（retrieve+rerank）」同「**Ark**（answer）」兩欄。
- Budget：scoring 全 $0，answer 經 Ark ≈ 1.2–1.5K/題 → **獨立 150K** budget（唔扣 main run 500K）。
- Stub 驗證：`--llm-stub`（mock reranker）、`--retrieve-only`（stub Ark）——驗 plumbing/metrics 唔打真服務。

---

## 5. Metrics（`eval_metrics.py`，公式）

共通：`gold` = doc 級 URI-prefix set；`retrieved` = 有序 top-k URIs（main run k=5；rerank 主 k=3）。

```math
recall@k    = |{g ∈ gold : ∃u∈top_k, u startswith g}| / |gold|
precision@k = #{u∈top_k : rel(u)} / k
MRR@k       = max_{i≤k} rel(u_i) / i          （冇命中=0）
DCG         = Σ_{i≤k} rel(u_i)/log2(i+1);  nDCG = DCG/IDCG
answer_F1   = 2·P·R/(P+R);  P、R 用 lowercase-alphanumeric token bag overlap
```

- **answer-F1 唔係事實命中**：中英混合句法、同義字、簡寫都扣分 → 全場 <0.13 **唔等於答錯**。判事實對錯要用 LLM-judge（D6 eval 先上）。
- **trap PASS**：答案字面含 `{KB 無資料, 没有, not found, 唔知}` 就算過；語義拒絕但字面唔入 lexicons → 假 FAIL。
- **citation verifier（agentic only）**：數 `【KB:】` markers（cited）→ 對 `load_knowledgebase` 實際返過嘅 viking:// URIs → `precision`（引用啱嘅比例）、**`falsified`**（引用咗但 agent 冇實際睇過 = **一票 fail**）、`coverage`（幾多句有標）、`calc_called`。
- **判定定案（用戶）**：falsified citation 一票當 fail；trap 唔肯講「無資料」= fail。

### 5.1 nDCG 點解可 >1（caveat）

`_rel` 用 prefix/token-overlap 判相關：同一 doc 嘅多份分片全部計相關，`dcg` 可以超過理想 `IDCG`（IDCG 假設每個 gold doc 只佔一個相關位）→ agentic fact nDCG 1.459 係 metric 特性，**唔係超越理想排序**；MRR/prec/recall 唔受影響。

---

## 6. 成本與預算模型

- 價（官方 per 1M tokens）：**input ¥0.15 ≈ $0.021、output ¥1.5 ≈ $0.211、cached ¥0.03 ≈ $0.004**（`_lib.PRICES`）。
- 計法：`usd = (prompt−cached)·0.021 + cached·0.004 + completion·0.211`（/1e6）。
- `estimate_tokens(chars) = (chars+3)//4`（CJK 約 4 字 = 1 token；streaming/不齊 usage 時 fallback 用）。
- **Token budget**：main run 500K：`EST_TOKENS_PER_ITEM` 跑前預查，over 寫 `BUDGET_SKIP`；每題後用真 usage 校正 `used_tokens`；agentic 排最後食剩餘。rerank/hyde/新方法各自獨立 ≤150K。
- **token 計數陷阱（重要）**：`events.jsonl` 淨喺 answer stage 帶 `tokens`；judge/rewrite/router 淨係喺 `<eid>/transcript.jsonl`（全 call LLM trace）→ 正確做法係**由 transcript 全 call 重計**（corrective 20,269 → **74,927**；adaptive → **33,813**）。RESULT.md §2.5 係修正後數字。
- **Ark `seed-1-6-flash-250715` 兩坑**：(1) 預設 `thinking=True` 燃燒 output 預算 → `ark_complete` 一律 `"thinking":{"type":"disabled"}`；(2) 答案 text 喺 `output[].content[].text`（part）而唔係 `output_text` → `_extract_text()` 讀。

---

## 7. Engine bench（`engine_bench/run.py`，D6）

### 7.1 設計

- **prompts**：12 條 = 6 golden sets（qa/fact_single、qa/fact_multi、tool_call/calc_expr、tool_call/news_extract、sentiment/sent_3way、sentiment/sent_score）每 set 抽 2（`random.Random(seed=7)`，deterministic）；QA 用 golden `context` inline（**唔行 KB**，獨立量引擎）。
- **迭代**：concurrency 1、`ITER=10` → 每 engine 120 個 measurements；逐條 append 落 `measurements_{ollama,ark}.jsonl`（**可 resume**：已有 10 條嘅 prompt 自動 skip）。
- **models**：`qwen3:4b-instruct-2507-q4_K_M`（Ollama :11434）vs `seed-1-6-flash-250715`（Ark ap-southeast）。

### 7.2 被量測數

| metric | Ollama | Ark |
|---|---|---|
| **TTFT** | native `/api/chat` 嘅 `prompt_eval_duration`（ns→ms，首 eval）| `responses.create(stream=True)` 第一個 `response.content_part.delta`/`response.output_text.delta` 事件（唔計 `output_token.usage`）|
| **total** | wall-clock (perf_counter) | `response.completed` 事件時間 |
| **throughput** | `eval_count / eval_duration`（native 量度）| (prompt+completion)/total；usage 由 `response.completed.response.usage` 攞，唔齊 → `estimate_tokens` fallback |
| **定數** | 每 round `num_predict 128` | `max_output_tokens 128`、`thinking disabled`、temp 0 |

### 7.3 Mock path

冇 `MODEL_AGENT_API_KEY` 時 Ark 欄以 **seeded lognormal**（`log~N(ln600, 0.35)` TTFT、tok/s ~ U(25,50)）模擬，report 標 `ark(mock)`、`mock:true`，唔會當真。本次實測有 key → 全 live。

---

## 8. Eval / Regression gate（`eval/`，D6 — 詳見 `eval.md`）

- **Golden datasets**：6 sets、34 records（qa 15：fact_single 11 × f1、fact_multi 4 × {llm_judge 2, trap 2}；tool_call 8：calc 5、news 3；sentiment 11：3way 6、score 5）。由 `eval/rebuild_goldens.py` deterministic 生成，QA 唔 hardcode URI（沿用 eval_set 慣例），least-common-denominator 冇 retrieval leak（trap 用「KB 檢索結果：無相關資料」模擬檢索空 path）。
- **Evaluators**：`exact`（相等）、`f1`（answer_f1 ≥ 0.25 PASS）、`trap`（USELESS_ANS lexicons）、`tool_call`（**Tool-call JSON + harness 真執行**：parse `{tool,args}` → 陰影內建 `calc`（1e-6 tol）/ 讀 `data/news/sample_news.csv`）、`sentiment`（strict JSON or label ∈ classes）、`llm_judge`（本地 Ollama qwen3：think:false、temp 0、num_predict 16、cache）。
- **Gate**：`eval/gate.py` → 同 `eval/baseline.json`（`--lock-baseline` 錄 overall + per-set score/exact_mean/judge_rate）比，跌穿 `margin=0.03`（judge `judge_margin=0.10`）→ FAIL；**exit 0/1/2**。冇 baseline 嘅 set 當 FAIL（新 set 要重新 lock）。
- **Budget**：`--max-tokens` default 250,000，QA 較貴先受 budget skip。
- 本地 `make eval` 即 CI；冇 GitHub Actions（定案）。

---

## 9. 重現性同 artifact 佈局

```
experiments/runs/<tag>/
├── run_meta.json            # model / prices / gate / rrf_k / budget / items（重現 config）
├── <strategy>/info.json     # read_limit / k / desc
├── <strategy>/events.jsonl  # 全 item × 全 stage {strategy,eid,category,stage,ts,ms,tokens,score,uris[],detail}
│                            #   stage = retrieve / gate / router / judge / rewrite / retry / answer / agent
├── <strategy>/<eid>/transcript.jsonl   # 逐 LLM call 全 replay（agentic = Runner events + usage）
├── <strategy>/<eid>/answer.txt         # final answer（連【KB:…】+ ## 來源）
└── <strategy>/report.md + SUMMARY.md
```

- rerank：`experiments/runs/rerank_*/`；engine bench：`engine_bench/{report.md, run.json, measurements_*.jsonl}`；eval：`eval/reports/<tag>/` + `eval/baseline.json`。
- 環境變數：`MODEL_AGENT_API_KEY` / `MODEL_AGENT_API_BASE` / `MODEL_PRIMARY` / `DATABASE_OPENVIKING_API_KEY`（`.env`）；Ollama :11434 有 `qwen3:4b-instruct-2507-q4_K_M`。

---

## 10. 已知陷阱同執行筆記（實測收集）

1. **thinking disabled 係必需**（Ark seed-1-6 同 Qwen3 都預設 thinking）→ `_lib.ark_complete` / rerank native call 已內建。
2. **`output_text` vs `output[].content[].text`**：Ark answers 只喺 part text 見到 → `_extract_text()`。
3. **events.jsonl token 陷阱**：judge/rewrite/router 無 `tokens` → 成本計數一定要由 transcript 重計（RESULTS §2.5 係修正版）。
4. **corpus reseed / f12**：main run（16 題）同 D5（15 題）唔係同一 corpus 狀態；採同一 8 份研報、同一 15 題，但每題簽到邊個 doc 嘅 prefix 個別 run 自洽；逐 item 有 grain 差異。
5. **rerank「rrf」bug**：`_rrf` 返 doc-prefix，`_ctx_selected` exact-match 唔上 chunk → ctx 空假答案（0.039）→ `_pref_to_chunk()` 修正後 0.114。
6. **read_limit instance 級**：每 pipe 一個 KB instance（compromise）。
7. **RRF 唔做 score scaling**（統一 k=60）——已係最簡可接受；細 pool（≤30 分片、8 doc）下 k/w 唔敏感（sweep 全 plateau）。
8. **agentic**：fresh subprocess／tracers=[]／raw viking:// uris（`_cite` 用 normalized）／completion usage 唔報（prompt side only）。
9. **Ollama 兩條 API 形態**：rerank 用 **native `/api/chat`**（攞 `prompt_eval_duration` 或 `think:false`）；`local_complete`（`_lib`）係 OpenAI-compat 給 rerank scoring。D6 engine_bench 混用兩者（TTFT 淨 native 有）。
10. **Ark streaming usage 唔一定齊**（`input_tokens_details`／`output_tokens` 有時 0）→ `estimate_tokens` fallback；Tok/s/$ 列屬估計，TTFT/total 係真 timestamp。
11. **eval gate 波幅**：fact_single answer-F1 係 live-hybrid，run-to-run ±0.01；trap 必須 deterministic（D6 已改「檢索空模擬」）。margin 3% 只蓋「同 pipeline 正常波幅」，換 KB 內容/剔題要 rerun。