# FIN-MATE 實驗結果總覽（RESULTS.md）

> 全部實驗（RAG Lab → Rerank Lab → 新 RAG 方法 → Engine Bench → Eval Gate）嘅**結果＋逐項解讀**集中喺度。
> 數門徑一路係一套：`eval_metrics.py`（retrieval/F1）+ `_lib.PRICES`（成本）。
> 方法論手冊：見 [METHODOLOGY.md](METHODOLOGY.md)；逐實驗細節：`rag_bench/RAG_LAB.md`、`rag_bench/REPORT_full_260908_1551.md`、`engine_bench/`、`eval.md`。
>
> **版本注意**：RAG main run 係 **D4、16 題、reseed 前 corpus**；D5 之後（rerank/HyDE/新方法/engine/eval）係 **15 題、reseed 後**（f12 剔出，因為 `msft_overview` 已被剷走）。兩組數字冇直接拼埋一表做 cross-pipe 比較嘅位，已喺各表標明對照組。

---

## 1. 執行摘要

**RAG 實驗室（D4，6 pipes × 16 題，`full_260908_1551`，500K budget，$0.011，0 err）**

| pipe | recall@5 | prec@5 | MRR@5 | answer-F1 | trap (2題) | ms/題 |
|---|---|---|---|---|---|---|
| **naive**（prod baseline）| **0.964** | 0.418 | 0.762 | 0.109 | 2/2 PASS | 1,576 |
| advanced | 0.964 | 0.214 | 0.762 | 0.105 | **1/2** | 1,814 |
| **hybrid** | **0.964** | 0.214 | **0.929** | **0.127** | 2/2 PASS | 1,754 |
| corrective | 0.607 | 0.287 | 0.524 | 0.077 | **1/2** | 1,354 |
| adaptive | 0.964 | 0.418 | 0.762 | 0.112 | 2/2 PASS | 2,079 |
| **agentic** 🚫退役 | 0.750 | **0.500** | 0.494 | 0.056 | 2/2 PASS | 11,810 |

**Engine Bench（D6，12 prompts × iter 10，concurrency 1，全 live）**

| engine | TTFT p50 ms | TTFT p95 ms | mean total ms | tok/s | tokens (p/c) | usd |
|---|---|---|---|---|---|---|
| **ollama** qwen3:4b | 49 | 65 | 4,846 | 27.2 | 6,400/10,571 | $0.0024* |
| **ark** seed-1-6-flash | 172 | 479 | **932** | **121.4** | 5,310/6,403 | $0.0015 |

> \* Ollama 呢個 $ 係「照 `_lib.PRICES` 對 usage 數計」嘅名義數；實際上 4-bit 本機係電費級，唔使真俾呢個價。

**JEV Agent Bench（phase-1 39×2 → phase-2 15×2 → 3-arm 15×3 → 4-arm 15×4，`runs_260921_1324` / `runs_260921_1354` / `runs_260921_1930` / `runs_260921_1508`，4 runs 0 err）**

| 範圍 | 對照 | 結論 | 亮點 |
|---|---|---|---|
| phase-1：淨係 tool-choice 用 Jev | original vs jev_tools | 正確率打和，**$ 一樣（$0.0017）但 latency +23%（41→50.5s）**——只有「邊個 tool」1-2 token 俾咗 System One，args/答案照舊 chat，變成 1 step 3 call | 10/10 pass、choice 準 |
| phase-2：全決策點開 System One | original vs jev | **噪音修剪＋記憶/私隱守衛真有用**（noise doc 100% 閘走、記憶 F1 0.481→0.706、總倉位記憶喺生成層之前篩走）；但有 3 個硬傷：judge 唔穩會連 gold 一齊剪（RAG_03）、1-token sentiment 輸 chat（1/3 vs 3/3）、57×~500ms decision call 開銷 > ctx 慳（μ$ 611→724、latency +141%） | mem/私隱 贏、RAG answer 冇贏 |
| 3-arm：加「真 JEV」arm | original vs jev（介面層） vs **jev2（真 JEV）** | review 確認決策層一路係真 JEV（1–3 token + logprobs，零 generation），但 **args 仲係 chat 生成 → 修好**：`jev2` args 3/3 確定式 fill（0 ms/0 tok）、**工具單步 471 ms 三 arm 最平**；gate 同守衛結果同 jev 一樣（ctx 6→2/1/0/0、mem leak 0）。**淨係慳到相對 jev 嘅 57 μ$（762→705），仍比 original 貴 18%**；sent 照輸、judge 唔穩照舊（RAG_03 gold 被誤剪） | args 零 generation、工具層最快 |
| **4-arm：加 JeV3 tier-0** | original vs jev vs jev2 vs **jev3** | **判定位唔好叫 LLM：** 工具路由／RAG gate／私隱 marker／STOP honor 全部換確定式規則（`jev/tier0.py`），決策 54 → 14（tier-0 頂 35）。**`jev3` 係第一次同時贏 original：14.5s（-22%）／564μ$（-5%）／accuracy 全面赢返**——工具 step 0ms、RAG gold 三題全保住+trap 1/1、情緒 1/3→3/3、noUL 3/3+stop-exact 2/2、記憶 F1 0.857+leak 0（四 arm 最靚）。**根因解開：original 勁係因為決定=chat 副產品（0 extra call）；JEV 老 54 個 serial RTT 開銷補唔返 ctx 慳，tier-0 先係對症** | **第一次 net 贏 original（速度+成本+準確）** |

**概括結論（4 條）：**

1. **檢索已逼天花板**：naive/advanced/hybrid/adaptive 全部 recall@5 = 0.964；唯一唔足 1.0 係 **m1**（跨兩份 doc 聯想，gold＝Barclays+Deutsche，全部 pipe 只中 1/2）。**Retrieval 唔係樽頸——樽頸喺「答」。** Rerank Lab 再加證：8 份 doc 嘅細 KB 入面，pool 原序已接近最優，所有 rerank（RRF / LLM pointwise / cross-encoder / listwise）都贏唔到「唔 rerank」。
2. **生成層先係樽頸**：所有 pipe answer-F1 < 0.13（料中但字面 F1 低，唔等於答錯）；唯一有效提升 F1 嘅軸係 **HyDE**（0.112→0.138，+23%，但 recall 跌 0.962→0.885，係 trade-off 唔係 free win）。
3. **程序 pipe 快過 agent 一個量級**：全部程序 pipe 1.35–2.1s/題；agentic 11.8s（~7×）＋ 最貴（$0.0023/題）＋ recall 得 0.75 → **退役**。
4. **引擎選擇睇優先順序**：要**最低延遲/離線**用 Ollama（TTFT 49ms，快 3.5×）；要**throughput/長尾部穩定**用 Ark（121 tok/s 快 4.5×、mean total 0.93s）。兩者 API 形態一致，切換只改 config。**閉環**：`eval/gate` 已 lock baseline（overall 0.723 / exact 0.706 / judge 1.000），重跑兩次 `make eval` 都 **GATE PASS**（波幅 ±0.01）。

---

## 2. RAG main run（D4）：詳細結果

### 2.1 按類別拆（fact n=12 / multi_hop n=2 / trap n=2）

| pipe | cat | recall@5 | prec@5 | MRR@5 | nDCG@5 | ans-F1 | trap PASS |
|---|---|---|---|---|---|---|---|
| naive | fact | 1.000 | 0.437 | 0.778 | 0.835 | 0.094 | – |
| naive | multi_hop | 0.750 | 0.300 | 0.666 | 0.592 | 0.199 | – |
| naive | trap | – | – | – | – | – | 2/2 |
| advanced | fact | 1.000 | 0.200 | 0.778 | 0.835 | 0.087 | – |
| advanced | multi_hop | 0.750 | 0.300 | 0.666 | 0.592 | 0.210 | – |
| advanced | trap | – | – | – | – | – | 1/2 |
| hybrid | fact | 1.000 | 0.200 | **1.000** | **1.000** | **0.120** | – |
| hybrid | multi_hop | 0.750 | 0.300 | 0.500 | 0.506 | 0.162 | – |
| hybrid | trap | – | – | – | – | – | 2/2 |
| corrective | fact | **0.583** | 0.285 | 0.500 | 0.522 | 0.071 | – |
| corrective | multi_hop | 0.750 | 0.300 | 0.666 | 0.592 | 0.113 | – |
| corrective | trap | – | – | – | – | – | 1/2 |
| adaptive | fact | 1.000 | 0.437 | 0.778 | 0.835 | 0.096 | – |
| adaptive | multi_hop | 0.750 | 0.300 | 0.666 | 0.592 | 0.206 | – |
| adaptive | trap | – | – | – | – | – | 2/2 |
| agentic | fact | 0.750 | **0.533** | 0.493 | 1.459* | 0.053 | – |
| agentic | multi_hop | 0.750 | 0.300 | 0.500 | 0.540 | 0.076 | – |
| agentic | trap | – | – | – | – | – | 2/2 |

\* agentic fact nDCG 1.459 > 1 係 metric 特性（同 doc 多分片都計相關令 dcg 可超 idcg），唔係超越理想排序；見 METHODOLOGY §5.1。

### 2.2 關鍵觀察

- **fact（12 題）**：naive＝adaptive＝advanced 檢索全紅（recall 1.0、MRR 0.778）；**hybrid 排名全勝**（MRR/nDCG = 1.0）但 prec 低（sparse 引入假陽性）。**answer-F1 全場低（0.05–0.12）**——retrieval 揀啱，但生成對「數字＋年份＋來源語」嘅精準表述唔及文字 gold（HK 混合語、同義句）。**樽頸喺生成，唔係檢索。**
- **multi_hop（m1/m2）**：所有 pipe 都 0.75 recall；**m2 係唯一全場 miss 嘅題**（gold 跨兩份 doc 聯合推論，單一 top-5 檢索做唔到）。
- **trap（t1/t2）**：naive/hybrid/adaptive/agentic 全 PASS；**advanced 同 corrective 各錯 1 題**——佢哋預先「補檢索/重寫」，令模型覺得有料而作答案。
- **agentic**：prec 最高（自己 filter 低分候選）、trap 冇呃；但 recall 得 0.75——工具 loop 揀源偏向「最近嗰份」，跨日/跨類型事實易漏；instruction 冇教 marker → cited 少，但 3 個 falsified 真係引錯。

### 2.3 逐 pipe 根因（基於 transcript/events 實測 replay）

**naive** — 點解 recall 咁高：題庫關鍵字（Mizuho、Barclays、F2Q、E7 SKU…）同文件標題對得極準，dense 一拉就中。唯一 miss 係 m1（跨兩份 doc）。點解 prec 0.418 / MRR 0.762：實測 f1/f4 retrieve 只得 **2 個 URIs**、gold 排第 2——top-5 撳完 hydrate 唔足 5 份、真份未上第一名。點解 F1 0.109：唔係答錯，係中英混合句法同 gold 對唔上（f3/f4/f5/f11 得 0.000 但 recall 1.0）。

**advanced**（k=15 細水化 + grep + gate 0.35）— Recall 不變（fact 1.0，gate 只濾明顯錯料）；prec 跌到 0.214（k=15 多帶文件）；multi_hop F1 微升（m1 0.210/m2 0.247，細水化畀到跨份 context）；trap t1 係**量度假象**（「目前提供的資料中並未提及…」語義有拒絕但字面唔入 lexicons → 判 FAIL，佢冇作料）。

**hybrid**（dense+sparse→RRF k=60）— 點解全場 rank 王（fact MRR/nDCG=1.0）：實測 f1/f4 由 naive 嘅「2 URs + gold rank 2」→ hybrid「5–6 URs + gold rank 1」。sparse grep 將 pure-dense 排名低嘅真份推上頂——呢類「問句同標題共 key」題 sparse 命中率高，補足 dense 盲點。answer-F1 都最高（0.127）；代價 prec 0.214（sparse 假陽性）。

**corrective**（self-check→rewrite→re-find）— **全場最差**（fact recall 0.583，12 題死 5 題：f3/f4/f5/f6/f10）。兩個致命位：(1) **judge 過嚴**——f3 明明攞到料，judge 要求原文直接含數值，水化 summary 帶唔到就當無料 → 觸發 rewrite；(2) **rewrite 之後 skip-inject**——f6 嘅 judge2 判 CORRECT 但 `gate → skip_inject=true`，最終答「KB 無資料」（68 tokens）——**原本有料俾佢整到冇料**。trap t1 係唯一真製造假資料（rewrite 撳到料後老作股息數字）。**執行「先判斷夠唔夠料」係淨虧**——detector 太保守，唔應該 default 觸發 rewrite。

**adaptive**（router SEARCH/SKIP）— 結果同 naive **完全一樣**（連 tokens 都等量）：router 對 trap 都判 SEARCH——「股息殖利率歷史」問題問得似正常，LLM 冇可能從 query 字面 pre-empt 到 KB 無料。即係「adaptive 慳錢」喺呢份題庫實現唔到（慳嘅前提係 router 敢 skip，而 trap 恰係最難 skip 嗰種）。

**agentic** — prec 最高（0.500）、trap 2/2、冇一秒老作（真經 tool 攞料先答、天然 grounded）；recall 跌到 0.75（f5 0 URI、f7 只 load 一次撳返另一批文件——agent 揀源有 bias）；慢（11.8s/題，ADK Runner + session + tool loop）。**citation verifier**：總 markers 11、**falsified 3**（f6×2、f11×1）。冇 pipe 可以睇到呢層審計——agentic 唯一（但個錢同時間唔值）。

### 2.4 Performance（吞吐量）

| pipe | ms/題 | 全 16 題 clock | n_events | 每題 LLM 往返 |
|---|---|---|---|---|
| naive | 1,576 | 25.2s | 32 | 1 |
| advanced | 1,814 | 29.0s | 48 | 2 |
| hybrid | 1,754 | 28.1s | 32 | 1 |
| corrective | 1,354 | 21.7s | 85 | 3–4 |
| adaptive | 2,079 | 33.3s | 48 | 2 |
| agentic | 11,810 | 188.0s | 16 | tool-loop |

→ 程序 pipe 全部 < 2.1s/題；latency 唔係差別因素；**agentic 係 outlier**（7×），且 `agent_timeout=240s` 下最差題都冇接近上限。

### 2.5 成本效率（token 已由 transcript 全 call 修正）

| pipe | prompt tokens | completion | **tokens/16 題** | **USD** | USD/題 |
|---|---|---|---|---|---|
| naive | 30,183 | 2,257 | 32,440 | $0.0011 | $0.00007 |
| advanced | 77,214 | 2,429 | 79,643 | $0.0021 | $0.00013 |
| hybrid | 75,810 | 2,374 | 78,184 | $0.0021 | $0.00013 |
| corrective | 71,946 | 2,981 | **74,927** | $0.0021 | $0.00013 |
| adaptive | 31,230 | 2,583 | **33,813** | $0.0012 | $0.00008 |
| agentic | 109,167 | 0\* | 109,167 | $0.0023\* | $0.00014 |

\* agentic `usage_metadata` 只報 prompt side → 成本略低估。

- **Full suite 總耗**：**408,174 / 500,000 tokens（81.6%）**，~$0.011 成全場 96 runs。BUDGET_SKIP = 0。
- 修正後結論：**無任何 pipe「慳過 naive」**；corrective 真身 74,927 ≈ 2.3× naive（52 次 call），adaptive 33,813 ≈ naive（32 次）。**大分別唔喺錢（$0.00007–0.00014/題），喺 time 同質素。**

---

## 3. Rerank Lab（D5 §9，15 題，只 run 新 variant，冇 retest 舊 pipe）

同一個 fixed candidate pool 上只比較「排序」（@3 為主、@5 參考；multi-hop 揀 top-5 做 answer ctx）：

| variant | recall@3 | prec@3 | MRR@3 | nDCG@3 | recall@5 | MRR@5 | answer-F1 | trap | local ms/題 | Ark ms/題 | Ark tokens (15題) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **none**（pool 原序）| **0.962** | 0.359 | **0.923** | **0.918** | 0.962 | 0.923 | 0.111 | 2/2 | 138 | 1,529 | 30,327 |
| rrf（k=60）修正後 | 0.923 | 0.333 | 0.910 | 0.899 | 0.962 | 0.910 | 0.114 | 2/2 | 127 | 563 | 30,432 |
| llm（Qwen3-4B pointwise）| 0.923 | 0.333 | 0.872 | 0.860 | 0.962 | 0.872 | 0.108 | 2/2 | 2,855 | 1,544 | 30,253 + local 17,871 |
| — 對照 — | | | | | | | | | | | |
| naive（main-run）| 0.923 | 0.436 | 0.744 | 0.765 | 0.962 | 0.744 | 0.112 | 2/2 | – | ~1,576 | – |
| hybrid（main-run）| 0.923 | 0.333 | 0.923 | 0.906 | 0.962 | 0.923 | 0.118 | 2/2 | – | ~1,754 | – |
| hyde（§10）| 0.846 | 0.397 | 0.769 | 0.748 | 0.885 | 0.769 | **0.138** | 2/2 | – | 2,707 | 49,974 |

**閱讀：**

- **Rerank 冇贏過「唔 rerank」**：`none` MRR@3=0.923 同 hybrid 平手、高過自己 pool 上嘅 RRF（0.910）；**LLM-as-reranker 最差（0.872）**——Qwen3-4B pointwise 喺呢個細枯 KB 反而搗亂 top-of-list，仲 +2.7s/題。
- `recall@5` 全線 0.962（≈ D4 的 0.964）→ **5 份內一定揾到 gold，問題只係排序**；而排序喺 8-doc KB 入面：pool 原序已經接近最優。
- Answer-F1：rrf 0.114 ≈ hybrid 0.118；none 0.111；llm 0.108——**排序改善對 answer 質素無實質幫助**（hyde 0.138 係另一軸）。
- **RRF sweep**：`k∈{10..200}×w∈{0.5..2}` **24 格全 plateau**（MRR@3=0.910 / recall@5=0.962）→ pool ≤ ~30 分片、8 doc 粒度下 RRF 權重完全唔敏感，現行 k=60/w=1 已喺 plateau、無需 tune。
- multi_hop m1/m2 喺 @3 係全體共痛位（gold 兩份 doc，context 得 5 位）。

---

## 4. 新 RAG 方法（D5 §10/§11，各 15 題、獨立 ≤150K budget）

### 4.1 HyDE（§10）—— 換 query 軸

| pipe | recall@5 | prec@5 | MRR@5 | nDCG@5 | answer-F1 | trap | ms/題 | Ark tokens（15題） |
|---|---|---|---|---|---|---|---|---|
| **hyde** | 0.885 | 0.397 | 0.769 | 0.768 | **0.138** | 2/2 | 2,707 | 49,974 |
| naive（對照）| **0.962** | 0.436 | **0.744** | **0.765** | 0.112 | 2/2 | ~1,576 | – |
| hybrid（對照）| 0.962 | 0.333 | 0.923 | 0.906 | 0.118 | 2/2 | ~1,754 | – |

**trade-off，唔係 free win**：answer-F1 0.112→**0.138（+23%）**，但 recall@5 跌 0.962→0.885、MRR@5 微升（0.744→0.769）；nDCG 微跌。hypothesis 文帶埋擬似名詞，揾少咗「非主流表述」嘅 doc。呢個細枯 KB 上原 query 嘅 dense 已經好穩——HyDE 嘅價值喺 **answer 表述更貼 gold**（ctx 更集中），唔係「揾多咗料」。

### 4.2 HyDE+RRF / cross-encoder / LLM listwise（§11）

| variant | recall@3 | prec@3 | MRR@3 | nDCG@3 | recall@5 | MRR@5 | answer-F1 | trap | local ms/題 | Ark ms/題 | Ark tokens（15題）|
|---|---|---|---|---|---|---|---|---|---|---|---|
| **hyde_rrf** | 0.923 | 0.333 | 0.821 | 0.837 | 0.962 | 0.821 | 0.125 | 2/2 | – | ~1,650 | 48,702 |
| **ce**（bge-reranker-v2-m3）| 0.923 | 0.333 | 0.872 | 0.856 | 0.962 | 0.872 | 0.101 | 2/2 | 2,230 | 1,434 | 29,775 |
| **llm_listwise** | 0.923 | 0.333 | 0.833 | 0.850 | 0.962 | 0.849 | 0.108 | 2/2 | 1,872 | 1,393 | 30,418 + local 8,665 |
| — 對照（同池同軸）— | | | | | | | | | | | |
| none（pool 原序）| **0.962** | 0.359 | **0.923** | **0.918** | 0.962 | 0.923 | 0.111 | 2/2 | 138 | 1,529 | 30,327 |
| rrf（k=60）| 0.923 | 0.333 | 0.910 | 0.899 | 0.962 | 0.910 | 0.114 | 2/2 | 127 | 563 | 30,432 |
| llm pointwise | 0.923 | 0.333 | 0.872 | 0.860 | 0.962 | 0.872 | 0.108 | 2/2 | 2,855 | 1,544 | 30,253 |
| hybrid（main-run）| 0.923 | 0.333 | 0.923 | 0.906 | 0.962 | 0.923 | 0.118 | 2/2 | – | ~1,754 | – |
| hyde（§10）| 0.846 | 0.397 | 0.769 | 0.748 | 0.885 | 0.769 | **0.138** | 2/2 | – | 2,707 | 49,974 |

**閱讀：**

- **官方排序質素排序（MRR@3）：none/hybrid 0.923 > rrf 0.910 > pointwise = ce 0.872 > llm_listwise 0.833 > hyde_rrf 0.821 > hyde 0.769 > naive 0.744。** 三條新方法都**贏唔到「唔 rerank」**。
- **cross-encoder 同 LLM pointwise 打和（0.872）**，但 ce local 快（2,230 vs 2,855 ms）、$0、deterministic、無 prompt 風險；answer-F1 ce 0.101 略輸（0.108）→ 仍輸畀 none 0.111。
- **LLM listwise 唔及 pointwise**（0.833 vs 0.872）：一次過排 ~20 候選對 4B 太散；每題 1 call vs ~25 call 嘅 latency 換唔返排序質素。
- **HyDE+RRF 融合救返 recall、但輸畀 q-lane 本身**：recall@3 0.846→**0.923**（q-lane 補返 h-lane 揾少咗嘅 doc）、MRR@3 0.821 仍低過 hybrid 0.923（h-lane top-of-list 係負資產）、answer-F1 0.138→0.125（fusion ctx 由「hypothesis 集中答案段」變返「雙 lane 雜訊」）。
- `recall@5` 全線 0.962 → **呢個 KB 嘅排序增益已經一陪兩盡；想推 answer-F1 唔應該再搞 ranking**，方向係「ctx 選段／少數 copy 合併」或者生成 prompt 工程（D6 eval 就係呢個方向嘅門）。

---

## 5. Engine Bench（D6，12 prompts × iter 10，concurrency 1；`engine_bench/report.md`）

### 5.1 per-engine aggregate

| engine | n | TTFT p50 ms | TTFT p95 ms | mean total ms | tok/s | tokens (p/c) | usd |
|---|---|---|---|---|---|---|---|
| **ollama** qwen3:4b | 120 | **49** | **65** | 4,846 | 27.2 | 6,400/10,571 | $0.0024* |
| **ark** seed-1-6-flash | 120 | 172 | 479 | **932** | **121.4** | 5,310/6,403 | $0.0015 |

> \* Ollama 名義 usd（按 `_lib.PRICES` 對 usage 計）；本機 4-bit inference 實際係電費。

### 5.2 per-prompt 詳細

| prompt | engine | TTFT p50 ms | TTFT p95 ms | mean total ms | tok/s | tok(p) | usd |
|---|---|---|---|---|---|---|---|
| qa_fm_03（trap 短問）| ollama | 48 | 141 | 4,745 | 28.7 | 250 | $0.0003 |
| qa_fm_03 | ark | 139 | 561 | 1,328 | 42.9 | 70 | $0.0001 |
| qa_fm_01（multi-hop）| ollama | 54 | 65 | 9,195 | 14.6 | 900 | $0.0003 |
| qa_fm_01 | ark | 144 | 181 | 1,153 | 111.9 | 710 | $0.0001 |
| qa_fs_07（fact）| ollama | 49 | 58 | 6,683 | 19.0 | 670 | $0.0003 |
| qa_fs_07 | ark | 379 | 866 | 857 | 133.3 | 700 | $0.0001 |
| qa_fs_01（fact）| ollama | 49 | 58 | 5,565 | 17.4 | 690 | $0.0002 |
| qa_fs_01 | ark | 222 | 569 | 859 | 167.6 | 680 | $0.0002 |
| sent_3w_01 | ollama | 46 | 133 | 237 | 61.3 | 460 | $0.0000 |
| sent_3w_01 | ark | 182 | 472 | 535 | 165.7 | 490 | $0.0001 |
| sent_3w_05 | ollama | 46 | 142 | 236 | 57.7 | 400 | $0.0000 |
| sent_3w_05 | ark | 151 | 310 | 790 | 127.1 | 430 | $0.0001 |
| sent_sc_01 | ollama | 49 | 61 | 1,866 | 25.8 | 720 | $0.0001 |
| sent_sc_01 | ark | 178 | 563 | 635 | 215.5 | 750 | $0.0001 |
| sent_sc_03 | ollama | 45 | 64 | 2,050 | 20.7 | 640 | $0.0001 |
| sent_sc_03 | ark | 172 | 462 | 590 | 192.7 | 680 | $0.0001 |
| tc_calc_05 | ollama | 53 | 327 | 8,052 | 16.4 | 420 | $0.0003 |
| tc_calc_05 | ark | 156 | 235 | 1,140 | 57.6 | 150 | $0.0001 |
| tc_calc_01 | ollama | 49 | 56 | 7,755 | 17.0 | 590 | $0.0003 |
| tc_calc_01 | ark | 172 | 226 | 978 | 90.7 | 270 | $0.0001 |
| tc_news_03 | ollama | 49 | 136 | 7,428 | 17.2 | 280 | $0.0003 |
| tc_news_03 | ark | 156 | 205 | 969 | 88.6 | 180 | $0.0001 |
| tc_news_01 | ollama | 48 | 65 | 4,340 | 31.0 | 380 | $0.0003 |
| tc_news_01 | ark | 148 | 519 | 1,342 | 63.6 | 200 | $0.0001 |

（tok(p) 係 10 次 iter 總和 → per-prompt 每次約 24–90 tokens。）

### 5.3 閱讀

- **TTFT：Ollama 快 3.5×（49 vs 172 ms）**，且尾部極穩（p95 65ms）——4-bit 本機首 eval 幾乎即出、無網絡 hop。**Ark TTFT 有 tail**：p95 479ms，fact 類（qa_fs_07/01）上到 379/222ms（排隊/首 hop），最差單次可到 ~1.8s。
- **Throughput：Ark 快 4.5×（121 vs 27 tok/s）**，長 prompt 更誇（fact 類 133–168 vs ollama 17–29）；Ollama 屬「首 token 快、generate 慢」型。
- **mean total：Ark 0.93s vs Ollama 4.8s（5×）**——短句（sent_3w）Ollama 254–237ms 可以反勝個別 Ark 題，但一上長 prompt 就注定輸。
- 成本接近打和（本機係電費，$ 計法見上）。
- **切換角度**：`local_complete`（OpenAI-compat、Ollama）同 `responses.create`（Ark）形態一致——要**離線/私隱/最低延遲**用 Ollama；要**throughput/長尾穩定**用 Ark。

---

## 6. 橫切綜合（點揀）

1. **Retrieval 策略（production pick）＝ hybrid**：唯一 fact MRR/nDCG = 1.0、answer-F1 全場最高（0.127）、trap 2/2、約 1.75s/題、$0.0021/16題。naive 係 fallback（簡、平、recall 同樣 0.964，只差 rank/F1 少少）。
2. **唔好加**：corrective（負貢獻）、rerank（任何 variant 都唔值）、agentic（慢貴又 miss）。adaptive 冇害但冇實際慳（router 唔敢 skip）。
3. **想提升 answer 質素**：唔係 ranking 嘅事。已試有效：HyDE（F1 +23% 但收 recall）；下一步係生成 prompt 工程（數字+年份+來源語統一）同 **fact-check LLM judge**——D6 eval 個 `llm_judge`（本地 qwen3）就係最低成本版嘅雛形。
4. **唯一結構性檢索 miss**：multi_hop m1/m2（跨兩份 doc 聯合）——要真做，方向係「top-5 內強制覆蓋兩份 gold prefix」或 second-pass query。
5. **閉環 gate 已 lock**：baseline `eval/baseline.json` = **overall 0.723 / exact_mean 0.706 / judge_rate 1.000**；重跑兩次都 **GATE PASS**（今次個 `fact_single` answer-F1 ≈ 0.145–0.160，同 RAG Lab 嘅 hybrid 0.127 同一族——全 pipeline 數字一致）。成個 D6 gate < 1 美仙，可日日跑（`make eval`）。

---

## 7. JEV Agent Bench（phase-1「tool-choice 換 Jev」→ phase-2「全決策點 System One」→ 3-arm「真 JEV」→ 4-arm「JeV3 tier-0」）

> 完整報告：[`jev_bench/JEV_REPORT.md`](jev_bench/JEV_REPORT.md)（4-arm 版，supersedes 3-arm 版）；phase-1 對照 run：`jev_bench/results/runs_260921_1324`。

### 7.1 背景同路線

- **Phase-1（`runs_260921_1324`，39 題/arm，5 任務）**：淨係將「揀工具」換做 JEV choice。結果：**正確率全線打和，成本一樣（兩 arm 都 $0.0017），工具 lane latency 555→1,570 ms**。原因：只有「邊個 tool」呢 1-2 個 token 交咗俾 System One，args 同後續答案照舊係完整 chat call → 一個 tool step 由 1 call 變成「choice+args+answer」3 call。另一個發現：JEV noUL false-positives **5/10**——「仲要唔要下步」呢種 boundary 判斷好易誤報。
- **Phase-2（`runs_260921_1354`，15 題/arm）**：將 System One 決策層開到成個 agent 嘅**所有系統一決策點**（工具、RAG 檢索 gate、記憶篩選、情緒、workflow noUL），目的唔係「慳 tool pick」，而係「**決定**同**生成**拆開，喺輔助位用 1-token 判斷砍走唔要嘅 context」。
- **Review → 3-arm（`runs_260921_1930`，15 題/arm）**：review 確認「決策層」一路都係真 JEV（`jev_client` 1–3 token + logprobs → score/confidence 做下一步，零 generation），但**兩個位唔係真 JEV**：(1) tool args 仍由 chat 生成、(2) live hook 只係 veto。今次修正：(A) bench 開新 arm **`jev2`**——args 用 `jev/actions.py` 確定式填，填唔到先 escalate；(B) live hook 升級做 **`JevToolDecider`**（`before_model_callback`，System One 揀 tool + 填 args → 短回路出 tool call）。
- **Review → 4-arm JeV3（`runs_260921_1508`，15 題/arm）**：3-arm 證實「決策 call 開銷（54×~500ms serial RTT）> ctx 慳」——**再優化 1-token call 冇用，要唔好叫嗰啲唔使叫嘅 call**。開新 arm **`jev3`（tier-0）**：確定式就夠嘅決定位（工具路由 `route_tool`、RAG gate `doc_gate_rrf`、私隱 marker `privacy_flagged`、noUL asymmetric STOP-honor）全部換 0-call 規則（`jev/tier0.py`），sentiment 退出決策層照 chat，剩返嘅 mem score 用 `asyncio.gather` 並行。**結果係第一次同時贏 original（14.5s -22% / 564μ$ -5% / 準確度全面赢返 jev/jev2）**。

### 7.2 方法論（JEV 三版嘅「實現」研究：同一個決策點，三種做法嘅差別）

每版 JEV 都係「喺現有 agent 上面加一層決策層」，但三版對「邊啲決策叫 LLM、邊啲用規則」有根本唔同嘅答案。下面逐決策點解剖三版各自嘅**輸入 state → 決定方式 → 輸出 contract → 失敗時點做**，先至睇得清每版改善咗啲乜、付出咗啲乜。

#### 7.2.1 同一決策點，三版嘅做法

| 決策點 | jev（介面層） | jev2（真 JEV） | jev3（tier-0） |
|---|---|---|---|
| **工具：揀 tool** | JEV 1-token choice（`jev_choice_tool`）── 輸入：工具盤 5 個 + 用戶句；輸出：tool id + confidence | 同 jev | `route_tool` 純規則（`t0_route`）── 輸入：用戶句；輸出：tool id + 已填 args；**唔中先落 JEV choice，然後先 chat** |
| **工具：填 args** | chat 生成（`jev_args_step`，完整 generation call）| `jev/actions.fill_args` 確定式（`jev2_det_args`，0 ms / 0 tok），填唔到先 escalate | 喺 `route_tool` 入面同一步，0 ms / 0 tok |
| **RAG gate** | 逐份候選 JEV score（`jev_doc_gate`，0-3）→ pool-relative keep | 同 jev | retriever RRF 實分（`t0_doc_gate`）→ `keep iff ≥ max(1e-9, 0.6×pool_max)`；淨剩 1 條又唔係 gold → `lowscore` flag |
| **記憶 gate** | 逐條 `decide_score`（`jev_mem_gate`，串行）| 同 jev | 先 `privacy_flagged` 硬 drop（`t0_mem_rule`），剩低 `asyncio.gather` 並行 `decide_score` |
| **情緒分類** | JEV choice 3 選 + confidence | 同 jev | **退出決策層，照 chat（`sent_label`）** |
| **workflow 續做 noUL** | JEV noul（`jev_cont`）→ 低 conf escalate chat | 同 jev | asymmetric：**STOP 一律 honor（唔理 confidence），只有 YES 先過 `CONT_CONF_MIN`**；低 conf YES 至 escalate |
| **escalation 鏈** | JEV → chat | **JEV → det-args → chat**（choices/args 低質或填唔到先落 chat）| **tier-0 → JEV → chat（三層）** |

- **三版輸出 contract 統一**：決策層永遠只出「choice / score / noul + probabilities/confidence」，唔出 prose、唔出 JSON tool-call 之後嘅內容；最終答案同 escalation 永遠落 System Two chat。所以三版嘅準確度差異只可能來自「邊啲位決定得啱唔啱 / 慳咗幾多 call」，唔係生成能力唔同。
- **jevs2 個「真 JEV」稱號點解成立**：決策 + args 都零 generation，System One 由「介面」變成「完整動作產生器」── 但佢仍然係「每個決策位一個 call」，所以準確度冇變，只慳咗 args 嗰個 chat call。
- **jevs3 先至郁「決策係咪要 call」本身**：親手把「deterministic 就夠」嘅位全部抽走（工具路由、RAG gate、私隱 marker、STOP honor = 35 個位），剩返嘅 14 個先係真‧判斷位（mem score 11 + wf 續做 3），而且 mem 11 個仲並行。
- **成本層次**（每版由平到貴嘅 call）：original = 0 喼決定；jevs3 = 35 個 0-call 規則 + 14 個 1-token；jevs2 = 53 個 1-token；jev = 57 個 1-token（含 args step）。**call 數由 21（original）→ 27（jevs3）→ 64（jevs2）→ 69（jev）**，但 jevs3 嘅 27 個入面 11 個係並行，serial 肯定少過 original（詳見 §7.3 ledger）。

#### 7.2.2 題目、模型、計價、閘門由嚟

- **對照**：`original`（所有決定全 chat）vs `jev`（介面層）vs `jev2`（真 JEV）vs `jev3`（tier-0）——四 arm 同一 5-tool 工具盤、同一 15 題、同一 System Two 生成層（flash chat）。唯一唔同係「決定 + args」行邊條路。
- **題目（15 題/arm）**：`datasets/jev5_{tool,rag,mem,sent,wf}.jsonl`。工具 3（calc / read_news_file / web_search）；RAG 4（3 fact + 1 trap，每題注入一份無關 `noise_*` doc 落候選池）；記憶 3（2 selection + 1 私隱-negative，含 `總倉位` marker）；情緒 3（pos/neg/neu）；workflow 2（multi-step + noUL 停止位，題內每 step 帶 `gold_stop` + `cont[]` 黃金 boundary）。
- **決策模型**：`seed-1-6-flash-250715`（seed-1.6-mini 喺本 account 唔存在 → fallback flash）——所以「決策慳」係純 interface 收益（1-3 token + probabilities/confidence），唔包「模型細咗」。計價：P $0.021/M、C $0.211/M、cached $0.004/M；arm 成本用 **μ$**（`jev/ledger.musd`）。
- **閘門 threshold 由嚟**：smoke（n=1/任務）實測 calibrate，**唔係 cross-val**。初版 RAG gate 用絕對 score（2.0）將 gold doc（judge 一題打 1.64、另一題得 0.09–0.81）誤剪 → 改 pool-relative 對抗 0-3 judge scale drift；jevs3 改成 retriever RRF 分（`T0_RRF_ABS=1e-9 / RATIO=0.60`）直接同 drift 絕緣。mem gate 絕對 2.0。
- **指標**：tool pass；RAG recall@5 ＋ answer-F1 ＋ trap_pass；mem answer-F1 ＋ selection R ＋ leak；sent pass；wf stop-exact ＋ noUL 命中率。小 n 下 Brier 唔用，改 mean abs error。
- **可重現性**：`cd projects/fin_mate && ./.venv/bin/python -m experiments.jev_bench.run`（資料/決策層喺 `jev/`、`experiments/jev_bench/`）。

### 7.3 JEV 嘅實現（我哋個 System One 決策層）

- **`jev/policy.py`** — 權限/閘門常數（`TOOL_CONF_MIN`、`SENT_CONF_MIN`、`CONT_CONF_MIN`、`RAG_KEEP_FLOOR/RATIO`、`MEM_GATE_MIN`）+ `gate_keep()`／`should_fallback()`（confidence 低過 threshold → escalation 去 System Two）。
- **`jev/decisions.py`** — state packer 同 rubric：`tool_state/doc_state/mem_state/cont_state`、`DOC_RELEVANCE_RUBRIC`、`MEM_RELEVANCE_RUBRIC`、`TOOL5`、`sent_opts()`＋`LABEL_LEVEL`（negative=0/neutral=1/positive=2）。
- **`jev/gate.py`** — `JevDecision`（kind/gate/ms/tokens/probabilities/confidence/score/choice/noul/escalated）；三個 public entry：`decide_choice`（分類）、`decide_score`（0..levels-1 score）、`decide_noul`（Y/N + probability）；`_maybe_resolve_model()` 保證 decision model 淨 resolve 一次。
- **`jev/ledger.py`** — `Ledger`：`usd()`／`musd()`（μ$ 精算）+ `now_ms()`；每 decision 嘅 ms/tokens 都有記錄（`events.jsonl` 落 `jev_*` stage）。
- **`experiments/jev_bench/lib/jev_client.py`** — 底層 client：`choice/score/noul` + `resolve_decision_model()`（probe 一串 seed-1.6-mini alias，404 → 記 pref 之後用 flash，logprobs 攞到先出 confidence/probabilities）。
- **`jev/actions.py`** — 真 JEV 確定式動作盤：`fill_args(tool, text)`（calc `target ±N%`/合法算式、read_news_file `*.csv`、fetch_news ticker、web_search/kb query、URL regex）+ `LIVE_TOOLS`（live decider 選項盤）；填唔到回 `None` → escalate。**bench `jev2` arm 同 live decider 共用**。
- **`jev/tier0.py`** — JeV3 tier-0 確定式決策層（bench-only，0 ms / 0 tokens / 0 call）：`route_tool(t)`（`.csv`→read_news_file、URL→link_reader、`_calcish` 算式→calc、搜尋動詞→web_search、`\$?[A-Z]{1,5}`→fetch_news，否則 `None`）、`privacy_flagged(mem)`（私隱 marker regex，`T0_MEM_MARKER_DROP`）、`doc_gate_rrf(cands, scores, gold_tags)`（retriever RRF score 閘門 + `lowscore` flag）——見 `policy.T0_*` 常數。
- **`agent_build.py`** — 實裝 hook：`JevToolDecider`（live `before_model_callback`：System One 揀 tool + 確定式填 args → 短回路出 `LlmResponse(function_call)`，只有低 conf / 填唔到 / 揀到 `N` / 唔係新 user turn 先 escalate 去 System Two）+ `attach_decision_gate(agent)`，**env `FIN_MATE_JEV=1` opt-in**（唔開 = 原裝行為完全唔變）；bench harness（`run.py`）唔靠呢個 hook，直接用 `jev/gate` 對三 arm 做 A/B。
- **`run.py`** — 4-arm harness：5 任務×N 題，寫 `jbv_{arm}/{events,rows}.jsonl` + `report.md`，頂層 `SUMMARY.md`；`--smoke`（每任務 1 題）／`--only`（`original,jev,jev2,jev3`）。`jev2` 嘅 det-args 落 `jev2_det_args` event（`det=True`，ms/tokens 都係 0）；`jev3` 嘅 tier-0 落 `t0_route` / `t0_doc_gate` event（`t0=True`）；`_jestats` 將 stage 以 `jev_` 開頭當決策 call（`jev2_det_args` 唔帶 `jev_` 前綴，所以 jev2 統計係 53 而 jev 係 57）。

**三版喺一次 15 題 run 入面嘅 call ledger（`runs_260921_1508`，由 `events.jsonl` stage 計）**

| stage（事件）| original | jev | jev2 | jev3 | 係咩 |
|---|---|---|---|---|---|
| `tool_json` | 5 | — | — | — | chat 出 tool-call（3 工具題 + 2 wf substep）|
| `t0_route` | — | — | — | 5 | tier-0 工具路由（0 ms / 0 tok）|
| `t0_mem_rule` | — | — | — | 1 | 私隱 marker 硬 drop |
| `t0_doc_gate` | — | — | — | 29 | RRF gate 逐 cand 記分（local）|
| `jev_choice_tool` | — | 3 | 3 | — | 1-token 揀工具 |
| `jev_args_step` | — | 4 | — | — | **args 用 chat 生成**（決策 call 計入）|
| `jev2_det_args` | — | — | 4 | — | args 確定式（0 ms，唔計決策）|
| `jev_doc_gate` | — | 29 | 29 | — | judge 逐 cand score |
| `jev_mem_gate` | — | 12 | 12 | 11 | 記憶 score（jev3 並行）|
| `jev_sent_choice` | — | 3 | 3 | — | 1-token 情緒 choice |
| `jev_choice_step` | — | 2 | 2 | — | wf 內工具 substep choice |
| `jev_cont` | — | 3 | 3 | 3 | noUL 續做 decision |
| `sent_label` / `cont_chat` / `answer` / `mem_answer` / `step_answer` | 5+3+3+2 | 2+5+3+2 | 1+5+3+2 | 3+5+3+1+1 | System Two chat 生成 |
| **決策 call 總數** | **0** | **57** | **53** | **14（+35 tier-0）** | `_jestats` |
| **LLM API call 總數** | ~21 | ~69 | ~64 | ~27（11 條並行）| 決策 + chat |

- 讀法：jevs3 唔係「少咗決策 call」咁簡單——佢係**把 53 個 1-token call 拆成 35 個 0-call 規則 + 14 個 1-token + 4 個退出**（sent 3 + 原本 29+12 入面嗰啲唔使 score 嘅位）；同時把 mem 11 個並行令 serial 數目低過 original 都仲得。

### 7.4 Phase-1 結果（`runs_260921_1324`，39 題/arm）

| task | original | jev_tools |
|---|---|---|
| 工具調用 | 10/10 | 10/10 |
| RAG 單源事實（recall/F1）| 0.818 / 0.085 | 0.818 / 0.069 |
| RAG 跨源推理（recall/F1）| 0.750 / 0.121 | 0.750 / 0.179 |
| 情緒分類 | 6/6 | 6/6 |
| 記憶召回 | 0.360 | 0.436 |
| 總計 | 41.0s **$0.0017** | 50.5s **$0.0017** |

Jev telemetry：30 decisions、median 515 ms、mean confidence 0.579、**noul flags 5/10**（false-positives）。結論：介面唔帶嚟正確率差；慳唔到錢（淨係換 tool pick）；noUL boundary 係弱位。

### 7.5 四 arm 總結果（`runs_260921_1508`，15 題/arm，supersedes `runs_260921_1930` 3-arm 版／`runs_260921_1354`）

**正確率**

| 任務 | n | original | jev | jev2 | **jev3（tier-0）** |
|---|---|---|---|---|---|
| 工具路由 | 3 | 3/3 | 3/3 | 3/3 | **3/3（全 tier-0，0 ms / 0 tokens）** |
| RAG recall@5 | 3 | 1.000 | 1.000 | 1.000 | 1.000 |
| RAG answer-F1 | 3 | 0.062 | 0.027 | 0.037 | 0.049 |
| RAG trap（唔好老作）| 1 | 1/1 | 0/1 | 0/1 | **1/1** |
| 記憶 answer-F1 | 3 | 0.477 | 0.500 | 0.667 | **0.857** |
| 記憶 selection R（jev 系先有）| 3 | — | 1.00 | 1.00 | 1.00 |
| 私隱 leak（3 題計）| 3 | 0 | 0 | 0 | 0 |
| 情緒分類 | 3 | 3/3 | 1/3 | 1/3 | **3/3** |
| workflow stop-exact | 2 | 1/2 | 1/2 | 1/2 | **2/2** |
| noUL 判斷準確（per-boundary）| 3 | 2/3 | 2/3 | 2/3 | **3/3** |

> 註 1：私隱 leak 呢個 run 四 arm 都係 0；1930 run 嘅 original 試過 1（run variance，見 §7.8 洞察 3）。註 2：SUMMARY 個 telemetry「noul YES flags 2/3」係原始旗標數（wf_01 兩格 YES + wf_02 一格 NO），唔係準確度；jev3 嘅 per-boundary noUL 準確度係 **3/3**（stop-exact 2/2）。

**延時／成本（med ms/題；arm 總計）**

| | original | jev | jev2 | **jev3** |
|---|---|---|---|---|
| 總計 | 18.6 s | 46.5 s（+150%）| 44.2 s（+138%）| **14.5 s（-22%）** |
| $ | 593 μ$ | 721 μ$（+22%）| 737 μ$（+24%）| **564 μ$（-5%）** |
| tokens（P/C）| 21,169 / 702 | 23,502 / 1,079 | 23,081 / 1,196 | **22,782 / 405** |
| decisions | — | 57 | 53 | **14（tier-0 頂 35）** |

**延時解構（點解 jev/jev2 單步贏、總時輸；同 jev3 點樣解返開）**

「快」要分兩層睇，四 arm 各自最快嘅位不同：

| 層面 | original | jev | jev2 | jev3 | 最快 |
|---|---|---|---|---|---|
| 單步工具路由（med ms）| 608 | 1,009 | 524 | **0** | jev3 |
| 全 run 總時（s）| 18.6 | 46.5 | 44.2 | **14.5** | jev3 |

點解 3-arm 嗰陣 single-step 贏、total 輸（JeV3 之後先解到）：

1. **original 根本冇「決策階段」——決策係 chat call 嘅副產品，額外 0 ms / 0 call。** jev / jev2 係「喺 chat 之上再疊一層」：成個 run 53–57 次決策 call，每次係獨立 serial network round trip（median ~529–546 ms）——純 overhead，唔係取代任何 chat call。
2. **ctx 慳嘅時間對比決策 RTT 係零頭。**RAG gate 將答案 prompt 由 ~4KB 剪到 ~2.4KB（-40%），但對 remote LLM 嚟講細 prompt 慳嘅只係幾十 ms 級；反之每次決策 call 係 ~500 ms serial RTT——54 次串埋 ≈ +27 s。
3. **jev2 vs jev：慳咗 args chat，但總時照樣輸。**jev2 單步 1,008→471 ms 係慳咗「args chat call」嘅證據；但決策 call 數量冇少到，38–40 s 嘅區 冇變過。
4. **延時同成本同一結構（call 次數主導）**：original 最少 call → 最平；決策有價，但細 context scale 下 RTT + tokens 值唔返慳落嚟嘅 context。

**JeV3 嘅答案唔係「慳 call」係「唔叫嗰啲唔使叫嘅 call」**——凡係 deterministic 就夠嘅決定位（工具路由、RAG gate、私隱 marker、STOP honor）全部落 `jev/tier0.py` 確定式規則，決策 53–57 → 14，剩返嘅 mem score 又用 `asyncio.gather` 並行（RTT 攤開）。四 arm 總時 14.5 s + 564 μ$ —— **第一次同時贏 original（speed + cost），準確度全面贏返 jev/jev2。**

### 7.6 JEV 三版比較（jev → jev2 → jev3 頭對頭）

#### 7.6.1 每個決策點行嘅 call 同時間

| 任務 | jev | jev2 | jev3 | 演化 |
|---|---|---|---|---|
| 工具路由 | choice + *chat args*：1,009 ms，2 call | choice + det-args：524 ms | t0 rule：**0 ms，0 call** | 每步 -1 call 再 -1 call |
| RAG gate | 29× judge score：4,911 ms | 29× judge score：5,045 ms | 29× RRF local：**1,178 ms** | judge 唔玩 → retriever 實分 |
| 記憶 gate | 12× 串行 score：3,627 ms | 12× 串行 score：3,215 ms | marker+11× **並行**：1,509 ms | 並行→RTT 攤開 |
| 情緒分類 | 3× choice：553 ms | 3× choice：520 ms | **零 decision**：589 ms（淨 chat）| 退出決策層 |
| workflow+noUL | 2 choice + 3 noul + escalate：5,622 ms | 同左：5,607 ms | 3 noul（asymmetric）：**1,741 ms** | STOP 唔再 escalation |
| **決策 call 數** | 57 | 53 | **14 + 35 規則** | 54 → 14 |
| **LLM API call** | ~69 | ~64 | ~27 | call 總數跌返接近 original（21）|

#### 7.6.2 準確度逐位（三版各自喺邊度錯過 / 贏返）

| 位 | jev | jev2 | jev3 | 得着 |
|---|---|---|---|---|
| 工具 3/3 | ✓（choice 對）| ✓（args 確定式）| ✓（route 直接命中）| jev3 唔使 choice 都識，靠 regex/fillers |
| RAG gate | ⚠️ over-prune：gold 喺 rag_03 被剪（**ctx=0**）→ F1 0.08 | 同 jev（ctx=0） | ✅ gold 三題全保（ctx=5）→ F1 0.146 | judge 分數唔穩係根源；RRF 直接係 retriever 排序 |
| trap | ✗ ctx=0 後 answer 補白 | ✗ 同 jev | ✅ 5 份去咗 noise 嘅 context → 答「無資料」 | 唔係 gate 更嚴，係 context 唔再誤導 |
| 記憶 F1 | 0.500 | 0.667 | **0.857** | 全線 keep 2/4（selR 1.0）；並行冇犧牲選擇品質 |
| 私隱 leak | 0 | 0 | 0（marker 硬規則）| jev3 呢個位由「score 靠住」變「regex 保證」 |
| 情緒 | 1/3（兩題誤判）| 1/3 | 3/3 | 1-token 分類唔係分類位——換 chat 即刻贏返 |
| noUL | 2/3、wf_02 OVER | 2/3、OVER | **3/3、stop-exact 2/2** | conf 0.02 嘅 STOP 而家直接 honor，唔再 escalation 變 OVER |

#### 7.6.3 三版各自「邊個 idea 係啱、邊個係盡頭」

- **jev**：證明「決定同生成可以拆」——choice/score/noul 全部唔靠 generation 都揀到啱嘢；但佢嘅盡頭係「**每個決定位都要一個 RTT**」同「**args 仲係 chat**」。
- **jev2**：證明「args 可以確定式」——單步 524 ms、args 0 tok；佢嘅盡頭係「**純化冇郁到根本問題**」：決策 call 數量冇少，準確度一項都未贏返。
- **jev3**：證明「好多決定位根本唔使 call」——35 個變規則、剩低 14 個仲並行、sent 退出；**先係三版入面唯一同時贏速度+成本+準確度嘅（但其淨贏大頭係 hard-coded 規則，唔係「System One 勁過 chat」，拆分見 §7.8 洞察 9）**。教訓：JEV 嘅價值唔係「用 1-token 取代 chat」，係「**用正確階層取代唔啱嗰層**」（0-call 規則 → 1-token 判斷 → chat 生成）。

### 7.7 四 arm 最終回顧

| 維度 | 贏家 | 點解 |
|---|---|---|
| 準確度 | **jev3**（連 original）| 5 個任務全數最高或打和：sent/trap/noUL/stop-exact 贏返、mem F1 最高、工具/RAG recall 打和 |
| 延時 | **jev3** | 14.5 s，連 original 都輸 4.1 s（-22%）|
| 成本 | **jev3** | 564 μ$，比 original 平 29 μ$（-5%），比 jev 平 157 μ$ |
| 最慳 call | original（21） | jev3 27 個但 11 個並行，serial 反而最少 |
| 可解釋性/可維護 | **jev3** | 每個決定都有 logs（t0_* / jev_*），規則可 review，唔使罰 57 次黑盒 confidence |
| 靈活性（新題目）| jev/jev2 | tier-0 手工規則越多，改課題要同步加規則（§7.8 洞察 5）|

**四 arm 順位**：**jev3 ≻ original ≫ jev2 ≈ jev**。詳情：

1. **original** —— 產生式嘅界線好精緻：決策 = chat generation 嘅副產品，零額外 RTT。呢個 scale 佢係「免費決定」嘅標竿，冇「決策層」嘅 overhead；弱位係決定唔可以分層/審計/優化（judge 同 gate 冇得獨立掂）。
2. **jev** —— 第一個「決定/生成拆開」嘅實現，但係喺最不利嘅條件下做（每決定補多一個 serial RTT），而且 args 未拆。佢嘅實驗價值係**證明 JeV 介面本身唔帶準確率損失**（choice 全部揀啱），示威好過實戰。
3. **jev2** —— 「真 JEV」嘅起點（args 零 generation），單步最慢位都收返，但係本質同 jev 一樣：每決策一個 call。佢嘅實驗價值係**證明「純化」唔夠**——準確率問題係「決定位揀錯」唔係「搞唔乾淨」。
4. **jev3** —— 行返「original 點解快」嗰條路：原樣用「零額外 call 嘅決定」，但換成**可審計嘅確定式規則**，做到同 original 一樣「決定 = 副作用」，但副作用係 deterministic 而唔係模型意志。**決策層由 54 個 1-token RTT 縮到 14 個，先至由「開銷」變「收益」。**

隱含一個較大嘅 insight：**「快」唔係計「每個決定幾慢」，係計「有幾多個 serial hop」**。original 快因為決定「搭」喺 chat hop 入面（0 個額外 hop）；jev3 快因為決定「跌」出鏈路（0 個 hop）；jev/jev2 慢因為每個決定多一個 hop。未來任何決策層設計都應該以「hops」做 budget，唔係「token 數」或「call 數」。

### 7.8 深入調查同洞察

#### 洞察 1：工具路由——命中 5/5，其中一個位修返咗 fill 機制本身
`route_tool` 5/5（3 工具題 + 2 wf substep），args 100% 確定式：calc `187*1.15`（target rule）、read_news_file `.csv` path、web_search 原句、fetch_news `MSFT`、calc `(42*17+9)/3`。最後嗰條係**新修返嘅位**：wf_02 用 full-width `（42*17+9)/3`，`_fill_calc` 而家 normalize `（）→()`，所以唔再 escalate（jev2 喺呢個 substep 本來要落 chat）。另外揾出一個潛伏 bug：`_safe_eval_expr` 一直無哩（`ast.walk` 連 operator 節點都 yield，被當成唔准）——之前冇爆發純粹因為工具題都行 target-PCT 規則入面條 path。

#### 洞察 2：RAG——judge（jev/jev2）同 retriever（jev3）嘅本質分別
四 arm 嘅 gate 行同一批候選，但做法唔同：
- `jev/jev2`（LLM judge 0-3 score）：js5_rag_03 個 gold doc 被打低分 → **ctx=0**，answer 冇料 → F1 得 0.08/0.111。呢個係 1930 run 一路以嚟嘅 over-prune 問題重現，即係同「純化」無關、係 judge 衡量穩定性問題。
- `jev3`（retriever RRF 實分，`T0_RRF_RATIO=0.6`）：三題 gold 全保（ctx=5），只剪走注入嘅 `noise_*`（score 0.0 < 1e-9）；js5_rag_03 F1 0.146（同 original 0.186 同級）。**RRF 分係 retriever 原生排序嘅副產品，0 個 judge call、0 個 drift risk。**
- `lowscore` flag（淨剩 1 條非 gold 時 fallback 語料偏弱）呢 run **冇觸發**（trap 題 keep 咗 5 條，都係真 doc）——佢係「ctx=0 補白」嘅第二重保險，設計保留。

#### 洞察 3：Trap 同 leak 係 run-variance 唔好過度詮釋
- **Trap**：jev/jev2 ctx=0 之後 answer 層上完成「KB 無資料」模板 → 泛泛而談（trap fail）；jev3 同 original 一樣有 5 份真實 context → answer 答「無資料」（pass）。即係 trap 幫唔幫到唔係「gate 更嚴」而係「context 唔再誤導」。
- **Leak**：私隱 marker（`總倉位`）今 run 四 arm 都冇漏（original 都 0）；1930 run original 試過 1。**結論要睇穩定性唔係睇單值**：jev 系三 arm 兩 run 都 0，先係結構雜質。jev3 更加用 regex 硬 drop（`t0_mem_rule`），由「靠 score 攔住」變成「結構保證」。

#### 洞察 4：記憶——並行冇犧牲品質，F1 升係「keep 得準 + answer 撞啱」疊加
- 三版 keep 都係 2/4、selR 1.0；私隱題 keep 1/4。jev3 嘅 4 條 `decide_score` 用 `asyncio.gather` 並行（1-token interface 一次一個 answer，並行係靠 concurrency），單步 3.2 s → 1.5 s。
- F1 數字要小心讀：js5_mem_01/02 jev3 去到 1.000，但 jev2 都喺 0.556–1.000 之間跳——**keep list 一樣嘅前提下剩下嘅差異係 answer call variance**。淨係講「jev 系 > original」先係穩陣（keep 咗無關記憶會直接拖低 answer）。

#### 洞察 5：noUL asymmetric——「錯嘅方向唔同代價唔同」
js5_wf_02 個 boundary（gold STOP）：System One 出 STOP 但 conf 得 0.0249——舊 symmetric 會 escalate → chat 傾向 YES → **OVER**（四 arm 入面 jev/jev2/original 全部 OVER）。asymmetric 嘅哲學：**STOP 唔使過閘，YES 先要**——喺 FIN-MATE 度「多行一步」嘅後果（作料/over-long）比「早收一步」嚴重，所以 STOP 係 safe-by-default。asen 之後 wf_02 一格【STOP@conf0.02】直接 honor → stop-exact 2/2。代價係假設「唔要下步」冇 false STOP（呢個只可靠更多 case 驗證）。

#### 洞察 6：成本結構——tokens 都係淨贏
C-tokens：original 702 → jev 1,079 → jev2 1,196 → **jev3 405**。決策 call 每個淨出 1-3 tok，但 53 個累埋仲多過 chat 生成；jev3 14 個決策 + 少咗 escalation/trap 補白，輸出 tokens 跌到最低，連帶 C 計價都慳。**即係決策層正確設計之後，tokens 唔止唔加，仲慳返。**

#### 洞察 7：threshold 全數喺 smoke（n=1/任務）calibrate——呢個係已知限制
RAG pool-relative floor（0.50/0.60）同 mem 2.0 都係一個題目度校；jev3 嘅 RRF threshold（`T0_RRF_ABS/RATIO`）都一樣語氣。n 細 + threshold 冇 cross-val → 正確率有 ±1 題級波幅，尤其 answer-F1。結論方向唔變，但絕對值要打格。

#### 洞察 8：對 live 層嘅含義（bench-only 至今）
`JevToolDecider` 而家仲係 jev2 邏輯（choice + `fill_args`）。要行去 jev3：`route_tool` 做第一層（0 call）+ 1-token 做 fallback；RAG gate 轉 `doc_gate_rrf`；sent 唔好接決策層；noUL asymmetric 接 live chain。全部 `FIN_MATE_JEV=1` opt-in 下先郁。**另一條路**：大 context agent 上量 prompt-caching 回本線（§7.7 嘅「hops budget」設計原則一樣適用）。

#### 洞察 9：淨贏嘅功勞拆分——大頭係 hard-coded 規則，唔係「真 JEV」

JeV3 全場（速度／成本／大半準確度）淨贏，**唔係因為 System One interface（真 JEV）勁咗，係因為嗰啲位根本唔使 call LLM**。逐改動拆開：

| jev3 改動 | 係咪「真 JEV」（System One LLM 決策）| 佔嘅收益 |
|---|---|---|
| 工具路由 `route_tool`（regex/fillers，0 ms）| ❌ 純規則 | 工具 step 608→0 ms、慳埋成串 choice+args |
| RAG gate `doc_gate_rrf`（RRF 實分）| ❌ retriever 原生算法 | RAG 4,911/5,045 → 1,178 ms、gold 唔再誤剪 |
| 私隱 marker regex 硬 drop | ❌ regex | leak 由「靠 score 攔」變「0 call 保證」 |
| noUL asymmetric STOP-honor | ❌ 規則 | wf 5,622/5,607 → 1,741 ms、stop-exact 2/2 |
| sentiment 退出決策層照 chat | ❌ 「唔用決策層」| sent 1/3 → 3/3（chat 本身贏返）|
| mem score 11 個（gather 並行）| ✅ 係 | F1 0.857＋單步 1,509 ms——但 F1 升幅混咗 answer variance |
| wf noul 3 個 | ✅ 係 | per-boundary 3/3（conf 0.02 嗰格最終係靠 asymmetric 規則至唔 escalate）|

**即係**：真 JEV 喺 JeV3 得返 14 個 decision，係「必要但唔足以獨攬功勞」；冇咗硬規則佢照樣輸。所以準確講法係「**tier-0 取締 call／決策層正確分層嘅架構價值成立**」，唔係「真 JEV 價值成立」（上一版 docs 嗰句已收回，見 JEV_REPORT ⚠️7）。

**Phase-2→JeV3 判詞（更新）**：三條硬傷（judge over-prune、sent 1/3、決策 call 開銷 > ctx 慳）喺 **JeV3 全部郁到**——做法係「判定位唔好叫 LLM」：確定式嘅（tool/RAG gate/私隱/STOP）用規則，真‧判斷先用 1-token（仲並行），分類唔係分類位嘅（sent）退出決策層照 chat。**第一次喺細 context scale 都做到淨錢 + 淨時 + 準確全面赢返 original、兼贏返所有 JEV 前版。注意呢個淨贏嘅大頭係 hard-coded 確定式規則（regex、retriever 分、marker）同「退出決策層照 chat」，唔係「真 JEV＝System One interface 勁啲」——真 JEV 剩返唯 14 個 decision 係必要但唔足以獨攬功勞（拆分見 §7.8 洞察 9／JEV_REPORT ⚠️7）。** 餘下：RAG answer 層（ref-gold 對比）係獨立課題；live 層未換 tier-0（bench-only，見 JEV_REPORT）。

---

## 附錄 A：所有 run 一覽

| run | 日期 | 內容 | 題×pipe | tokens | err |
|---|---|---|---|---|---|
| `full_260908_1551` | 09-08 | naive/advanced/hybrid/corrective/adaptive | 16×5 | 299,007（5 pipe 合計；D4 總 408,174/500,000）| 0 |
| `full_agentic_260908_1601` | 09-08 | agentic | 16×1 | 109,167 (prompt) | 0 |
| rerank（none/rrf/llm）| 09-09 | Rerank Lab | 15×3 | 91,012 Ark + 17,871 local | 0 |
| rerank ce | 09-09 | cross-encoder（新 RAG 方法 §11）| 15×1 | 29,775 Ark | 0 |
| rerank llm_listwise | 09-09 | LLM listwise（§11）| 15×1 | 30,418 Ark + 8,665 local | 0 |
| hyde | 09-09 | HyDE | 15×1 | 49,974 | 0 |
| hyde_rrf | 09-09 | HyDE+RRF（§11）| 15×1 | 48,702 | 0 |
| `engine_bench` | 09-09 | Ollama vs Ark | 12×10×2 | 120+120 次 call | 0 |
| eval `260909_2254/2255` | 09-09 | D6 golden 34 條（含 gate lock + 重跑）| 34×2 | ~68.8K/round | 0 |
| `runs_260921_1324` | 09-21 | JEV phase-1 refined：tool-choice Jev vs chat | 39×2 | 30 decisions（jev arm）| 0 |
| `runs_260921_1354` | 09-21 | JEV phase-2：全決策點 System One（gate 全開，2-arm）| 15×2 | 46,551（兩 arm 合計）| 0 |
| `runs_260921_1930` | 09-21 | JEV 3-arm：original vs jev（介面層） vs jev2（真 JEV，args 確定式）| 15×3 | 71,016（三 arm 合計）| 0 |
| `runs_260921_1508` | 09-21 | JEV 4-arm：+ jev3（tier-0：RRF gate / rule 路由 / marker / asymmetric noUL）| 15×4 | 93,916（四 arm 合計）| 0 |

D4 總耗 408,174/500,000（81.6%）；全部 D5 各自獨立 ≤150K budget。

## 附錄 B：執行誤差／caveat 陳述（出現過嘅坑同修正）

1. **corpus reseed ／ f12 剔出**：D4（16 題）同 D5（15 題）唔係同一 corpus 狀態；對照係「同一 8 份研報 + 同一 15 題」，但逐題 URI-prefix 個別 run 自洽。
2. **token 計數一度低估 corrective/adaptive**：events 淨記 answer-stage → 由 transcript 全 call 重計（§2.5 為準）；舊數 20,269 已作廢。
3. **nDCG >1**：metric 特性（同 doc 多分片計相關），非超越理想排序（METHODOLOGY §5.1）。
4. **rerank「rrf」首版 bug**：`_rrf` 返 doc-prefix 令 answer ctx 空 → 假答案 0.039；`_pref_to_chunk()` 修正後 0.114（§3 全用修正後數字）。
5. **answer-F1 偏低唔等於答錯**（表述/語言問題）；真正 fact-check 要人判或 LLM judge。
6. **agentic 退役後**：相關執行細節（fresh subprocess、tracers=[]）只係歷史記錄，唔再行。
7. **Engine bench Ark usage 唔齊**（streaming）：tok/s 及 $ 列有 `estimate_tokens` fallback，TTFT/total 係真 timestamp。

## 附錄 C：定案（用戶）

- falsified citation 一票當 fail；trap 唔肯講「無資料」＝ fail。
- 全部 run 唔可以超過 500K tokens（D5 各新 type 獨立 ≤150K）。
- `ByteDance-Seed-1.6` ⇒ alias `seed-1-6-flash-250715`（其餘 alias 全 404）；`thinking=disabled` 為必需。
- agentic 退役；rerank 結論「唔用」；production retrieval = hybrid。
- D6：gate = regression vs baseline（`--lock-baseline`）；tool_call = harness 真執行；CI = 本地 `make eval`；engine_bench concurrency 1 / iter 10。
- JEV bench：report 只可引 phase-1（`runs_260921_1324`）、phase-2（`runs_260921_1354`）、3-arm（`runs_260921_1930`）同 4-arm（`runs_260921_1508`）；`jbv_full`／`jbv_full2` 唔入任何 report。
- JEV 四個相位都用同 model（`seed-1-6-flash-250715`，mini 缺席 → fallback）：「決策層 = interface 收益」。
- 3-arm 起：`jev2`（真 JEV）= args 一律 `jev/actions` 確定式填，填唔到先 escalate；live 層用 `JevToolDecider`（`before_model_callback`），唔再用舊嘅 `JevToolAuthorizer`（veto）。
- 4-arm 起：`jev3`（tier-0）= 確定式決定位（`route_tool`／`doc_gate_rrf`／`privacy_flagged`／asymmetric noUL）唔好叫 LLM，`jev/tier0.py` 淨喺 bench 驗證，live decider 未接。
- RAG doc gate 用 pool-relative（floor 0.50 / ratio 0.60，jev/jev2 係 LLM judge；jev3 一律 retriever RRF `T0_RRF_ABS=1e-9 / RATIO=0.60`），threshold 喺 smoke（n=1/任務）上校；mem gate 用絕對 2.0。
- RAG gold 校正過一版：DB doc 嘅正確事實係「Intelligent Cloud +28.0% vs 舊預測 +27.5%」，唔係一時寫錯嘅「38 percent」。