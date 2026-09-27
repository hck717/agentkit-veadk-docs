# FIN-MATE E1 · Fine-Tune（LoRA / QLoRA）vs RAG vs Base 深度對比報告（廣東話）

> 配套檔案：`experiments/lora_bench/run.json`（原數據）、`experiments/lora_bench/report.md`（自動生成摘要）、
> `finetune/build_dataset.py`（訓練數據生成）、`finetune/log_{lora,qlora}_train.txt`（完整訓練 log）、
> `Makefile`（`ft-data` / `ft-lora` / `ft-qlora` / `ft-fuse` / `lora-bench` targets）。
> 呢份文件係**人手寫嘅深度分析**：方法論（點樣實作 LoRA / QLoRA）＋ 對比結果 ＋ 逐點見解，
> 特別釐清「**點解 Fine-Tune 之後能力會跌**」。

---

## 0. TL;DR（一句總結）

- **RAG（k≥15）係事實類問題（fact recall）結構性贏家**；閉卷 Fine-Tune 頂盡睇數據。
- **LoRA 犧牲原能力換記憶（0.182% 參數改動 → catastrophic forgetting）**；**QLoRA 保得住原能力但記唔到嘢**。
- **fact_single 個「1/11」90% 係 metric artifact**（英語 golden × 粵語答案嘅 token-overlap），唔係 RAG 失敗——
  用語言中立 llm_judge 重評後 hybrid/advanced 真係 **4/11**。
- **樽頸唔喺 retrieval**（加料至 k=15+sparse 都係 4/11），樽頸喺 **4-bit 4B 生成能力**。
- 要做準確 fact recall → **RAG + 好啲生成模型**；要保留原有能力 → **QLoRA**；要 camp 少量 fact → **LoRA（要接受能力跌）**。

---

## 1. 實驗背景同問題

FIN-MATE 已有多跳 RAG 系統（OpenViking KB + Ark `seed-1-6-flash` 答題，D6 baseline 全 34 條 = 25/34）。
E1 想答一條問題：

> **如果改用全本地（Apple Silicon，16GB 機，零雲費用）＋ 一個細模型（Qwen3-4B），
> 我哋應唔應該 Fine-Tune？用 LoRA 定 QLoRA？靠 RAG 好定靠閉卷記憶好？**

四個被測方案（同一 eval 34 條 golden）：

| 方案 | 做法 | 記憶體 | 代答模型 |
|---|---|---|---|
| **base** | 閉卷，原裝 Qwen3-4B（bf16 / 4-bit） | 7.5G / 2.1G | Qwen3-4B-Instruct-2507 |
| **LoRA** | 閉卷，bf16 base + LoRA adapter fused | 7.5G（fused） | fused/lora（bf16） |
| **QLoRA** | 閉卷，4-bit base + 同一 adapter fused | 2.1G（fused） | fused/qlora（4-bit） |
| **RAG** | naive / hybrid / adaptive（＋ diagnostic: hybrid / advanced）用 **本地 4-bit base** 代答 | 2.1G server | 同一 Qwen3-4B-4bit |

---

## 2. 方法論

### 2.1 硬體同「記憶體安全」原則（16GB Mac，最重要約束）

- 每一次**只 serve 一個 model**（MLX server 或 Ollama judge，兩者**永遠唔會同時 resident**）。
- llm_judge 全部拆開做獨立 `--judge` / `--judgefs` pass，喺所有 MLX server kill 晒之後先淨 Ollama 行。
- 全程 swap 高峰 ~6GB，冇 crash。

### 2.2 訓練數據：`finetune/build_dataset.py`（deterministic、防 leakage）

合成 SFT 數據（唔用 eval golden，做足防 leak）：

| 類別 | 份量 | 內容 |
|---|---|---|
| QA（context + closed） | 8 docs × 30 = 多數 | 由 KB `.txt` 抽句子，問「當時情況」；`--mask-prompt` 只學答案 |
| trap | 40 | KB 冇料 → 訓練答案一律「KB 無資料」 |
| calc | 50 | 嚴格 JSON tool call `{"tool":"calc","args":{"expr":...}}` |
| news | 24 | 嚴格 JSON `read_news_file` |
| sentiment | 90 | 合成 headlines → label / JSON（用 `_score_text` 真判 label） |

- 9:1 切 train/valid：**576 train / 64 valid**。
- **Leakage 黑名單**：將 eval/golden 嘅 prompt/context/answer 全部 normalized-token 入 blacklist，凡句子撞中即剔除。
- rng seed 全部固定（7 / 11 / 21 / 33 / 47），**可重現**。

### 2.3 LoRA 實作（`make ft-lora`）

```bash
mlx_lm.lora --model Qwen/Qwen3-4B-Instruct-2507 --train --data finetune/datasets \
  --fine-tune-type lora \
  --num-layers 16          # 改頭 16 層 attention（MLX-LM 數法）
  --batch-size 4 --iters 500 \
  --learning-rate 1e-5     # 極細 LR，希望唔好郁咁多
  --mask-prompt            # 只計算 assistant 部分 loss
  --grad-checkpoint        # 換記憶體，慳 activation
  --max-seq-length 2048 --seed 7 --optimizer adamw \
  --save-every 100 --adapter-path finetune/adapters/lora
```

- **Trainable parameters: 0.182% = 7.34M / 4,022M**——絕大多數權重凍結，只改低秩 adapter。
- 實際結果（log 節錄）：
  - Peak mem **9.678 GB**、trained tokens 47,767。
  - train loss 一路跌落 **0.086**，但 **val loss 喺 iter 300 谷底 0.230 之後反彈到 0.533**。
  - 即係 **過擬合**：個 adapter 背誦訓練數據，冇泛化到未見過嘅 pattern（呢點係「能力會跌」嘅第一個證據，見 §5.2）。

### 2.4 QLoRA 實作（`make ft-qlora`）

```bash
mlx_lm.lora --model mlx-community/Qwen3-4B-Instruct-2507-4bit --train --data finetune/datasets \
  --fine-tune-type lora \
  --num-layers 16 --batch-size 4 --iters 500 \
  --learning-rate 1e-5 --mask-prompt --grad-checkpoint \
  --max-seq-length 2048 --seed 7 --optimizer adamw \
  --adapter-path finetune/adapters/qlora
```

- 只要傳 **4-bit base**，MLX-LM 自動行 QLoRA（量化嘅 BF16 喺正反傳中都保持低精度 → 慳記憶）。
- 實際結果：
  - Peak mem **3.956 GB**（vs LoRA 9.678 GB，慳 **59%**）、trained tokens 55,767。
  - train loss 0.136 / val loss 0.522——同 LoRA 一樣過擬合，但注意**改動幅度細好多**（低精度約束），呢個解釋佢點解保得住原能力（見 §5.3）。

### 2.5 Fuse + Serve

```bash
mlx_lm.fuse --model Qwen/Qwen3-4B-Instruct-2507 --adapter-path finetune/adapters/lora  --save-path finetune/fused/lora
mlx_lm.fuse --model mlx-community/Qwen3-4B-Instruct-2507-4bit --adapter-path finetune/adapters/qlora --save-path finetune/fused/qlora
```

- adapter 每個 **169 MB**；fused：LoRA **7.5 GB**（bf16）、QLoRA **2.1 GB**（4-bit）。
- serve：`mlx_lm.server --model <fused> --port 82xx`，threading 1，`think:false`（防 Qwen3 出 thinking 拖爆 output）。

### 2.6 Execution Harness：`experiments/lora_bench/run.py`

- **統一 Scoring**：`_score` 用 `eval/evaluators.py` 同一套 `EVALUATORS`（`exact/f1/trap/tool_call/sentiment/llm_judge`），所以同 D6 台檯可比較。
- **closed-book row（base/lora/qlora）**：`_chat_record` 純 prompt，**唔注入任何 KB/context**（系統 prompt 只有 task 格式規則）。
- **RAG row**：`strategies.ark_complete` monkeypatch 成 local 版 `_local_wrapper` → 三條 pipe 用**同一個 4-bit base** 代答，器材一致。
- **`--judge` / `--judgefs`**：llm_judge 拆開行（memory-safe），`--judgefs` 針對 fact_single 全 88 個 preds 用語言中立 judge 重評，f1 原分保留喺 `score_f1`。

### 2.7 RAG strategies（同 D6 method）

| pipe | retrieve 節點 | read_limit | k | 備註 |
|---|---|---|---|---|
| naive | dense only | 200 | 5 | production baseline |
| hybrid | dense + sparse grep，RRF(K=60) | 200 | 15 | **D6 定案 production pick** |
| adaptive | LLM router（SEARCH/SKIP）| 200 | 5 | 唔查 = 純 model |
| advanced（diagnostic）| dense + grep + gate 0.35 | 2000 | 15 | 粗改細 + expand + gate |

`better` row = `["hybrid", "advanced"]`，fact_single 11 條 × 2 pipes，**專門驗證「加唔加料會唔會幫到 fact recall」**。

---

## 3. 評估設定

- **34 條 golden**：fact_single 11（f1，後加 judge 重評）、fact_multi 4（llm_judge×2 + trap×2）、calc 5、news 3、sent_3way 6、sent_score 5。
- RAG / better rows 淨係跑 **QA 15 條**（RAG 對非 QA task 冇版本可比）。
- Temperature 一律 0、thinking 關；judge = Ollama `qwen3:4b-instruct-2507-q4_K_M`，`think:false`，strict PASS/FAIL + cache。
- **PASS 門檻**：`answer_f1 ≥ 0.25`；llm_judge 出 `PASS/FAIL`。

---

## 4. 結果：Base vs 各 RAG vs LoRA vs QLoRA

### 4.1 總覽

| 方案 | 範圍 | pass | 備註 |
|---|---|---|---|
| **base（閉卷）** | 全 34 | **21/34** | fact_single 0/11 |
| **QLoRA（閉卷）** | 全 34 | **21/34** | = base 完全保留，但 fact 都 0/11 |
| **LoRA（閉卷）** | 全 34 | **18/34** | fact_single 1/11，但非-QA 明顯跌 |
| RAG naive | QA 15 | 6/15 | fact_single 2/11（judge）|
| **RAG hybrid** | QA 15 | **8/15** | **fact_single 4/11（judge）= 全場最高** |
| RAG adaptive | QA 15 | 6/15 | fact_single 2/11（judge）|
| better hybrid / advanced | QA 15 | 8/15 | fact_single 4/11（= 普通 hybrid）|

> D6 baseline（Ark `seed-1-6-flash-250715` + hybrid RAG）= **25/34**，fact_single 2/11（f1 量度）、fact_multi 4/4。
> 本地 4-bit 4B 已經由 D6 嘅 25 → RAG 8/15（QA 子集）——係唔錯，但**唔到 D6 全場**（重點係 D6 用緊一個大啲強啲嘅模型做「答」）。

### 4.2 per-set 明細

| row | fact_single 11 | fact_multi 4 | calc 5 | news 3 | sent_3way 6 | sent_score 5 | **total** |
|---|---|---|---|---|---|---|---|
| base | 0 | 2 | 5 | 3 | 6 | 5 | **21** |
| LoRA | **1** | **1** | 5 | 3 | **5** | **3** | **18** |
| QLoRA | 0 | 2 | 5 | 3 | 6 | 5 | **21** |
| RAG naive | 2 | 4 | – | – | – | – | 6/15 |
| RAG hybrid | **4** | 4 | – | – | – | – | **8/15** |
| RAG adaptive | 2 | 4 | – | – | – | – | 6/15 |
| better hybrid/advanced | 4 | 4 | – | – | – | – | 8/15 |

### 4.3 Latency / 資源對比

| 方案 | avg ms/record | fused 大小 | 訓練 peak mem |
|---|---|---|---|
| base 閉卷 | ~0.3–4.2s | 7.5G / 2.1G | – |
| LoRA 閉卷 | ~0.6–9.8s | 7.5G | 9.678 GB |
| QLoRA 閉卷 | ~0.3–1.4s | 2.1G | 3.956 GB |
| RAG naive | ~20s | 2.1G（server 4-bit）| – |
| RAG hybrid | ~66s | 同上 | – |
| RAG advanced | ~85–104s | 同上 | – |

---

## 5. 深入見解（重點分析）

### 5.1 事實類問題：RAG 贏，但個比分被 metric 呃咗

**a) fact_multi（多跳）——RAG 結構性贏硬**
RAG 三個 pipe 全部 **4/4**；閉卷最多 2/4（base/QLoRA），LoRA 仲得返 1/4。
原因好直接：要 cross-doc（Barclays + Deutsche / Wells Fargo + …）先答到嘅問題，閉卷模型冇材料，「咁多跳數」唔存在於佢 4B 記憶入面。呢度技術上無得揀，**多跳 synthesis = 一定要 retrieval**。

**b) fact_single（單跳）——「1/11」係假象**
初版用 `answer_f1`（英語 golden × 粵語答案嘅 token-overlap）計：RAG hybrid 得 1/11、naive 0/11，睇落「RAG 輸晒畀 LoRA 閉卷 3/11」。但調查發現係 metric artifact：

```
answer_f1 個 _tok = [a-z0-9]+（英文數字 token）
golden answer = 英文（"market cap ~$2,977B"）
pred answer    = 廣東話 + 英文數字（"市值大約 $2,977B"）
→ token overlap 結構性封頂，正確答案都只得 f1 0–0.24（PASS bar 0.25）
```

實例：
- `qa_fs_09`（Cloud 首破 $50B / +26%）RAG 答啱晒，f1 = **0.244**，差 0.006 唔 pass。
- `qa_fs_11`（市值 $2,977B）答啱，因為格式 `2,977,b` vs `2977`，f1 = **0.000**。
- **D6 Ark 都係 3/11** — 同一 metric 之下，雲上強模型一樣被拖低。

用語言中立 llm_judge 重評（`--judgefs`，88 個 preds）：

| row / pipe | f1-pass | **llm_judge-pass** |
|---|---|---|
| base | 0/11 | 0/11 |
| LoRA | 3/11 | **1/11**（有 2 條係 f1 高分但 judge 判漏數字）|
| QLoRA | 0/11 | 0/11 |
| RAG naive | 0/11 | **2/11** |
| **RAG hybrid** | 1/11 | **4/11** |
| RAG adaptive | 0/11 | **2/11** |
| better hybrid / advanced | 1/11 | **4/11** |

所以**真相係**：RAG hybrid 事實 recall **4/11**，係全場最高；LoRA 閉卷最多 1/11（而且其中 fs_09/fs_10 兩個「f1 高分」係虛高）。

**c) 樽頸唔喺 retrieval**
`better` row 用 k=15 + sparse grep + RRF/gate（advanced 甚至 read_limit 2000 全文）都係 **4/11**，同普通 hybrid 一樣 → **加唔加料都唔會再升**。真正樽頸：
1. **k 太細**：naive/adaptive（k=5）missing 咗 fs_01 嘅 Deutsche doc、fs_11 嘅 DeMatteo doc → 得 2/11；**k=15 或以上即到頂**。
2. **4-bit 4B 生成能力**：有料都答唔準（回絕「KB 無資料」/ 答漏一個數字 / 4 條避到都係靠幸運拎中數字）。
結論：**retrieval 已到頂，樽頸已移到「答」**——呢個完全呼應 D4/D5 嘅發現（retrieval 到頂、樽頸喺答）。

### 5.2 點解 LoRA 之後「能力會跌」？（用戶問嘅核心題目）

> 見 4.2：LoRA 由 base 21/34 → **18/34**；非 QA task 明顯跌（sent_score 5/5→3/5、sent_3way 6/6→5/6、fact_multi 2/4→1/4）。
> 剩低得 fact_single 微升（0→1，judge 量度），即「camp 到少量 fact，但計埋犧牲係負數」。

機制／原因，由淺到深：

**① Catastrophic forgetting（災難性遺忘）**
Fine-Tune 係將模型重量**向訓練分佈推**。LoRA 雖然只改 0.182% 參數（7.34M/4022M），但佢加喺**頭 16 層 attention 嘅低秩投影**上——呢啲正正係決定「格式跟唔跟到」／「instruction 聽唔聽」嘅地方。`--mask-prompt` 只學 assistant 回答，個 adapter 被推去「你想我講乜／點樣答」嘅 sink，於是：
- 未見夠多樣嘅 text → 背誦，唔小心寫死咗「讚」嘅傾向（sent_score 跌）。
- tool-call JSON 訓練太多 → 連 sentiment 想行 JSON 都亂（sent_3way 5/6、sent_score 3/5）。

**② 過擬合證據擺喺度**
```
LoRA:   train loss 0.086  val loss 0.533  ← 谷底後反彈（iter 300 係 0.230）
QLoRA:  train loss 0.136  val loss 0.522
```
train/valid 差距咁大＝**背誦訓練數據**，唔係學到可泛化規則。泛化能力跌 → 未見過嘅 eval prompt 偏差大。

**③ 容量 trade-off（記新 vs 保舊）**
adapter 得 7.34M 參數要同時「記新 fact」＋「保住原本大量能力」，係一個**固定容量**要 split。LoRA 揀咗記 fact（fact_single 0→1），結果舊能力被推走咗。

**④ 訓練數據分佈 bias**
576 條入面幾乎全部係 QA/tool/JSON 範本，Sentiment 又係合成 headline（個 adapter 對「句句都有變數」嘅真實評分 prompt 冇樣版可依）→ 對 D3/D6 eval 嗰啲**唔同措辭**嘅問題，格式 drift 喺 bench 上暴露。

**結論：唔係 LoRA 個方法錯，係「SFT 想叫佢做嘅嘢」集中喺答 sentence/JSON，而咁啱性格上推走咗通用能力。** 想救：加多 diversity、加 eval-like 句式、LR 再細、或者少 iter。

### 5.3 點解同一 adapter，QLoRA 就「保得住本體」？

QLoRA 同 LoRA 完全同 hyperparams（lr 1e-5 / 500 iters / 16 layers / seed 7），差別**只有 base 係 4-bit**（LoRA = bf16）。效果天壤之別：

- QLoRA = **21/34** = base（零損失，sent/calc/news 全滿分）；LoRA = 18/34（能力跌）。
- QLoRA fact_single **0/11** = base；LoRA = 1/11（camp 到少少）。

原因（機制）：
1. **低精度約束**：4-bit base 嘅正反傳都係低精度 → LoRA update 對整體行為嘅影響相對細 → 模型「郁得少」。
2. **量化嘅去噪**：4-bit 有少量量化噪聲當 regularization → 冇 LoRA 咁痴實訓練分佈。
3. **慳記憶**：3.956GB vs 9.678GB（-59%），想喺細機行 multiple variants 或者更長 seq 都得。

一句講：**QLoRA = 「近乎複製 base 能力」＋「幾乎冇 camp 到任何 fact」**。要「保有原能力、一蚊都唔蝕」→ QLoRA；呢個係 E1 最實際嘅 deployment 建議（如果你想保留現有 D6 behaviour）。

### 5.4 RAG 各 pipe 點解差咁遠（additive findings）

| 問題 | naive k=5 | adaptive k=5 | hybrid k=15 | 原因 |
|---|---|---|---|---|
| fs_01（Deutsche 38% vs guidance）| ✗ | ✗ | ✓ | doc 唔係 top-5 → k 太細先係 bottleneck |
| fs_09（Cloud 50B / 26%）| ✓ | ✓ | ✓ | 大 doc，grep 都中 |
| fs_11（DeMatteo 市值）| ✗ | ✗ | ✓ | 啱啱 k=15 撈得到，sparse term 幫手 |
| fs_07（Wells Fargo $99）| ✗ | ✗ | ✓* | hybrid 答到 $99/用戶（f1 0.41 PASS），但 judge 判 FAIL（pred 加咗 Agent 365/Copilot 誇大，或假陰性）|

- ✓* = retrieval 拎到 + f1 過閘，但 llm_judge 判 FAIL 嘅灰色 case：4B 攞到材料、答到價錢，但附加資訊或 judge 誤判。
- adaptive 仲有自身弱點：router 見到「雲/增長」呢類高頻字就答「直接答」→ 跳過 retrieval → 有時冇料都答（fs_07/fs_11 miss）。所以**adaptive ≤ naive ≤ hybrid** 又一次驗證（D5 已定案 hybrid）。

### 5.5 一個更正（refusal 假 fail）

有幾條（fs_04/05/06/10）KB 真係冇料（「股價目標」「座位數」要 doc 有），4-bit 4B 答「KB 無資料」，judge 判 FAIL——但呢個**唔算答錯**，係「無資料」正確行為（D6 trap evaluator 會當 PASS）。所以 RAG 真實分可能再高少少，但「KB 無資料」係唔可以 class 做 fact recall success，所以唔打折。

---

## 6. 結論同建議

| 你想…… | 揀 | 原因 |
|---|---|---|
| 事實 recall 準 | **RAG hybrid（k=15 + sparse RRF）** | fact_multi 4/4、fact_single 4/11（judge）|
| 保留原 task 能力（sentiment/calc/news）| **QLoRA** | 21/34 = base，慳 59% 記憶 |
| camp 極少量 fact 兼肯接受能力跌 | LoRA | fact_single 1/11，但其他全面跌 |
| 又快又平 | base / QLoRA 閉卷 | 0.3–1.4s/record |
| 要 D6 級 accuracy | **RAG + 強 model（Ark）** | D6 baseline 25/34 |

**最終答案**：「係本地、要細機、想全開源」→ **QLoRA 閉卷做便宜 example + RAG（強 model 或至少 4b local）做事實層**；
「唔好信英文-f1，要用語言中立 judge」→ 事實 recall 其實 **RAG hybrid 4/11 係全場最高**；
「能力會跌」嘅根因係 **SFT 背誦（train 0.086 vs val 0.533 overfit）＋ 容量 trade-off ＋ 訓練分佈集中喺 JSON/sentence**，唔係 4B 本身。

---

## 7. 重現 Commands

```bash
make ft-data    # 由 KB 生成 training data（deterministic）
make ft-lora    # LoRA training（bf16 base, 500 iters, peak 9.68GB）
make ft-qlora   # QLoRA training（4-bit base, 500 iters, peak 3.96GB）
make ft-fuse    # fuse adapters → fused/lora (7.5G) + fused/qlora (2.1G)
make lora-bench # 全 matrix run + report（貪 memory-safe：逐 server 開關）
# 仲有 diagnostics：
python -m experiments.lora_bench.run --row better --port 8201 --model <4bit base>   # better retrieval panel
python -m experiments.lora_bench.run --judge      # fact_multi llm_judge pass（Ollama only）
python -m experiments.lora_bench.run --judgefs    # fact_single llm_judge re-score（f1 保留喺 score_f1）
python -m experiments.lora_bench.run --report     # 重生成 report.md
```