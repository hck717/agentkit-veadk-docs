# FIN-MATE D4–D5 · RAG 實驗室 全量評估報告

- **報告日期**：2026-09-08（D4）＋ 2026-09-09（D5：Rerank Lab + HyDE + 「新 RAG 方法」§9/§10/§11）
- **運行 tag**：`full_260908_1551`（naive / advanced / hybrid / corrective / adaptive；16 題 × 5 pipe）
             + `full_agentic_260908_1601`（agentic；16 題）——**agentic 已退役**（單一細 KB 冇 routing/多源價值，§8），
             結果下面保留作記錄；D5 現役 run set = naive/advanced/hybrid/corrective/adaptive/**hyde / hyde_rrf**（新 type）+ Rerank Lab（§9）+ 新 RAG 方法（§11）。
- **模型**：`seed-1-6-flash-250715`（ByteDance-Seed-1.6 帳號可存取 alias，Ark ap-southeast；`thinking={"type":"disabled"}`）
- **語料**：OpenViking `fin_kb`（agentkit FIN-MATE seed：MSFT 研究/財報/新聞 ~20 份文件）
- **Token 預算**：500,000（D4 每 run 上限）；D4 實耗 **408,174 / 500,000（81.6%；agentic 只計 prompt，實耗更高）**，全部 6×16 = 96 條跑完，**0 error**（token 計法見 §6：judge/rewrite/router 由 transcript 全 call 重計）。D5 另耗（full runs 計）：**hyde 49,974** ＋ rerank 3 variant **91,012**（none 30,327 / rrf 30,432 / llm 30,253）＋ local Qwen 17,871 —— 全部喺各自獨立 budget 內、0 error（另 smoke/plumbing ~40K）。**§11 新方法另耗**：hyde_rrf 48,702 ＋ ce 29,775 ＋ llm_listwise 30,418 Ark ＋ local Qwen 8,665 —— 各喺 §11 獨立 ≤150K budget 內、0 error。
- **依據 caveat #8**：OpenViking corpus 喺 D4 run 後被 reseed（`msft_txt/` 路由剷走、`msft_overview` 消失）→ **D5 只跑 15 題**（f12 剔出）。

---

## 1. 執行摘要（Executive Summary)

全部 6 條 pipe（naive / advanced / hybrid / corrective / adaptive / agentic）× 16 題，真 model 一次過跑完，零錯誤。下表係 D4（16 題，reseed 前 corpus）；**D5 結論先講**：rerank（RRF / Qwen3-4B pointwise）喺呢個細枯 KB 冇幫助、HyDE 有 recall↔answer-F1 trade-off——詳見 §9 / §10。核心結果（recall@5 / MRR@5 / answer-F1 / trap / 每題耗時）：

| pipe | recall@5 | prec@5 | MRR@5 | answer-F1 | trap (2 題) | ms/題 |
|---|---|---|---|---|---|---|
| **naive**（prod baseline）| **0.964** | 0.418 | 0.762 | 0.109 | 2/2 PASS | 1,576 |
| advanced | 0.964 | 0.214 | 0.762 | 0.105 | **1/2** | 1,814 |
| **hybrid** | **0.964** | 0.214 | **0.929** | **0.127** | 2/2 PASS | 1,754 |
| corrective | 0.607 | 0.287 | 0.524 | 0.077 | **1/2** | 1,354 |
| adaptive | 0.964 | 0.418 | 0.762 | 0.112 | 2/2 PASS | 2,079 |
| **agentic** | 0.750 | **0.500** | 0.494 | 0.056 | 2/2 PASS | 11,810 |

**四個重點結論：**

1. **Retrieval 已逼天花板**：naive/advanced/hybrid/adaptive 都拿到 recall@5 = 0.964——唯一唔足 1.0 嘅係 **m1**（跨兩份 doc 聯想，gold = Barclays+Deutsche 兩條 prefix，全部 pipe 都只中 1/2）。Retrieval 層唔係樽頸——樽頸喺「答」。
2. **Hybrid（dense+sparse→RRF）rank 最好**：MRR@5 0.929、fact nDCG=1.0，且係唯一令 fact MRR=1.0 嘅 pipe；answer-F1 亦最高（0.127）。但 prec 跌到 0.2，代價係多罰 sparse 命中有關的錯誤證據。
3. **Corrective 反而拖矮**：recall 由 0.964 跌到 0.607——LLM review 誤判「無料」→ rewrite 走向錯方向。fact 命中由 12/12 跌到 7/12。**即係：「檢測唔到」嗰下喺得呢個模型上面冇用，仲虧。**
4. **Agentic 係兩面體**：prec@5 全場最高（0.500，因佢自動 filter 低分候選），trap 2/2；但 recall 0.75、每題 11.8s（程序 pipe 嘅 ~7 倍）、成本 $0.0023（最貴）。citation verifier：總 markers 11，**falsified 3**（f6×2、f11×1 = 引用咗但 agent 實際未睇過）。agentic 唔識出 `【KB:】` marker（instruction 冇教 → cited 好低），但 retrieval 本身冇呃人。

---

## 2. 方法論（Methodology)

### 2.1 Benchmark 設計

- **16 題**：12 fact + 2 multi_hop（m1/m2）+ 2 trap（t1/t2，KB 無據，評「唔作」）。
- **Gold**：`eval_set.resolve_gold()`——每題一個 **URI-prefix set**（要cite到邊份文件）＋一段**文字 gold answer**。
- **檢索指標**：`recall@5 / precision@5 / MRR@5 / nDCG@5`，全部 **prefix match**（`viking://resources/fin_kb/<doc>/…`）。
- **答案指標**：answer-F1（word-token overlap）；trap 唔計 F1，PASS 條件係答案明示「KB 無資料/没有/not found/唔知」。
- **agentic citation verifier**：由 final answer 抽 `【KB:】` markers，對返 `load_knowledgebase` function response 實際返過嘅 `viking://` URIs；「引用咗但 agent 冇睇過」＝ **falsified（一票 fail）**。

### 2.2 語料同 KnowledgeBase（OpenViking，builtin 為主）

- L0 = find（dense top-p k 檢索）、L1 = read/hydrate（L2 全文）、sparse = grep。
- `read_limit` 係 **instance 級**，所以每條 pipe 自己 `build_kb(read_limit)`：naive/adaptive 200、advanced 2000（粗水化 15 份）、hybrid 200、corrective 1000、agentic 200。
- 每題一次 retrieval-save：`advanced.k=15 粗水化→dedupe`；`hybrid dense k=15 + sparse grep→RRF(k=60)`（無 score scaling）；`corrective find→LLM self-check→rewrite→re-find→再差 skip`；`adaptive LLM router 決定查唔查（trap→唔查）`。
- Gate：`GATE=0.35`（hybrid RRF/advanced dedupe 後低於 threshold 唔入 answer）。

### 2.3 Model 同評分設定

- `seed-1-6-flash-250715`，reserved `thinking={"type":"disabled"}`——實測呢個模型預設 thinking=True 會燃燒 output 預算（out=84 而 reasoning=83）兼唔出正式答案。
- Answer 要求帶 `【KB:<uri>】` / `【CALC】` markers；`falsified citation = fail`。
- 成本計法：`_lib.PRICES = {input 0.021 / output 0.211 / cached 0.004}` USD/1M tokens。

### 2.4 Token budget 機制（守「全部 run ≤ 500K」）同執行控制

- `EST_TOKENS_PER_ITEM` 每 pipe 預查 → over budget 寫 `BUDGET_SKIP`；每題後用真 experiment usage 校正 `used_tokens`。
- agentic 每題 spawn **fresh subprocess**（`python -c` 內嵌體，`--agent-timeout 240s` 硬殺）——veadk Agent + ADK Runner 喺同一進程連跑會 hang/litellm threadpool 死，且 sync Runner generator 一定要喺**無 active event loop** 環境行。
- `_build_agent` 用 `tracers=[]`（OTel tracer 同 litellm 相撞）。

### 2.5 指標：公式、點計、含義

全部實現喺 `experiments/eval_metrics.py`。共通設定：`gold` = doc 級 **URI-prefix set**（`resolve_gold`）；`retrieved` = 有次序嘅 top-5 URIs；相關判定 `rel(u) = u.startswith(任一個 gold prefix)`（**同一 doc 唔同分片全部當相關**）。k = 5。

**recall@5 —— 「有冇撳齊」**

$$R@5 = \frac{\#\{\,g\in\mathrm{gold} : \exists\, u\in \mathrm{top5},\ u \text{ startswith } g\,\}}{|\mathrm{gold}|}$$

- 每個 gold doc 只睇「有、冇」，唔睇位置；gold 有幾多份，上限就係幾多。
- **含義**：檢索漏唔漏料。1.0 = top-5 入面齊晒要睇嘅文件。gold 越大難度越高——m1/m2 要 **兩份**（如 m1＝Barclays+Deutsche），只中一份就 0.5。
- 例：gold={A,B}、top5=[A′,C,B] → 2/2=1.0；top5=[A′,C,D,E,F] → 1/2=0.5。
- 睇表：**fact 全部 pipe 1.0 → 係 multi_hop 嘅 m1 先拉低到 0.964/0.75**。

**precision@5 —— 「五個入面幾多有用」**

$$P@5 = \frac{\#\{u\in \mathrm{top5} : rel(u)\}}{5}$$

- **含義**：噪音比例。recall 高 + prec 低 = 揀得中但夾雜假陽性。naive/adaptive fact prec=0.437（平均~2.2 份相關/題）；advanced/hybrid fact 0.2（平均 1 份）——k=15 / sparse 帶多咗非 gold 份。

**MRR@5 —— 「首份真料幾快中」**

$$MRR@5 = \max_{i \le 5} \frac{rel(u_i)}{i},\quad(\text{冇命中}=0)$$

- 只有第一個相關份有分：1.0 = 第 1 名；0.5 = 第 2；0.333 = 第 3。
- **含義**：順序敏感。**hybrid fact MRR=1.0 → RRF 將 gold 推上第一名**；naive 0.778 → f1/f3/f4/f9/f10 嘅 gold 喺第 2。

**answer-F1 —— 「生成答案同標準答案字面似幾多」**

$$F_1 = \frac{2\,P\,R}{P+R},\quad P=\frac{|\mathrm{overlap}|}{|\mathrm{pred}|},\ R=\frac{|\mathrm{overlap}|}{|\mathrm{gold}|}$$

- 兩邊都 token 化（lowercase alnum、bag-of-words、計重覆），overlap = 共同 token 數。
- **含義**：**唔係事實命中**——魔術：HK 中英混合句法、同義字、簡寫都扣分；所以全場 <0.13 唔等於答錯（f3/f4/f5/f11 = 0.000 但 retrieval 全中=料啱）。

**trap PASS —— 「識唔識話『冇料』」**

$$PASS \iff \text{答案含}\ \{\text{KB 無資料, 没有, not found, 唔知}\} \ (\text{字面 match，`_trap_pass`})$$

- 唔計 F1；只評「有冇老作」。pass = 明確拒答＝唔比資料。
- **量度陷阱**：語義拒絕但字面唔入 lexicons → 假 FAIL（**advanced t1「並未提及…」**）；呢個表入面**唯一真 fail 係 corrective t1**（老作咗股息數字）。

**nDCG@5（表有但唔喺標題做頭牌）**

$$DCG = \sum_{i\le5}\frac{rel(u_i)}{\log_2(i+1)},\quad nDCG = DCG / \underbrace{\sum_{i=1}^{\min(|gold|,5)}\frac{1}{\log_2(i+1)}}_{\text{理想}IDCG}$$

- **含義**：整體排序質素（唔只第一名）。⚠️ 本試行 `rel` 用 token-overlap（同 doc 多分片全計相關）⇒ 可 **>1**——agentic fact nDCG 1.459 係 metric 特性，唔係超越理想排序。

---

## 3. Performance（吞吐量）

| pipe | ms/題（mean）| 全 16 題 clock | n_events | 每題 LLM 往返 |
|---|---|---|---|---|
| naive | 1,576 | 25.2s | 32 | 1（retrieve 內）|
| advanced | 1,814 | 29.0s | 48 | 2（retrieve + answer）|
| hybrid | 1,754 | 28.1s | 32 | 1 |
| corrective | 1,354 | 21.7s | 85 | 3–4（query + rewrite + answer）|
| adaptive | 2,079 | 33.3s | 48 | 2（router + answer）|
| agentic | 11,810 | 188.0s | 16 | tool-loop（1 retrieve round，~3 LLM 步，含 load + final）|

- **程序 pipe 全部 < 2.1s/題**，同一語料下 latency 唔係差別因素。
- **agentic 係 outlier**：11.8s/題 ≈ 程序 pipe 7 倍（ADK Runner + session + 工具 loop 開銷）。agent_timeout=240s 下最差個題都冇接近上限。

---

## 4. Accuracy（準確度）

### 4.1 按類別拆（fact / multi_hop / trap）

| pipe | cat | n | recall@5 | prec@5 | MRR@5 | nDCG@5 | ans-F1 | trap PASS |
|---|---|---|---|---|---|---|---|---|
| naive | fact | 12 | 1.000 | 0.437 | 0.778 | 0.835 | 0.094 | – |
| naive | multi_hop | 2 | 0.750 | 0.300 | 0.666 | 0.592 | 0.199 | – |
| naive | trap | 2 | – | – | – | – | – | 2/2 |
| advanced | fact | 12 | 1.000 | 0.200 | 0.778 | 0.835 | 0.087 | – |
| advanced | multi_hop | 2 | 0.750 | 0.300 | 0.666 | 0.592 | 0.210 | – |
| advanced | trap | 2 | – | – | – | – | – | 1/2 |
| hybrid | fact | 12 | 1.000 | 0.200 | **1.000** | **1.000** | **0.120** | – |
| hybrid | multi_hop | 2 | 0.750 | 0.300 | 0.500 | 0.506 | 0.162 | – |
| hybrid | trap | 2 | – | – | – | – | – | 2/2 |
| corrective | fact | 12 | **0.583** | 0.285 | 0.500 | 0.522 | 0.071 | – |
| corrective | multi_hop | 2 | 0.750 | 0.300 | 0.666 | 0.592 | 0.113 | – |
| corrective | trap | 2 | – | – | – | – | – | 1/2 |
| adaptive | fact | 12 | 1.000 | 0.437 | 0.778 | 0.835 | 0.096 | – |
| adaptive | multi_hop | 2 | 0.750 | 0.300 | 0.666 | 0.592 | 0.206 | – |
| adaptive | trap | 2 | – | – | – | – | – | 2/2 |
| agentic | fact | 12 | 0.750 | **0.533** | 0.493 | 1.459* | 0.053 | – |
| agentic | multi_hop | 2 | 0.750 | 0.300 | 0.500 | 0.540 | 0.076 | – |
| agentic | trap | 2 | – | – | – | – | – | 2/2 |

\* agentic fact nDCG 1.459 > 1：`eval_metrics._rel` 用 token overlap 判相關（同一 doc 多份分片都計相關），令 dcg 可超 idcg；見 §6 限制。

### 4.2 關鍵觀察

- **fact（12 題）**：
  - naive＝adaptive＝advanced 檢索全紅（recall 1.0, MRR 0.778）；**hybrid 排名全勝**（MRR/nDCG = 1.0）但 prec 低（sparse 引入假陽性）。
  - answer-F1 全場好低（0.05–0.12）——即 retrieval 揀啱咗，但生成對「數字＋年份＋來源語」嘅精準表述唔及文字 gold（HK 語混合、同義句）。**樽頸喺生成，唔係檢索。**
- **multi_hop（m1/m2）**：所有 pipe 都 0.75 recall；m2 係唯一全場 miss 嘅題（gold 要跨兩份 doc 聯合推論，單一 top-5 檢索做唔到）。
- **trap（t1/t2）**：naive / hybrid / adaptive / agentic 全 PASS（知「無據唔答」）；**advanced 同 corrective 各錯 1 題**——佢哋預先「補檢索/重寫」，令模型覺得有料而作答案。
- **agentic**：prec 最高（自己 filter 低分候選）、trap 冇呃；但 recall 得 0.75——工具 loop 揀源偏向「最近嗰份」，跨日/跨類型嘅事實易漏；另外 instruction 冇教 marker → cited 少（但 3 個 falsified 真係佢自己引錯）。

### 4.3 agentic citation verifier（逐題）

| eid | cited | prec | fals | cov | uris |
|---|---|---|---|---|---|
| f1 | 2 | 1.00 | 0 | 0.10 | 5 |
| f2–f5, f8 | 0 | 1.00 | 0 | 0.00 | 5–9 |
| f6 | 2 | 0.00 | **2** | 0.10 | 6 |
| f7 | 1 | 1.00 | 0 | 0.04 | 6 |
| f9 | 1 | 1.00 | 0 | 0.02 | 5 |
| f10 | 1 | 1.00 | 0 | 0.09 | 6 |
| f11 | 1 | 0.00 | **1** | 0.04 | 5 |
| f12 | 1 | 1.00 | 0 | 0.22 | 9 |
| m1/m2/t1/t2 | 0–2 | 1.00 | 0 | 0.00–0.09 | 5–7 |

→ 總 markers 11、falsified 3（f6×2、f11×1）；其餘引用全部對返 agent 實際睇過嘅源。**冇 pipe 可以**睇到呢層審計——agentic 唯一。

---

## 5. 結果解讀（逐條 pipe：點解出呢啲數）

> 呢章係§3/§4 數字嘅根因分析，全部基於實測 artifact：`<pipe>/<eid>/transcript.jsonl`（逐 LLM call）同 `<pipe>/events.jsonl`（stage 事件）。

### 5.1 naive（dense find top-5 + hydrate ＝ prod baseline）

- **點解 recall 咁高（0.964 / fact 1.0）**：呢題庫嘅問題關鍵字（Mizuho、Barclays、F2Q、E7 SKU…）同文件標題對得極準，dense 一拉就中。唯一唔足係 **m1**：gold＝**Barclays + Deutsche 兩份**一齊答（`resolve_gold` 兩條 prefix），naive 只撳到 1/2 → recall 0.5。唔係檢索差，係「跨文件合併」類題佢冇第二步。
- **點解 prec 得 0.418 / MRR 0.762**：實測 f1/f4 `retrieve` 得 **2 個 URIs**、gold doc 排第 **2**（MRR 0.5）——top-5 撳完 hydrate 之後剩低少過 5 份，真嗰份又未上第一名。即係 recall 高但 rank 唔靚。
- **點解 answer-F1 得 0.109**：唔係「答錯」，係 *表述同 gold 對唔上*。F1 只做 word-overlap，香港式中英混合句法會大扣分（f3/f4/f5/f11 得 0.000 但 recall 1.0=料啱句唔似）。

### 5.2 advanced（k=15 粗水化 + grep 擴 + dedupe + gate 0.35）

- **Recall 唔變（fact 1.0）**：k=15 一樣中到，gate 只濾明顯錯料 → 檢索命中同 naive 平手。
- **點解 prec 跌到 0.214**：k=15 ⇒ 每題多帶入份文件，answer 誤入非 gold 份又多咗 → precision 必然跌。
- **點解 multi_hop answer-F1 微升（m1 0.210 / m2 0.247）**：粗水化畀到跨份 context，multi-hop 題執料執得好啲。
- **點解 trap 錯 1 題（t1）＝量度假象**：t1 第一句「目前提供的資料中並未提及相關具體信息…」——語義上有拒絕，但 PASS 判據係字面 match「KB 無資料/没有/not found/唔知」，佢嘅講法唔入 lexicons → 判 FAIL。佢**冇**作料。

### 5.3 hybrid（dense + sparse → RRF k=60）

- **點解係全場 rank 王（fact MRR/nDCG = 1.0）**：實測 f1/f4 由 naive 嘅「2 URIs + gold rank 2」→ hybrid「**5–6 URIs + gold rank 1**」。sparse grep（關鍵字匹配）將 pure-dense 排名低嘅真份推上嚟，RRF 融合後真 doc 上返頂——呢類「問句同文件標題共 key」嘅題，sparse 命中率高，補足 dense 盲點。
- **點解 answer-F1 都係全場最高（0.127）**：注入多咗、rank 準咗，模型最多原文抄到貼。
- **代價 prec 0.214**：多出嘅 5–6 個 URIs 入面有 sparse 假陽性。

### 5.4 corrective（find → LLM self-check → rewrite → re-find → skip-inject）

- **全場最差（fact recall 0.583，12 題死咗 5 題：f3/f4/f5/f6/f10）**。兩個致命位：
  1. **judge 過嚴**：f3 初次 find 明明攞到料，judge 判「FAIL 資料中無論是公司基本面摘要還是瑞…」——detector 要求原文*直接含數值*，水化 summary 帶唔到就當無料 → 觸發 rewrite。
  2. **rewrite 之後 skip-inject**：f6 嘅 judge2 明明判「CORRECT」，但 `gate → skip_inject=true` → answer 出返「KB 無資料」（68 tokens）。rewrite 個 query 改到 re-find 攞唔返啲料，answer stage 成盤丟棄——**原本有料俾佢整到冇料**。
- **trap t1 係唯一真製造假資料**：rewrite 將「股息」query 撳到料，模型老作「股息殖利率（截至 2023 年 10 月）」連數字。
- m1 都係 0.5（rewrite 拉唔返另一份）；m2 冇加冇減。**結論：喺呢個模型+題庫，執行「先判斷夠唔夠料」係淨虧**——detector 太保守，唔應該 default 觸發 rewrite。

### 5.5 adaptive（LLM router 決定查唔查）

- **結果同 naive 完全一樣（0.964 / 0.418 / 0.762，連 tokens 都同量）**：router 對 trap t1/t2 都判「SEARCH」——問題問得似正常（「股息殖利率歷史」），LLM 無可能從 query 字面 pre-empt 到 KB 無料。
- 即係「adaptive 慳錢」喺呢份題庫實現唔到：慳嘅前提係 router 敢 skip，而 trap 恰係最難 skip 嗰種。（未來有「明確閂關」題如 upload 範圍限定先發揮到。）

### 5.6 agentic（Agent + LoadKnowledgebaseTool 自捽 retrieval）

- **prec 最高（0.500）、trap 2/2、冇一秒老作**：真係經 tool 攞料先答，天然 grounded；會喺候選入面自動揀細。
- **點解 recall 跌到 0.75（f5/f7/f9 = 0.000）**：f7 得 **一次 load_knowledgebase**（3 event 鏈：function_call → function_response → final），返嘅 URIs 係另一批文件——**冇掂到 gold 嗰份**。即係 agent 用自己的 query 表述去搵，揀源有 bias（偏近期/標題啱嗰份）；f5 直頭 0 URI。
- **點解慢（11.8s/題）**：ADK Runner + session + tool loop 開銷，每題 fresh subprocess。
- **citation verifier**：11 markers、**3 falsified**（f6×2、f11×1＝引用咗但冇實際睇過）；其餘引用全部有對返 tool 實際返嘅源。低 `cited` 係因為 agent instruction 冇教出 `【KB:】` marker，**唔代表呃**。completion=0 係 API `usage_metadata` 只報 prompt side。

### 5.7 綜合根因

- **檢索層**：呢份題庫太易中（dense 已 0.964）；真正提升 rank 靠 **sparse 補位（hybrid）**；真正害嘢靠 **rewrite 吞證據（corrective）** 同 **agentic 揀源 bias（f5/f7/f9）**；唯一結構性 miss 係 **m1 跨兩份 doc**（全場 pipe 都中唔晒）。
- **生成層先係樽頸**：所有 pipe answer-F1 < 0.13——料中但字面 F1 低，係「表述」評分問題（且冇人評事實對錯），唔可以當「答錯」。
- **量度陷阱**：advanced t1「語義拒絕但字面唔中」＝假 FAIL；corrective t1 先係真 FAIL（真係老作）。

---

## 6. Efficiency（成本效率）

| pipe | prompt tokens | completion | **tokens/16 題** | **USD** | USD/題 |
|---|---|---|---|---|---|
| naive | 30,183 | 2,257 | 32,440 | $0.0011 | $0.00007 |
| advanced | 77,214 | 2,429 | 79,643 | $0.0021 | $0.00013 |
| hybrid | 75,810 | 2,374 | 78,184 | $0.0021 | $0.00013 |
| corrective | 71,946 | 2,981 | **74,927** | $0.0021 | $0.00013 |
| adaptive | 31,230 | 2,583 | **33,813** | $0.0012 | $0.00008 |
| agentic | 109,167 | 0* | 109,167 | $0.0023* | $0.00014 |

\* agentic `usage_metadata` 只報 prompt side；completion 實際 >0，但 API 唔畀 → 成本略低估。

> **計數修正（重要）**：`events.jsonl` 只喺 `answer` stage 帶 `tokens`——corrective 嘅 judge/rewrite/judge2（共 36 次 call）同 adaptive 嘅 router（16 次 call）淨係落喺
> `<strat>/<eid>/transcript.jsonl`（LLM trace）。舊表淨計 answer-stage，令 corrective 報細到 20,269（好似最慳）。**正確做法係由 transcript 全 call 重計**（上面已經係）
> → corrective 真正 **74,927 ≈ 2.3× naive**（52 次 call），adaptive 33,813（32 次 call）。修正後無任何 pipe 係「慳過 naive」。

- **Full suite 總耗**：**408,174 / 500,000 tokens（81.6%**；agentic completion 未計，實數更高），約 **$0.011** 成全場 96 runs。
- **每題成本**差唔多（$0.00007–0.00014）；大分別唔喺錢，喺 **time**（agentic 11.8s vs 程序 ~1.5–2.1s）。
- **Token 效率**：
  - advanced/hybrid 因「k=15 粗水化 + 每題食多份」prompt 係 naive 2.5×；
  - corrective 多 stage（judge → rewrite → judge2 → answer，16+10+10+16 call）成本係 naive 2.3×——唔會「驗證反而慳」，因為每次驗證本身都要 ARK；
  - adaptive 同 naive 等量（33,813 ≈ 32,440）——呢個 benchmark 入面 router 對非 trap 全部放行，**冇慳到 pin**（慳嘅潛力喺「skip retrieve」嘅 trap item，只 2 題）。
- **BUDGET_SKIP**：0 題被跳——全部 pipe 埋單都喺 500K 內。

---

## 7. 已知限制同 Caveats

1. **nDCG 可 >1**：`_rel` 以 token-overlap 判相關（同 doc 多分片計相關），agentic fact nDCG 1.459 係 metric 特性，非真實超越理想排序；MRR/prec/recall 唔受影響。
2. **Answer-F1 偏低嘅解讀**：係「表述」唔係「事實命中」—— F1 只做 word overlap，HK mixed-language 表達同 gold 唔同句法就扣分；真正事實正確率要人判或者用 LLM-judge（未做）。
3. **Corrective 失效本質**：個 rewrite/review 用嘅係同一模型同一 prompt 設計，detector「夠證據」判定器喺 6/16 題誤判 → 建議換閘（threshold/加 reference 檢查）先再上 D5。
4. **Agentic usage 少計 completion**；agentic top-k 係 veadk tool 內部設定（本試行冇單獨 tune）。
5. **無 rerank（D5 未上）**——dense 分數未做 cross-encoder rerank，係下一步對比。
6. **reference 文件粗幼**：`read_limit` 每 pipe 唔同（200–2000），advanced 用 err 做 threshold，未有統一 HR judge 返填充質量。
7. **Token 計數一度低估 corrective/adaptive**：events 淨記 answer-stage，judge/rewrite/router 得 transcript 有 → §6 已用 transcript 全 call 修正（corrective 20,269→**74,927**；adaptive 32,638→**33,813**）；如有 cite「舊數」請以 §6 為準。
8. **OpenViking corpus 喺 run 期間被 reseed**（folder modTime 2026-09-08 ~19:56 本地）：
   - 舊路由 `viking://resources/fin_kb/msft_txt/` → 家下 **doc folder 直接喺 `fin_kb/` 下**（`eval_set.TXT` 已改）；`msft_overview` 被剷走。
   - → **f12（overview 題）再冇 gold 對應，D5 新 type（hyde / rerank）只跑 15 題**；舊 run 16 題數字保留，因為當時 overview 仲喺度。
   - **公平一句**：D5 數字係喺 reseed 後 corpus 上跑，同 main-run（reseed 前）同比係「同一 8 份研報、同一 15 題」，但每題簽到邊個 doc 嘅 URI prefix 個別 run 自洽；演繹上有少少「corpus 狀況唔完全一樣」嘅 grain，見 §5/§9 已註。
   - **rrf variant 另有 bug**：首版 `_rrf` 返 doc-prefix 令 rrf 嘅 answer ctx 全空（假答案 0.039）——已 fix（pref→chunk 展開）並重跑；llm variant 無呢個問題（llm 直接 score chunks）。全表用修正後 rrf。

---

## 8. 下一步

- **agentic 已退役（唔再跑）**：單一 `fin_kb` 得一個 retrieval 動作，agent 嘅「自己決定查幾多次」只係多 LLM 往返——
  實測 fact recall 0.75（低過 naive 0.964）＋最貴最慢。**當有多源異構（多 KB / RDBMS / web / 工具 chain）先重新上已實證體**。
- **D5 rerank（✅ 已跑完）**：固定 pool × {none / RRF / Qwen3-4B pointwise}——**結論：喺呢個細枯 KB 冇幫助**
  （top-of-list 已啱；RRF 同 LLM-as-reranker 都冇贏過 pool 原序，仲加 delay/$），詳情見 §9。
- **HyDE（✅ 已跑）**：LLM 生成 hypothesis 做 query——recall 跌 0.077 但 answer-F1 升 0.026，trade-off 取捨見 §10。
- **生成層**：改 answer prompt（數字+年份+來源語合一、Cantonese/English 統一），先解決 F1 假低；加 fact-verifier（答完抽 claim 對檔）。
- **Corrective**：換「detector 閾值＋reference 判據」，或者喺呢個 corpus 直接 drop pipe（實測負貢獻）；token 計數已修正，成本唔係「慳咗」而係 2.3× naive——更值得衡量有冇留低。

---

## 9. Rerank Lab（D5）——設計同狀態

**狀態：✅ 已完成（2026-09-09）。15 題（f12 已剔出，見 §7 caveat #8）；只 run 新 variant；naive/advanced/hybrid/corrective/adaptive/agentic 冇重跑。**
**只 run 新 variant**：`none` / `rrf` / `llm` 三條（+ `--rrf-sweep`）；naive/advanced/hybrid/corrective/adaptive/agentic 唔會重跑。

目標：同一 **fixed candidate pool** 上只比「排序」，睇 **RRF** 同 **本地 LLM-as-reranker** 有冇改善 top-of-list 質素（MRR/recall@3）同 answer-F1，以及 latency/$ 代價。

| 設定 | 值 |
|---|---|
| Pool | `kb.search(q, top_k=15)`（read_limit=200）＋ `_sparse(kw≤3, limit≤20)`，doc-prefix 去重 → ~15–25 候選/題；**3 variant 共用同一 pool** |
| variant「none」 | pool 原序（dense 15 先行、grep 補）＝ rerank 前 baseline；$0 |
| variant「RRF」 | `_rrf([dense, grep], k=60)` 融合兩個 ranked list（rank-based、無 calibration）；$0；`--rrf-sweep` 掃 `k∈{10,20,60,100}×w∈{0.5,1,1.5,2}` 揾 plateau 最細 k |
| variant「LLM」 | **Qwen3-4B pointwise**：Ollama `qwen3:4b-instruct-2507-q4_K_M` native `/api/chat`、`think:false`、temp 0、num_predict 8；每 candidate score 0–3（抽 `\b[0-3]\b`，fail→0）；desc sort、tie 用原序；**$0（本機）** |
| Ranking metrics | **@3 主**（recall/prec/MRR/nDCG）＋ **@5 參考**（同 §4 對比；RRF 路徑≈hybrid） |
| answer-F1 | 揀中嘅 **top-5** 組 ctx → `_ans_msgs` → Ark answer（multi-hop m1/m2 要兩份 doc） |
| Budget | scoring $0 唔扣；answer 經 Ark → **獨立 150K**（48 次 answer ≈ 75K，另頭） |
| Latency 記錄 | 分「local（RRF/LLM 段）」同「Ark（answer 段）」兩欄；LLM variant 每題 ~10–40s（~25 次 Ollama call） |
| 對照基準 | main run **hybrid** 行（RRF 路徑完全相同）直接同比；`none` vs naive 類比 |

**預期檢查點**：RRF 有冇推高 MRR@3（hybrid MRR@5=0.929 係高樓）；Qwen3 pointwise 有冇再贏 RRF（$0 但要 +Xs latency）；multi_hop m1/m2 喺 @3 會唔會因「要兩份 doc」而被打返 0.5；trap 行為（無料照 score）有冇走樣。

### 9.1 結果（15 題，除 trap 外 n=13）

巰列 = **同 15 題重算**（`RUNS` 統一 extraction + `eval_metrics`）：

| variant | recall@3 | prec@3 | MRR@3 | nDCG@3 | recall@5 | MRR@5 | answer-F1 | trap | local ms/題 | Ark ms/題 | Ark tokens（15 題） |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **none**（pool 原序）| **0.962** | 0.359 | **0.923** | **0.918** | 0.962 | 0.923 | 0.111 | 2/2 | 138 | 1,529 | 30,327 |
| rrf（k=60）修正後 | 0.923 | 0.333 | 0.910 | 0.899 | 0.962 | 0.910 | 0.114 | 2/2 | 127 | 563 | 30,432 |
| llm（Qwen3-4B pointwise）| 0.923 | 0.333 | 0.872 | 0.860 | 0.962 | 0.872 | 0.108 | 2/2 | 2,855 | 1,544 | 30,253 + local 17,871 |
| — 對照 — | | | | | | | | | | | |
| naive（main-run）| 0.923 | 0.436 | 0.744 | 0.765 | 0.962 | 0.744 | 0.112 | 2/2 | – | ~1,576 | – |
| hybrid（main-run）| 0.923 | 0.333 | 0.923 | 0.906 | 0.962 | 0.923 | 0.118 | 2/2 | – | ~1,754 | – |
| hyde（§10）| 0.846 | 0.397 | 0.769 | 0.748 | 0.885 | 0.769 | **0.138** | 2/2 | – | 2,707 | 49,974 |

**閱讀**：
- **Rerank 冇贏過「唔 rerank」**：`none` MRR@3=0.923 同 hybrid 平手、仲高過自己 pool 上嘅 RRF（0.910）；**LLM-as-reranker 最差（0.872）**——Qwen3-4B pointwise 喺呢個細枯 KB 反而搗亂 top-of-list。
- `recall@5` 全線 0.962（≈ old 0.964）→ **5 份內一定揾到 gold，問題只係排序**；而排序喺 8-doc KB 入面：pool 原序已經接近最優。
- Answer-F1：rrf 0.114 ≈ hybrid 0.118；none 0.111；llm 0.108——**排序改善對 answer 質素無實質幫助**（hyde 0.138 係另一軸，見 §10）。
- Latency/$：llm 每題 +2.7s local（~25 次 Qwen call $0）但 ranking 仲差 → **喺呢個尺度唔值**；RRF $0 幾近免費不過都係平手。
- **RRF sweep**（retrieve-only，$0）：`k∈{10,20,40,60,100,200} × w∈{0.5,1,1.5,2}` **24 格全部 plateau**（MRR@3=0.910 / recall@5=0.962 / recall@3=0.923）——pool ≤ ~30 個分片、8 份 doc 嘅粒度，RRF 權重完全唔敏感；現行 k=60 / w=1 已經喺 plateau，無需 tune。
- multi_hop m1/m2 喺 @3 係全體共痛位（gold 兩份 doc，context 得 5 位）——rerank 冇單獨改善到。
- **中途 bug**（§7 caveat #8 尾部）：rrf 首版 `_rrf` 返 doc-prefix，`_ctx_selected` 對唔上 → ctx 空 → 全體「KB 無資料」假答案（ans-F1 0.039、trap 1/2）；修正（pref→chunk 展開）後重跑 → 0.114/2/2。以上係修正後數字。

---

## 10. HyDE（D5 新 type）——設計同狀態

**狀態：✅ 已完成（2026-09-09）。`run.py --only hyde`，15 題，49,974 Ark tokens（$0.0016），0 錯誤。只 run 新 type；冇 retest 舊 pipe。**

| 設定 | 值 |
|---|---|
| 流程 | `q → LLM 生成 hypothesis h（60–120 tokens，`MODEL_PRIMARY`）→ kb.search(h, k=5)@read_limit=200 → dedupe → answer` |
| 對照 | **同 naive 同 k / read_limit**（5/200）——單一變數＝「換 query」；直接同 naive 行比 |
| 成本 | +1 Ark call/題（生成 ~0.3–0.5s）；實測 49,974 tokens / 15 題（est 2.2K/題） |
| 預計效益 | 短 query／query 用詞同報告文唔對（如「Microsoft Cloud 突破 50 億」）靠假設文補語義 gap → recall@5 / answer-F1 升 |
| 風險 | 假設文過度靠估／帶錯名詞 → retrieval 可差過原 query；生成空 → fallback 原 query（fail-safe） |

### 10.1 結果（15 題，同 naive / hybrid 對照；@5 軸）

| pipe | recall@5 | prec@5 | MRR@5 | nDCG@5 | answer-F1 | trap | ms/題 | Ark tokens（15 題） |
|---|---|---|---|---|---|---|---|---|
| **hyde** | 0.885 | 0.397 | 0.769 | 0.768 | **0.138** | 2/2 | 2,707 | 49,974 |
| naive（對照）| **0.962** | 0.436 | **0.744** | **0.765** | 0.112 | 2/2 | ~1,576 | – |
| hybrid（對照）| 0.962 | 0.333 | 0.923 | 0.906 | 0.118 | 2/2 | ~1,754 | – |

**閱讀**：
- **又係一個 trade-off，唔係 free win**：HyDE 換 query 拉高咗 answer-F1（0.112→**0.138**，+23%），但 **recall@5 跌 0.962→0.885**、MRR@5 0.744→0.769（微升）——hypothesis 文帶埋擬似名詞，揾少咗啲「非主流表述」嘅 doc；nDCG 亦微跌。
- 即係話：喺呢個細枯 KB，原 query 嘅 dense find 已經好穩；HyDE 嘅價值喺 **answer 表述更貼 gold**（hypothesis 令 ctx 更集中於答案句），唔係「揾多咗料」。
- 同 naive 對照係唯一變數（k/read_limit 相同）——個 gain 純粹來自「換 query」呢一步。
- per-item 見 `run_260909_hyde_full/hyde/report.md`。

---

## 11. 新 RAG 方法（D5 §2）——HyDE+RRF 融合、cross-encoder、LLM listwise

**狀態：✅ 已完成（2026-09-09）。三條新方法各 15 題、各自獨立 ≤150K Ark budget、0 error、$0.0017 / $0.0010 / $0.0009。只 run 新 type；冇 retest 任何舊 pipe。**
（Env pre-flight：`.venv` 原本冇 torch/sentence-transformers，補裝 CPU 版 + `bge-reranker-v2-m3`（~2.2GB 本機）先行到 ce。）

| 設定 | 值 |
|---|---|
| hyde_rrf（新 main type） | `q → h=LLM hypothesis（同 §10）→ 3-channel RRF([dense(q,15), dense(h,15), grep≤20], k=60)` → **top-5 RRF doc 各取 1 分開（最高分）作 answer ctx** → Ark answer。= 「HyDE 生成 + 雙 dense lane + sparse 融合」 |
| ce（rerank variant） | **cross-encoder**：`BAAI/bge-reranker-v2-m3`（multilingual，CPU）sigmoid score → desc、tie 原序；同 §9 fixed pool（dense 15 + grep ≤20）；scoring 本機 CPU **無 token**、$0 |
| llm_listwise（rerank variant） | Qwen3-4B **一次過排全部候選**（`[i] pref — content[:150]` 一份 msg）→ 輸出編號序；parse fail → 原 pool 序 fallback；每題 **1 次** Ollama call（vs pointwise ~25 次） |
| Budget | 各自獨立 ≤150K Ark；ce/llm_listwise scoring $0，answer 經 Ark；hyde_rrf 全 Ark |
| 對照 | hyde_rrf vs §10 hyde / hybrid（RRF 路徑）；ce、llm_listwise vs §9 pointwise llm 同 pool 同 ctx |

### 11.1 結果（15 題，除 trap 外 n=13；同 §9.1 唔同：新增三行）

巰列 = **同 15 題重算**（`_table11.py`，同一 extraction）：

| variant | recall@3 | prec@3 | MRR@3 | nDCG@3 | recall@5 | MRR@5 | answer-F1 | trap | local ms/題 | Ark ms/題 | Ark tokens（15 題） |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **hyde_rrf** | 0.923 | 0.333 | 0.821 | 0.837 | 0.962 | 0.821 | 0.125 | 2/2 | – | ~1,650 | 48,702 |
| **ce**（bge-reranker-v2-m3）| 0.923 | 0.333 | 0.872 | 0.856 | 0.962 | 0.872 | 0.101 | 2/2 | 2,230 | 1,434 | 29,775 |
| **llm_listwise** | 0.923 | 0.333 | 0.833 | 0.850 | 0.962 | 0.849 | 0.108 | 2/2 | 1,872 | 1,393 | 30,418 + local 8,665 |
| — 對照（§9/§10 同池同軸）— | | | | | | | | | | | |
| none（pool 原序）| **0.962** | 0.359 | **0.923** | **0.918** | 0.962 | 0.923 | 0.111 | 2/2 | 138 | 1,529 | 30,327 |
| rrf（k=60）修正後 | 0.923 | 0.333 | 0.910 | 0.899 | 0.962 | 0.910 | 0.114 | 2/2 | 127 | 563 | 30,432 |
| llm（Qwen3-4B pointwise）| 0.923 | 0.333 | 0.872 | 0.860 | 0.962 | 0.872 | 0.108 | 2/2 | 2,855 | 1,544 | 30,253 + local 17,871 |
| hybrid（main-run）| 0.923 | 0.333 | 0.923 | 0.906 | 0.962 | 0.923 | 0.118 | 2/2 | – | ~1,754 | – |
| hyde（§10）| 0.846 | 0.397 | 0.769 | 0.748 | 0.885 | 0.769 | **0.138** | 2/2 | – | 2,707 | 49,974 |

**閱讀**：
- **官方排序質素排序（MRR@3）：none/hybrid 0.923 > rrf 0.910 > llm pointwise = ce 0.872 > llm_listwise 0.833 > hyde_rrf 0.821 > hyde 0.769 > naive 0.744。** 三條新方法都**贏唔到「唔 rerank」**——同 §9.1 結論一致：細枯 KB、8-doc、pool 原序已經接近最優。
- **cross-encoder 同 LLM pointwise 打和（都 0.872）**，但 ce「local ms/題 = 2,230ms」仲快過 pointwise（2,855ms）、同佢一樣 $0，且係 deterministic、唔使 prompt。差別只在 answer-F1（ce 0.101 vs pointwise 0.108）——都要再輸畀不做 rerank（none 0.111）。
- **LLM listwise 唔及 pointwise**（0.833 vs 0.872）：一次過排 ~20 候選對 4B 模型太散，輸出序有 noise；就算每題由约 25 次 call 縮到 1 次，用排序質素換 latency 唔抵。
- **HyDE+RRF fusion 救返 hyde 嘅 recall、但輸畀 q-lane**：hyde_rrf recall@3 0.846→**0.923**（q-lane 補返 h-lane 揾少咗嘅 doc）、answer-F1 0.138→0.125（fusion ctx 由「hypothesis 集中答案段」變返「雙 lane 雜訊」）、MRR@3 0.821**仍然低過 hybrid 0.923**——即係 h-lane 喺 top-of-list 係負資產，純靠 q-lane 先畫返平。
- `recall@5` 全線 0.962 → 5 份內一定揾到 gold；**呢個 KB 嘅排序增益已經一陪兩盡（top-of-list 無得再推），想推 answer-F1 唔應該再搞 ranking，傾向換 ctx 選段／少數 copy 合併**（§10 hyde 係唯一有效軸）。
- 執行學到嘅嘢：a) **hyde_rrf 嘅 answer ctx 唔可以兩 lane 分開全文直塞**——初版（q+h 兩 lane 共 30 分開入 ctx）11K tokens/題爆預算；限「top-5 RRF doc 各取 1 最佳分開」後 3.2K/題；b) **ce 要 torch+sentence-transformers**（`.venv` 原本冇，補裝 CPU 版；bge-reranker-v2-m3 本機 ~2.2GB）；c) `llm_listwise` 每題 1 次 Ollama call，local-token 計數要 trace 有 `local_tokens`（qwen3_listwise 條 key 都要 trace）。

---

### 附錄 A：重跑指令</think>

```bash
cd projects/fin_mate
# 快試（4 題 = f1/f9/t1/m1）：
.venv/bin/python -m experiments.rag_bench.run --smoke
# 全 15 題（f12 已剔，見 §7 caveat #8）× 現役 pipe（naive/advanced/hybrid/corrective/adaptive/hyde，500K budget）：
.venv/bin/python -m experiments.rag_bench.run --out experiments/runs/full_$(date +%y%m%d_%H%M) --max-tokens 500000
# 淨 run 新 type（唔 retest）：
.venv/bin/python -m experiments.rag_bench.run --only hyde --out experiments/runs/hyde_$(date +%y%m%d_%H%M) --max-tokens 150000
.venv/bin/python -m experiments.rag_bench.rerank --out experiments/runs/rerank_$(date +%y%m%d_%H%M) --max-tokens 150000
# 新 RAG 方法（§11）：
.venv/bin/python -m experiments.rag_bench.run --only hyde_rrf --out experiments/runs/hyde_rrf_$(date +%y%m%d_%H%M) --max-tokens 150000
.venv/bin/python -m experiments.rag_bench.rerank --only ce --out experiments/runs/rerank_ce_$(date +%y%m%d_%H%M) --max-tokens 150000
.venv/bin/python -m experiments.rag_bench.rerank --only llm_listwise --out experiments/runs/rerank_llmlist_$(date +%y%m%d_%H%M) --max-tokens 150000
# RRF 權重暖靴（retrieve-only、$0）：
.venv/bin/python -m experiments.rag_bench.rerank --rrf-sweep
```

### 附錄 B：定案（用戶）

- falsified citation 一票當 fail；trap 唔肯講「無資料」= fail。
- 全部 run 唔可以超過 500K tokens。
- `ByteDance-Seed-1.6` ⇒ 帳號可存取 alias `seed-1-6-flash-250715`（`ByteDance-Seed-1.6*` 全 404）；`thinking=disabled` 為必需。

---

*產出：`experiments/runs/full_260908_1551/`（五 pipe）+ `experiments/runs/full_agentic_260908_1601/`（agentic）。逐題 replay 見 `<pipe>/<eid>/transcript.jsonl`，stage 事件見 `<pipe>/events.jsonl`。*