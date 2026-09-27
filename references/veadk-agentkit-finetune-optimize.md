# VeADK + AgentKit 精調 / 優化精要（框架 vs 底層）

呢份文件講清楚一件事：**喺 VeADK / AgentKit 架構入面做「精調 / 優化」，你其實係喺邊一層做嘢。**

答案好簡短——**框架層（VeADK / AgentKit）本身冇任何微調 API**。精調模型係**火山方舟「模型精調」功能**嘅產物（底層、模型層），VeADK / AgentKit 只係透過 `model_name` + endpoint 將佢「消費」返嚟。

> ✅ **核心心法**：
> - **底層（火山方舟模型平台）** = 訓練 LoRA、建任務、出模型、做推理渠道 —— 呢度先有「精調」。
> - **框架層（VeADK / AgentKit）** = 掛 `model_name` 用精調後嘅模型；本身免費、冇微調概念、唔使知 LoRA 原理。
> - Sales 要懂另一條線：**精調產物唔喺 Agent Plan 包埋**，屬「按量 / 模型單元」第二條收費線（見 `veadk-agentkit-pricing.md`）。
> - **呢個 tab 係「精調 + 優化」**，唔淨係 LoRA —— prompt 層、output_schema、compaction、routing、蒸餾、RL 全部都係優化武器。

---

## 0. 先答三條最常被問嘅問題

| 問題 | 答案 |
|---|---|
| 「VeADK 有冇得 fine-tune？」 | **冇。** 精調喺火山方舟控制台 / OpenAPI 做，VeADK 只係用精調後嘅 model_name。 |
| 「精調模型用 Agent Plan 平唔平？」 | **唔包。** Agent Plan 包嘅係訂閱內列明嘅模型；精調後模型走**按 token 後付費**（約基模 2–2.5×）或**模型單元在線推理**（包時長）。 |
| 「改 agent 行為一定要精調咩？」 | **唔一定。** 改 prompt / output_schema / compaction / fallback routing 係零成本先做嘅；精調係進階武器，按場景決定。 |

---

## 1. 優化 / 精調全圖（一張表：全部武器排好）

呢個 tab 覆蓋由零成本到高成本嘅完整光譜——唔淨係 LoRA：

| 武器 | 類型 | 改啲咩 | 成本 | 幾時用 |
|---|---|---|---|---|
| **prompt / instruction 優化** | Prompt 層 | 語氣、格式、風格、少量規則 | 零 | 先做，八成場景夠用 |
| **output_schema / structured output** | Prompt 層 | 強制 JSON schema、欄位抽取 | 零 | 要穩定結構化輸出 |
| **compaction / context 管理** | Prompt 層 | 縮 context、排位、截斷策略 | 零 | Context 滿、成本壓力大 |
| **fallback model routing** | 架構層 | 主模掛時自動轉後備模型 | 零 | 提高可用性、壓成本 |
| **揀細 model** | 模型選擇 | 揀更平更細嘅基模 | 零/負 | 效果夠就揀細 |
| **LoRA** | 精調 | 領域知識 + 專用術語 + 穩定格式 | 低 | 大多數 vertical 場景 |
| **QLoRA** | 精調 | 同 LoRA，但 4-bit 量化基模 | 低（更低顯存） | 單卡 / 資源有限 |
| **全參數 SFT** | 精調 | 整個 domain 改寫、極限效果 | 高 | 數據極多、最後先用 |
| **DPO** | 精調（偏好） | 對齊偏好（好/壞回答揀優） | 中 | 要偏好對齊 |
| **RLHF / GRPO** | 精調（強化） | 推理能力、指令跟隨（rule-based reward） | 高 | 要唔靠 prompt 嘅推理提升 |
| **Distillation（蒸餾）** | 精調 | 大 model 輸出教細 model | 高（數據工程） | 細 model 做大 model 效果 |

> ✅ **Sales 一句**：「優化唔淨係精調——prompt / schema / routing 係零成本先做；精調係進階，但唔係唯一選擇。」

---

## 2. 概念層：六種「改模型」方法對比

| 方法 | 更新幾多參數 | 數據類型 | 效果 | 成本 | 火山方舟 支援 |
|---|---|---|---|---|---|
| **LoRA** | <1%（低秩旁路） | 指令→回應配對 | ~98% of 全量 | 低 | ✅ SFT / DPO / GRPO |
| **QLoRA** | <1%（4-bit 基模） | 同 LoRA | ≈ LoRA | 更低 | 同 LoRA |
| **全參數 SFT** | 100% | 指令→回應配對 | 基準 100% | 高 | ✅ SFT |
| **DPO** | LoRA 或全量 | 偏好（好/壞回答） | 偏好對齊 | 中 | ✅ DPO |
| **GRPO / RL** | LoRA only | Rule-based reward | 推理提升 | 高 | ✅ GRPO（只 LoRA） |
| **Distillation** | 取決於目標模型 | 大 model 輸出 | 細 model ≈ 大 model | 高（數據） | 間接（用 SFT 流程） |

**支援模型速查（2026-07）：**

| 模型系列 | SFT | DPO | GRPO |
|---|---|---|---|
| `doubao-seed-2.0-mini` / `2.0-lite` | ✅ 全量 + LoRA | ✅ | ✅（LoRA） |
| `doubao-1.5` 系列 | ✅ | ✅ | — |

> ⚠️ **RL（GRPO/PPO）** 要 rule-based reward 做 reasoning，通常需要 veRL 框架 + 超大 GPU 集群 → 係 **TrainingKit 場景**（cross-ref `veadk-agentkit-training-kit.md`）。方舟 GRPO 只支援 LoRA，全量 RL 要自己搞集群。成本係訓練 + 推理 sandbox 雙食，唔係淨訓練費。
>
> ⚠️ **Distillation** 本質係用大 model 生成高質量訓練數據再 SFT 經細 model——數據工程量大，效果極好但投入唔低。適合嘅場景：要用細 model 大量跑推理（成本壓到最低），但唔想犧牲太多效果。

---

## 3. LoRA 原理（底層概念，30 秒版）

**LoRA（Low-Rank Adaptation）** 思路：唔改原模型嘅全部權重，而係喺某啲層**旁邊**加一個「低秩」嘅小矩陣 `ΔW = A×B`，訓練期間只更新 `A`、`B`，原權重凍結。

| 對比 | LoRA | 全參數 SFT |
|---|---|---|
| 更新參數 | 極少（<1%） | 100% |
| 訓練成本 | 低（幾張卡、幾小時） | 高 |
| 收斂速度 | 快 | 慢 |
| 效果 | 約全量 **~98%+** | 基準 100% |
| 產物 | 小巧 daemon 檔（`*.lora`） | 完整 checkpoint |

**QLoRA**：將基模用 4-bit 量化載入再訓練，顯存需求再降一大截，單卡都用得。同 LoRA 效果差唔多，但顯存壓力細好多——對 GPU 資源有限嘅團隊好關鍵。

> 對客戶講：**「LoRA = 用 1% 嘅參數買返 98% 嘅效果」**。絕大多數 vertical 場景（客服風格、行業術語、抽取格式）LoRA 已經夠，唔使燒全量。QLoRA 係同一樣嘢但更慳顯存。

**Distillation（蒸餾）原理**：用一個大嘅「教師 model」生成高質量回應，再用呢啲回應去 SFT 一個細嘅「學生 model」。學生 model 用少好多嘅參數同推理成本，但可以學到教師 model 大部分嘅能力。呢個方法嘅核心唔係訓練技巧，而係**數據工程**——教師 model 輸出嘅質量直接決定學生 model 嘅上限。

---

## 4. 火山方舟「模型精調」方法矩陣 + 支援模型（底層）

官方來源：[火山方舟 模型精調概述](https://www.volcengine.com/docs/82379/1099459)（更新 2026-07-21）。

| 精調方法 | 支援 LoRA | 支援全量 | 一句說明 |
|---|---|---|---|
| **SFT**（有監督微調） | ✅ | ✅ | 最常用；用「問題→答案」配對教風格/格式/領域知識 |
| **DPO**（人類偏好對齊） | ✅ | ✅ | 用「偏好」數據（好/壞回答）教模型揀更好輸出 |
| **GRPO**（強化學習） | ✅ 只 LoRA | ❌ | 用規則計算回報，優化推理、指令跟隨 |
| **CPT**（領域繼續預訓練） | — | 屬其他渠道 | 大規模領域文本 |

> ⚠️ **新 model 唔一定唔一定啱精調**——揀基模前先查該模型頁面「精調支援」列。做新項目唔好揀「即將下線」模型做基模（見定價 doc §4.1）。

---

## 5. 精調後嘅三種推理渠道 + 價格（底層）

精調完成唔等於用得——仲要揀「推理渠道」，**價格同計費方式差好遠**：

| 推理渠道 | 點計 | 適合 | 是否要「壓縮」產物 |
|---|---|---|---|
| **在線推理（模型單元）** | 包虛擬資源時長，睇控制台報價 | 穩定高用量、SLA 要求高 | ✅ **要**（LoRA 產物需壓縮後先買到模型單元） |
| **按 token 後付費** | 精調後模型 ≈ **2–2.5× 同參數基礎模型**價格 | 用量波動、起步期 | ❌ 唔使壓縮（部分模型支援） |
| **批量推理** | 夜間離線跑，最平 | 離線大批量任務 | ✅ **要** |

**LoRA 精調後按 token 付費嘅參考倍率（2026-07，官方頁面）：**

| 基模 | 精調後按 token = |
|---|---|
| `doubao-seed-2.0-mini` | 同窗口基礎模型 **2 倍** |
| `doubao-1.5` 系列 | 同窗口基礎模型 **2.5 倍** |

**價位對照（參考）**：`doubao-seed-evolving` 訂閱外約 ¥6/百萬輸入、¥30/百萬輸出（見定價 doc）。假設 `seed-2.0-mini` 訂閱外更平，LoRA 後約 ~2×。

> ✅ **慳成本提示**：精調前先問——用**細 model + LoRA**（平、快）定**大 model + prompt**（貴但零訓練）？好多時細 model + LoRA 嘅效果夠好，推理單價細一個數量級。揀細 model 本身就係「零成本」優化武器。

> ⚠️ 報價時唔好淨講「精調貴少少」——要講清楚**續命成本**：在線/批量要壓縮 ≥1.5GB？按 token 唔使壓縮但貴 2–2.5×。每個 model 唔同，**以控制台精調「推理服務」頁面為準**。

---

## 6. 框架層接入：VeADK / AgentKit 點用精調模型

框架層只做一件事：**用 `model_name` 指住精調後模型**。三條路：

### 6.1 VeADK `Agent.model_name` 直接指

```python
from veadk import Agent, Runner

agent = Agent(
    name="tuned_faq_bot",
    model_name="ep-2026080100000-lora",          # 精調後模型/推理 endpoint
    model_provider="ark",
    instruction="你是公司客服，用官方語氣回答，嚴格按 FAQ 格式出。",
)

runner = Runner(agent=agent, app_name="tuned_faq_bot")
print(asyncio.run(runner.run(messages="保養期幾長？")))
```

`model_name` 都接受 list（主模 + 回退）：主模唔可用時自動轉 `deepseek-r1-250528` 等後備，提高可用性。

### 6.2 環境變數（Deploy 時用）

```bash
export MODEL_AGENT_NAME="ep-2026080100000-lora"     # 或者 MODEL_NAME
export MODEL_AGENT_API_KEY="sk-..."                  # 方舟 API Key
export MODEL_AGENT_API_BASE="https://ark.cn-beijing.volces.com/api/v3"
```

控制台 / `ak config` 嘅環境變數係同一個 namespace，`ModelAgentName` 等同上面。

### 6.3 Zero-code Harness

```yaml
harness:
  harness_name: my-lora-faq
  cloud: volt
  model: ep-2026080100000-lora        # 精調後推理 endpoint 名
  tools:
    - web_search
  system_prompt: "你係公司客服，按 FAQ 知識庫回答。"
```

> **牽一髮動全身嘅位**：Harness / Runtime 上面其他區塊（knowledgebase、memory、auth）跟 `veadk-agentkit-cli.md` 原樣照配，唯一分別就係 `model` 欄揀精調 id。

---

## 7. 幾時先要用咩優化武器 → 決策樹

```
想改 agent 行為？
├─ 只改語氣/格式/風格
│   └─ ➜ 改 system prompt（Agent.instruction）—— 零成本，先做
├─ 要結構化輸出（JSON schema、欄位抽取）
│   └─ ➜ 用 output_schema（Responses API，見 vector/cache doc）
├─ 要慳錢慳 context
│   └─ ➜ compaction / prompt 排位 / fallback list
├─ 領域知識 + 專用術語 + 穩定格式（仲係唔夠準）
│   └─ ➜ 先試 `seed-2.0-mini` LoRA（平、按 token、唔使壓縮）
├─ 要對齊偏好（好/壞回答揀優）
│   └─ ➜ DPO（LoRA）
├─ 要唔靠 prompt 嘅推理能力提升
│   └─ ➜ GRPO / RL（veRL + TrainingKit，cross-ref veadk-agentkit-training-kit.md）
├─ 要細 model 做到大 model 效果、成本壓到最低
│   └─ ➜ Distillation（蒸餾：大 model 輸出 → SFT 經細 model）
└─ 真係改寫成個 domain
    └─ ➜ 全量 SFT + 在線推理（成本最高，最後先用）
```

> **Sales 一句**：「優化唔係一步到位——改 prompt / schema / routing 唔使錢先做；LoRA 係最平嘅精調路；RL / 蒸餾係最後手段。」

**場景速判**：

| 場景 | 推薦路線 | 成本 |
|---|---|---|
| 客服語氣太機械 | prompt 優化 → 唔夠再 LoRA | 零 → 低 |
| JSON 抽取欄位唔穩定 | output_schema → 唔夠再 LoRA | 零 → 低 |
| 要細 model 跑大量推理 | Distillation → SFT 經細 model | 高（前期）→ 低（推理） |
| 推理題正確率唔夠 | GRPO / RL（TrainingKit） | 高 |
| 整個 domain 要改寫 | 全量 SFT | 高 |

---

## 8. 避雷 + 成本意識

| 避雷點 | 詳情 |
|---|---|
| **唔好用「即將下線」基模做精調** | `2.0-pro` / `2.0-code` 白做，精調咗都冇用 |
| **精調唔入 Agent Plan** | 精調後模型默認**唔入訂閱**，係第二條收費線 |
| **新基模未必即開精調** | 揀基模前睇「精調支援」標誌 |
| **RL 成本係雙食** | 訓練成本（超大 GPU 集群）+ 推理 sandbox 成本——唔係淨訓練 |
| **Distillation 要數據工程** | 蒸餾唔係一鍵——要大 model 生成數據、清洗、格式化、再 SFT，數據質量決定效果 |
| **在線 / 批量要壓縮** | LoRA 產物 ≥1.5GB 要壓縮先買到模型單元，按 token 唔使（部分模型） |
| **唔好同 Agent Plan 混埋計** | 精調後模型走按 token 或模型單元，同 Agent Plan 訂閱分開 |

> **Sales 一句**：「精調唔係功能掣，係**一個模型換另一個模型**。換之前，先確認你要改嘅嘢 prompt 搞唔搞得掂。」

---

## 9. 資料來源

| 來源 | URL | 日期 |
|---|---|---|
| 火山方舟 模型精調概述（方法矩陣 + 推理渠道 + LoRA 倍率） | https://www.volcengine.com/docs/82379/1099459 | 更新 2026-07-21 |
| 有監督微調最佳實踐 | https://www.volcengine.com/docs/82379/1221664 | 頁面日 |
| 火山方舟 SaaS 平台 SFT 教學（CSDN，社群範例） | https://blog.csdn.net/zhaoyuanh/article/details/145783407 | 2026-02 前 |
| VeADK 模型配置（`model_name` / list + `MODEL_AGENT_*` env） | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/agent/model | 頁面日 |
| 定價指南（Agent Plan / 按量 / 模型可用性矩陣） | `references/veadk-agentkit-pricing.md` | 2026-08-09 |
| TrainingKit（veRL / GRPO 場景） | `references/veadk-agentkit-training-kit.md` | — |

> **免責**：LoRA 訓練費、按 token 倍率、模型單元價屬「參考估算」，以火山方舟控制台「模型精調」+「用量明細」為準。RL / 蒸餾成本視乎集群規模同數據量，更唔穩定。

---

*Last audit date: 2026-08-17 · 精調支援矩陣、模型同價格會變，賣之前對正官方頁。*
