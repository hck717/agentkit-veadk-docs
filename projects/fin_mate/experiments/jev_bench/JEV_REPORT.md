# JEV agent bench：original vs JEV 介面層 vs 真 JEV vs JeV3（tier-0）

> `runs_260921_1508` · 2026-09-21 · 15 題 × 4 arm（supersedes `runs_260921_1930` 3-arm 版）· decisions model = seed-1-6-flash-250715（seed-1.6-mini 喺本 account 唔存在 → fallback flash，即「決策層 = interface + 1-3 token + probabilities/confidence」嘅純對照）

## TL;DR
三台階問題一路係：**決定 call（~54 × ~500 ms serial RTT）取代咗「chat 嘅副產品決定」，反而輸畀 original。** 到 jev2（真 JEV：args 都確定式）單步慳到 471 ms，但總時照輸（41.8s vs 16.5s）、錢照加（705 vs 598 μ$）——因為「介面 call 再慳都係多啲 RTT」。

**JeV3 嘅做法唔係再優化決定 call，係直接唔好叫佢**：呃「1-token 都係 chat 縮影」嘅位，全部換 tier-0 確定式規則（0 ms / 0 tokens / 0 call）：

| 決策點 | jev/jev2（1-token JEV） | **jev3（tier-0 規則）** |
|---|---|---|
| 揀工具 + args | JEV choice + 確定式 fill | 純 regex/rules `route_tool`（`.csv`→read、URL→link、算式→calc、搜尋動詞→web、ticker→fetch），命中即 0 call |
| RAG gate | score+conf judge（會誤剪 gold） | retriever RRF score 閘門（`doc_gate_rrf`）——gold 三題全部保住，trap 1/1 |
| 記憶 gate | score->keep | 私隱 marker 硬規則先 drop；剩低 parallel `decide_score`（RTT overlap） |
| 情緒分類 | 1-token choice（1/3） | 退出決策層，照 original chat（→ 3/3） |
| workflow noUL | symmetrical conf gate（低 conf escalate 會拖累 STOP） | asymmetric：**STOP 一律 honor**，只有 YES 先過 conf_min → stop-exact 2/2 |

**結果（runs_260921_1508）：後台 `jev3` 14.5 s / 564 μ$ — 快過 original 4.1 s、平過 original 29 μ$，而準確度全部贏返 jev/jev2。** 工具路由 step 0 ms；RAG gold 唔再被誤剪（閘門由 unstable judge 換做 retriever RRF 實分）；trap 由 0/1 → 1/1；情緒 1/3 → 3/3；noUL 判斷 3/3、workflow stop-exact 2/2；記憶 F1 0.667 → **0.857（四 arm 最靚）**、私隱 leak 0。決策次數由 57/53 → 14（tier-0 頂咗 35 個決定位）。

> **⚠️ 認清楚（好重要）：JeV3 個「淨贏 original」唔係證明「真 JEV」（System One 1-token interface）勁咗，係證明「嗰啲位根本唔使 call LLM」——由 hard-coded 確定式規則（regex / fillers / retriever 分數 / marker）直接攞走咗。** 真正剩返嘅「真 JEV」決策得 **14 個**（mem score 11 並行 + wf noul 3），而佢哋每一個嘅準確度貢獻都混雜咗 System Two answer call variance。即係：**速度／成本個大頭係 hard-coded rules，唔係 JEV；準確度嘅大頭係「退出決策層照 chat」＋「規則唔再剪錯」，一樣唔係 JEV 本身贏 chat。** 淨返證明到「決策層要識得分層（0-call 規則 → 1-token 判斷 → chat 生成）」呢個架構 insight。

## 點解 JeV3 先至得（一路以嚟嘅根因）
original 唔會輸，唔係因為佢勁，係因為**決定 = chat 已有嘅 generation 副產品（0 額外 call）**。任何「再開一條 call 嚟決定」嘅架構（jev/jev2 個 ~54 個 1-token score call）都硬多 ~27 s serial RTT + ~100 μ$，補唔返 ctx 慳（~4KB→2.4KB 值幾十 ms 級）。JeV3 先係真正對住「決策係咪一定要 call」落刀：**凡係 deterministic 就夠（工具路由、RAG gate、私隱 marker、STOP honor）都唔叫 LLM**，decision 由 54 → 14（剩返嘅都係真‧判斷：mem score ×2 組 + wf 續做），先由「決定開銷」變成「決定收益」。
- **慢一場**（sentiment 分類嗰 3 題）JeV3 退出決策層照 chat——因為 1-token 分類唔係分類位，唔好硬靠佢慳 call。
- **快一場**（忍補協議隔籬個 memory 組）就算要 score，同組 4 條用 `asyncio.gather` 並行——RTT 攤開，唔係 4 次 serial。

## 設計

### 四條 arm 嘅分工（同一 5-tool 工具盤 + 同一題目，唔同嘅只係「決定 + args」點做）

| 決策點 | original（全 chat） | jev（介面層） | jev2（真 JEV） | **jev3（tier-0）** | 閘門/policy |
|---|---|---|---|---|---|
| 揀工具（tool） | chat 出 tool-call JSON（含 args） | JEV choice → chat args | JEV choice → `jev/actions` 確定式 args | **`route_tool` 純規則，命中即 0 call** | `TOOL_CONF_MIN=0.5`；tier-0 唔中先至 escalate |
| RAG 檢索 gate | 全部候選入 context | judge score+conf | 同 jev | **retriever RRF score：keep iff ≥ max(1e-9, 0.6×pool_max)**；淨剩返一條又唔係 gold → `lowscore` | `T0_RRF_ABS / T0_RRF_RATIO` |
| 記憶篩選 pushdown | 全部記憶餵 answer call | 每條 JEV score | 同 jev | **先 `privacy_flagged` 硬 drop（marker regex），剩低 gather 並行 score** | `MEM_GATE_MIN=2.0` + `T0_MEM_MARKER_DROP` |
| 情緒分類 | chat 出 label | JEV choice（3 選） | 同 jev | **退出決策層，照 chat** | `SENT_CONF_MIN=0.4`（jev3 唔用） |
| 多步 workflow + noUL | 每步 chat tool-call；續唔續 chat YES/NO | JEV choice + JEV noul | 同 jev | **asymmetric noul：STOP 一律 honor，只有 YES 過 `CONT_CONF_MIN`** | `CONT_CONF_MIN=0.5` + `NOUL_STOP_ALWAYS_HONORED` |

- **`jev3` 嘅 order 係 residual**：tier-0 命中 → 零 call；唔中先落 JEV 1-token；JEV 都搞唔掂先 escalate chat。決策次數 57/53 → 14，tier-0 35 次。
- 決定模型 + prose 都係 flash——JeV3 嘅收益同「模型細咗」無關，純係架構位。
- `route_tool` 次序（most specific → generic）：`.csv` → read_news_file；URL → link_reader；`_calcish`（關鍵字 / `%` / 算式）→ calc（`actions` 填 `expr`，含 full-width `（）` normalize）；搜尋動詞 → web_search；`\$?[A-Z]{1,5}` → fetch_news；否則 None → escalate。
- `mem` 嘅「並行」= `asyncio.gather` 幾隊 `decide_score`（1-token interface，同組多條靠 concurrency 唔係多-answer）。
- 今次改動只係 bench 後台（`experiments/jev_bench/run.py` + `jev/tier0.py`）；live `JevToolDecider` 冇郁。

### 題目（15 題 × 4 arm）
工具 3（calc / read_news_file / web_search）、RAG 4（3 fact + 1 trap，每題注入無關 doc `noise_*`）、記憶 3（2 selection + 1 私隱-negative，含總倉位 marker）、情緒 3（pos/neg/neu）、workflow 2（multi-step + noUL 停止位）。

## 結果（`runs_260921_1508`）

### 正確率（15 題/arm）

| 任務 | n | original | jev | jev2 | **jev3** |
|---|---|---|---|---|---|
| 工具路由 | 3 | 3/3 | 3/3 | 3/3 | **3/3（全 tier-0，0 ms / 0 tokens）** |
| RAG recall@5 | 3 fact | 1.000 | 1.000 | 1.000 | 1.000 |
| RAG answer-F1 | 3 fact | 0.062 | 0.027 | 0.037 | 0.049 |
| RAG trap（唔好老作）| 1 | 1/1 | 0/1 | 0/1 | **1/1** |
| 記憶 answer-F1 | 3 | 0.477 | 0.500 | 0.667 | **0.857** |
| 記憶 selection R（jev 系先有）| 3 | — | 1.00 | 1.00 | 1.00 |
| 私隱 leak | 3 | 0 | 0 | 0 | 0 |
| 情緒分類 | 3 | 3/3 | 1/3 | 1/3 | **3/3** |
| workflow stop-exact | 2 | 1/2 | 1/2 | 1/2 | **2/2** |
| noUL 判斷準確（per-boundary）| 3 | 2/3 | 2/3 | 2/3 | **3/3** |

> 注意：SUMMARY 個 telemetry row 寫「noul YES flags 2/3」係**原始 YES 旗標數**（js5_wf_01 兩個 YES + wf_02 一個 NO = 2 flag / 3 boundary），唔係準確度。jev3 嘅 per-boundary 準確度係 3/3（兩題 gold Y/Y、N 全中，stop-exact 2/2）。

### 延時／成本（med ms/題；arm 總計）

| 任務 | original | jev | jev2 | **jev3** |
|---|---|---|---|---|
| 工具路由 | 608 | 1,009 | 524 | **0** |
| RAG 檢索 gating | 1,173 | 4,911 | 5,045 | **1,178** |
| 記憶篩選 | 1,250 | 3,627 | 3,215 | **1,509** |
| 情緒分類 | 613 | 553 | 520 | 589 |
| workflow＋noUL | 3,225 | 5,622 | 5,607 | **1,741** |
| **總計** | **18.6 s** | **46.5 s（+150%）** | **44.2 s（+138%）** | **14.5 s（-22%）** |
| **$（μ$）** | **593 μ$** | **721 μ$（+22%）** | **737 μ$（+24%）** | **564 μ$（-5%）** |
| tokens（P/C） | 21,169 / 702 | 23,502 / 1,079 | 23,081 / 1,196 | **22,782 / 405** |

Jev telemetry：jev3 14 decisions（med 546 ms、conf 0.640）、tier-0 35 次；jev 57 / jev2 53 decisions。**JeV3 係第一次喺呢個 scale 同時贏 original（speed + cost + accuracy）**——唔係因為「決定更快」，係因為 tone 就唔係一定要有決定 call 嘅位置，由 54 個縮到 14 個。

## 分析

### ✅ 1. Tier-0 工具路由：0 ms / 0 tokens / 0 call
`route_tool` 5/5 命中（3 題 + wf 2 substep），args 全部確定式：
- js5_tool_01 → `calc {"expr": "187*1.15"}`（target rule）
- js5_tool_02 → `read_news_file {"path": "data/news/sample_news.csv"}`
- js5_tool_03 → `web_search {"query": "<原句>"}`
- js5_wf_01 → `fetch_news {"ticker": "MSFT"}`；js5_wf_02 → `calc {"expr": "(42*17+9)/3"}`（fixed full-width paren normalize，jev2 呢個 substep 本來要 escalate）

`route_tool` 唔中先 fallback JEV + chat——今次 run 冇任何 tool decision call（工具 step 0 ms）。

### ✅ 2. RAG gate：由「unstable judge」轉做「retriever 實分」，gold 唔再被誤剪 + trap 修返
- js5_rag_03 舊 judge 誤剪 gold（ctx=0）喺 jev3 消失：**三個 fact item gold 全部保住**（RRF keep ≥ ratio floor），RAG 因而入返 answer 層料。
- **js5_rag_04 trap 1/1**：RRF 閘走晒注入嘅 `noise_e7`（score 0.0），**剩返嘅 5 份係真 doc**（`lowscore` 無觸發）→ answer 層見返冇被誤導嘅 context → 答「KB 無資料」（同 original 行為一致）。jev/jev2 0/1 嘅「ctx=0 之後補白」源自 over-prune 攞走晒 context；`lowscore` flag（淨剩 1 條非 gold 時）係另外設計嘅第二重保險，呢 run 冇觸發但保留。
- 揀 gate 由「LLM score」換「retriever RRF」係**同 scoring 本身嘅穩定性交換**：RRF 反映 retriever 原生排序，唔再受 judge drift 影響；突出成本唔加（score 喺 retrieval 已有）。

### ✅ 3. 情緒分類：退出決策層 → 3/3
確認 1-token 分類唔係分類位。JeV3 唔硬慳呢 3 條 call，照 chat → 3/3（同 original）。「真正嘅分類位」先識用嘴：呢個組唔係 tier-0 嘅冤家，係話 1-token choice 唔啱用。

### ✅ 4. 記憶：marker 硬規則先卡私隱，剩低 gather 並行 → F1 0.857 + leak 0
- js5_mem_03（「唔好提總倉位」）：`privacy_flagged` **marker regex 0 call 直接閘走**敏感記憶，leak=0（結構上比依賴 judge score+conf 更硬）。
- 2 selection items：4 條 `decide_score` 用 `asyncio.gather` 並行 → 單步 med 1,509 ms（同 original 1,250 同級，vs jev2 3,215）；F1 升到 **0.857**（其他 arm 0.48–0.67）。
- 剩返嘅 decision 次數 14 入面大半係呢組 mem score——但已並行，無 serial 開銷。

### ✅ 5. noUL asymmetric：STOP 一律 honor → stop-exact 2/2
js5_wf_02（gold STOP）：System One conf 0.025 → 舊 symmetric 會 escalate（chat 傾向 YES → OVER）；**asymmetric 直接 honor STOP（conf 唔使過閘）** → 1 step 停正。js5_wf_01 兩格 YES（conf 0.91 直接過；0.39 escalate 後 chat 都講 continue）→ 行足 3 步。per-boundary 3/3。

### ⚠️ 6. RAG answer-F1 仍係 answer 層話事（四 arm 同 profile）
js5_rag_01/02 四 arm answer-F1 全部 0.0、rag_03 先有分（0.08–0.19）——retrieval gate 全部入晒 gold，分別純屬 System Two answer call 嘅 item variance。**gate 已經做滿（gold 保 + 噪音剪 + trap flag），再上一層係 answer/ref 設計問題，唔係 JEV 位。**

### ⚠️ 7. 貢獻拆分：速度/成本嘅大頭係 hard-coded regex，唔係「真 JEV」

| jev3 嘅改動 | 係咪「真 JEV」（System One LLM 決策）| 佔嘅收益 |
|---|---|---|
| 工具路由 `route_tool`（regex/fillers，0 ms）| ❌ 唔係——純規則 | 工具 step 608→0 ms、慳埋成串 1-token choice + args |
| RAG gate `doc_gate_rrf`（RRF 實分）| ❌ 唔係——retriever 排序（原生算法）| RAG 4,911/5,045 → 1,178 ms |
| 私隱 marker regex 硬 drop | ❌ 唔係——regex | leak 由「靠 score 攔」變「0 call 保證」 |
| noUL asymmetric STOP-honor | ❌ 唔係——規則 | wf 5,622/5,607 → 1,741 ms、stop-exact 2/2 |
| sentiment 退出決策層照 chat | ❌ 唔係——「唔用決策層」 | sent 1/3 → 3/3（即係 chat 本身贏返）|
| mem score 11 個（gather 並行）| ✅ 係（真 System One）| F1 0.857、單步 1,509 ms——但 F1 升幅混咗 answer variance |
| wf noul 3 個 | ✅ 係 | per-boundary 3/3（一個位 conf 0.02 要靠 asymmetric 規則先唔 escalate）|

**結論要照實講**：JeV3 全場淨贏 = 「由 1-token LLM 換做 hard-coded deterministic 規則」＋「退出決策層照 chat」＋「bool/algorithm gate」。**真 JEV（System One interface）剩返嘅 14 個 decision 係「必要但唔足以成贏面」**——佢哋要做但唔夠料 alone 講「JEV 贏咗」。所以上一版 TL;DR 嗰句「真 JEV 價值第一次成立」收回，正確講法係「**tier-0 取締 call 嘅架構價值第一次成立**」。

## Live 層（Option B）：`JevToolDecider` —— 唔變，bench-only
- 今次 tier-0（`jev/tier0.py`）只喺 bench 後台驗證；live `JevToolDecider`（`before_model_callback` 短回路）暫時保持 jev2 版「JEV choice → args fill」，未換 `route_tool`。tier-0 嘅 RAG/mem/noUL gate 亦未接 live。
- 演變方向：將 `route_tool` 提升為 live decider 嘅第一層（args 都係 `fill_args`），JEV 1-token 做 fallback；RAG gate 接手 `doc_gate_rrf`。驗證方式照舊 FIN_MATE_JEV=1 opt-in。

## 限制
- n=15／arm；閘門 threshold 係 smoke item 上校；RAG answer-F1 對單句 ref-gold 好敏感（第 6 點）；`stop_exact`／`trap_pass` 係啟發式。
- 決定模型 = flash fallback →「決策快」係 interface 收益。
- 撞到嘅行為雜訊仍然在；tier-0 手工規則越多，題目改動越要同步（加 tool 要加 `route_tool` 分支）。
- OpenViking KB 內容同 phase-1/2 同一毒 doc 池。

## 可重現性
```
cd projects/fin_mate
./.venv/bin/python -m experiments.jev_bench.run            # 15 題 × 4 arm（~3-4 min）
./.venv/bin/python -m experiments.jev_bench.run --only jev3 --smoke   # JeV3 smoke
```
結果寫入 `experiments/jev_bench/results/runs_<ts>/SUMMARY.md`；每個 `jbv_<arm>/` 有 `rows.jsonl` + `events.jsonl`（含 t0_route / t0_doc_gate / jev_mem_gate 並行 score / jev_cont 等 telemetry）。