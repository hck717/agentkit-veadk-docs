# FIN-MATE D6 · 評測與回歸檢查（EVAL.md）

> 一鍵跑：`make eval`（跑 34 條 golden 然後對 baseline 做 regression gate）；首次鎖 base：`make eval-lock`。
> 引擎對比：`make bench` → `experiments/engine_bench/report.md`。
> 觀測：`make obs` → `scripts/trace_all.py`。
> 本文件與 [experiments/rag_bench/RAG_LAB.md](experiments/rag_bench/RAG_LAB.md)、`experiments/rag_bench/REPORT_full_260908_1551.md` 連貫：eval 係全 pipeline（含 KB 檢索＋hybrid 生成）嘅**結果面** gate，RAG_LAB 係**檢索面** bench。

---

## 1. 目的

D5 建好嘅 hybrid RAG pipeline 一路靠人手開 RAG_LAB 唔到，冇自動 check「prompt 改壞咗／pipeline 退化咗」。D6 目標：

1. 一組**細而精**嘅 golden dataset（6 sets、34 records），cover 真 user 會問嘅嘢；
2. 一個 **deterministic evaluator** 層（無 network 依賴嘅 5 個 + 1 個本地 LLM judge）；
3. 一個 **regression gate**：同一跑法之下，分數跌穿 baseline −3% 即 FAIL（exit 1），CI 就係本地 `make eval`；
4. 一組**engine bench**：同一 prompt，Acme Cloud（Ark cloud LLM）vs 本地 Ollama 開箱即用可切換方案，量 TTFT / throughput / 成本。

跑法設計 lock 咗：gate = regression vs baseline（`--lock-baseline` 錄 base）；tool_call = model 出 `{tool,args}` JSON、harness **真執行** tool；bench concurrency 1、iter 10。

---

## 2. Golden datasets（`eval/golden_datasets/`）

由 `eval/rebuild_goldens.py` 生成（deterministic、有 provenance；改咗 `experiments/rag_bench/eval_set.py` 之後 rerun 佢）。每條 record 一個 JSONL 列：

```jsonc
{
  "set": "calc_expr", "id": "tc_calc_01", "type": "tool_call",
  "prompt": "…", "context": "…(qa 用，即 KB 黃金 doc 內容，唔會當真實檢索)",
  "golden": { /* 每種 evaluator 唔同 */ },
  "evaluator": "tool_call",   // exact | f1 | trap | tool_call | sentiment | llm_judge
  "meta": {...}
}
```

| set | file | n | evaluator | golden 內容 | prompt 來源 |
|---|---|---|---|---|---|
| fact_single | `qa/fact_single.jsonl` | 11 | `f1` | `{answer, gold_docs}`（英文 gold；跑法經 `run("hybrid")` 過真 KB） | eval_set f1–f11（f12 剔除，因 9/2 reseed 後冇 `msft_overview`） |
| fact_multi | `qa/fact_multi.jsonl` | 4 | `llm_judge`×2、`trap`×2 | m1/m2 多跳答（行 hybrid）；t1/t2 = hallucination trap（模擬「KB 檢索空」，meta.useless_ans） | eval_set m1/m2 + t1/t2 |
| calc_expr | `tool_call/calc_expr.jsonl` | 5 | `tool_call` | `{tool:calc, args, result, variants, check:result}` | Deutsche/Mizuho/CRR/Barclays/EC2 數字 |
| news_extract | `tool_call/news_extract.jsonl` | 3 | `tool_call` | `{tool:read_news_file, args:{path:data/news/sample_news.csv}, fields:[ticker,sentiment], expect, row}` | 本地 CSV 3 行 |
| sent_3way | `sentiment/sent_3way.jsonl` | 6 | `sentiment` | `{label, classes}` | D3 news headline |
| sent_score | `sentiment/sent_score.jsonl` | 5 | `sentiment` | `{label, classes, score_range, require_driver:true, strict_json}` | D3 headline + 理由 |

總數 **34**；QA 15 條真行 live OpenViking KB 檢索（`run("hybrid")`、no hardcode URI），tool/sentiment 19 條唔使 KB。

---

## 3. Methodology

### 3.1 執行 harness（`eval/run_eval.py`）

- `python -m eval.run_eval [--suite qa|tool_call|sentiment|all] [--tag X] [--no-judge] [--max-tokens N]`
- QA：`strategies.run("hybrid", …)` → 真 KB 檢索 + Ark 生成（`_lib.ark_complete`，max_tokens 512）。**trap 例外**：唔行 KB，直接問 + 明確寫低「KB 檢索結果：無相關資料」，測「檢索空時 model 會唔會老作」呢個 path（deterministic，唔受檢索波幅影響）。tool/sentiment：同一 `_lib` Ark chat，system prompt 分 `TOOL_SYSTEM` / `SENT_SYSTEM`。
- 每條 record 記 `score / pass / ms / pred / note`；輸出 `eval/reports/<tag>/report.{json,md}` 及 `latest.{json,md}`；`judge_cache.jsonl` 重用 LLM judge 結果（同 prompt 唔使再 judge）。
- **Token budget**：default 250,000（`--max-tokens`），用晒先 skip 餘下 QA（節省預算；−$0.20 上限）。

### 3.2 Evaluators（`eval/evaluators.py`，self-test `python -m eval.evaluators`）

| evaluator | 定義 |
|---|---|
| `exact` | pred 去掉空白/全形後與 golden 相等 |
| `f1` | `answer_f1(pred, gold)`；**PASS 閾值 F1 ≥ 0.25**（RAG_LAB 慣用 answer-F1） |
| `trap` | pred 含任何 `USELESS_ANS`（無資料/没有/no information/not found/唔知）→ PASS（承認唔知）；硬答 → FAIL |
| `tool_call` | `extract_json`（balanced-brace）解析 `{tool,args}`；`calc`：真執行陰影 `calc`（內建 eval，1e-6 tol）或任何 `variants`；`read_news_file`：讀 `data/news/sample_news.csv`，對 `expect[row]` 每 field |
| `sentiment` | 接受 strict JSON `{label,score,...}` 或文字；label ∈ classes 即 PASS；`score_range` 另查且有 option 輸出 |
| `llm_judge` | async，本地 Ollama qwen3（`think:false`、temp 0、num_predict 16）評 PASS/FAIL，配 cache |

### 3.3 Regression gate（`eval/gate.py` + `eval/gate_config.json`）

- `python -m eval.gate --lock-baseline` → 寫 `eval/baseline.json`（overall + per-set 嘅 score/exact_mean/judge_rate）。
- `python -m eval.gate`：每一格同 baseline 比，跌穿 `margin=0.03`（judge `judge_margin=0.10`）標 FAIL：
  - overall + 每 set 都 check score 與 exact_mean
  - 冇 baseline 嘅 set 當 FAIL（`NO BASE`，新 set 要重新 lock）
  - **exit 0 = GATE PASS，1 = 有 regression，2 = 執行錯誤**。
- 校準：第一次 lock 依家個 pipeline 為「正常」，之後任何 prompt/pipeline 改動令分數跌 >3% 就炸 gate。budget/網絡波幅唔會搞到 −3%（實際 margin 好鬆）。

### 3.4 Engine bench（`experiments/engine_bench/run.py`）

12 條 prompt（每 set 2 條，HASH 決定）、QA 用 golden `context` inline（**唔行 KB**，獨立量引擎）、concurrency 1、iter 10 → 每 engine 120 個 measurements，寫 `measurements_{ollama,ark}.jsonl`（**可 resume**）。

- **TTFT**：Ollama = native `/api/chat` 嘅 `prompt_eval_duration`（首 eval）；Ark = `responses.create(stream=True)` 第一個 `content_part.delta` / `output_text.delta` 事件時間（`response.completed` 收 usage）。
- **Throughput**：Ollama = `eval_count/eval_duration`；Ark = 總 tokens / total（usage 唔齊就用 `estimate_tokens`（CJK 每 4 字 = 1 tok）fallback）。
- **mock**：冇 `MODEL_AGENT_API_KEY` 時 Ark 欄以 seeded lognormal 模擬，report 標 `ark(mock)`。（本次有 key → 全部 live。）
- 成本：`_lib.usd`（input ¥0.15 ≈ $0.021 / output ¥1.5 ≈ $0.211 / cached ¥0.03 ≈ $0.004，每 1M tokens）。

### 3.5 環境／模型

| 嘢 | 值 |
|---|---|
| cloud LLM | Ark `seed-1-6-flash-250715`（`MODEL_AGENT_API_BASE`…/api/v3） |
| local LLM | `qwen3:4b-instruct-2507-q4_K_M` @ Ollama :11434 |
| KB | OpenViking `fin_kb`（live，hybrid：dense + rerank・qwen3） |

---

## 4. Results（2026-09-09，baseline `eval/reports/260909_2254`，重跑 `260909_2255`）

### 4.1 Eval per-set（baseline 2254）

| set | n | score | pass | exact_mean | judge_rate | tokens | usd | ms |
|---|---|---|---|---|---|---|---|---|
| fact_single | 11 | 0.145 | 2/11 | 0.145 | n/a | 52,189* | $0.0013* | 39,781* |
| fact_multi | 4 | 1.000 | 4/4 | 1.000 | 1.000 | 14,168 | $0.0004 | 14,236 |
| calc_expr | 5 | 1.000 | 5/5 | 1.000 | n/a | 1,080 | $0.0000 | 3,862 |
| news_extract | 3 | 1.000 | 3/3 | 1.000 | n/a | 473 | $0.0000 | 2,231 |
| sent_3way | 6 | 1.000 | 6/6 | 1.000 | n/a | 894 | $0.0001 | 6,505 |
| sent_score | 5 | 1.000 | 5/5 | 1.000 | n/a | 716 | $0.0001 | 5,774 |
| **overall** | 34 | **0.723** | **25/34** | 0.706 | 1.000 | 68,779 | **$0.0020** | 39,855 |

> *fact_single 嘅 tokens/ms/usd 由 2212 run 轉錄（2254 用同一 hybrid，數字一致）；只有 trap 分支改為唔行 KB 先令 fact_multi 慳。重跑 2255：overall 0.729、pass 26/34、fact_single 0.160——兩轉都 **GATE PASS**，run-to-run 波幅 ≈ ±0.01。

- **tool + sentiment（19 條）全 PASS**：tool-call JSON 全部 parse 到、`calc` 陰影實行數字全對、news CSV 3 行 ticker/sentiment 全部正確、sentiment strict JSON 全對。
- **fact_multi（4 條）全 PASS**：2 條多跳 LLM judge 判 PASS；2 條 trap（模擬檢索空）成功「承認冇資料」。
- **fact_single 係唯一弱點**：overall score 0.723 正正係俾佢拖低。呢個**唔係 regression**——同 RAG_LAB hybrid run（`experiments/runs/full_260908_1551/hybrid`）完全一致：該 run answer-F1 = 0.127、per-item f1 同樣喺 0.000–0.565 之間、f3/f4 = 0.000。原因係 gold 係英文一句（F2Q Azure 38% CC…）、model 用中文／廣東話答，token overlap 細，`answer_f1` 對語言唔敏感。低絕對分但**穩定可複現**（±0.01），正好做 regression base。

### 4.2 Regression gate

```
baseline locked → eval/baseline.json  (overall 0.723 / 0.706 / 1.000)
python -m eval.gate → GATE PASS (exit 0)
```
thresholds：overall score 0.693、exact 0.676、judge 0.970；per-set 全部 `ok`。REPRO：`make eval-lock`（第一次）→ `make eval`。

### 4.3 Engine bench（`experiments/engine_bench/report.md`，12 prompts × 10 iter）

| engine | TTFT p50 ms | TTFT p95 ms | mean total ms | tok/s | tokens (p/c) | usd |
|---|---|---|---|---|---|---|
| **ollama** qwen3:4b | **49** | 65 | 4,846 | 27.2 | 6,400/10,571 | $0.0024* |
| **ark** seed-1-6-flash | 172 | 479 | **932** | **121.4** | 5,310/6,403 | $0.0015 |

- **TTFT：Ollama 快 3.5×**（首 eval 幾乎即出，無網絡）；但因為逐 4-bit token 行 CPU，**generate 慢**、mean total 5× 慢（4.8s vs 0.93s）。
- **Throughput：Ark 快 4.5×**（121 vs 27 tok/s）。QA+tool 長 prompt 更誇（fact 類 Ark 133–168 tok/s；ollama 17–29）。
- 成本：全套 bench（120+120 calls）ollama 計 $0.0024（4-bit 本地其實係電費，Ollama `usage` 計法），Ark $0.0015。差唔多一樣。
- Ark TTFT p95（479ms）敏感過 Ollama（65ms）——cloud 第一 hop + 排隊可以上到 1.8s（qa_fs_01）。

——結論：需要**最低延遲/離線/私隱** → Ollama；需要 **throughput／長尾部穩定** → Ark。二者 API 形態一樣（`/api/chat` vs `responses.create`），切換只改 config。

### 4.4 成本總結

full eval（34 條、含 live KB + hybrid 生成）+ gate = **$0.0020**（baseline 2254：68,779 tokens；重跑差唔多）；engine bench（240 calls）≈ $0.004。成個 D6 gate 一轉 < 1 美仙，可以日日跑。

---

## 5. 限制與 caveat

1. **fact_single 用英文 `answer_f1` 對中文答**：低絕對分（0.145）而**非低品質**。要睇「答啱唔啱」要 upgrade 做 LLM judge（成本 +）或改 gold 做中文。依家定位係：穩定、deterministic、捉 regression。
2. **trap / fact_multi 條 prompt 冇 context**（特登），所以 bench 入面 qa_fm_03 短 prompt、tok 細係正常。
3. **LLM judge 係本地 qwen3 4b** 唔係最強；verdict 只兩格（PASS/FAIL）。有 cache；`--no-judge` 可 skip。
4. **Ark streaming usage 唔一定齊**（冇 `input_tokens_details` 時 fallback `estimate_tokens`）；tok/s 同 usd 列係估計，TTFT/total 係真 timestamp。
5. **live KB 會波幅**：OpenViking 快慢、reseed、top_k 影響 hybrid 結果。gate margin 3% 已 cover「同一個 pipeline 嗰啲正常波幅」；**換 KB 內容本身都應該觸發 regression check**（例如 9/2 剔走 f12 要 rerun）。
6. **mock 路徑**今次冇行（有 key 所以全 live）；無 key 環境照出 `ark(mock)` 標清楚，唔會當真。

---

## 6. Repro

```bash
./.venv/bin/python -m eval.rebuild_goldens     # 改 eval_set/rebuild 後 rerun（deterministic）
./.venv/bin/python -m eval.run_eval --tag x    # 全 34 條
./.venv/bin/python -m eval.gate --lock-baseline  # 第一次鎖 base（make eval-lock）
./.venv/bin/python -m eval.gate                  # regression check（make eval，exit 0 = pass）
./.venv/bin/python -m experiments.engine_bench.run  # 引擎對比（make bench；可 resume）
./.venv/bin/python -m eval.evaluators             # evaluator self-test
```

`make` targets：`eval`（run_eval + gate）、`eval-lock`、`eval-qa`（--suite qa --no-judge）、`bench`、`obs`。