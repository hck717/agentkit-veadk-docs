# FIN-MATE E1 · LoRA/QLoRA vs RAG（全 local）bench report

- generated: 2026-09-11 18:11:32
- 設定：Qwen3-4B-Instruct-2507 base；LoRA（bf16 base, r=8, 16 layers, 500 iters）；QLoRA（4-bit base）；
  RAG = naive/hybrid/adaptive 用本地 4-bit base 代答；eval = 34 條 golden，同 D6 同一套 evaluators
- 全 local：無 Ark／無雲／無 API 費用。ranking 用同一批 golden，同枱對比閉卷 vs RAG。
- 記憶體友好：每 row 只 serve 1 個 model；llm_judge 拆開做 `--judge` pass（Ollama 單獨）。

## 結論

- **QA 子集（15 條，唯一 RAG 有跑嘅 subset，fact_single 用 llm_judge 語言中立重評）**：
  RAG hybrid/better 8/15 > naive/adaptive 6/15 > LoRA 閉卷 5/15 > base/QLoRA 4/15。
  - **fact_multi（4 條）**：RAG 全 pipe 4/4，閉卷只得 base/QLoRA 2/4、LoRA 1/4——
    多跳 synthesis 靠 retrieval 畀料先做到，閉卷結構性做唔到。
  - **fact_single（11 條）**：hybrid/better（hybrid+advanced）**4/11** > naive/adaptive 2/11 >
    LoRA 閉卷 1/11 > base/QLoRA 0/11。RAG 拎到嘅 4 條（fs_01 Azure 38% vs guidance、fs_08 agentic→安全、
    fs_09 Cloud $50B/+26%、fs_11 市值 $2,977B）全部屬實且含關鍵數字。
- **fact_single 低分 90% 係 metric artifact，唔係 RAG 失敗**（見下節）。英語 golden × 粵語 pred 嘅
  `answer_f1` token-overlap 結構性封頂（高質 pred 都只得 f1 0–0.24，低過 PASS 0.25）。
  用語言中立 llm_judge 重評：`$2,977B（啱）` 由 f1=0.000 → PASS；`50B/+26%（啱）` 由 0.244 → PASS；
  相反 LoRA 有 2 條 f1 高分（fs_09 0.250、fs_10 0.588）judge 判 FAIL（漏關鍵數字）——f1 高分唔等如啱。
- **更好 retrieval 有冇幫到手？** better panel（hybrid+advanced，k=15+sparse）對 fact_single 同普通 hybrid
  一樣 4/11——**樽頸唔喺 retrieval**：加多料（15k、sparse/grep 覆蓋 gold doc）都唔會再升，
  4B 生成本身先係樽頸（回絕「KB：檔案名」或答漏數字）。
  反而 **adaptive/naive 只有 2/11**（k=5 太窄，MISS 咗 fs_01 嘅 Deutsche doc、fs_11 嘅 DeMatteo doc）——
  k 太細先係真 retrieve 樽頸，k=15 或以上即到頂。
- **QLoRA 保留 base 能力（非-qa task）**：sent_score 5/5、sent_3way 6/6、calc/news 滿分，完全追返 base；
  LoRA 反而跌（sent_score 3/5、sent_3way 5/6）——FT 有 catastrophic forgetting，QLoRA 傷害細好多。
- **Latency／資源**：閉卷 0.7–4.8s/record 快過 RAG（naive ~14s、adaptive ~21s、hybrid ~66s/record）；
  QLoRA 訓練 peak 3.96GB vs LoRA 9.68GB，fused 模型 2.1GB vs 7.5GB，eval 亦更快。
- **總評**：本地 4B 做係可以，但 fact recall 上限低——公司數就要 RAG + 強 model（D6 hybrid 全 34 條 26/34）；
  事實類問題 RAG（k≥15）> FT 閉卷，但唔好信英文-f1；要保留原 task 能力 → QLoRA。

## fact_single 深度調查（metric vs llm_judge，每 row 同一批 11 條）

`answer_f1` 將英文 golden 同粵語 pred 用 `[a-z0-9]+` token 化，overlap 結構性封頂 → f1-pass 嚴重低估。

| row / pipe | f1-pass | llm_judge-pass | 被 metric 隱藏嘅啱答案 |
|---|---|---|---|
| base（閉卷） | 0/11 | 0/11 | — |
| LoRA（閉卷） | 3/11 | 1/11 | （fs_09/fs_10 f1 高分但 judge FAIL：漏數字） |
| QLoRA（閉卷） | 0/11 | 0/11 | — |
| rag naive | 0/11 | 2/11 | fs_08、fs_09（兩條答啱，f1 只得 0.235/0.244） |
| rag hybrid | 1/11 | 4/11 | fs_01、fs_08、fs_09、fs_11（fs_11 啱晒但 f1=0.000） |
| rag adaptive | 0/11 | 2/11 | fs_08、fs_09 |
| better hybrid | 1/11 | 4/11 | 同上（=普通 hybrid） |
| better advanced | 1/11 | 4/11 | 同上（=普通 hybrid） |

### 每條 fact_single 根因

| id | 內容 | 根因 |
|---|---|---|
| fs_01 | Azure 38% vs guidance 37% | hybrid/better 啱（+38%>37%）但 f1 0.18→FAIL；naive k=5 MISS Deutsche doc |
| fs_02 | F2Q revenue vs 預期 beat | 答到「略高於市場預期」冇實數 → judge FAIL |
| fs_03 | 總收入 $81,189M | 數字錯（答 81,215 或 76,441 萬）→ 錯答案 |
| fs_04 | 股價目標 | KB 冇 → model 求其答 → FAIL |
| fs_05 | 中國再保 EPS 17.11/15.80 | dense@5/15 都 MISS（table chunk 沉底），sparse 冇 term → 冇料答 |
| fs_06 | F2Q26 座位數 15M | 答到無咗/漏 → FAIL |
| fs_07 | Wells Fargo E7 $99 | hybrid/better 答到 $99/用戶（f1 0.41→PASS）但 judge 判 FAIL（pred 加咗「Agent 365/Copilot」可能誇大/假陰性）；naive/adaptive MISS doc |
| fs_08 | agentic adoption 靠安全 | 全 pipe 啱（judge PASS ×6）但 f1 0.14–0.24→FAIL |
| fs_09 | Cloud 首破 $50B/+26% | 全 pipe 啱（judge PASS ×6）但 f1 0.244 差少少→FAIL |
| fs_10 | 辦公 tile+收入 | KB 冇 → FAIL |
| fs_11 | 市值 $2,977B | hybrid/better 啱（答啱 $2,977B）但 f1=0.000（2,977,b vs 2977）→ 最誇張 1 宗 |

> 即：11 條入面 metric-pass 3/11（loRA 有 2 條係假高分），judge 判 hybrid/better 均有 4/11 真啱。
> 呢個同 D6 Ark（同 metric）3/11 比較唔公平——D6 都係用英文-f1 量度；judge 版先係真本事。
> 結論：唔加料都加 k=15 + sparse 就好；4B 生成上限先係事實 recall 樽頸。

## 模型 / 訓練

| item | LoRA | QLoRA |
|---|---|---|
| base | Qwen3-4B-Instruct-2507 (bf16) | ...-2507-4bit |
| train loss (500 iters) | 0.086 | 0.136 |
| val loss | 0.533 | 0.522 |
| peak mem | 9.68 GB | 3.96 GB |
| trained tokens | 47,767 | 55,767 |
| adapter size | 169 MB | 169 MB |
| fused model | bf16 (7.5G) | 4-bit (2.1G) |
| training data | finetune/datasets (576 train / 64 valid) | 同左 |
| leakage check | golden answers/context 由 training data 剔除 | 同左 |

## 總覽

| row | pipe | 範圍 | n | pass | score(mean) | total ms | ms/rec |
|---|---|---|---|---|---|---|---|
| **base** | - | 全部 34 條（閉卷） | 34 | **21/34** | 0.750 | 58820 | 1730 |
| **better** | advanced / hybrid | 全部 34 條（閉卷） | 30 | **16/30** | 0.682 | 2562350 | 85412 |
| **lora** | - | 全部 34 條（閉卷） | 34 | **18/34** | 0.629 | 164751 | 4846 |
| **qlora** | - | 全部 34 條（閉卷） | 34 | **21/34** | 0.750 | 24426 | 718 |
| **rag** | adaptive / hybrid / naive | QA 15 條 ×pipe | 45 | **20/45** | 0.621 | 1665242 | 37005 |

> D6 baseline（Ark `seed-1-6-flash` + hybrid RAG，全 34 條）= 26/34、fact_single 3/11（英文-f1 量度）、~40.5s/record。
> 本場 rag/better rows 只跑 QA 15 條（fact_multi 4 + fact_single 11），其餘 19 條閉卷 task 冇 RAG 版本可比。
> 公平比法：QA 子集內「本地 RAG vs 閉卷」，閉卷總做唔到 multi-hop；RAG 得唔到 D6 級 fact_single（但 D6 分都用英文-f1 低估）。

## per-set 明細

### base · - · calc_expr（5/5，score=1.000，15608 ms）
- `tc_calc_01` score=1.0 pass=OK 2859ms | computed 37.0 vs want 37.0
  pred: {"tool": "calc", "args": {"expr": "38 - 1"}}
- `tc_calc_02` score=1.0 pass=OK 3008ms | computed 1.0 vs want 1.0
  pred: {"tool": "calc", "args": {"expr": "81.3 - 80.3"}}
- `tc_calc_03` score=1.0 pass=OK 3216ms | computed 17.064000000000004 vs want 17.064
  pred: {"tool": "calc", "args": {"expr": "15.80 * 1.08"}}
- `tc_calc_04` score=1.0 pass=OK 3760ms | computed 65.0 vs want 65.0
  pred: {"tool": "calc", "args": {"expr": "((99 - 60) / 60) * 100"}}
- `tc_calc_05` score=1.0 pass=OK 2765ms | computed 39.682539682539684 vs want 39.6825396825
  pred: {"tool": "calc", "args": {"expr": "50 / 1.26"}}
### base · - · fact_multi（2/4，score=0.500，2976 ms）
- `qa_fm_01` score=0.0 pass=-- 881ms | verdict='FAIL' ms=2419
  pred: 無資料
- `qa_fm_02` score=0.0 pass=-- 689ms | verdict='FAIL' ms=484
  pred: 無資料
- `qa_fm_03` score=1.0 pass=OK 685ms | hit=['無資料']
  pred: 無資料
- `qa_fm_04` score=1.0 pass=OK 721ms | hit=['無資料']
  pred: 無資料
### base · - · fact_single（0/11，score=0.000，7753 ms）
- `qa_fs_01` score=0.0 pass=-- 926ms | verdict='FAIL' ms=1074 | f1=0.000
  pred: 無資料
- `qa_fs_02` score=0.0 pass=-- 661ms | verdict='FAIL' ms=1635 | f1=0.000
  pred: 無資料
- `qa_fs_03` score=0.0 pass=-- 683ms | verdict='FAIL' ms=2157 | f1=0.000
  pred: 無資料
- `qa_fs_04` score=0.0 pass=-- 665ms | verdict='FAIL' ms=1413 | f1=0.000
  pred: 無資料
- `qa_fs_05` score=0.0 pass=-- 686ms | verdict='FAIL' ms=1416 | f1=0.000
  pred: 無資料
- `qa_fs_06` score=0.0 pass=-- 670ms | verdict='FAIL' ms=1597 | f1=0.000
  pred: 無資料
- `qa_fs_07` score=0.0 pass=-- 676ms | verdict='FAIL' ms=1739 | f1=0.000
  pred: 無資料
- `qa_fs_08` score=0.0 pass=-- 661ms | verdict='FAIL' ms=1217 | f1=0.000
  pred: 無資料
- `qa_fs_09` score=0.0 pass=-- 680ms | verdict='FAIL' ms=1626 | f1=0.000
  pred: 無資料
- `qa_fs_10` score=0.0 pass=-- 726ms | verdict='FAIL' ms=2391 | f1=0.000
  pred: 無資料
- `qa_fs_11` score=0.0 pass=-- 718ms | verdict='FAIL' ms=1743 | f1=0.000
  pred: 無資料
### base · - · news_extract（3/3，score=1.000，8201 ms）
- `tc_news_01` score=1.0 pass=OK 3053ms | row 0: MSFT/positive
  pred: {"tool": "read_news_file", "args": {"path": "data/news/sample_news.csv"}}
- `tc_news_02` score=1.0 pass=OK 2577ms | row 1: 005930/negative
  pred: {"tool": "read_news_file", "args": {"path": "data/news/sample_news.csv"}}
- `tc_news_03` score=1.0 pass=OK 2571ms | row 2: TSM/neutral
  pred: {"tool": "read_news_file", "args": {"path": "data/news/sample_news.csv"}}
### base · - · sent_3way（6/6，score=1.000，3499 ms）
- `sent_3w_01` score=1.0 pass=OK 782ms 
  pred: positive
- `sent_3w_02` score=1.0 pass=OK 532ms 
  pred: negative
- `sent_3w_03` score=1.0 pass=OK 539ms 
  pred: neutral
- `sent_3w_04` score=1.0 pass=OK 535ms 
  pred: positive
- `sent_3w_05` score=1.0 pass=OK 530ms 
  pred: negative
- `sent_3w_06` score=1.0 pass=OK 580ms 
  pred: positive
### base · - · sent_score（5/5，score=1.000，20784 ms）
- `sent_sc_01` score=1.0 pass=OK 4832ms 
  pred: {"label": "positive", "score": 0.9, "driver": "Microsoft Cloud 收入突破500億美元，年增長26%，顯示業務強勁擴張"}
- `sent_sc_02` score=1.0 pass=OK 3030ms 
  pred: {"label": "negative", "score": -0.8, "driver": "Azure growth misses expectations导致股票下跌"}
- `sent_sc_03` score=1.0 pass=OK 4212ms 
  pred: {"label": "neutral", "score": 0.0, "driver": "公司維持本季度指引，無顯著升跌，反映市場預期"}
- `sent_sc_04` score=1.0 pass=OK 3744ms 
  pred: {"label": "negative", "score": -0.8, "driver": "Bank cuts cloud estimates, indicating pessimism about future investments and market conditions"}
- `sent_sc_05` score=1.0 pass=OK 4967ms 
  pred: {"label": "positive", "score": 0.9, "driver": "Wells Fargo upgrades Microsoft and raises price target to $600, indicating strong confidence in the company's fut
### better · advanced · fact_multi（4/4，score=1.000，340038 ms）
- `qa_fm_01` score=1.0 pass=OK 101798ms | cached; verdict='PASS' ms=9699
  pred: Azure 供應受限時，Microsoft 仍推動 E7 加價式 upsell，是因為 E7 SKU 並非僅依賴 Azure 供應，而是基於 Microsoft 365 整體生態系統的整合與企業客戶的價值需求。根據資料，E7 SKU 結合了 M365 E5、Entra Suite、Agent 365 及 Copilot
- `qa_fm_02` score=1.0 pass=OK 89778ms | cached; verdict='PASS' ms=5109
  pred: security 对 agentic adoption 同 E7 bundle 咁關鍵，因為 security 提供了 agent 的治理、身份驗證、風險信號及可觀察性等核心功能，使組織能有效管理及監控 agent 的行為，確保其在安全邊界內運作。根據資料，Microsoft 已在 security 領域引入 secu
- `qa_fm_03` score=1.0 pass=OK 83644ms | hit=['無資料']
  pred: KB 無資料
- `qa_fm_04` score=1.0 pass=OK 64818ms | hit=['無資料']
  pred: KB 無資料
### better · hybrid · fact_multi（4/4，score=1.000，247790 ms）
- `qa_fm_01` score=1.0 pass=OK 56639ms | verdict='PASS' ms=9699
  pred: Azure 供應受限時，Microsoft 仍推動 E7 加價式 upsell，是因為 E7 SKU 並非僅依賴 Azure 供應，而是基於 Microsoft 365 整體生態系統的整合與企業客戶的價值需求。根據資料，E7 SKU 結合了 M365 E5、Entra Suite、Agent 365 及 Copilot
- `qa_fm_02` score=1.0 pass=OK 66836ms | verdict='PASS' ms=5109
  pred: security 对 agentic adoption 同 E7 bundle 咁關鍵，因為 security 提供了 agent 的治理、身份驗證、風險信號及可觀察性等核心功能，使組織能有效管理及監控 agent 的行為，確保其在安全邊界內運作。根據資料，Microsoft 已在 security 領域引入 secu
- `qa_fm_03` score=1.0 pass=OK 79010ms | hit=['無資料']
  pred: KB 無資料
- `qa_fm_04` score=1.0 pass=OK 45305ms | hit=['無資料']
  pred: KB 無資料
### better · advanced · fact_single（4/11，score=0.364，1144026 ms）
- `qa_fs_01` score=1.0 pass=OK 100904ms | verdict='PASS' ms=2566 | f1=0.133
  pred: Deutsche Bank 嘅資料顯示，Microsoft F2Q（2026年第二季度）Azure 增長為 +38% y/y（年同比較），略高過指引（guidance）的 37%。  

【KB:20260205_Deutsche_Bank_MSFT_Microsoft-_F2Q_L】  

## 來源  
https
- `qa_fs_02` score=0.0 pass=-- 109050ms | verdict='FAIL' ms=6016 | f1=0.000
  pred: Deutsche Bank 對 MSFT F2Q 結果的評價顯示，**收入與盈利均略高於市場預期**。  

根據文件 [1] <20260205_Deutsche_Bank_MSFT_Microsoft-_F2Q_L>，MSFT F2Q 的總收入為 **$81,588 million**（新預測），較舊預測的 $81
- `qa_fs_03` score=0.0 pass=-- 118284ms | verdict='FAIL' ms=4341 | f1=0.029
  pred: Mizuho 話 MSFT F2Q 總收入為 $81,189M（根據 Deutsche Bank 的最新預期，非 Mizuho 提供的數據）。  

然而，根據提供的資料，Mizuho 的報告中並無直接提供 F2Q 總收入的數值，僅有 Mizuho 的模型數據顯示 MSFT 在 Mar-25 至 Jun-25 的總收入
- `qa_fs_04` score=0.0 pass=-- 58308ms | cached; verdict='FAIL' ms=1551 | f1=0.000
  pred: KB 無資料【KB:檔案名】
- `qa_fs_05` score=0.0 pass=-- 88806ms | cached; verdict='FAIL' ms=1709 | f1=0.000
  pred: KB 無資料【KB:檔案名】
- `qa_fs_06` score=0.0 pass=-- 99919ms | cached; verdict='FAIL' ms=1994 | f1=0.000
  pred: KB 無資料
- `qa_fs_07` score=0.0 pass=-- 114650ms | verdict='FAIL' ms=2648 | f1=0.400
  pred: Wells Fargo 講 E7 新 SKU 每月每位用戶為 $99。  
此 SKU 包含 M365 E5、Entra Suite、Agent 365 及 M365 Copilot。【KB:8】
- `qa_fs_08` score=1.0 pass=OK 83908ms | cached; verdict='PASS' ms=3299 | f1=0.143
  pred: Wells Fargo 認為 agentic adoption 取決於安全。【KB:20260316_Wells_Fargo_MSFT_MSFT-_Agentic_Adop】  

## 來源  
https://example.com/kb/20260316_Wells_Fargo_MSFT_MSFT-_Agenti
- `qa_fs_09` score=1.0 pass=OK 107911ms | cached; verdict='PASS' ms=3246 | f1=0.238
  pred: F2Q26 call 話 Microsoft Cloud 季度收入首次突破 $50 billion，同比升 26%。【KB: <Microsoft_Corp_Earnings_Call_2026128_RT00000>】  

## 來源  
https://example.com/kb/Microsoft_Corp_
- `qa_fs_10` score=0.0 pass=-- 131772ms | cached; verdict='FAIL' ms=1875 | f1=0.000
  pred: KB 無資料【KB:檔案名】
- `qa_fs_11` score=1.0 pass=OK 130514ms | verdict='PASS' ms=2203 | f1=0.000
  pred: DeMatteo Research 嘅 MSFT 市值大約 $2,977B（根據 02/25/2026 呈現嘅資料）【KB:9】
### better · hybrid · fact_single（4/11，score=0.364，830496 ms）
- `qa_fs_01` score=1.0 pass=OK 81382ms | cached; verdict='PASS' ms=2711 | f1=0.178
  pred: Deutsche Bank 嘅資料顯示，Microsoft F2Q（第二季度）Azure 增長為 +38% y/y（年率），超出指引（guidance）的 37%，高出 1 個百分點。【KB:20260205_Deutsche_Bank_MSFT_Microsoft-_F2Q_L】

## 來源
https://exa
- `qa_fs_02` score=0.0 pass=-- 102325ms | cached; verdict='FAIL' ms=6612 | f1=0.000
  pred: Deutsche Bank 對 MSFT F2Q 結果的評價顯示，**收入與盈利均略高於市場預期**。  

根據資料 [1]（20260205_Deutsche_Bank_MSFT_Microsoft-_F2Q_L）的「Estimates Summary」，MSFT 在 F2Q 的總收入為 **81,588 百萬美元
- `qa_fs_03` score=0.0 pass=-- 78996ms | cached; verdict='FAIL' ms=4652 | f1=0.098
  pred: Mizuho 話 MSFT F2Q 總收入為 $81,215 million（根據資料 [3]，2026年第二季預期總收入）。  

同 Street 預期比：Mizuho 的預期總收入為 $81,215 million，與街口預期（Street View）的 $81,189 million（見資料 [12]）非常接近
- `qa_fs_04` score=0.0 pass=-- 48827ms | cached; verdict='FAIL' ms=1551 | f1=0.000
  pred: KB 無資料【KB:檔案名】
- `qa_fs_05` score=0.0 pass=-- 48051ms | cached; verdict='FAIL' ms=1709 | f1=0.000
  pred: KB 無資料【KB:檔案名】
- `qa_fs_06` score=0.0 pass=-- 73306ms | cached; verdict='FAIL' ms=1994 | f1=0.000
  pred: KB 無資料
- `qa_fs_07` score=0.0 pass=-- 75524ms | cached; verdict='FAIL' ms=2645 | f1=0.414
  pred: Wells Fargo 講 E7 新 SKU 每月每位用戶為 $99。  
包含：M365 E5、Entra Suite、Agent 365 以及 M365 Copilot。【KB:8】
- `qa_fs_08` score=1.0 pass=OK 59145ms | cached; verdict='PASS' ms=3299 | f1=0.143
  pred: Wells Fargo 認為 agentic adoption 取決於安全。【KB:20260316_Wells_Fargo_MSFT_MSFT-_Agentic_Adop】  

## 來源  
https://example.com/kb/20260316_Wells_Fargo_MSFT_MSFT-_Agenti
- `qa_fs_09` score=1.0 pass=OK 83482ms | cached; verdict='PASS' ms=3246 | f1=0.238
  pred: F2Q26 call 話 Microsoft Cloud 季度收入首次突破 $50 billion，同比升 26%。【KB: <Microsoft_Corp_Earnings_Call_2026128_RT00000>】  

## 來源  
https://example.com/kb/Microsoft_Corp_
- `qa_fs_10` score=0.0 pass=-- 86479ms | cached; verdict='FAIL' ms=1875 | f1=0.000
  pred: KB 無資料【KB:檔案名】
- `qa_fs_11` score=1.0 pass=OK 92980ms | cached; verdict='PASS' ms=2927 | f1=0.000
  pred: DeMatteo Research 嘅 MSFT 市值大約 $2,977B（根據 02/25/2026 呈現嘅資料）。【KB:9】  

## 來源  
https://www.barchart.com/research/ideanote/20260227/MSFT/DeMatteo/MSFT-Long-Idea-20
### lora · - · calc_expr（5/5，score=1.000，19008 ms）
- `tc_calc_01` score=1.0 pass=OK 6165ms | computed 37.0 vs want 37.0
  pred: {"tool": "calc", "args": {"expr": "38 - 1"}}
- `tc_calc_02` score=1.0 pass=OK 3039ms | computed 1.0 vs want 1.0
  pred: {"tool": "calc", "args": {"expr": "81.3 - 80.3"}}
- `tc_calc_03` score=1.0 pass=OK 3117ms | computed 17.064000000000004 vs want 17.064
  pred: {"tool": "calc", "args": {"expr": "15.80 * 1.08"}}
- `tc_calc_04` score=1.0 pass=OK 3800ms | computed 65.0 vs want 65.0
  pred: {"tool": "calc", "args": {"expr": "((99 - 60) / 60) * 100"}}
- `tc_calc_05` score=1.0 pass=OK 2886ms | computed 39.682539682539684 vs want 39.6825396825
  pred: {"tool": "calc", "args": {"expr": "50 / 1.26"}}
### lora · - · fact_multi（1/4，score=0.250，7071 ms）
- `qa_fm_01` score=0.0 pass=-- 1142ms | verdict='FAIL' ms=583
  pred: no upsell happened.
- `qa_fm_02` score=1.0 pass=OK 2084ms | verdict='PASS' ms=510
  pred: security 對 agentic adoption 同 E7 bundle 咁關鍵。
- `qa_fm_03` score=0.0 pass=-- 2150ms | pred='Microsoft 嘅股息殖利率同歷年派息紀錄係點？'
  pred: Microsoft 嘅股息殖利率同歷年派息紀錄係點？
- `qa_fm_04` score=0.0 pass=-- 1696ms | pred='Microsoft 喺 Japan search market share 1 point.'
  pred: Microsoft 喺 Japan search market share 1 point.
### lora · - · fact_single（1/11，score=0.091，108099 ms）
- `qa_fs_01` score=0.0 pass=-- 2349ms | verdict='FAIL' ms=1981 | f1=0.143
  pred: Deutsche speaks Microsoft F2Q's Azure growth, and how it compares to guidance.
- `qa_fs_02` score=0.0 pass=-- 2922ms | verdict='FAIL' ms=1637 | f1=0.000
  pred: Deutsche 黩點樣形容 F2Q 結果 vs 市場預期？主要原因？
- `qa_fs_03` score=0.0 pass=-- 3554ms | verdict='FAIL' ms=2126 | f1=0.187
  pred: Mizuho 話 MSFT F2Q 總收入 48.1 billion; Street expects 48.2 billion.
- `qa_fs_04` score=0.0 pass=-- 1982ms | verdict='FAIL' ms=1718 | f1=0.000
  pred: Mizuho 對 MSFT 嘅評級係 Neutral.
- `qa_fs_05` score=0.0 pass=-- 79714ms | verdict='FAIL' ms=8978 | f1=0.024
  pred: China Renaissance 2026E EPS 預測 $1.86 vs market consensus of $1.92; 3.1% vs 2.6% Y/Y growth; 3.1% vs 2.6% Y/Y growth; 3.1% vs 2.6% Y/Y growth; 3.1% vs 2.6% Y/Y g
- `qa_fs_06` score=0.0 pass=-- 2402ms | verdict='FAIL' ms=1713 | f1=0.074
  pred: Barclays 講 Microsoft new E7 SKU is $1,100.
- `qa_fs_07` score=0.0 pass=-- 3369ms | verdict='FAIL' ms=2086 | f1=0.095
  pred: Wells Fargo 講 E7 新 SKU 每月每位用戶 $100,000.00。
- `qa_fs_08` score=1.0 pass=OK 2083ms | verdict='PASS' ms=2197 | f1=0.462
  pred: Wells Fargo 認為 agentic adoption depends on the following:
- `qa_fs_09` score=0.0 pass=-- 2684ms | verdict='FAIL' ms=1277 | f1=0.250
  pred: F2Q26 call 話 Microsoft Cloud 季度收入首次突破 $30 billion.
- `qa_fs_10` score=0.0 pass=-- 3288ms | verdict='FAIL' ms=2393 | f1=0.588
  pred: F2Q26 call into Microsoft 365 Copilot 2H26: 400k paid seats.
- `qa_fs_11` score=0.0 pass=-- 3752ms | verdict='FAIL' ms=1876 | f1=0.000
  pred: DeMatteo idea note presented 02/25/2026) that MSFT will be at $430.
### lora · - · news_extract（3/3，score=1.000，8522 ms）
- `tc_news_01` score=1.0 pass=OK 3077ms | row 0: MSFT/positive
  pred: {"tool": "read_news_file", "args": {"path": "data/news/sample_news.csv"}}
- `tc_news_02` score=1.0 pass=OK 2580ms | row 1: 005930/negative
  pred: {"tool": "read_news_file", "args": {"path": "data/news/sample_news.csv"}}
- `tc_news_03` score=1.0 pass=OK 2864ms | row 2: TSM/neutral
  pred: {"tool": "read_news_file", "args": {"path": "data/news/sample_news.csv"}}
### lora · - · sent_3way（5/6，score=0.833，3784 ms）
- `sent_3w_01` score=1.0 pass=OK 868ms 
  pred: positive
- `sent_3w_02` score=1.0 pass=OK 578ms 
  pred: negative
- `sent_3w_03` score=1.0 pass=OK 569ms 
  pred: neutral
- `sent_3w_04` score=1.0 pass=OK 614ms 
  pred: positive
- `sent_3w_05` score=0.0 pass=-- 563ms | pred='neutral'
  pred: neutral
- `sent_3w_06` score=1.0 pass=OK 592ms 
  pred: positive
### lora · - · sent_score（3/5，score=0.600，18268 ms）
- `sent_sc_01` score=1.0 pass=OK 4354ms 
  pred: {"label": "positive", "score": 0.45, "driver": "公司 Cloud revenue tops $50 billion, up 26% year over year"}
- `sent_sc_02` score=0.0 pass=-- 3627ms | label=neutral score=0.0 driver='公司 shares fall 4% af'
  pred: {"label": "neutral", "score": 0.0, "driver": "公司 shares fall 4% after Azure growth misses expectations"}
- `sent_sc_03` score=1.0 pass=OK 3089ms 
  pred: {"label": "neutral", "score": 0.0, "driver": "公司 holds its guidance steady this quarter"}
- `sent_sc_04` score=0.0 pass=-- 3419ms | label=neutral score=0.0 driver='公司 warns of AI capex'
  pred: {"label": "neutral", "score": 0.0, "driver": "公司 warns of AI capex bubble, cuts cloud estimates"}
- `sent_sc_05` score=1.0 pass=OK 3779ms 
  pred: {"label": "positive", "score": 0.4, "driver": "公司 upgrades Microsoft, raises price target to $600"}
### qlora · - · calc_expr（5/5，score=1.000，6550 ms）
- `tc_calc_01` score=1.0 pass=OK 1772ms | computed 37.0 vs want 37.0
  pred: {"tool": "calc", "args": {"expr": "38 - 1"}}
- `tc_calc_02` score=1.0 pass=OK 1152ms | computed 1.0 vs want 1.0
  pred: {"tool": "calc", "args": {"expr": "81.3 - 80.3"}}
- `tc_calc_03` score=1.0 pass=OK 1201ms | computed 17.064000000000004 vs want 17.064
  pred: {"tool": "calc", "args": {"expr": "15.80 * 1.08"}}
- `tc_calc_04` score=1.0 pass=OK 1387ms | computed 65.0 vs want 65.0
  pred: {"tool": "calc", "args": {"expr": "((99 - 60) / 60) * 100"}}
- `tc_calc_05` score=1.0 pass=OK 1038ms | computed 39.682539682539684 vs want 39.6825396825
  pred: {"tool": "calc", "args": {"expr": "50 / 1.26"}}
### qlora · - · fact_multi（2/4，score=0.500，1573 ms）
- `qa_fm_01` score=0.0 pass=-- 537ms | cached; verdict='FAIL' ms=2419
  pred: 無資料
- `qa_fm_02` score=0.0 pass=-- 352ms | cached; verdict='FAIL' ms=484
  pred: 無資料
- `qa_fm_03` score=1.0 pass=OK 345ms | hit=['無資料']
  pred: 無資料
- `qa_fm_04` score=1.0 pass=OK 339ms | hit=['無資料']
  pred: 無資料
### qlora · - · fact_single（0/11，score=0.000，3807 ms）
- `qa_fs_01` score=0.0 pass=-- 334ms | cached; verdict='FAIL' ms=1074 | f1=0.000
  pred: 無資料
- `qa_fs_02` score=0.0 pass=-- 333ms | cached; verdict='FAIL' ms=1635 | f1=0.000
  pred: 無資料
- `qa_fs_03` score=0.0 pass=-- 352ms | cached; verdict='FAIL' ms=2157 | f1=0.000
  pred: 無資料
- `qa_fs_04` score=0.0 pass=-- 333ms | cached; verdict='FAIL' ms=1413 | f1=0.000
  pred: 無資料
- `qa_fs_05` score=0.0 pass=-- 337ms | cached; verdict='FAIL' ms=1416 | f1=0.000
  pred: 無資料
- `qa_fs_06` score=0.0 pass=-- 332ms | cached; verdict='FAIL' ms=1597 | f1=0.000
  pred: 無資料
- `qa_fs_07` score=0.0 pass=-- 340ms | cached; verdict='FAIL' ms=1739 | f1=0.000
  pred: 無資料
- `qa_fs_08` score=0.0 pass=-- 334ms | cached; verdict='FAIL' ms=1217 | f1=0.000
  pred: 無資料
- `qa_fs_09` score=0.0 pass=-- 339ms | cached; verdict='FAIL' ms=1626 | f1=0.000
  pred: 無資料
- `qa_fs_10` score=0.0 pass=-- 338ms | cached; verdict='FAIL' ms=2391 | f1=0.000
  pred: 無資料
- `qa_fs_11` score=0.0 pass=-- 433ms | cached; verdict='FAIL' ms=1743 | f1=0.000
  pred: 無資料
### qlora · - · news_extract（3/3，score=1.000，3279 ms）
- `tc_news_01` score=1.0 pass=OK 1320ms | row 0: MSFT/positive
  pred: {"tool": "read_news_file", "args": {"path": "data/news/sample_news.csv"}}
- `tc_news_02` score=1.0 pass=OK 975ms | row 1: 005930/negative
  pred: {"tool": "read_news_file", "args": {"path": "data/news/sample_news.csv"}}
- `tc_news_03` score=1.0 pass=OK 984ms | row 2: TSM/neutral
  pred: {"tool": "read_news_file", "args": {"path": "data/news/sample_news.csv"}}
### qlora · - · sent_3way（6/6，score=1.000，2057 ms）
- `sent_3w_01` score=1.0 pass=OK 508ms 
  pred: positive
- `sent_3w_02` score=1.0 pass=OK 317ms 
  pred: negative
- `sent_3w_03` score=1.0 pass=OK 304ms 
  pred: neutral
- `sent_3w_04` score=1.0 pass=OK 309ms 
  pred: positive
- `sent_3w_05` score=1.0 pass=OK 302ms 
  pred: negative
- `sent_3w_06` score=1.0 pass=OK 317ms 
  pred: positive
### qlora · - · sent_score（5/5，score=1.000，7160 ms）
- `sent_sc_01` score=1.0 pass=OK 1735ms 
  pred: {"label": "positive", "score": 0.95, "driver": "Microsoft Cloud revenue growth of 26% year over year indicates strong market performance and expanding digital t
- `sent_sc_02` score=1.0 pass=OK 1023ms 
  pred: {"label": "negative", "score": -0.8, "driver": "Azure growth misses expectations"}
- `sent_sc_03` score=1.0 pass=OK 1401ms 
  pred: {"label": "neutral", "score": 0.0, "driver": "公司保持本季度指引穩健，無顯著樂觀或樂觀情緒"}
- `sent_sc_04` score=1.0 pass=OK 1235ms 
  pred: {"label": "negative", "score": -0.8, "driver": "Bank cuts cloud estimates indicating reduced confidence in AI investment"}
- `sent_sc_05` score=1.0 pass=OK 1767ms 
  pred: {"label": "positive", "score": 0.95, "driver": "Wells Fargo upgrades Microsoft and raises price target to $600, indicating strong confidence in the company's fu
### rag · adaptive · fact_multi（4/4，score=1.000，115741 ms）
- `qa_fm_01` score=1.0 pass=OK 33964ms | cached; verdict='PASS' ms=1567
  pred: Azure 供應受限時，Microsoft 仍推動 E7 加價式 upsell，因 E7 SKU 並非依賴 Azure 供應，而是基於 M365 套件內的整合服務（如 Copilot、Agent 365、Entra Suite）及現有企業用戶的高價值需求，透過 bundling 高階功能提升用戶黏性與收入。E7 作為一
- `qa_fm_02` score=1.0 pass=OK 41079ms | cached; verdict='PASS' ms=2158
  pred: security 對 agentic adoption 同 E7 bundle 咁關鍵，因為 security 提供了 agent 運作所需嘅治理、身份驗證、風險信號同觀察能力，使組織可以安全地部署同管理 AI agent。根據資料，Microsoft 推出 Agent 365 作為一個 control plane，讓
- `qa_fm_03` score=1.0 pass=OK 24987ms | hit=['無資料']
  pred: KB 無資料【KB:檔案名】  
## 來源  
https://www.example.com/kb-finance-microsoft-dividend-records
- `qa_fm_04` score=1.0 pass=OK 15711ms | hit=['無資料']
  pred: KB 無資料【KB:檔案名】
### rag · hybrid · fact_multi（4/4，score=1.000，265520 ms）
- `qa_fm_01` score=1.0 pass=OK 91033ms | verdict='PASS' ms=2020
  pred: Azure 供應受限時，Microsoft 仍推動 E7 加價式 upsell，是因為 E7 SKU 並非僅依賴 Azure 供應，而是基於 Microsoft 365 整體生態系統的整合與企業客戶的價值需求。根據資料，E7 SKU 結合了 M365 E5、Entra Suite、Agent 365 及 Copilot
- `qa_fm_02` score=1.0 pass=OK 70639ms | verdict='PASS' ms=1697
  pred: security 对 agentic adoption 同 E7 bundle 咁關鍵，因為 security 提供了 agent 的治理、身份驗證、風險信號及可觀察性等核心功能，使組織能有效管理及監控 agent 的行為，確保其在安全邊界內運作。根據資料，Microsoft 已在 security 領域引入 secu
- `qa_fm_03` score=1.0 pass=OK 57150ms | hit=['無資料']
  pred: KB 無資料
- `qa_fm_04` score=1.0 pass=OK 46698ms | hit=['無資料']
  pred: KB 無資料
### rag · naive · fact_multi（4/4，score=1.000，80685 ms）
- `qa_fm_01` score=1.0 pass=OK 20472ms | verdict='PASS' ms=1567
  pred: Azure 供應受限時，Microsoft 仍推動 E7 加價式 upsell，因 E7 SKU 並非依賴 Azure 供應，而是基於 M365 套件內的整合服務（如 Copilot、Agent 365、Entra Suite）及現有企業用戶的高價值需求，透過 bundling 高階功能提升用戶黏性與收入。E7 作為一
- `qa_fm_02` score=1.0 pass=OK 27160ms | verdict='PASS' ms=2158
  pred: security 對 agentic adoption 同 E7 bundle 咁關鍵，因為 security 提供了 agent 運作所需嘅治理、身份驗證、風險信號同觀察能力，使組織可以安全地部署同管理 AI agent。根據資料，Microsoft 推出 Agent 365 作為一個 control plane，讓
- `qa_fm_03` score=1.0 pass=OK 19196ms | hit=['無資料']
  pred: KB 無資料【KB:檔案名】  
## 來源  
https://www.example.com/kb-finance-microsoft-dividend-records
- `qa_fm_04` score=1.0 pass=OK 13857ms | hit=['無資料']
  pred: KB 無資料【KB:檔案名】
### rag · adaptive · fact_single（2/11，score=0.182，203039 ms）
- `qa_fs_01` score=0.0 pass=-- 29717ms | cached; verdict='FAIL' ms=2851 | f1=0.130
  pred: Deutsche Bank 話 Microsoft F2Q 嘅 Azure 增長為 +28.0%，同 guidance 比點為 +28.1%。【KB:20260205_Deutsche_Bank_MSFT_Microsoft-_F2Q_L】  

## 來源  
https://example.com/final/kb
- `qa_fs_02` score=0.0 pass=-- 40955ms | cached; verdict='FAIL' ms=4304 | f1=0.000
  pred: Deutsche Bank 對 MSFT F2Q 結果的評價顯示，總收入為 $81,189mn，較市場預期的 $81,588mn 略低，差異為 -0.5%（新預期 vs. 市場預期），顯示結果略低於市場預期。然而，各業務線表現強勁，尤其是 Intelligent Cloud 以 +28.0% 的年增長率領先，遠高於市場
- `qa_fs_03` score=0.0 pass=-- 28482ms | cached; verdict='FAIL' ms=4286 | f1=0.044
  pred: Mizuho 話 MSFT F2Q（2025年第二季）總收入為 **76,441萬美元**。  

根據資料，此數值來自 Mizuho Securities 的 MSFT 公司報告，顯示在 FYE（截至日期）為 2025 年 6 月的數據中，F2Q（即 2025 年第二季）的總收入為 76,441 萬美元。  

資料
- `qa_fs_04` score=0.0 pass=-- 19177ms | cached; verdict='FAIL' ms=3023 | f1=0.000
  pred: KB 無資料【KB:檔案名】  

## 來源  
https://example.com/kb/20260205_Mizuho_Securities_MSFT_MSFT-_Good_O
- `qa_fs_05` score=0.0 pass=-- 19810ms | cached; verdict='FAIL' ms=3045 | f1=0.000
  pred: KB 無資料【KB:檔案名】  

## 來源  
https://example.com/microsoft-earnings-call-2026128-rt00000
- `qa_fs_06` score=0.0 pass=-- 1359ms | cached; verdict='FAIL' ms=1994 | f1=0.000
  pred: KB 無資料
- `qa_fs_07` score=0.0 pass=-- 1058ms | verdict='FAIL' ms=2101 | f1=0.000
  pred: KB 無資料
- `qa_fs_08` score=1.0 pass=OK 17768ms | cached; verdict='PASS' ms=3658 | f1=0.235
  pred: Wells Fargo 認為 agentic adoption 取決於安全。【KB:20260316_Wells_Fargo_MSFT_MSFT-_Agentic_Adop】
- `qa_fs_09` score=1.0 pass=OK 22489ms | cached; verdict='PASS' ms=3495 | f1=0.244
  pred: Microsoft Cloud 季度收入首次突破 $50 billion，同比升 26%。【KB: <Microsoft_Corp_Earnings_Call_2026128_RT00000>】

## 來源  
https://www.microsoft.com/investor-relations/earnings
- `qa_fs_10` score=0.0 pass=-- 19665ms | cached; verdict='FAIL' ms=1875 | f1=0.000
  pred: KB 無資料【KB:檔案名】
- `qa_fs_11` score=0.0 pass=-- 2560ms | verdict='FAIL' ms=2182 | f1=0.000
  pred: KB 無資料
### rag · hybrid · fact_single（4/11，score=0.364，727609 ms）
- `qa_fs_01` score=1.0 pass=OK 73054ms | verdict='PASS' ms=2711 | f1=0.178
  pred: Deutsche Bank 嘅資料顯示，Microsoft F2Q（第二季度）Azure 增長為 +38% y/y（年率），超出指引（guidance）的 37%，高出 1 個百分點。【KB:20260205_Deutsche_Bank_MSFT_Microsoft-_F2Q_L】

## 來源
https://exa
- `qa_fs_02` score=0.0 pass=-- 89318ms | verdict='FAIL' ms=6612 | f1=0.000
  pred: Deutsche Bank 對 MSFT F2Q 結果的評價顯示，**收入與盈利均略高於市場預期**。  

根據資料 [1]（20260205_Deutsche_Bank_MSFT_Microsoft-_F2Q_L）的「Estimates Summary」，MSFT 在 F2Q 的總收入為 **81,588 百萬美元
- `qa_fs_03` score=0.0 pass=-- 72073ms | verdict='FAIL' ms=4652 | f1=0.098
  pred: Mizuho 話 MSFT F2Q 總收入為 $81,215 million（根據資料 [3]，2026年第二季預期總收入）。  

同 Street 預期比：Mizuho 的預期總收入為 $81,215 million，與街口預期（Street View）的 $81,189 million（見資料 [12]）非常接近
- `qa_fs_04` score=0.0 pass=-- 44068ms | verdict='FAIL' ms=1551 | f1=0.000
  pred: KB 無資料【KB:檔案名】
- `qa_fs_05` score=0.0 pass=-- 41517ms | verdict='FAIL' ms=1709 | f1=0.000
  pred: KB 無資料【KB:檔案名】
- `qa_fs_06` score=0.0 pass=-- 64417ms | verdict='FAIL' ms=1994 | f1=0.000
  pred: KB 無資料
- `qa_fs_07` score=0.0 pass=-- 66764ms | verdict='FAIL' ms=2645 | f1=0.414
  pred: Wells Fargo 講 E7 新 SKU 每月每位用戶為 $99。  
包含：M365 E5、Entra Suite、Agent 365 以及 M365 Copilot。【KB:8】
- `qa_fs_08` score=1.0 pass=OK 52666ms | verdict='PASS' ms=3299 | f1=0.143
  pred: Wells Fargo 認為 agentic adoption 取決於安全。【KB:20260316_Wells_Fargo_MSFT_MSFT-_Agentic_Adop】  

## 來源  
https://example.com/kb/20260316_Wells_Fargo_MSFT_MSFT-_Agenti
- `qa_fs_09` score=1.0 pass=OK 68892ms | verdict='PASS' ms=3246 | f1=0.238
  pred: F2Q26 call 話 Microsoft Cloud 季度收入首次突破 $50 billion，同比升 26%。【KB: <Microsoft_Corp_Earnings_Call_2026128_RT00000>】  

## 來源  
https://example.com/kb/Microsoft_Corp_
- `qa_fs_10` score=0.0 pass=-- 74789ms | cached; verdict='FAIL' ms=1875 | f1=0.000
  pred: KB 無資料【KB:檔案名】
- `qa_fs_11` score=1.0 pass=OK 80050ms | verdict='PASS' ms=2927 | f1=0.000
  pred: DeMatteo Research 嘅 MSFT 市值大約 $2,977B（根據 02/25/2026 呈現嘅資料）。【KB:9】  

## 來源  
https://www.barchart.com/research/ideanote/20260227/MSFT/DeMatteo/MSFT-Long-Idea-20
### rag · naive · fact_single（2/11，score=0.182，272648 ms）
- `qa_fs_01` score=0.0 pass=-- 34244ms | verdict='FAIL' ms=2851 | f1=0.130
  pred: Deutsche Bank 話 Microsoft F2Q 嘅 Azure 增長為 +28.0%，同 guidance 比點為 +28.1%。【KB:20260205_Deutsche_Bank_MSFT_Microsoft-_F2Q_L】  

## 來源  
https://example.com/final/kb
- `qa_fs_02` score=0.0 pass=-- 39524ms | verdict='FAIL' ms=4304 | f1=0.000
  pred: Deutsche Bank 對 MSFT F2Q 結果的評價顯示，總收入為 $81,189mn，較市場預期的 $81,588mn 略低，差異為 -0.5%（新預期 vs. 市場預期），顯示結果略低於市場預期。然而，各業務線表現強勁，尤其是 Intelligent Cloud 以 +28.0% 的年增長率領先，遠高於市場
- `qa_fs_03` score=0.0 pass=-- 24270ms | verdict='FAIL' ms=4286 | f1=0.044
  pred: Mizuho 話 MSFT F2Q（2025年第二季）總收入為 **76,441萬美元**。  

根據資料，此數值來自 Mizuho Securities 的 MSFT 公司報告，顯示在 FYE（截至日期）為 2025 年 6 月的數據中，F2Q（即 2025 年第二季）的總收入為 76,441 萬美元。  

資料
- `qa_fs_04` score=0.0 pass=-- 14347ms | verdict='FAIL' ms=3023 | f1=0.000
  pred: KB 無資料【KB:檔案名】  

## 來源  
https://example.com/kb/20260205_Mizuho_Securities_MSFT_MSFT-_Good_O
- `qa_fs_05` score=0.0 pass=-- 15760ms | verdict='FAIL' ms=3045 | f1=0.000
  pred: KB 無資料【KB:檔案名】  

## 來源  
https://example.com/microsoft-earnings-call-2026128-rt00000
- `qa_fs_06` score=0.0 pass=-- 17362ms | verdict='FAIL' ms=2473 | f1=0.000
  pred: KB 無資料【KB:檔案名】
- `qa_fs_07` score=0.0 pass=-- 52937ms | verdict='FAIL' ms=8538 | f1=0.000
  pred: KB 無資料【KB:檔案名】  

## 來源  
https://www.example.com/kb-finance-microsoft-2026-03-13-02-05-01-00-00-00-00-00-00-00-00-00-00-00-00-00-00-00-00-00-00-00-00-00-00-00-
- `qa_fs_08` score=1.0 pass=OK 15697ms | verdict='PASS' ms=3658 | f1=0.235
  pred: Wells Fargo 認為 agentic adoption 取決於安全。【KB:20260316_Wells_Fargo_MSFT_MSFT-_Agentic_Adop】
- `qa_fs_09` score=1.0 pass=OK 18012ms | verdict='PASS' ms=3495 | f1=0.244
  pred: Microsoft Cloud 季度收入首次突破 $50 billion，同比升 26%。【KB: <Microsoft_Corp_Earnings_Call_2026128_RT00000>】

## 來源  
https://www.microsoft.com/investor-relations/earnings
- `qa_fs_10` score=0.0 pass=-- 16646ms | verdict='FAIL' ms=1875 | f1=0.000
  pred: KB 無資料【KB:檔案名】
- `qa_fs_11` score=0.0 pass=-- 23849ms | verdict='FAIL' ms=2305 | f1=0.000
  pred: KB 無資料【KB:檔案名】  

## 來源  
https://www.example.com/kb-finance-microsoft-2026-02-25
