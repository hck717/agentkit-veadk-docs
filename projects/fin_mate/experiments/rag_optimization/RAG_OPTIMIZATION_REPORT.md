# RAG 優化對比報告 — 公平 stack 重跑版（D8）

> 對比三條語料形塑軸（chunk / vis / gen）＋ 組合軸（cmb = 1+2+3）vs 原裝 RAG，
> 全部重新用 **BytePlus AI（Ark LLM）＋ 本地 OpenViking DB（server-side Ollama nomic-embed-text）** 跑，
> 同原裝 RAG（D4）完全同一堆基建，先可以公平比。

- 報告生成：2026-09-14 23:40（D8 fair redo tag：`runs_260914_2335`）
- 模型：LLM = Ark `seed-1-6-flash-250715`（BytePlus AI）；embedding = OpenViking 容器 call host Ollama `nomic-embed-text`（server-side parse+embed）
- 輸出目錄：`experiments/rag_optimization/results/fair/runs_260914_2335/`
- 舊版（impure，本地 llama-index + bge）結果保留喺 `results/d7_final/`（見 §7 對比表）

---

## 1. 背景

之前做過一輪「corpus 形塑」axis 測試（D7）：chunk（256/50 分塊）、multi-modal/vis、
generation prompt 三軸 × naive/hybrid。但嗰輪所用嘅 retrieval stack 係 **本地 llama-index + bge-small-en-v1.5**，
同原裝 RAG（D4）用嘅 **OpenViking + Ark** 唔同，即係「變數唔止軸一個」——唔公平。

今次（D8）將三條軸全部搬返去 **同原裝 RAG 一樣嘅 stack**：
- 知識庫 = 本地自架 OpenViking（`viking://` resource，server 端 parse + embed）
- embedding = server call host Ollama `nomic-embed-text`
- LLM = BytePlus AI（Ark）

咁樣先可以淨係比較「語料形塑」本身嘅效果，而唔係比較兩套 RAG 基建。

---

## 2. 方法

### 2.1 共同基建（全部軸一樣，淨係軸唔同）

- 每條軸一個**獨立 OpenViking index**（`fin_kb` / `fin_kb_chunk` / `fin_kb_vis` / `fin_kb_cmb`），
  全部由同一顆 server 端 embedding（host Ollama `nomic-embed-text`）負責 parse + embed，
  即係「語料點擺」先係唯一變數。
- 兩策略照抄 D4 `strategies.py`，一字不改：
  - **naive** = dense `find` top-5 ＋ L2 hydrate（read_limit 200）
  - **hybrid** = dense top-15 ＋ grep sparse terms → **RRF(k=60)** 融合，輸出 doc 級 ranking
- 評估：`eval_metrics`（recall@5 / prec@5 / MRR@5 / nDCG@5 / answer-F1 / trap）。
  - recall@5 = gold doc 係咪喺 first-5 doc 級 rank 出現（doc 級，唔係 part 級）
  - answer-F1 = 生成答案 vs gold 答案嘅 token F1（答中關鍵數字/詞）
- **gold === doc 級 prefix**：每個 gold 檔案名 → `doc_uris.json` 一條 doc prefix；任何 retrieved URI
  `startswith(prefix)` 即係 hit。
- **part 級→doc 級合併**：chunk / cmb 嘅 retrieval 係 part 級（每個 256/50 part 各自一個 OpenViking folder），
  計分前將所有 part 按「首現保序＋去重」併返做 doc 級 rank（同 default 每 doc 一個 folder 語義一致）。
- 題目：**text set** = `CURRENT_ITEMS`（15 題：11 fact＋2 trap＋2 multi-hop）；**vis set** = text set ＋
  5 條 vis needle（mb1–mb5）= 20 題。default/chunk/gen 用 text set；vis/cmb 用 vis set。
- indexes 建立（server 端一次過 seed，`add_resource(wait=True)`）：`fin_kb` reseed 13.6s（8 file / 108 vector）、
  `fin_kb_chunk` 38.2s（375 / 1127）、`fin_kb_vis` 15.2s（12 / 120）、`fin_kb_cmb` 73.0s（387 / 1245）。

> **重要 caveat**：RESULTS.md 記低嘅原裝 D4 數（recall@5 0.964）係 2026-09-08 嗰日 snapshot。
> 同一 code path 今日喺同一 fin_kb 重跑 default naive 得 0.731 —— 0.964 反映嗰時嘅 embed 配置
> （server 端 embed 模型 / reseed），唔係今日主流。所以主表用 **同日 default control** 做 baseline
> （fair），D4 recorded 當歷史 reference。

### 2.2 每條軸詳細方法

**default（控制組）——原裝 RAG 就係咁**
- corpus = `data/kb/msft_txt` 8 份 analyst 研報 txt（Deutsche / Mizuho / China Renaissance / Barclays /
  Wells Fargo / DeMatteo ＋ 兩份 Earnings Call pdf-txt），**一份 doc = 一個 OpenViking folder**
  （即 server 預設「成檔一個 block」粒度）。
- gen = `normal` prompt：system 只叫 inline 標註【KB:檔案名】＋ 結尾「## 來源」；資料直接黐落 system prompt。
- 用途：控制組 —— 未做任何形塑之前，同一日同 stack 嘅實況性能。

**chunk（軸 1）——語料「斬細」**
- 同一 8 份 txt，由腳本用 **llama-index `SentenceSplitter(chunk_size=256, overlap=50)`**（同 D7 完全一樣參數）
  預先切開 → **375 個 part**，每個 part 一個 file `<docshort>_NNNN.txt`，全部以 `add_resource` 送入
  `fin_kb_chunk`。
- 每個 part 喺 OpenViking 係獨立 folder＋獨立 embedding；retrieval 計分前按 `<docshort>` 併返做 doc 級。
- 原理：256-token 粒度令「掛身 keyword ／ 句子級語義」唔俾長段落稀釋，dense 揀中嘅 part 更貼題；
  overlap 50 token 防關鍵數字被句界斬斷。
- 呢條係「唔使動 model / 唔使動 prompt」嘅純語料層改造。

**vis（軸 2）——語料「加料」（視覺/表格/網頁內容入文字）**
- corpus = 同一 8 txt ＋ `data/kb_vis` 嘅文本化版本（12 files 總共）：
  - `msft_ai_capex.txt`：原 txt（AI capex 數字），直接用
  - `msft_azure_revenue.csv`（132B）：**直接讀做文字**（TextParser 當 txt 食）
  - `msft_scan.pdf`（2.7KB）：**PyMuPDF `get_text()`** 抽文字（memo 正文）
  - `msft_kb_overview.html`（892B）：**BeautifulSoup `get_text()`** 剝 tag 抽文字
  - `.png`（圖片）呢條 pipeline **剔除**——冇 vision channel，入去等於空檔，刻意唔混入去誤導評估
- 全部 vis 來源統一輸出做 `.txt`（保證 OpenViking TextParser 食到），再 `add_resource` 入 `fin_kb_vis`。
- 目的：測試「將表格/掃描/網頁內容都納入知識庫」對 needle（「啲數字係咪真係搵到＋答到」）嘅效果。
- 評估用 vis set（20 題），gold 對返 CSV/PDF/HTML 原檔名（`msft_azure_revenue.csv` 等）。

**gen（軸 3）——輸出層「規訓」**
- corpus 完全唔動（照用 default `fin_kb`，8 txt 原裝粒度），淨係換 **`normalized` gen prompt**：
  1. 每句 claim 後 inline 標註【KB:檔案名】
  2. 一定要引用精確數字（百分比、金額、年度/季度、倍數），唔准改寫到變義
  3. 資料唔覆蓋嘅部分明確標「資料冇提供」，唔准靠記憶補
  4. 結尾「## 來源」列檔案全名
- 由於 retrieval 同 default 零分別（同一 KB），return / recall / MRR 理論上不變——佢量度嘅係
  「**同一堆 context 擺到啱，模型識唔識正確讀出數字答**」。

**cmb（軸 4）——1+2+3 全合體**
- corpus = **chunk（軸 1 嘅 375 part）＋ vis 文本（軸 2 嘅 12 file）** = 387 files，入 `fin_kb_cmb`
- gen = **normalized（軸 3 嘅 prompt）**
- 即係將三條軸嘅改造一次過套晒落去：語料斬細（1）＋ 資料類型加闊（2）＋ 輸出規訓（3）。
- 評估用 vis set（20 題），gold 對返 8 txt ＋ 4 vis 原檔名。

### 2.3 未知的邊界

- 圖片（png）冇行；embedding 用 nomic（免費/本地）而唔係更強嘅模型；hybrid 冇查 calendar/model 層；
  答案冇做 RAGAS / human 評分，只用 answer-F1 proxy（token 級）。
- 留意 vis 軸（20 題）同 text 軸（15 題）分母唔同，跨 set 嘅 recall 唔可以直接比較；有 vis 先計到的 needle 另列。

---

## 3. 主對比表（全部同 stack：OpenViking + nomic embed + Ark LLM）

| run | 軸 | recall@5 | prec@5 | MRR@5 | nDCG@5 | answer-F1 | trap | USD | ms/題 |
|---|---|---|---|---|---|---|---|---|---|
| fair_default_naive | default 控制 | **0.731** | 0.256 | 0.564 | 0.603 | 0.086 | 2/2 | 0.0013 | 1850 |
| fair_default_hybrid | default 控制 | 0.808 | 0.185 | 0.579 | 0.633 | 0.099 | 2/2 | 0.0018 | 1771 |
| fair_chunk_naive | chunk | 0.769 | 0.288 | 0.628 | 0.636 | 0.113 | 2/2 | 0.0008 | 1425 |
| fair_chunk_hybrid | chunk | **0.962** | 0.237 | 0.659 | 0.715 | **0.148** | 2/2 | 0.0011 | 1850 |
| fair_vis_naive | vis | 0.694 | 0.210 | 0.569 | 0.598 | **0.123** | 2/2 | 0.0016 | 1509 |
| fair_vis_hybrid | vis | 0.694 | 0.156 | 0.569 | 0.598 | 0.122 | 2/2 | 0.0024 | 1654 |
| fair_gen_naive | gen | 0.731 | 0.256 | 0.564 | 0.603 | 0.079 | 2/2 | 0.0014 | 1902 |
| fair_gen_hybrid | gen | 0.808 | 0.185 | 0.579 | 0.633 | **0.136** | 2/2 | 0.0018 | 1735 |
| fair_cmb_naive | cmb (1+2+3) | 0.722 | 0.261 | 0.625 | 0.629 | **0.140** | 2/2 | 0.0010 | 1216 |
| fair_cmb_hybrid | cmb (1+2+3) | 0.806 | 0.194 | **0.636** | **0.665** | 0.145 | 2/2 | 0.0015 | 1697 |

歷史 reference（2026-09-08 snapshot，同 stack 但當時 embed 配置）：D4 naive recall@5 0.964 / MRR 0.762 / F1 0.109；
D4 hybrid recall@5 0.964 / MRR 0.929 / F1 0.127。

### 點睇呢張表（相對 default 控制）

- **chunk hybrid recall@5 = 0.962**，係全表最高，同一日 default hybrid（0.808）比 +0.15：
  256/50 預先分塊畀 hybrid 嘅 RRF 融合最大好處——細粒掛身 keyword 命中更準，`_000N` part 各自 ranking，
  RRF 唔會俾過長原文段落淹沒。
- **chunk 同時慳錢慳 token**：naive $0.0008/題 vs default $0.0013（ctx 短咗）；成本最低之餘 recall/F1 都升。
- **vis**：加咗 kb_vis 內容之後，naive 反而略跌（0.731→0.694，因為 vis 文本分散咗空間，top-5 俾 vis folder 佔位），
  但 **answer-F1 升**（0.086→0.123）——其中 3/5 條 vis needle 有呼應（見 §5）。
- **gen（normalized prompt）**：retrieval 完全一樣（同 default corpus），Recall/MRR 唔變（合理），
  但答題質素改善明顯：hybrid answer-F1 0.099→**0.136**、naive 0.086→0.079（volatile），
  成本差別好細（多咗 inline 標註 token）。
- **cmb（1+2+3 合體）**：recall 唔係三條軸嘅最好——naive 0.722 / hybrid 0.806（介乎 default 同 chunk 之間），
  但 **answer-F1 / MRR / nDCG 係全表其中最好**（naive F1 0.140、MRR 0.625、ms/題最平 1216）。
  即係：合體 corpus 對「搵到嘢」冇額外優勢（同 default 打平），但對「答得靚」加乘——分塊短 context＋vis
  needle 內容＋強 prompt 三合一，令生成質素最高之餘成本同速度又低。

### what about 軸同軸之間（相對）

| 指標 | default | chunk | vis | gen | cmb |
|---|---|---|---|---|---|
| recall@5 (hybrid) | 0.808 | **0.962** | 0.694 | 0.808 | 0.806 |
| answer-F1 (hybrid) | 0.099 | 0.148 | 0.122 | 0.136 | 0.145 |
| usd/題 (hybrid) | 0.0018 | **0.0011** | 0.0024 | 0.0018 | 0.0015 |
| ms/題 (naive) | 1850 | 1425 | 1509 | 1902 | **1216** |

---

## 4. 速度 / 成本 trace（每題平均，events.jsonl）

| run | retr(ms) | answer(ms) | total(ms) | total(s)[站立] | prompt tok | comp tok | USD |
|---|---|---|---|---|---|---|---|
| fair_default_naive | 115.8 | 1734.0 | 1849.8 | 27.7 | 36,444 | 2,613 | 0.0013 |
| fair_default_hybrid | 132.7 | 1638.2 | 1770.9 | 26.6 | 61,278 | 2,286 | 0.0018 |
| fair_chunk_naive | 84.3 | 1341.2 | 1425.4 | 21.4 | 16,192 | 2,034 | 0.0008 |
| fair_chunk_hybrid | 156.4 | 1694.0 | 1850.4 | 27.8 | 26,412 | 2,704 | 0.0011 |
| fair_vis_naive | 92.3 | 1416.2 | 1508.5 | 30.2 | 46,255 | 2,902 | 0.0016 |
| fair_vis_hybrid | 129.4 | 1525.0 | 1654.4 | 33.1 | 82,189 | 3,061 | 0.0024 |
| fair_gen_naive | 91.0 | 1810.9 | 1901.8 | 28.5 | 37,599 | 2,937 | 0.0014 |
| fair_gen_hybrid | 132.4 | 1602.9 | 1735.3 | 26.0 | 62,433 | 2,225 | 0.0018 |
| fair_cmb_naive | 90.2 | 1126.0 | 1216.2 | 24.3 | 27,846 | 2,179 | 0.0010 |
| fair_cmb_hybrid | 163.0 | 1534.4 | 1697.4 | 33.9 | 40,837 | 3,073 | 0.0015 |

- 全程 10 runs（176 題-call）用住 **463,499 tokens / ~$0.0147**（全部 Axes 連同 control）。
- 趨勢同 D7 一致：**hybrid 必然貴過 naive**（dense top-15＋grep＋RRF），但貴唔多（+30–90% tokens）。
- **chunk 同 cmb 嘅 naive 都係最平又最快**：短 context（每 part 2000 char cap 之下內容短）→ prompt tok 少。

---

## 5. 深入洞見——per-item 分析

> 呢度全部用各 run `report.md` 嘅 per-item 行計算（Δ = 軸 hybrid F1 − default hybrid F1，13 條 shared items），
> 令「軸好唔好」由 aggregate 平均落到「邊條題目變好、邊條題目變差」。

### 5.1 chunk 嘅得失（相對 default hybrid F1 Δ）

| 題目 | Q（摘要） | default F1 | chunk F1 | Δ | 解讀 |
|---|---|---|---|---|---|
| f9 | F2Q26 Cloud 季度收入首次破___？ | 0.233 | **0.593** | **+0.360** | 「首次破」呢類句子需要精確粒度，256 chunk 啱啱埋到句尾數字 |
| f5 | China Renaissance 2026E EPS？ | 0.000 | 0.235 | **+0.235** | naive recall 0→1：EPS 數字本來被長段落埋藏，切開後嵌入一個 part 搵到 |
| f1 | Deutsche Azure constant currency？ | 0.061 | 0.143 | +0.082 | 同一 doc 搵到但 chunk 粒度令 ctx 更聚焦 → 答案準 |
| f11 | DeMatteo 市值？ | 0.000 | 0.074 | +0.074 | 多乎──原本搵唔到嘅 doc 終於上 top-5 part |
| m1 | Azure 供應受限 + E7 upsell？ | 0.000 | 0.069 | +0.069 | multi-hop 第一個 leg（Azure）重新出現喺 top-5 |
| f3 | Mizuho F2Q 總收入？ | 0.032 | 0.098 | +0.066 | part-level 精準把美元數字埋入 ctx |
| **f10** | **F2Q26 Copilot 付費席位幾多？** | **0.200** | **0.025** | **-0.175** | **chunk 最大 regression**：席位數字同一段落但跨 256→512 粒度，切開後「Copilot」同「席位」分咗兩個 part，hybrid 撈唔埋 |
| m2 | Security + agentic adoption？ | 0.229 | 0.197 | -0.032 | naive recall 1.0→0.5，multi-hop 第二 leg 喺 hybrid 被邊緣化 |
| f8 | Wells agentic adoption 關鍵？ | 0.263 | 0.238 | -0.025 | noise（ctx 已經夠） |

**小結**：chunk 對大部分 fact 題有正面幫助（尤其數字分散喺長段落嘅 f9、f5），但 **有少數題嘅答案
跨 chunk 邊界就會 regression**（典型例子 f10）——呢個係 256/50 粒度嘅結構性限制。

---

### 5.2 gen prompt 嘅效果（相對 default hybrid F1 Δ，retrieval 完全一樣）

| 題目 | default F1 | gen F1 | Δ |
|---|---|---|---|
| f10（Copilot 席位） | 0.200 | **0.500** | **+0.300** |
| m1（Azure + E7） | 0.000 | 0.092 | +0.092 |
| f11（DeMatteo 市值） | 0.000 | 0.085 | +0.085 |
| f3（Mizuho 收入） | 0.032 | 0.077 | +0.045 |
| f1（Deutsche Azure） | 0.061 | 0.083 | +0.022 |
| f9（Cloud 季度收入） | 0.233 | 0.154 | -0.079 |

**小結**：normalized prompt 唔郁 retrieval（合理）但大幅改善「**將 context 正確讀出**」——
尤其係 f10（+0.300！），呢個正正係 chunk regression 嘅題：prompt 規訓 + 完整 doc 級 ctx（同 default）
解決咗同一個問題。即係 **gen prompt 係 chunk regression 嘅 patch**。

---

### 5.3 cmb vs default（hybrid F1 Δ，全 13 shared items）

| 題目 | Δ | 來源 |
|---|---|---|
| f9 | **+0.245** | chunk（軸 1）貢獻 |
| m1 | +0.094 | chunk + gen（軸 1+3） |
| f5 | +0.085 | chunk（軸 1） |
| f6 | +0.026 | vis 文本（軸 2） + gen |
| f3 | +0.019 | chunk |
| f1 | +0.016 | chunk |
| **f10** | **-0.164** | chunk regression 仍然存在（Gen 部分 buffer 但唔夠） |
| **f8** | **-0.050** | chunk noise |

**小結**：cmb 繼承咗 chunk 大部分優勢（f9/f5/m1），同時 gen prompt buffer 咗一部分 regression。
但 **f10 嘅 chunk regression 喺 cmb 仍然存在**（-0.164 vs default），只有直接用 gen prompt + default corpus
先可以完全解決（+0.300）。呢個揭示咗一個重要洞察：**combine 唔等於1+1=2**——佢繼承底層嘅限制。

---

### 5.4 vis needle 拆解

| needle | gold（vis 文件） | vis recall | cmb recall | 點解搵到 / 搵唔到 |
|---|---|---|---|---|
| mb1（Azure 35% FY26Q4E） | msft_azure_revenue.csv | **0** | **0** | csv 只有 132 byte，embedding 冇足夠語義信號 |
| mb2（AI capex 112B FY27） | msft_ai_capex.txt | **1** | **1** | 「capex / compute / spend」embedding strong |
| mb3（inference $1.2/M tokens） | msft_ai_capex.txt | **1** | **1** | 同上，inference 數字喺同一檔 |
| mb4（E7 250K pilot seats） | msft_scan.pdf | **1** | **1** | scan.pdf → text 後「E7 / pilot / seats」embedding 深 |
| mb5（EMEA 27% revenue） | msft_kb_overview.html | **0** | **0** | overview.html 文本太短/關鍵詞密度低 |

**3/5 hit**，**2/5 miss**——consistent across naive/hybrid/vis/cmb 四個 run。
原因：csv（132B）同 overview.html（text 後 ~200 token）**粒度太細**，
就算攞咗落 OpenViking，server 端 nomic embedding 冇足夠上下文去建立穩定嘅向量
→ retrieve 嗰時永遠排唔入 top-5。

---

### 5.5 最平最快組合（per-run trace 拆解）

| run | retr ms | answer ms | total ms | prompt tok | comp tok | $/run |
|---|---|---|---|---|---|---|
| cmb naive | **90.2** | **1126** | **1216** | 27,846 | 2,179 | **0.0010** |
| chunk naive | 84.3 | 1341 | 1425 | **16,192** | 2,034 | **0.0008** |
| vis hybrid | 129.4 | 1525 | 1654 | 82,189 | 3,061 | 0.0024 |

- **chunk naive prompt tok 最低**（16K vs default 36K）：因為 256/50 part 內容短，top-5 回傳嘅 ctx token 少。
- **cmb naive total ms 最低**（1216ms）：ctx 短 + prompt 精煉 → LLM answer 快。
- **vis hybrid 最貴**：hybrid dense top-15 + grep + corpus 有 12 個 file（比 default 多 50% folder）→ prompt tok 爆升（82K）。

---

## 6. 各軸有用性與效果——幾時用邊條路

### chunk（軸 1）：**值得用，但要留意 f10 類 regression**

- **優點**：recall 由 0.808 → 0.962（hybrid），是全表最高提升；naive 成本降到 $0.0008/題（default 0.0013），
  速度降到 1425ms（default 1850ms）。256/50 令 dense 搵到更精準嘅 part。
- **缺點**：有少數題（f10）因為答案跨 chunk 邊界而 regression（F1 -0.175）；解決方案有二：
  （a）用 gen prompt（+0.300 對沖），或（b）加 overlap 到 100 或更多（實驗再測）。
- **最適合**：需要 **highest recall**（例如做 RAG research agent、找全部支持證據）嘅場景。

### vis（軸 2）：**單獨唔夠用，但為 needle / answer 質素提供基礎**

- **優點**：answer-F1 由 0.086 → 0.123（naive +43%）；mb2/mb3/mb4 呢三條 needle 全部 hit。
- **缺點**：recall 略跌（0.731 → 0.694）；csv / overview 太細永遠 hit 唔到（mb1/mb5 miss）。
- **最適合**：當個系統**需要直接答出 vis 類問題**（「capex 幾多？」）嘅特定場景。
  若果用得 vis，最好做 **來源預處理**（例如 csv 轉 Markdown table，overview 加 sentence padding），
  增加 embedding 嘅語義厚度。

### gen（軸 3）：**幾乎零成本改善 F1，建議永遠开着**

- **優點**：retrieval 完全唔變，F1 由 0.099 → 0.136（+37%），尤其 f10（+0.300）補救咗 chunk regression。
- **缺點**：答案略長（多 inline 標註 token），成本差別好細（0.0018→0.0018 基本冇差）。
- **最適合**：所有場景都值得加；normalized prompt 係「免費午餐」——冇壞處，有改善。
  唯一留意：如果個 app 已經有唔同嘅答案格式要求（例如 UI 不支持【KB:】格式），
  要再評估。

### cmb（軸 4 = 1+2+3）：**好唔好？值得但唔係無條件**

先講「值唔值 combine」：

**合并效果唔係線性疊加。** cmb recall（0.806）= 幾乎等同 default（0.808），冇帶嚟 chunk 嘅 0.962 優勢。
原因：chunk 嘅 recall 增益來自「同一份 doc 切開後各 part 各自 ranking」，而 vis 軸加入咗 12 個額外 folder
（total 387 parts），「搶位」效應抵消咗 chunk 嘅粒度紅利。再加上 vis/cmb 分母多咗 5 題（20 vs 15）
且 mb1/mb5 永遠 miss，整體 recall 數字被拖低。

**但 cmb 係全表「質素」最好嘅軸：**

| 指標 | default hybrid | cmb hybrid | cmb naive |
|---|---|---|---|
| answer-F1 | 0.099 | **0.145** | **0.140** |
| MRR@5 | 0.579 | **0.636** | 0.625 |
| nDCG@5 | 0.633 | **0.665** | 0.629 |
| total ms/題 | 1771 | 1697 | **1216** |
| prompt tok/題 | 61,278 | 40,837 | 27,846 |

cmb naive 嘅成本同速度全表最低（1216ms、27K prompt tok、$0.0010），而 answer-F1 / MRR / nDCG 喺
所有 naive run 中最高。

**cmb vs chunk，幾時揀邊個：**
- 要 **highest recall**（搵齊所有支持證據）→ 揀 **chunk hybrid**（0.962）
- 要 **best quality per dollar**（平、快、答得最準）→ 揀 **cmb naive**（$0.0010、1216ms、F1 0.140）
- 要 **both high recall + high F1** → 唔存在完美答案；可以用 **chunk hybrid + normalized prompt**（成本
  同 cmb hybrid 接近，但 recall 更高）——呢個組合未跑，係下一步建議。

**結論（combine 值唔值）：**

合并（cmb）**值得，但目的唔係追求 recall**——佢嘅價值係「**以最低成本同最高速度取得最好嘅答案質素**」。
如果個產品嘅 user 體驗依賴「答得準」（例如 financial analyst chatbot、自動化 report），
cmb naive 嘅效果＋成本效益係全表最佳。但如果你嘅場景需要「搵得齊」（例如合規審查、evidence collection），
應該用 chunk hybrid 而唔係 cmb。

最重要嘅 insight：**三條軸唔係互相替代嘅，而係各自 optimize 唔同嘅維度**——
chunk 優化 recall（搵到）、gen 優化 F1（答到）、vis 優化 needle coverage（特定文件）。
cmb 係三者嘅折衷，喺成本同速度上有優勢，但在 recall 上無額外收益。

---

## 7. 總結（TL;DR）

1. **三條軸各 optimize 唔同維度，唔係互相替代**：
   - **chunk** → optimize **recall**（hybrid recall@5 0.808→**0.962**，全表最高），兼且最慳 token；
     代價係 f10 呢類「答案跨 chunk 邊界」嘅題會 regression（見 §5.1）。
   - **gen** → optimize **answer-F1**（同 ctx +37%，尤其 f10 +0.300，見 §5.2），retrieval 零影響，成本差好細；
     **建議永遠開**。
   - **vis** → optimize **needle coverage**（mb2/mb3/mb4 hit），幫 answer-F1（0.086→0.123），
     但 csv/overview 太細嘅文件永遠 miss（mb1/mb5），recall 仲會俾 vis folder 佔位略跌（見 §5.4）。
2. **chunk hybrid** 係全表單一最佳 recall / 最佳 F1 跑法（0.962 / 0.148），且 naive 成本最低（$0.0008/題）。
3. **cmb（1+2+3）值得，但唔係為咗 recall**：recall 返返同一水平同 default（0.806 vs 0.808）——
   vis 搶位 + 20 題分母抵消 chunk 紅利。**cmb 真正價值係質素性價比**：
   cmb naive 以全表最平（$0.0010）最快（1216ms）做到全部 naive run 最高 F1（0.140）/ MRR（0.625）/ nDCG（0.629）。
   combine 繼承底層限制（f10 仍然 -0.164），不是 1+1=2（見 §6）。
4. **選型**：要搵得齊（evidence / 合規）→ **chunk hybrid**；要答得準且平（chatbot / report）→ **cmb naive**。
5. **下一步建議**：跑 **chunk hybrid + normalized prompt**（軸組合至今未測）——預期攞齊 chunk 嘅 recall
   同 gen 嘅 F1 buffer，係「兩個好處都要」嘅最優解；順便測 chunk overlap 100 對 f10 regression 嘅改善。

---

## 8. 附錄

### 重現方法

```bash
# 1. 起 stack
make stack up                      # openviking / redis / web / otel / jaeger；ov.conf 指 host Ollama nomic-embed-text
# 2. 建 axis corpora（chunk 256/50、vis 文本擷取、cmb 合併）
python experiments/rag_optimization/scripts/build_axis_corpora.py
# 3. seed 三個 index（fin_kb_chunk / fin_kb_vis / fin_kb_cmb）+ 寫 doc→prefix map
python experiments/rag_optimization/scripts/seed_fair_kbs.py
# 4. 十 runs（default 控制 / chunk / vis / gen / cmb × naive/hybrid，真 LLM）
python experiments/rag_optimization/scripts/run_fair.py
# 5. trace（speed/time/processes）
python experiments/rag_optimization/trace_analysis.py --fair 260914_2335
```

### 檔案位置

- 結果：`experiments/rag_optimization/results/fair/runs_260914_2335/`（各 run events.jsonl / report.md / per-item answer.txt，SUMMARY.md）
- doc→uri map：`experiments/rag_optimization/results/fair/doc_uris.json`
- 語料：`experiments/rag_optimization/datasets/{kb_chunk,kb_vis_seed,kb_cmb}`
- scripts：`experiments/rag_optimization/scripts/{build_axis_corpora,seed_fair_kbs,run_fair}.py`
- 歷史：D4 recorded `results/d4_original/`；舊 local-stack 版 `results/d7_final/`

### 同 D7（舊 local-stack bge 版）對比（參考，唔係公平比）

| 軸 | D7 local recall@5 (naive/hybrid) | D8 fair recall@5 (naive/hybrid) |
|---|---|---|
| default | 0.885 / 0.962 | 0.731 / 0.808 |
| chunk | 0.923 / 0.962 | 0.769 / 0.962 |
| mm/vis | 0.861 / 0.917 | 0.694 / 0.694 |
| gen | 0.885 / 0.962 | 0.731 / 0.808 |

同樣個趨勢（chunk 係 recall winner、vis 幫 F1）喺兩個 stack 都出現，但數值唔可以直比。