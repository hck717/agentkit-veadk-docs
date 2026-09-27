# VeADK + AgentKit 評估 / 評測（Eval）指南 — BytePlus 點提供唔同類型嘅評估

改 agent 一定要有量度。呢份講 **BytePlus / AgentKit 點做評估**：唔同 eval 類型（Offline / CI / Shadow / Studio 自動回流）、由 **dataset → evaluator → experiment → regression** 成條流水線，用 **AgentKit CLI + VeADK** 落地。

> **核心心法**：
> 1. **Eval 四件事**：**Dataset（測咩）→ Evaluator（點評）→ Experiment（點跑）→ Regression（點守）**。
> 2. **改嘢就要有量度**——慳到飛起但 accuracy 跌晒 = 白做。每次改 prompt / 模型 / 工具，都過一次 eval。
> 3. **Founding 一件事**：AgentKit/VeADK 提供 eval **框架同 CLItooling**，評分 core（LLM-as-judge）call 方舟模型。你唔使自己砌評分器。

---

## 0. 快睇：BytePlus / AgentKit eval 全家

| Eval 類型 | 喺邊跑 | 做咩 | 幾時用 | 工具 |
|---|---|---|---|---|
| **Offline / Dataset eval** | 固定評測集 | 改 prompt / model 前後對比分 | **每次改動** | `agentkit eval run --dataset ... --evaluator 相关性 --target my-agent` |
| **CI eval** | CI pipeline | deploy 前自動守關 | **每次 de / 更新** | `agentkit eval run` 回傳 `experimentId` → `eval experiment get / results` |
| **Shadow eval** | 上線流量抽 10% | 平行評分，唔影響用戶 | 持續監控 | Studio auto-sample |
| **Studio 自動回流** | 每輪對話自動評分 | Good/Bad Case 落返評測集 | 持續數據飛輪 | Studio「自動創建評測集」 |
| **VeADK DeepEval 集成** | 本地 Python | LLM-as-judge 評測 | 開發期 iterate | `pip install "veadk-python[eval]"` |

> **Sale 一句**：「性能優化唔使講『應該快少少』——我哋用 eval 每改一版都畀分，慳錢之餘有實績。」

---

## 1. Eval 四件事 — 由頭到尾

```
Dataset（測咩）→ Evaluator（點評）→ Experiment（點跑）→ Regression（點守）
    固定集        評分方法           一次運行           攞返結果守住
```

| 環節 | 做咩 | AgentKit 點做 |
|---|---|---|
| **Dataset** | 一堆 (input, reference_output) 對 | `agentkit dataset create / add / show` |
| **Evaluator** | 評分方法：字面 / embedding / LLM-as-judge | `agentkit evaluator list` |
| **Experiment** | 一次評価運行 | `agentkit eval run` → 回傳 `experimentId` |
| **Regression** | 新版本分數對舊版本（防倒退） | `agentkit eval experiment show <id>` 比對 |

> 🎯 重點：**eval 唔係「測一次」，係「次次改嘢都測」**——Regression 先係 eval 存在嘅理由。

---

## 2. AgentKit CLI — 全套指令

### 2.1 Dataset

```bash
agentkit dataset list
agentkit dataset show qa-set --items 50
agentkit dataset create --name qa-set --schema "input,reference_output"
agentkit dataset add qa-set --field "input=法國首都是？" --field "reference_output=巴黎"
agentkit dataset add qa-set --file ./cases.json
agentkit dataset remove qa-set item-1 item-2 -y
agentkit dataset delete qa-set -y
```

> 💡 `eval` 前綴可以省略：`agentkit dataset ...` = `agentkit eval dataset ...`。

### 2.2 Evaluator + Run

```bash
agentkit evaluator list
agentkit eval run --dataset qa-set --runtime my-agent
agentkit eval experiment list
agentkit eval experiment show <experiment-id>
```

### 2.3 升級用法（perf doc §10 節錄）

```bash
agentkit eval run --dataset qa-set --evaluator 相关性 --target my-agent \
  --concurrency 10 --dry-run      # 先試行，唔真跑
agentkit eval run --dataset qa-set --evaluator 相关性 --target my-agent --json
```

- 一次多個 `--evaluator`（相關性 / 完整性）加權。
- CI 用：`eval run` 回傳 `experimentId` → `eval experiment get / results`。
- `--concurrency 10` 縮短 turnaround。

> ⚠️ 參數字面以 `agentkit evaluator list` 顯示為準。

---

## 3. Evaluator 類型對比 — 揀評分方法

| Evaluator | 原理 | 優點 | 弱點 | 幾時用 |
|---|---|---|---|---|
| **字面匹配（BLEU/ROUGE）** | n-gram 重疊 | 快、平、可重現 | 唔睇語義 | 翻譯 / 摘要基準 |
| **Embedding 相似度** | 比語義距離 | 快、語義 | 唔識評「要點精」 | 粗略回歸 |
| **LLM-as-judge** | 用 model 評分（相關性/完整性） | 準、可自訂 rubric | 貴、要校準 | **主流**（`agentkit eval run --evaluator 相关性`） |
| **參考對照（reference）** | 對 golden answer | 客觀 | 要造 golden | 有標準答案 |
| **人工 / HITL** | 人評 | 最準 | 貴、慢 | 高風險 / 小集 |

> **BytePlus / Volcengine 點落地**：evaluator「相关性」= 方舟 LLM-as-judge（call 方舟模型評分）。要同 model 唔同來評？可以配 `agentkit.yaml` 個 eval evaluator 指定模型。

---

## 4. VeADK Python — DeepEval 集成

開發期想喺 code 入面跑評測（未上 AgentKit runtime），用 `veadk-python[eval]`（DeepEval 評測）：

```bash
pip install "veadk-python[eval]"
```

```python
# 開發期本地評測（唔使 deploy）：
# 1) 建 dataset（見 topic 上面 CLI）
# 2) 喺 code 入面行 LLM-as-judge 對比 baseline vs 新 prompt
```

> 🎯 VeADK eval 集成主要係 **DeepEval**（LLM-as-judge / metric 庫）。設計意圖：**開發期 iterate 用 VeADK，上線回歸用 AgentKit CLI + Studio 自動回流**——唔好兩邊重做。

---

## 5. 四種 Eval 類型罩面睇

| 類型 | 點跑 | 攞到咩 | 重點 |
|---|---|---|---|
| **Offline** | `eval run --dataset ...` | 固定集分數 | 改 model / prompt 前後對比分數 |
| **CI** | pipeline 入 `eval run` → `experiment get` | pass/fail 門檻 | **每次 deploy 前自動守關** |
| **Shadow** | 上線流量抽 10% 平行評分 | 唔影響用戶嘅質量曲線 | 同 offline 結果比，防線上 drift |
| **Studio 回流** | 每輪對話自動評分（0–1） | Good/Bad Case → 評測集 | **數據飛輪**：新 case 自動入集 |

### 5.1 Studio 自動回流（數據飛輪）

部署開「自動創建評測集」→

```
每輪對話自動評分（0–1）→ ≥0.6 入 Good Case → Good/Bad Case 落返 {agent}_good_case / {agent}_bad_case
```

> 好處：**真實用戶 case 自動肥評測集**——唔使淨係靠人工標注。壞 case 就係下一輪 eval 嘅靶。

---

## 6. Eval 入 CI — 實作

```bash
# deploy pipeline 入面：先跑 eval，Fail 就唔放行
agentkit dataset list                       # 有冇評測集
agentkit eval run --dataset qa-set --target my-agent --json \
  > exp.json                                # 攞 experimentId + 分數
agentkit eval experiment show $(jq -r .experimentId exp.json)
# 分數 < 門檻 → 停 pipeline
```

> 🎯 `--concurrency 10` 縮短 turnaround；CI 用 `experiment get / results` 攞結構化結果唔好靠 parse log。

---

## 7. Eval 嘅隱性成本（報價要加）

| 成本 | 出處 |
|---|---|
| Shadow eval 10% 流量 | = **+10% 模型消耗** → 計入報價 buffer（pricing doc） |
| Studio 自動評測 | 每輪評分 model call |
| PII scan | 額外 LLM-FW 消耗（guardrail） |

> ⚠️ 報價時記得：**eval 唔係免費**。LLM-as-judge 每 case 一次 model call；Shadow 10% 流量同 Studio 每輪評分都要buffer。

---

## 8. 幾時用邊種（決策）

| 情況 | 揀 |
|---|---|
| 改 prompt / 換 model 前後 | **Offline** dataset eval |
| 每次 deploy 前 | **CI eval**（自動守關） |
| 上線後想持續監查 | **Shadow eval**（10% 抽樣） |
| 想數據飛輪（真實 case 自動入集） | **Studio 自動回流** |
| 開發期 iterate | **VeADK DeepEval** |
| 高風險 / 小集（金融、合規） | 加 **人工 / HITL** |

> **Sale 一句**：「Eval 四件——dataset、evaluator、experiment、regression——一次搞掂埋單『改版有分數』。你嘅 agent 唔係練完就算，係帶住分數行。」

---

## 9. Benchmark 全覽 — 按任務類型（一口氣表）

**任務類型決定 evaluator**——唔同任務用唔同 metric，唔好一套 `相关性` 走天涯：

| 任務類型 | 例 | 最常用 evaluator / metric | 門檻建議（起步） | AgentKit 落地 |
|---|---|---|---|---|
| **純文字台** | FAQ、知識問答 | LLM-as-judge（相关性 / 完整性） | 相关性 ≥0.8 | `--evaluator 相关性` |
| **RAG（連知識庫）** | 客服查產品、查 policy | Faithfulness + Answer Relevancy + Context Precision/Recall（DeepEval 內置） | Faithfulness ≥0.8 · Relevancy ≥0.7 | 檢索/生成兩層分開測（見 §10.1） |
| **OCR / 文檔抽取** | 發票、身份證、契約 | CER / WER（字符層）+ **字段準確率** | CER <5% · 字段準確 ≥95% | 字面 evaluator 對 golden + agent 完成率 |
| **摘要** | 長文壓縮、會議紀要 | ROUGE（baseline）+ Completeness rubric（judge） | 完整性 ≥0.8 | judge + 人工抽 |
| **翻譯** | 多語輸出 | BLEU / ROUGE（baseline）+ 忠實度 judge | BLEU 淨做 baseline | 字面 + judge |
| **工具調用 / function-calling** | 落 tool、填參數 | JSON schema 正確率 + 參數命中率 | parse 正確 ≥95% · 參數錯誤 <2% | 字面 evaluator（對 JSON） |
| **生圖（Seedream）** | prompt-following、consistency、編輯一致 | LLM-as-judge rubric + 抽樣人工 | 人工抽可用率 ≥80% | 工具前後測（seedream tab §9） |
| **生片（Seedance）** | 動作 / 物理真實 / 時間一致 / 音畫 | **人工 HITL 為主** + judge 初篩 | 人工優良率（每團隊自定） | 異步 task + 人工抽片（seedance tab §9） |
| **語音 ASR / TTS** | 轉錄、合成 | WER / CER | WER <8%（標準場景） | 字面 + judge |

---

## 10. 細任務 Benchmark 深探

### 10.1 RAG（檢索 + 生成分開測）

| 層 | 測咩 | Metric |
|---|---|---|
| **檢索** | 應唔應該撳返正確段落 | Recall@k / hit rate、MRR、Contextual Precision（多餘段落比例） |
| **生成** | 有冇照住 context 講、有冇吹 | **Faithfulness**（唔造謠）、Answer Relevancy、G-Eval |

- DeepEval（`veadk-python[eval]`）內置 Faithfulness / Relevancy / Contextual Precision/Recall / G-Eval——**唔使自己砌**。
- 上游（chunking / Ranker / 速度—準確—成本權衡）見 **rag tab §3–4**。
- 檢索層單獨測：評估集刻意加「多餘段落」case，睇 Contextual Precision 跌唔跌。

### 10.2 OCR / 文檔（發票、身份證、契約）

- **字符層 CER / WER**：唔理版面，淨睇字啱唔啱。
- **字段層準確率**：對返 `invoice date / amount / supplier` 等 slot——**字段誤判先係最傷**。
- **版面 / 佈局**：表格重組、欄位對齊有冇亂。
- **Agent 完成率**：成條 pipeline（OCR→翻譯→驗證→匯總→審批）有幾多單 100% 無需人執（見 `projects/invoice-pipeline.md`）。
- 門檻：CER <5%、字段準確 ≥95% 起步；身份證 / PII 類 → 必加 HITL。

### 10.3 客服 / 知識型（最高量）

- 維度：**相关性、完整性、tone**、**hallucination rate**（講咗冇出處嘅嘢）。
- 用 **Studio 自動回流**（Good/Bad Case）做數據飛輪——壞 case 就係下一輪 eval 靶。
- 門檻：相关性 ≥0.8；新 feature 嘅 hallucination rate 唔好過 3–5%。

### 10.4 生圖 / 生片（多模態）

- **Seedream**：prompt-following、text-image consistency、**editing consistency**、知識推理（MagicBench 維度，見 seedream tab §9）。
- **Seedance**：instruction adherence、**motion realism / 物理真實**、temporal coherence、**音畫同步（ms）**（見 seedance tab §9）。
- 做法：**judge 初篩 + 人工抽樣定生死**——LLM-as-judge 對圖/片只做 pre-filter，品質綠燈靠人。

### 10.5 翻譯 / 摘要

- 字面（BLEU / ROUGE）做 **baseline**，judge 做 **決策**——ROUGE 高分但意思錯都係壞。
- 摘要漏咗核心點 → Completeness rubric（完整性）。

### 10.6 工具調用 / 多步 Agent

- **JSON parse 正確率** + **參數命中率**（落錯 tool / 填錯參數最痛）。
- **任務完成率**：成個 workflow 有幾多成功到尾（對照 `experimentId` 連續版本）。
- **Step-wise regression**：每步埋 output 比較，唔好淨睇最後分數。

> 🎯 **總原則**：RAG 拆檢索/生成兩層，OCR 睇字段準確而唔係成段，生圖生片靠人抽樣，客服用真實 case 回流——**揀對 evaluator 先有對嘅分數**。

---

## 11. 資料來源

| 來源 | URL | 日期 |
|---|---|---|
| AgentKit CLI 評測（dataset / evaluator / experiment） | `references/agentkit-cli.md` | 2026 |
| 性能優化 Playbook Eval（含 Studio 回流 / 反模式） | `references/veadk-agentkit-performance.md` §10/§11 | 2026 |
| AI 概念百科 Evaluation 字典（13.x） | `references/veadk-agentkit-ai-concepts.md` §13 | 2026 |
| `veadk-python[eval]`（DeepEval 評測） | `references/veadk-api.md` | 2026 |
| RAG 指標（Faithfulness / Relevancy / Contextual Precision / G-Eval / RAGAS） | DeepEval 文檔 | 2026 |
| RAG 檢索層 + Ranker（chunking / ranker / 權衡） | `references/veadk-agentkit-rag-guide.md` §3–4 | 2026 |
| Seedream 評測維度（MagicBench 抽樣） | `references/veadk-agentkit-seedream.md` §9 | 2026 |
| Seedance 評測維度（物理真實 / 音畫同步） | `references/veadk-agentkit-seedance.md` §9 | 2026 |
| OCR / 發票 AI Pipeline（完成率目標） | `projects/invoice-pipeline.md` | 2026 |

> **免責**：`--evaluator 相关性` 等 evaluator 中文名、CLI 參數字面以 `agentkit evaluator list` / AgentKit 官方文檔為準；方舟 LLM-as-judge 同 Studio 自動回流功能隨版本迭代。門檻數字（§9–10）係 startup 建議，唔係官方 SLA，按場景調。

---

*Last audit date: 2026-09-06 · 新增 §9–10 按任務類型 benchmark（RAG / OCR / 客服 / 多模態 / 工具調用）。evaluator 名稱同參數可能郁，落地前 refetch。*