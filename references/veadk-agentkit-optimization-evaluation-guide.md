# BytePlus / Volcengine Agent 生態：Agent 優化（Optimization）與評估（Evaluation）完全指南

> **來源與日期**：本文以 2026-09-15 實時抓取嘅官方文檔為準（Mintlify mirror、GitHub raw source、docs.byteplus.com doccenter JSON API）。
> 每個章節末標明 URL。凡「本地 cache」推斷嘅內容都會明確標示。
>
> **一句總結**：BytePlus 唔係用「一個 eval 功能」解決問題，而係喺**三層**（模型層 / 框架層 / 平台層）各有一套 evaluation + optimization 武器，再用 **observability（tracing）** 做貫穿三層嘅量測底座。改任何嘢之前先有分數，改完之後分數要唔跌——呢個就係整個體系嘅設計意圖。

---

## 0. 全局架構：三層 × 兩軸

```
┌─────────────────────────────────────────────────────────────────┐
│  L3  平台層  AgentKit                                           │
│      ├─ Evaluation : CLI eval loop（dataset→evaluator→target    │
│      │              →experiment）、Studio 自動評測回流            │
│      ├─ Optimization: Harness Sidecar（5 個優化組件）、          │
│      │               runtime 資源調優、model-gateway routing      │
│      └─ Observability: 基礎監控（metrics）+ 應用可觀測（traces）  │
├─────────────────────────────────────────────────────────────────┤
│  L2  框架層  VeADK（built on Google ADK）                        │
│      ├─ Evaluation : ADKEvaluator（軌跡/工具）、                 │
│      │              DeepevalEvaluator（輸出質量）、BaseEvaluator  │
│      ├─ Optimization: PromptPilot（prompt）、Ark RL / Agent      │
│      │              Lightning（RL）、LocalReflector（自反思）     │
│      └─ Observability: OpentelemetryTracer + 4 個 exporter       │
├─────────────────────────────────────────────────────────────────┤
│  L1  模型層  ModelArk + TrainingKit                              │
│      ├─ Evaluation : 模型評測系統（預設數據集 + 4 種評分方法）    │
│      ├─ Optimization: 模型精調 SFT/DPO/GRPO/CPT、LoRA/QLoRA/全量 │
│      └─ TrainingKit : veRL、MFU>60%、ETTR>99%、RL 吞吐 20×       │
└─────────────────────────────────────────────────────────────────┘
```

**關鍵分工原則**：

| 你想改嘅嘢 | 喺邊層做 | 用咩 |
|---|---|---|
| 模型本身嘅能力／推理 | L1 模型層 | ModelArk 精調、TrainingKit RL |
| Agent 嘅行為、prompt、工具編排 | L2 框架層 | VeADK prompt / RL / 自反思 |
| 已部署 runtime 嘅版本守關、線上質量 | L3 平台層 | AgentKit CLI eval、Studio 自動回流 |
| 「依家發生咩事」 | 貫穿三層 | Observability / tracing |

---

# 第一部分：Evaluation（評估）

## 1. AgentKit CLI —— 完整 eval loop（L3 平台層）

### 1.1 核心心法

AgentKit 將 eval 拆成**四件事**，每件一件 CLI 子命令群：

```
Dataset（測咩）→ Evaluator（點評）→ Target（跑邊個）→ Experiment（跑一次 + 睇結果）
   評測集            評分器            被評對象            實驗記錄
```

> 來源：https://agentkit-f14c9eb5.mintlify.site/productions/agentkit-cli/preview/en/workflows/evaluation

### 1.2 Evaluation backend —— 先搞清楚你連邊個平台

`agentkit eval` 唔係一套實作，佢係一個**統一前端**，後面接兩個 backend：

| Backend | 特徵 | 版本要求 |
|---|---|---|
| **Coze** | 用 Ark endpoint ID 做 judge model；唔一定要 `--evaluator-version`；`-p/--project` 有效 | — |
| **TEA** | 要求每次 `--evaluator` 配一個 `--evaluator-version`；dataset / evaluator / target 全部有版本概念；支援 `eval target` | — |

**CLI 點知你用邊個？** 佢自動 resolve，你可以查：

```bash
agentkit eval backend          # 解析當前憑證對應嘅 backend + 刷新 cache
agentkit eval backend --json
```

- Backend 結果**按 identity + evaluation gateway 快取 7 日**。
- 想繞過 cache：`--cache-refresh`（`eval` 群組或頂層 `dataset` 群組都支援）。
- 想睇完整 TEA request（debug）：`--verbose`（`session_key` cookie 會 mask）。

```bash
agentkit eval --cache-refresh backend
agentkit eval --verbose dataset list
```

**Evaluation Gateway 配置（指向測試環境用）**：

| 環境變數 | 說明 | 預設 |
|---|---|---|
| `AGENTKIT_EVAL_HOST` | 評測 gateway host | `agentkit.cn-beijing.volcengineapi.com` |
| `AGENTKIT_EVAL_SERVICE` | request 簽名用嘅 service name | `agentkit` |
| `AGENTKIT_EVAL_REGION` | 簽名 region | `cn-beijing` |
| `AGENTKIT_TEA_ACCOUNT_ID` | 轉發俾 TEA 嘅 account ID；唔填就由 SSO session / STS identity 解析 | 自動 |
| `EXTRA_HEADER` | 額外 request header，`Name: Value` 用分號分隔 | — |

```bash
AGENTKIT_EVAL_HOST=agentkit-ppe.cn-beijing.volcengineapi.com \
AGENTKIT_EVAL_SERVICE=agentkit_ppe \
agentkit eval backend --json
```

> 來源：https://agentkit-f14c9eb5.mintlify.site/productions/agentkit-cli/preview/en/commands/eval/backend

### 1.3 Dataset（評測集）

```bash
# 列出
agentkit dataset list

# 睇詳情（schema / 版本 / cases）
agentkit dataset show qa-set --items 50
agentkit dataset show qa-set --dataset-version 0.0.1 --json

# 建立（schema 一旦建立就固定，case 嘅 key 必須 match）
agentkit dataset create --name qa-set --schema "input,reference_output"

# 加 case（逐條）
agentkit dataset add qa-set \
  --field "input=What is the capital of France?" \
  --field "reference_output=Paris"

# 加 case（批量，由 JSON file）
agentkit dataset add qa-set --file cases.json

# 移除 / 刪除
agentkit dataset remove qa-set item-1 item-2 -y
agentkit dataset delete qa-set -y
```

**`cases.json`（Coze backend 格式 — flat object array）**：

```json
[
  { "input": "What is the capital of France?", "reference_output": "Paris" },
  { "input": "What is the chemical formula of water?", "reference_output": "H2O" }
]
```

**`items.json`（TEA backend 格式 — full turn-shaped item）**：

```json
[
  {
    "turns": [
      {
        "field_data_list": [
          {
            "key": "input",
            "name": "input",
            "content": {
              "content_type": "Text",
              "format": 1,
              "text": "What is the capital of France?"
            }
          }
        ]
      }
    ]
  }
]
```

**TEA dataset 版本管理**（只有 TEA 有）：

```bash
agentkit dataset version list --dataset qa-set
agentkit dataset version create 0.0.2 --dataset qa-set --description "Add edge cases"
agentkit dataset update <dataset-id> --name qa-set-v2 --description "Customer-support QA set"
```

| Flag | 說明 | 預設 |
|---|---|---|
| `--name` | dataset 名（required） | — |
| `--schema` | 逗號分隔欄位名 | `input,reference_output,output` |
| `--description` | 描述 | — |
| `--items <n>` | show 時列幾多條 case；`0` = 唔列 | `20` |
| `--file <path>` | JSON file（Coze=flat object/array，TEA=full item） | — |
| `--items-json <json>` | 原始 TEA item array（**優先於 `--file`**） | — |
| `-r, --region` | region | 自動偵測 |
| `-p, --project` | Coze project（TEA 忽略） | `default` |

> **實務建議**：dataset 通常只需要 `input` + `reference_output`。`output` 係被評 target 喺實驗期間產生嘅，**唔應該寫入 dataset**。
>
> 來源：https://agentkit-f14c9eb5.mintlify.site/productions/agentkit-cli/preview/en/commands/eval/dataset

### 1.4 Evaluator（評分器 = rubric prompt + judge model）

**Evaluator 本質**：一個 rubric prompt（評分準則）+ 一個 judge model（評分模型）。佢接收 input fields，輸出一個分數或分佈。

```bash
# 瀏覽內建模板
agentkit eval evaluator template list
agentkit eval evaluator templates --type prompt        # 兼容入口

# 睇某個模板嘅 prompt + input fields
agentkit eval evaluator template show relevance

# 由模板衍生一個 evaluator，換上你自己嘅 judge model
agentkit eval evaluator create \
  --name relevance \
  --from-template "relevance" \
  --model ep-xxxxxxxx

# 或者用自訂 prompt file 定義
agentkit eval evaluator create \
  --name custom-score \
  --prompt-file ./rubric.txt \
  --input-schemas input,output,reference_output \
  --model 2

# 列出 / 睇詳情
agentkit eval evaluator list
agentkit eval evaluator show relevance
agentkit eval evaluator show relevance --evaluator-version 0.0.1

# TEA：更新 draft → 提交版本
agentkit eval evaluator update-draft <evaluator-id> \
  --prompt-file ./rubric.txt \
  --input-schemas-json '[{"key":"input"},{"key":"output"},{"key":"reference_output"}]'
agentkit eval evaluator version list --evaluator relevance
agentkit eval evaluator version submit 0.0.2 --evaluator relevance --description "Update rubric"

# 刪除
agentkit eval evaluator delete relevance -y
```

**`evaluator create` 全部 flag**：

| Flag | 說明 | 預設 |
|---|---|---|
| `--name` | evaluator 名（required） | — |
| `--from-template <key\|id\|name>` | 由內建模板 clone rubric + schema。TEA 用 template key；Coze 用 template ID/name | — |
| `--model <name\|id>` | **Judge model**。TEA 接受 `Doubao 2.0 Lite` / `Doubao 2.0 Pro` / `Doubao 2.0 Mini`，或 model ID `1`/`2`/`3`；Coze 用 Ark endpoint ID | — |
| `--prompt-file <path>` | 自訂 rubric 文字檔 | — |
| `--description` | 描述 | — |
| `--input-schemas <keys>` | 逗號分隔 input field keys（**只有 TEA**） | — |
| `--type <type>` | 內建模板類型（`prompt` 或數字） | `prompt` |
| `--locale <locale>` | 模板語言；`cn` / `zh-CN` 會附加中文版 | `zh-CN` |

**Prompt 佔位符（placeholder）**：喺 prompt 入面用 `{{input}}`、`{{output}}`、`{{reference_output}}` 引用欄位。呢啲欄位名就係 evaluator 嘅 **input schema**，`eval run` 時會自動做 field mapping。

> **重要**：On Coze 至少要提供 `--from-template` 或 `--prompt-file` 其中一個。
> **Judge model 要揀強嘅**——`--model` 指向能力好嘅 Ark endpoint；弱 model 出嘅分數會好嘈（noisy）。
>
> 來源：https://agentkit-f14c9eb5.mintlify.site/productions/agentkit-cli/preview/en/commands/eval/evaluator

### 1.5 Target（被評對象）

```bash
agentkit eval target list --name my-agent
agentkit eval target version-list --source-target-id <source-target-id>
```

| 項目 | 說明 |
|---|---|
| 預設 target type | `101`（Volcengine 標準 source evaluation target type） |
| 支援 backend | **只有 TEA** |
| 對應實體 | 通常就係一個已部署嘅 Runtime |
| `--target-version` 省略時 | 用 version list 入面**最新**版本 |

> 來源：https://agentkit-f14c9eb5.mintlify.site/productions/agentkit-cli/preview/en/commands/eval/target

### 1.6 Run（跑實驗）

```bash
agentkit eval run \
  --dataset qa-set \
  --evaluator relevance \
  --evaluator-version 0.0.1 \
  --target my-agent
```

**完整 flag 表**：

| Flag / Argument | 說明 | 預設 |
|---|---|---|
| `--dataset <id\|name>` | 評測集 ID 或精確名 | **Required** |
| `--dataset-version <id\|name>` | TEA dataset 版本；省略時用已 committed 版本，需要時自動 publish draft | — |
| `--evaluator <id\|name>` | Evaluator ID 或精確名；**可重複** | **Required** |
| `--evaluator-version <id\|name>` | TEA evaluator 版本；每個 `--evaluator` 都要配一個 | — |
| `--target <runtime name\|id>` | 被評嘅已部署 Runtime 或 TEA source evaluation target | **Required** |
| `--target-type <n>` | TEA source evaluation target type | `101` |
| `--target-version <version>` | TEA target 版本；省略時用最新 | 最新版本 |
| `--name <name>` | 實驗名 | `<dataset>-<timestamp>` |
| `--description <text>` | 實驗描述 | — |
| `--concurrency <n>` | 並行 case 數 | `5` |
| `--map <spec>` | 覆寫 field mapping；可重複 | 自動 |
| `--dry-run` | 只印出將會提交嘅 request，唔真跑 | `false` |
| `-p, --project <name>` | Coze project（TEA 忽略） | `default` |
| `--json` | 輸出原始 JSON | `false` |

**升級用法**：

```bash
agentkit eval run \
  --dataset qa-set \
  --dataset-version 0.0.1 \
  --evaluator relevance \
  --evaluator-version 0.0.1 \
  --target my-agent \
  --target-version <target-version> \
  --concurrency 8
```

**自動 Field Mapping（三層對齊）**——實驗要對齊三層資料：dataset fields、target input/output、evaluator inputs。預設靠慣例自動接：

- Target Runtime 通常用 `user_input` 做 input、`actual_output` 做 output。
- Dataset 嘅主 input 欄（如 `input`）→ target 嘅 `user_input`。
- Evaluator 代表「模型答案」嘅欄（如 `output`）← target output `actual_output`。
- 其餘欄位（如 `input`、`reference_output`）→ 按名 match 由 dataset 取。

**`--map` 語法**：

| Backend | 形式 | 意思 |
|---|---|---|
| TEA | `evaluator.<field> <- dataset.<field>` | Evaluator input 來自 dataset 欄位 |
| TEA | `evaluator.<field> <- target.<field>` | Evaluator input 來自 target output 欄位 |
| TEA | `target.<field> <- dataset.<field>` | Target input 來自 dataset 欄位 |
| Coze | `<evaluatorField>=<datasetField>` | Evaluator input 來自 dataset |
| Coze | `<evaluatorField>=target:<targetOutput>` | Evaluator input 來自 target output |
| Coze | `target:<targetInput>=<datasetField>` | Target input 來自 dataset |

```bash
agentkit eval run --dataset qa-set --evaluator relevance --evaluator-version 0.0.1 --target my-agent \
  --map "evaluator.output <- target.actual_output" \
  --map "target.user_input <- dataset.question"
```

**強烈建議先 `--dry-run`**，確認 resolved 嘅 dataset version、evaluator version、target version、field mapping 都對：

```bash
agentkit eval run --dataset qa-set --evaluator relevance --evaluator-version 0.0.1 --target my-agent --dry-run
```

**回傳**：

```json
{ "experimentId": "75901...", "runId": "75902...", "name": "qa-set-<timestamp>" }
```

> TEA 額外回傳 `runId`。一次實驗需要一個 committed dataset version；如果省略 `--dataset-version` 而 dataset 只有未 committed 嘅 draft，`eval run` 會自動 publish 一個版本先提交。
>
> 來源：https://agentkit-f14c9eb5.mintlify.site/productions/agentkit-cli/preview/en/commands/eval/run

### 1.7 Experiment（睇結果）

```bash
agentkit eval experiment list                    # 別名 agentkit eval exp list
agentkit eval experiment show 75901xxxxxxxxxxxxx # 別名 get
agentkit eval experiment results 75901xxxxxxxxxxxxx --json
```

| 子命令 | 內容 | 主要 flag |
|---|---|---|
| `experiment list` | ID、名、狀態、開始時間、建立者、**aggregate score** | `-p/--project`、`--json` |
| `experiment show` | 狀態、dataset、target、evaluators、**aggregate scores**、field mappings | `<id>`（required）、`-p/--project`、`--json` |
| `experiment results` | **逐 case**：每條 case、target output、每個 evaluator 嘅分數同理由 | `<id>`、`--limit <n>`（上限 20，預設 20）、`--page <n>`（預設 1）、`--json` |

**`experiment show` 輸出實例**：

```
ID              75901xxxxxxxxxxxxx
Name            qa-set-<timestamp>
Status          Success
Dataset         qa-set (75900xxxxxxxxxxxxx)
Target          my-agent
Overall score   1.00

Evaluators:
  relevance @0.0.1  avg 1.00
    1.00: 2 (100%)

Field mappings:
  target: user_input <- dataset.input
  relevance: output <- target.actual_output, reference_output <- dataset.reference_output
```

**Experiment 狀態**：

| Status | 意思 |
|---|---|
| `Success` | 所有 case 執行完成 |
| `Failed` | 部分 case 執行失敗（例如 target 冇回應） |
| `Draining` / `Processing` | 仍在跑 |

> **除錯關鍵**：當 case 失敗但**冇** experiment-level error message，通常係 target Runtime 冇正確回應（未部署 / 未 ready / 認證失敗），**唔係**評測配置問題。先確認 `--target` 指住嘅 Runtime 有喺度跑。
>
> 來源：https://agentkit-f14c9eb5.mintlify.site/productions/agentkit-cli/preview/en/commands/eval/experiment

### 1.8 完整端到端流程（官方六步）

```bash
# 1) 初始化 + 部署一個 agent，取得可評嘅 target runtime
agentkit init qa-agent --template basic
cd qa-agent
agentkit launch
agentkit invoke run "hello"          # 確認 runtime 有回應

# 2) 建立 dataset + 加 case
agentkit eval dataset create --name qa-set --schema "input,reference_output"
agentkit eval dataset add qa-set --field "input=What is the capital of France?" --field "reference_output=Paris"
agentkit eval dataset add qa-set --file cases.json
agentkit eval dataset show qa-set

# 3) 建立 evaluator
agentkit eval evaluator template list
agentkit eval evaluator create --name relevance --from-template "relevance" --model ep-xxxxxxxx
agentkit eval evaluator version submit 0.0.1 --evaluator relevance   # TEA 需要

# 4) 跑實驗
agentkit eval run --dataset qa-set --evaluator relevance --evaluator-version 0.0.1 --target qa-agent --dry-run
agentkit eval run --dataset qa-set --evaluator relevance --evaluator-version 0.0.1 --target qa-agent

# 5) 睇結果
agentkit eval experiment show 75901xxxxxxxxxxxxx
agentkit eval experiment results 75901xxxxxxxxxxxxx

# 6) 迭代：改 prompt / tools / model → 重新部署 → 用同一 dataset + evaluator 再跑，比分
agentkit launch
agentkit eval run --dataset qa-set --evaluator relevance --evaluator-version 0.0.1 --target qa-agent
```

### 1.9 接入 CI

Eval 命令**唔需要瀏覽器登入**，而且全部支援 `--json`，所以可以直接喺 CI pipeline 編排：

```bash
# 一個可以掉落 CI 嘅最小迴圈
EXP=$(agentkit eval run --dataset qa-set --evaluator relevance --evaluator-version 0.0.1 --target qa-agent --json | jq -r .experimentId)
agentkit eval experiment show "$EXP" --json
# 分數 < 門檻 → 停 pipeline
```

### 1.10 官方實務指引（逐條照抄）

1. **Fix the dataset**：跨迭代用**同一個** dataset，結果才可以並排比較。改 agent 之前先穩定 dataset。
2. **只保留穩定嘅 input + reference answer**：dataset 通常只需要 `input` + `reference_output`。模型實際輸出係被評 target 喺實驗期間產生，**唔應寫入 dataset**。
3. **優先由內建模板衍生 evaluator**：`evaluator template list` 提供成熟嘅評分 rubric；clone 一個再換上自己嘅 judge model，唔好由零寫。
4. **用強嘅 judge model**：`--model` 指向能力好嘅 Ark endpoint；弱 model 出嘅分數會更嘈。
5. **多 evaluator 加權**：一次 `eval run` 可以落幾個 `--evaluator`，跨維度評分（例如 relevance + completeness）。
6. **確認 target runtime 在線**：`--target` 必須指住已部署、有回應嘅 runtime，否則 case 會失敗。

> 來源：https://agentkit-f14c9eb5.mintlify.site/productions/agentkit-cli/preview/en/workflows/evaluation

---

## 2. AgentKit Studio —— 自動評測 + 數據飛輪（L3）

Studio 係 AgentKit 嘅可視化工作台（同 VeADK Frontend 共用同一套 service + UI）。佢將 eval 由「手動跑一次」變成**持續自動化**。

### 2.1 自動建立評測集（Auto-create evaluation sets）

部署設定入面有一個開關：

| 設定 | 預設 | 說明 |
|---|---|---|
| **Auto-create evaluation sets** | **Disabled** | 部署成功後，自動為 agent 建立 **Good Case** 同 **Bad Case** 兩個評測集。關閉就跳過。建立失敗只會喺部署結果顯示警告，**唔影響已部署嘅 Runtime**。 |

### 2.2 自動評分機制（源碼實證）

從 `veadk-python` 源碼可確認實際運作：

```python
# frontend/server/evaluation_automation/service.py
GOOD_SCORE_THRESHOLD = 0.6
MINIMUM_RUNNING_STATUS_SECONDS = 10.0

kind = "good" if evaluation.score >= GOOD_SCORE_THRESHOLD else "bad"
```

**自動評分嘅資料模型**（`evaluation_automation/models.py`）：

```python
EvaluationKind = Literal["good", "bad"]
AutomaticEvaluationState = Literal["pending", "running"]
OptimizationPriority = Literal["high", "medium", "low"]
OptimizationModule = Literal[
    "agent_structure", "prompt", "tool",
    "knowledge", "memory", "workflow", "other",
]

class AutoEvaluationOutput(BaseModel):
    """Strict model output for one completed conversational turn."""
    score: float = Field(ge=0, le=1)      # 0–1 分
    reason: str = Field(min_length=1, max_length=2000)
```

**每個自動評測 case 帶住嘅欄位**：

| 欄位 | 說明 |
|---|---|
| `itemKey` / `id` | case 識別 |
| `kind` | `good` 或 `bad` |
| `input` / `output` / `referenceOutput` | 輸入 / 實際輸出 / 參考輸出 |
| `comment` | 反饋註解 |
| `agentName` / `sessionId` / `messageId` / `runtimeId` / `invocationId` / `userId` | 溯源用 |
| `evaluationSetId` / `evaluationSetName` / `workspaceId` | 所屬評測集 / workspace |
| `source` | 固定 `"auto"` |
| `score` | 0–1 |
| `reason` | 評分理由 |
| `evaluatorVersion` | 用邊個 evaluator 版本 |

> **數據飛輪嘅意義**：真實用戶對話自動被評分 → ≥0.6 入 Good Case、<0.6 入 Bad Case → 呢啲 case 自動肥咗評測集 → 下一輪 eval 就有真實靶。唔使純靠人手標注。

### 2.3 優化建議（Optimization Suggestions）

自動評測唔止打分，仲會**生成優化建議**，結構化分組：

```python
class OptimizationSuggestion(BaseModel):
    suggestion: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=1, max_length=2000)

class OptimizationGroup(BaseModel):
    priority: OptimizationPriority     # high / medium / low
    module: OptimizationModule         # agent_structure / prompt / tool / knowledge /
                                       # memory / workflow / other
    custom_module: str | None          # module == "other" 時必填
    items: list[OptimizationSuggestion]  # 1–20 條

class OptimizationOutput(BaseModel):
    groups: list[OptimizationGroup]     # 最多 30 組
    # 驗證：(priority, module, custom_module) 必須唯一
```

**優化快照（Optimization Snapshot）**：

```python
class OptimizationSnapshot(BaseModel):
    runtimeId: str
    appName: str
    generatedAt: datetime
    optimizerVersion: str
    sourceItemKeys: list[str]        # 由邊啲評測 case 得出
    groups: list[OptimizationGroup]
```

**存放位置**（TOS 物件儲存）：

```
veadk-studio/v1/evaluation-optimizations/<Runtime ID>/<app name>.json
```

每個 Runtime application **只保留最新一份快照**。

> **前提**：Studio 嘅自動評測、優化快照等功能需要 **persistent object storage（TOS）**。要設定 `VEADK_STUDIO_TOS_BUCKET` 同 `VEADK_STUDIO_TOS_REGION` 兩個環境變數，否則依賴持久化嘅功能會 disable（UI 顯示「管理員未配置持久化存儲」），純文字功能不受影響。

### 2.4 Harness Sidecar 優化組件（5 個）

Studio 嘅「Custom creation」流程喺 Debug 同 Environment 之間多咗一個 **Optimization** 步驟，可以開 Harness Sidecar 優化。

> ⚠️ **Harness Sidecar 優化只支援 Volcengine 帳號**。BytePlus 帳號唔可以用優化項，要留空先可以繼續部署。普通 BytePlus agent 不受影響。

**優化場景**：

| 場景 | 幾時用 | 預設選中嘅組件 |
|---|---|---|
| **Custom** | 按需要揀組件；唔揀就唔會起 Sidecar | — |
| **Operations** | 運維診斷、數據庫、日誌、監控 MCP | Context governance、Answer verification and repair、Goal-task control、MCP-resilience governance |

> 揀 Operations 場景會**自動載入 SQL read-only 保護**。

**優化組件分類**：

| 組別 | 組件 | 作用 |
|---|---|---|
| **Improve answer quality** | Context governance | 治理 context 組裝、task anchoring、context 預算 |
| **Improve answer quality** | Answer verification and repair | 驗證證據同答案，失敗時執行修復或告警 |
| **Reduce running cost** | Context and result compression | 壓縮長 context 同大型 tool 結果，降低 token 成本 |
| **Enhance stability** | Goal-task control | 管理 Goal-task 進度、恢復、結束條件 |
| **Enhance stability** | MCP-resilience governance | 治理連接、timeout、空結果、大返回、調用預算；預設含 SQL read-only 保護 |

**Publish 時嘅 runtime 要求**：

- 揀咗 Context governance / Context and result compression / Answer verification and repair / Goal-task control 而用 Volcengine Ark model → **需要 model-gateway 設定**。Studio 會自動填入 model provider、model API base、model name；Ark API Key 由所選 API Key 注入，唔需手動輸入。
- 揀咗 MCP-resilience governance → Studio 由之前「Add MCP Tool」步驟嘅 HTTP MCP tools 自動注入 MCP 配置。至少要有一個 HTTP transport 嘅 MCP tool 配咗有效 service URL。**stdio transport 嘅 MCP tool 唔支援** MCP-resilience governance。
- 開啟後，相關增強行為會喺 managed runtime 執行並訪問 model 同 MCP gateway。

### 2.5 Migration effect evaluation（遷移效果評估）

由現有項目遷移去 AgentKit 時，可以開一個**可選**步驟：自動部署臨時 Runtime，跑評測 case，為原 agent 同遷移後 agent 之間嘅行為差異打分，產生可睇可下載嘅 **HTML 報告**。預設關閉。

**Evaluation case 結構**：

| 欄位 | 必須 | 類型 | 限制 | 說明 |
|---|---|---|---|---|
| User input | 是 | `str` | 每 case 對話文字 ≤ 32 KiB；≤ 20 條訊息 | 遷移後 agent 應該處理嘅真實用戶請求 |
| Expected outcome | 否 | `str` | ≤ 16 KiB | 描述 agent 應該達成咩；唔要求精確措辭 |
| Requirements | 否 | `list[str]` | ≤ 20 項；每項 ≤ 2 KiB | agent 輸出必須滿足嘅具體條件 |

> 正規化後嘅 dataset 總量 ≤ 10 MiB，case 數 1–100。

**評估維度**：

| 模式 | 預設維度 | 說明 |
|---|---|---|
| **Standard evaluation** | Semantic fidelity、Output contract、Workflow/tool fidelity | 適合大部分遷移；**維度不可改** |
| **Custom dimensions** | 由下面維度自選 | 按業務風險揀一或多個 |

**六個可用維度**：

| 維度 | 檢查咩 |
|---|---|
| Semantic fidelity | 意圖、結論、關鍵事實係否保持一致 |
| Output contract | 必需欄位、結構、語言、格式約束 |
| Workflow and tool fidelity | 可觀察嘅 workflow 分支同 tool-driven 行為 |
| Context and memory fidelity | 支援嘅多輪 context 同 memory 行為 |
| Boundary and error fidelity | 無效輸入、缺資料、依賴失敗 |
| Safety and refusal fidelity | 現有授權、拒絕、敏感資料邊界 |

> ⚠️ 評估方法同維度**一經上傳就唔可以改**。

**六步評估流程**：

1. **準備評估環境**：驗證遷移產物同評測 case。
2. **提供環境變數**（只在需要時）：如果遷移產物聲明必需／可選環境變數，Studio 會暫停評估並提示輸入。
3. **部署臨時 Runtime**：由遷移產物部署臨時 Runtime 執行評測 case。
4. **執行 case**：逐條 case 送去臨時 Runtime，捕捉輸出同原始 Runtime 觀察。
5. **跑評估分析**：喺單一可恢復嘅 Codex thread 入面，按維度為原 agent 同遷移後 agent 嘅行為差異打分，產生證據同 gap 描述。
6. **產生評估報告**：將逐維度分數、證據覆蓋率、執行結果匯總成 HTML 報告。

> 臨時 Runtime 喺評估完成或取消前**一定會被清理**。

**報告欄位**：

| 報告欄位 | 說明 |
|---|---|
| Overall fidelity | 0–100 分；證據不足時為 N/A |
| Evidence coverage | 有證據嘅維度 ÷ 總維度 |
| Execution success | 成功完成嘅 case ÷ 總 case |
| N/A count | 證據不足嘅維度數（唔計入分數） |
| Lowest-scoring cases | 最低分嘅 case 同差異證據 |
| Execution issues | 執行失敗嘅 case 同錯誤詳情 |
| Critical evidence | Critical severity 嘅證據條目 |
| Evaluation limitations | 影響評估結論嘅已知限制 |

**評分／捨入規則（確定性）**：

> 每個原始維度分數先 **round half up** 成 0–100 整數，再聚合。Case 分數同維度平均由呢啲整數計算，總分係**已捨入維度平均嘅平均**。每個平均都 round half up 並排除 N/A 值，確保各層分數同報告驗證、最低分 case 排名一致。

**報告唔會出 pass/fail 判定**——只呈現量化分數同差異證據。

**評估狀態全集**：Evaluation is off → Waiting for evaluation cases → Evaluation starts automatically after migration → Preparing the evaluation environment → Runtime environment variables are required → Deploying a temporary Runtime → Running evaluation cases → Running evaluation analysis → Aggregating evaluation results → Evaluation completed → Evaluation incomplete → Evaluation requires attention → Evaluation cancelled

> 開評估會將 Dev Sandbox Session TTL 由 1 小時延長到 2 小時。失敗可以重試，重試會**重用同一個鎖定嘅 dataset 同維度配置**，重新部署臨時 Runtime 再執行。
>
> 來源：https://agentkit-f14c9eb5.mintlify.site/productions/veadk/preview/en/components/frontend/studio

---

## 3. VeADK —— 框架層評估框架（L2）

VeADK 建基於 **Google ADK**，所以 eval 能力係「ADK 嘅軌跡評估 + DeepEval 嘅輸出質量評估」兩條腿。

### 3.1 三種評估方式

| 方式 | 命令／工具 | 適合 |
|---|---|---|
| **Web UI** | `veadk web` | 互動式評估、邊傾邊睇、生成 eval case |
| **CLI** | `veadk eval` | 對住已有 evalset file 快速跑，唔開 GUI |
| **Programmatic** | `pytest` | 整合入現有測試 / CI pipeline |

### 3.2 評估嘅兩個部分（核心觀念）

> LLM agent 有**概率性**，傳統嘅 deterministic "pass/fail" assertion 唔夠用。取而代之要**定性評估**兩樣嘢：

1. **評估軌跡同工具使用（trajectory & tool usage）**：分析 agent 達成解答嘅步驟——工具選擇、策略、效率。
2. **評估最終回應（final response）**：評估最終輸出嘅質量、相關性、正確性。

```
Evaluation Input          Agent Execution        Agent Output           Assessment
┌────────────────┐        ┌─────────┐      ┌──────────────────┐    ┌───────────┐
│  Eval Case     │─User──▶│         │─────▶│ Actual Trajectory│───▶│           │
│  - User Input  │  Input │  Agent  │      ├──────────────────┤    │ Evaluator │──▶ Result
│  - Expected    │        │         │─────▶│ Final Response   │───▶│           │
│    Trajectory  │────────┼─────────┼──────┴──────────────────┴────┘           │
└────────────────┘ Expected Trajectory                                        ┘
```

### 3.3 Evalset（評測集）—— Google ADK 格式

**兩種產生方式**：

**(a) 用 `veadk web` 互動生成**：

```bash
veadk web
```

流程：揀 agent → 傾偈建立 session → 右邊揀 `Eval` tab → 建立／揀 evalset → 撳 `Add current session` → 當前 session（你嘅輸入 + agent 回覆 + 中間步驟）存為新 eval case → evalset file（如 `simple.evalset.json`）自動喺 agent 所在目錄建立／更新。

**(b) 程式化 export**：

```python
import asyncio
import uuid
from veadk import Agent, Runner
from veadk.memory.short_term_memory import ShortTermMemory
from veadk.tools.demo_tools import get_city_weather

agent = Agent(tools=[get_city_weather])
session_id = "session_id_" + uuid.uuid4().hex
runner = Runner(agent=agent, short_term_memory=ShortTermMemory())
prompt = "How is the weather like in Beijing? Besides, tell me which tool you invoked."
asyncio.run(runner.run(messages=prompt, session_id=session_id))
# Collect runtime data
dump_path = asyncio.run(runner.save_eval_set(session_id=session_id))
print(f"Evaluation file path: {dump_path}")
```

**Evalset 格式**：

```json
{
  "eval_set_id": "simple",
  "name": "simple",
  "description": null,
  "eval_cases": [
    {
      "eval_id": "product-price",
      "conversation": [
        {
          "invocation_id": "e-f25f5edb-f75b-4aa6-ab9b-657c4b436a12",
          "user_content": {
            "parts": [{ "text": "Price" }],
            "role": "user"
          },
          "final_response": {
            "parts": [{ "text": "According to our knowledge base, ..." }]
          },
          "intermediate_data": {
            "tool_uses": [
              {
                "id": "call_u6mzq918tz8nbxfp3lehhtme",
                "args": { "question": "Price" },
                "name": "knowledge_base"
              }
            ]
          }
        }
      ]
    }
  ]
}
```

| 欄位 | 說明 |
|---|---|
| `eval_set_id` | evalset 唯一標識 |
| `name` / `description` | 名稱 / 描述 |
| `eval_cases[]` | 多個 eval case |
| `eval_cases[].eval_id` | eval case 唯一標識 |
| `eval_cases[].conversation[]` | 對話歷史 |
| `conversation[].user_content` | 用戶輸入 |
| `conversation[].final_response` | agent 最終回覆 |
| `conversation[].intermediate_data` | agent 產生最終回覆嘅中間步驟（如 tool calls）。**評估時 ADK 會拿呢個同你定義嘅 expected trajectory 比對** |

### 3.4 軌跡評估方法（ADK ground-truth based）

| 方法 | 要求 |
|---|---|
| **Exact match** | 必須同理想軌跡完全一致 |
| **In-order match** | 正確動作要按正確次序執行，但**允許額外動作** |
| **Any-order match** | 正確動作可以任意次序，亦允許額外動作 |
| **Precision** | 衡量預測動作嘅相關性／正確性 |
| **Recall** | 衡量預測捕捉到幾多必要動作 |
| **Single-tool use** | 檢查有冇包含某個特定動作 |

### 3.5 兩種 Evaluator

VeADK 目前支援兩個 evaluator：**DeepEval** 同 **ADKEval**。

#### (a) Google ADK Evaluator（`ADKEvaluator`）

**建議場景**：
- 你嘅系統係 agent（或多 agent）系統：用戶問題可能觸發多個 tool call 同子步驟，agent 要決策、切換工具、執行任務再輸出。
- 你唔止想追「最終答案」，仲想追「中間 tool calls」、「agent 用咗邊啲 sub-agent」、「執行軌跡符唔符預期」。例如：任務規劃、執行、反饋迴圈、業務流程自動化。

```python
from veadk.evaluation.adk_evaluator import ADKEvaluator
import pytest
from ecommerce_agent.agent import root_agent

class TestAgentEvaluation:

    @pytest.mark.asyncio
    async def test_simple_evalset_with_adkevaluator(self):
        """Agent evaluation tests using ADKEvaluator"""
        evaluator = ADKEvaluator(agent=root_agent)
        await evaluator.evaluate(
            eval_set_file_path="tests/simple.evalset.json",
            response_match_score_threshold=1,
            tool_score_threshold=0.5,
            num_runs=1,
            print_detailed_results=True
        )
```

#### (b) DeepEval Evaluator（`DeepevalEvaluator`）

**建議場景**：
- 你嘅系統主要係「LLM → output」型，例如：用戶問 → 模型答；或 RAG 系統，強調答案嘅相關性、事實正確性、連貫性、可解釋性，較少依賴 tool call 或複雜軌跡，你想專注監控「生成質量」。
- 你想引入更豐富嘅 metric（hallucination detection、contextual recall/precision、answer relevancy 等），並想將評估當 unit test 咁跑喺 CI/CD。

```python
from veadk.evaluation.deepeval_evaluator import DeepevalEvaluator
from veadk.prompts.prompt_evaluator import eval_principle_prompt
from deepeval.metrics import GEval, ToolCorrectnessMetric
from deepeval.test_case import LLMTestCaseParams
import pytest
from ecommerce_agent.agent import root_agent

class TestAgentEvaluation:
    @pytest.mark.asyncio
    async def test_simple_evalset_with_deepevalevaluator(self):
        """Agent evaluation tests using DeepevalEvaluator"""
        evaluator = DeepevalEvaluator(agent=root_agent)
        metrics = [
            GEval(
                threshold=0.8,
                name="Base Evaluation",
                criteria=eval_principle_prompt,
                evaluation_params=[
                    LLMTestCaseParams.INPUT,
                    LLMTestCaseParams.ACTUAL_OUTPUT,
                    LLMTestCaseParams.EXPECTED_OUTPUT,
                ],
                model=evaluator.judge_model,
            ),
            ToolCorrectnessMetric(threshold=0.5, model=evaluator.judge_model),
        ]
        await evaluator.evaluate(
            eval_set_file_path="tests/simple.evalset.json",
            metrics=metrics)
```

**`veadk-python[eval]` 實際包含咩（源碼實證，`pyproject.toml`）**：

```toml
eval = [
    "prometheus-client>=0.22.1",    # For exporting data to Prometheus pushgateway
    "deepeval>=3.2.6",              # For DeepEval-based evaluation
    "google-adk[eval]>=1.34.0",     # For Google ADK-based evaluation
]
```

```bash
pip install "veadk-python[eval]"
```

#### (c) 自訂 Evaluator（`BaseEvaluator`）

當內建兩個 evaluator 唔夠用，繼承 `veadk.evaluation.base_evaluator.BaseEvaluator` 自己寫。

**核心場景**：
1. **整合內部評測服務**：接你公司自己嘅評分 API。
2. **驗證外部系統狀態**：檢查數據庫、API、硬件狀態有冇被正確改動（例如電商下單、IoT 裝置控制）。
3. **評估非文字輸出**：compile、run、驗證生成嘅 code、圖片、配置文件。
4. **實作特殊 metric**：計成本、測安全、檢查多輪對話一致性。

**核心步驟**：
1. 定義 evaluator class，繼承 `BaseEvaluator`。
2. 實作 `evaluate` method：`self.build_eval_set()` 載入測試 case → `await self.generate_actual_outputs()` 跑 agent 取實際輸出 → 實作自訂評分邏輯，結果存入 `self.result_list`。

```python
from typing import Optional
from google.adk.evaluation.eval_set import EvalSet
from typing_extensions import override
from veadk.evaluation.base_evaluator import BaseEvaluator, EvalResultData, MetricResult

class MyCustomEvaluator(BaseEvaluator):
    @override
    async def evaluate(
        self,
        eval_set: Optional[EvalSet] = None,
        eval_set_file_path: Optional[str] = None,
    ):
        # Step 1: Load the test cases
        self.build_eval_set(eval_set, eval_set_file_path)

        # Step 2: Run the agent to obtain the actual outputs
        await self.generate_actual_outputs()

        # Step 3: Implement your scoring logic
        for eval_case_data in self.invocation_list:
            score = 1.0 if eval_case_data.invocations[0].actual_output == eval_case_data.invocations[0].expected_output else 0.0
            metric_result = MetricResult(
                metric_type="ExactMatch",
                success=score == 1.0,
                score=score,
                reason=f"Outputs {'matched' if score == 1.0 else 'did not match'}.",
            )
            eval_result_data = EvalResultData(metric_results=[metric_result])
            eval_result_data.call_before_append()
            self.result_list.append(eval_result_data)

        return self.result_list
```

> 來源：https://github.com/volcengine/veadk-python/blob/main/docs/content/docs/framework/evaluation.en.mdx

### 3.6 `veadk eval` CLI 完整參考

**兩種評估模式**：

| 模式 | 說明 |
|---|---|
| **Local** | 由本地源碼載入 agent 評估 |
| **Remote** | 連去以 A2A 模式部署嘅 agent（經 URL）評估 |

**兩個評估框架**：

| 框架 | 說明 |
|---|---|
| **`adk`** | Google ADK 評估框架，標準化 metric |
| **`deepeval`** | 更進階框架，可自訂 metric，包括 GEval 同 tool-use correctness |

**Flag 表**：

| Flag | 類型 | 說明 |
|---|---|---|
| `--agent-dir` | TEXT | （Local）要評估嘅 agent 本地目錄；必須含 `agent.py` 並 export `root_agent`。預設 `.` |
| `--agent-a2a-url` | TEXT | （Remote）已部署 A2A 模式 agent 嘅完整 URL |
| `--evalset-file` | TEXT | **（Required）** Google ADK 格式 evalset file 路徑 |
| `--evaluator` | `[adk\|deepeval]` | **（Required）** 用邊個評估框架 |
| `--judge-model-name` | TEXT | Judge model 名。預設 `doubao-1-5-pro-256k-250115`。**`adk` evaluator 下忽略** |
| `--volcengine-access-key` | TEXT | Volcengine AK（模型認證用） |
| `--volcengine-secret-key` | TEXT | Volcengine SK（模型認證用） |

> - 必須提供 `--agent-dir` 或 `--agent-a2a-url` 其中一個；兩個都畀就 **`--agent-a2a-url` 優先**。
> - evalset file 必須係 Google ADK 格式。

```bash
# Local evaluation
veadk eval \
  --agent-dir ./my-agent \
  --evalset-file ./eval.json \
  --evaluator adk

# Remote evaluation
veadk eval \
  --agent-a2a-url http://my-agent-url.com/invoke \
  --evalset-file ./eval.json \
  --evaluator deepeval \
  --volcengine-access-key "YOUR_AK" \
  --volcengine-secret-key "YOUR_SK"
```

### 3.7 `veadk uploadevalset` —— 上傳到 CozeLoop

**點解要上 CozeLoop？** CozeLoop 係一個提供 observability、分析、監控嘅 LLM 應用平台。上傳後得到：

- **集中管理**：統一平台儲存、管理、追蹤所有評測數據同歷史，方便團隊協作同版本控制。
- **可視化分析**：豐富嘅可視化工具，更直觀分析 agent 行為、比較唔同版本嘅效能差異。
- **深入洞察**：透過分析評測數據，深入理解 agent 嘅 tool-call 軌跡、回應質量、潛在問題，從而得出優化方向。
- **持續監控**：將評估結合 CI，實現自動化監控同 regression testing。

```bash
veadk uploadevalset --file tests/simple.evalset.json
```

**Flag 表**：

| Flag | 說明 |
|---|---|
| `--file` | **（Required）** 含 dataset entries 嘅 JSON file 路徑 |
| `--cozeloop-workspace-id` | CozeLoop workspace ID。fallback 到 `OBSERVABILITY_OPENTELEMETRY_COZELOOP_SERVICE_NAME` |
| `--cozeloop-evalset-id` | CozeLoop eval set ID。fallback 到 `OBSERVABILITY_OPENTELEMETRY_COZELOOP_EVALSET_ID` |
| `--cozeloop-api-key` | CozeLoop API key。fallback 到 `OBSERVABILITY_OPENTELEMETRY_COZELOOP_API_KEY` |

```bash
veadk uploadevalset \
  --file ./my_eval_set.json \
  --cozeloop-workspace-id "YOUR_WORKSPACE_ID" \
  --cozeloop-evalset-id "YOUR_EVALSET_ID" \
  --cozeloop-api-key "YOUR_API_KEY"
```

> 此命令會將 Google ADK 格式嘅測試 case **轉換成 CozeLoop 期望嘅格式**再上傳。
>
> 來源：https://github.com/volcengine/veadk-python/blob/main/docs/content/docs/cli/veadk-cli.en.mdx

---

## 4. ModelArk —— 模型層評測系統（L1）

### 4.1 評測系統定位

ModelArk 匯集主流基礎模型，亦容許你基於呢啲模型訓練更貼合場景嘅精調模型。為咗幫你快速揀合適模型、或準確評估精調模型喺你自己數據上嘅效果，ModelArk 設計咗一套評測系統，全方位量化模型嘅能力維度。

**三個特性**：

| 特性 | 說明 |
|---|---|
| **Convenience** | 以自動測試為主導，方便快速評測模型同睇結果 |
| **Authority** | 整合業界高度認可嘅**公開數據集**，可同唔同主流模型比較；另外輔以 ModelArk 累積嘅**非公開數據集**，減少全公開數據對排名嘅潛在影響，令結果更可靠 |
| **Flexibility** | 按唔同能力維度評測，可按需揀模型，產生符合場景要求嘅結果 |

### 4.2 評測維度

| 類型 | 說明 |
|---|---|
| **Comprehensive evaluation** | 橫向跨學科、跨能力評測，快速衡量模型有冇廣泛知識同解難能力 |
| **Basic capability evaluation** | 針對特定能力評測，衡量模型喺某場景有冇突出能力。三個子維度： |
| ├─ **Language writing** | 理解同生成文字嘅能力，對應人類讀寫能力 |
| ├─ **Inference and mathematics** | 邏輯推理、數學計算、複雜規則學習能力 |
| └─ **Knowledge capability** | 各領域知識嘅記憶同理解（常識、生活知識、社會文化知識） |

> 其他能力維度會陸續推出。

### 4.3 評測數據（預設數據集）

| 評測類型 | 能力 | 評測數據 |
|---|---|---|
| **Preset dataset-based evaluation** | Comprehensive capability | **MMLU**：業界最常用嘅綜合數據集，由各學科選擇題組成，涵蓋人文、社會科學、自然科學等領域。含 **57 個任務**，包括初等數學、歷史、電腦科學、法律等。要高分，模型必須有廣泛知識同解難能力 |
| | Basic capability → Language writing | **College entrance examination (Chinese language)**：中國最具權威性同綜合性嘅標準化考試之一。含 2010–2022 年語文試題共 **246 題** |
| | Basic capability → Language writing | **College entrance examination (English language)**：⋯ |

### 4.4 四種評分方法（關鍵）

| 評分方法 | 適用題型 | 例子 |
|---|---|---|
| **Prefix match**（前綴匹配） | 要求模型提供同標準答案一樣嘅答案。模型可以輸出額外補充資訊，唔影響評分判定 | 問首都在哪，標準答案北京。答「北京」或句子以「北京」開頭（如「北京是古城」）→ 100 分。答案唔以「北京」開頭 → 0 分 |
| **Keyword inclusion**（關鍵詞包含） | 要求答案包含特定關鍵詞或資訊，唔需要精確匹配標準答案 | 問首都在哪，標準答案北京。答「北京」或「首都是北京」→ 100 分。答案唔含「北京」→ 0 分 |
| **Referee scoring**（裁判評分 = LLM-as-judge） | 開放式問題或複雜對話場景 | 採用**用戶自訂評分準則**。如果冇定義準則，平台採用**預設評分準則** |
| **Inference only**（只推理） | — | 只基於評測數據集完成推理。提交嘅任務記錄模型產生嘅答案，但**唔做分數統計**。你可以按模型答案靈活計算相關評測指標 |

**另外兩個配置項**：
- **評測任務類型**：按實際業務場景揀**單輪**或**多輪**。
- **數據集來源**：預設評測數據集 **或** 自訂評測數據集（上傳 dataset 或由 TOS 導入）。

### 4.5 評測數據集格式

支援 **`.jsonl`、`.xlsx`、`.xls`**，每行一個評測樣本。
**每次評測最多上傳 10 個檔案，每個檔案最多 1,000 行樣本。**

**單輪對話 — JSONL 輸入參數**：

| 參數 | 類型 | 必須 | 說明 |
|---|---|---|---|
| `prompt` | str | 是 | 作為問題輸入模型嘅指令 |
| `answer` | str | 否。如果評測方法揀「Inference + automatic evaluation」就必須 | 參考答案，用嚟驗證模型產生嘅答案 |
| `system` | str | 否 | 角色介紹嘅輸入指令 |
| `parameters` | dict | 否 | 請求參數。支援 `logprobs`、`top_logprobs`、`frequency_penalty`、`temperature`、`top_p`、`max_tokens`、`stop` |

**輸出參數**：

| 參數 | 類型 | 說明 |
|---|---|---|
| `response` | str | 模型產生嘅答案 |
| `usage` | dict | token 用量資訊 |
| `error` | str | 如果因為數據或平台問題導致推理失敗，顯示錯誤訊息 |

**範例**：

```jsonl
{"system":"Please complete the following calculation question","prompt":"0+0","parameters":{"top_k":1},"answer":"0"}
{"system":"Please complete the following calculation question","prompt":"0+1","parameters":{"top_k":1},"answer":"1"}
{"system":"Please complete the following calculation question","prompt":"0+2","parameters":{"top_k":1},"answer":"2"}
```

### 4.6 建立評測任務

**三個入口**：
1. 登入 ModelArk → 左側導航揀 **Evaluation task**。
2. **Model repository** → 揀要評嘅模型 → 底部撳 **Initiate evaluation**。
3. **Model fine-tuning** → 揀要評嘅模型 → Actions 欄撳 **Initiate evaluation**。

**前提**：模型廣場嘅主流 LLM，以及模型倉庫中儲存嘅精調模型，都可以直接揀嚟評測，唔需額外配置。

### 4.7 睇評測報告

- **Task details tab**：顯示任務基本資訊同能力維度。
- **Evaluation report tab**：睇當前模型喺所選能力維度嘅**綜合分數**同**個別分數**。每個維度可以逐個 dataset 睇分。
- **Model evaluation result comparison（樣本分析）**：可以按**評測能力**同**dataset** 睇某個評測任務嘅題目、答案、模型答案，並排比較。

> 來源：https://docs.byteplus.com/en/docs/ModelArk/1150779（Model evaluation system）
> https://docs.byteplus.com/en/docs/ModelArk/1150782（Creating model evaluation task）
> https://docs.byteplus.com/en/docs/ModelArk/1150783（Viewing Evaluation Report）
> https://docs.byteplus.com/en/docs/ModelArk/1150781（Evaluation dataset format description）

---

# 第二部分：Optimization（優化）

## 5. VeADK —— 框架層優化武器（L2）

VeADK 提供三類持續優化能力：**prompt tuning**、**reinforcement learning**、**agent self-reflection**。

### 5.1 Prompt Optimization（PromptPilot）

Prompt 係大模型嘅核心輸入指令，直接影響理解準確度同輸出質量。**PromptPilot** 提供全流程智能優化，涵蓋 generation、tuning、evaluation、management 各階段。

```bash
veadk prompt
```

**選項**：

| Flag | 說明 |
|---|---|
| `--path` | 要優化嘅 agent file 路徑。預設當前目錄 `agent.py`。**注意：定義嘅 agent 必須 export 成 global variable** |
| `--feedback` | prompt 優化建議，用嚟引導優化方向 |
| `--api-key` | PromptPilot 平台 API key |
| `--workspace-id` | PromptPilot workspace ID（**required**） |
| `--model-name` | 優化用嘅模型名 |

```bash
veadk prompt --path ./weather_reporter/agent.py \
  --feedback "希望提示詞能夠更加具體明確" \
  --api-key "YOUR_API_KEY" \
  --workspace-id "YOUR_WORKSPACE_ID"
```

### 5.2 Reinforcement Learning（RL）

**點解要 RL？** 喺效果同泛化要求高嘅複雜業務場景，RL 嘅上限高過 PE、SFT、DPO，而且更貼合核心業務需求：

- 基於**反饋迭代**嘅訓練模式，更好激發模型嘅推理同泛化能力；
- **唔需要大量標注數據**，成本更低、實作更簡單；
- 支援基於**業務指標反饋**評分優化，直接驅動指標提升。

VeADK 內建兩個 RL 方案：**Ark Platform RL** 同 **Agent Lightning**。

#### (a) Ark Platform Reinforcement Learning

Ark RL 將 RL 流程封裝，降低複雜度。用戶主要關注三件事：**rollout 入面嘅 agent 邏輯**、**reward function 嘅構建**、**訓練樣本嘅選擇**。

VeADK 整合 Ark 平台嘅 Agent RL。用 VeADK 提供嘅 scaffolding，你可以開發一個 VeADK agent，然後提交 job 去 Ark 平台做 RL 優化。

```bash
# 初始化 RL 項目
veadk rl init --platform ark --workspace veadk_rl_ark_project

# 提交 job
cd veadk_rl_ark_project
veadk rl submit --platform ark
```

**生成嘅項目結構**：

```
veadk_rl_ark_project/
├── data/
│   └── *.jsonl                          # Dataset
├── plugins/
│   ├── config.yaml.example
│   ├── random_reward.py                 # reward 範例
│   ├── raw_async_veadk_rollout.py       # 用 veadk agent 嘅 rollout 範例
│   └── weather_rollout.py
├── job.py                               # 訓練參數 + 指定 rollout / reward
├── job.yaml
└── test_agent.py
```

**核心檔案**：
- **Dataset**：`data/*.jsonl`
- **`/plugins` 下嘅 rollout 同 reward**：
  - **rollout**：定義 agent 嘅 workflow。`raw_async_veadk_rollout.py` 提供喺 Ark RL 用 veadk agent 嘅範例。
  - **reward**：提供 RL 需要嘅 reward value。範例喺 `random_reward.py`。
- **`job.py` 或 `job.yaml`**：配置訓練參數，指定用邊個 rollout 同 reward。

#### (b) Agent Lightning

Agent Lightning 提供靈活可擴展嘅框架，**完全解耦 agent（client）同 training（server）**。

```bash
# 初始化
veadk rl init --platform lightning --workspace veadk_rl_lightning_project
```

```bash
# Terminal 1 — 啟動 client
cd veadk_rl_lightning_project
python veadk_agent.py

# Terminal 2 — 重啟 ray cluster
cd veadk_rl_lightning_project
bash restart_ray.sh

# Terminal 2 — 啟動 server
cd veadk_rl_lightning_project
bash train.sh
```

**生成嘅項目結構**：

```
veadk_rl_lightning_project/
├── data/
│   ├── demo_train.parquet
│   └── demo_test.parquet
├── demo_calculate_agent.py     # agent rollout 邏輯 + reward 規則
├── train.sh                    # 訓練參數 + 啟動訓練 server
└── restart_ray.sh
```

**核心檔案**：
- **agent_client**：`*_agent.py` 定義 agent 嘅 rollout 邏輯同 reward 規則。
- **training_server**：`train.sh` 定義訓練相關參數，用嚟啟動訓練 server。

### 5.3 Agent Self-Reflection（自反思）

VeADK 支援基於 **tracing file data** 嘅自反思——用第三方 agent 嘅推理，生成優化後嘅 system prompt。

```python
import asyncio

from veadk import Agent, Runner
from veadk.reflector.local_reflector import LocalReflector
from veadk.tracing.telemetry.opentelemetry_tracer import OpentelemetryTracer

agent = Agent(tracers=[OpentelemetryTracer()])
reflector = LocalReflector(agent=agent)

app_name = "app"
user_id = "user"
session_id = "session"


async def main():
    runner = Runner(agent=agent, app_name=app_name)

    await runner.run(
        messages="你好，我觉得你的回答不够礼貌",
        user_id=user_id,
        session_id=session_id,
    )

    trace_file = runner.save_tracing_file(session_id=session_id)

    response = await reflector.reflect(
        trace_file=trace_file
    )
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
```

**輸出兩部分**：

| 欄位 | 說明 |
|---|---|
| `optimized_prompt` | 優化後嘅 system prompt |
| `reason` | 優化嘅理由 |

**實例（官方範例）**：

原始 prompt：
```text
You an AI agent created by the VeADK team.

You excel at the following tasks:
1. Data science
- Information gathering and fact-checking
- Data processing and analysis
2. Documentation
- Writing multi-chapter articles and in-depth research reports
3. Coding & Programming
- Creating websites, applications, and tools
- Solve problems and bugs in code (e.g., Python, JavaScript, SQL, ...)
- If necessary, using programming to solve various problems beyond development
4. If user gives you tools, finish various tasks that can be accomplished using tools and available resources
```

優化後：
```text
optimized_prompt='You are an AI agent created by the VeADK team. Your core mission is to assist users with expertise in data science, documentation, and coding, while maintaining a warm, respectful, and engaging communication style.\n\nYou excel at the following tasks:\n1. Data science\n- Information gathering and fact-checking\n- Data processing and analysis\n2. Documentation\n- Writing multi-chapter articles and in-depth research reports\n3. Coding & Programming\n- Creating websites, applications, and tools\n- Solving problems and bugs in code (e.g., Python, JavaScript, SQL, ...)\n- Using programming to solve various problems beyond development\n4. Tool usage\n- Effectively using provided tools and available resources to accomplish tasks\n\nCommunication Guidelines:\n- Always use polite and warm language (e.g., appropriate honorifics, friendly tone)\n- Show appreciation for user feedback and suggestions\n- Proactively confirm user needs and preferences\n- Maintain a helpful and encouraging attitude throughout interactions\n\nYour responses should be both technically accurate and conversationally pleasant, ensuring users feel valued and supported.'

reason="The trace shows a user complaint about the agent's lack of politeness in responses. The agent's current system prompt focuses exclusively on technical capabilities without addressing communication style. The optimized prompt adds explicit communication guidelines to ensure the agent maintains a warm, respectful tone while preserving all technical capabilities. This addresses the user's feedback directly while maintaining the agent's core functionality."
```

> **注意呢個閉環**：tracing file（觀察）→ reflector（分析）→ optimized prompt（優化）。呢個就係「observability 係 optimization 嘅輸入」嘅最佳示範。
>
> 來源：https://github.com/volcengine/veadk-python/blob/main/docs/content/docs/framework/optimization.en.mdx

---

## 6. ModelArk —— 模型層優化：精調（L1）

### 6.1 核心觀念：框架層冇微調 API

> **VeADK / AgentKit 本身冇任何微調 API。** 精調係**火山方舟「模型精調」功能**嘅產物（模型層），VeADK / AgentKit 只係透過 `model_name` + endpoint 將佢「消費」返嚟。

| 層 | 做咩 |
|---|---|
| **底層（火山方舟模型平台）** | 訓練 LoRA、建任務、出模型、做推理渠道 —— **呢度先有「精調」** |
| **框架層（VeADK / AgentKit）** | 掛 `model_name` 用精調後嘅模型；本身免費、冇微調概念 |

### 6.2 精調方法矩陣

| 精調方法 | 支援 LoRA | 支援全量 | 一句說明 |
|---|---|---|---|
| **SFT**（有監督微調） | ✅ | ✅ | 最常用；用「問題→答案」配對教風格／格式／領域知識 |
| **DPO**（人類偏好對齊） | ✅ | ✅ | 用「偏好」數據（好／壞回答）教模型揀更好輸出 |
| **GRPO**（強化學習） | ✅ **只 LoRA** | ❌ | 用規則計算回報，優化推理、指令跟隨 |
| **CPT**（領域繼續預訓練） | — | 屬其他渠道 | 大規模領域文本 |

### 6.3 六種「改模型」方法對比

| 方法 | 更新幾多參數 | 數據類型 | 效果 | 成本 |
|---|---|---|---|---|
| **LoRA** | <1%（低秩旁路） | 指令→回應配對 | ~98% of 全量 | 低 |
| **QLoRA** | <1%（4-bit 基模） | 同 LoRA | ≈ LoRA | 更低 |
| **全參數 SFT** | 100% | 指令→回應配對 | 基準 100% | 高 |
| **DPO** | LoRA 或全量 | 偏好（好／壞回答） | 偏好對齊 | 中 |
| **GRPO / RL** | LoRA only | Rule-based reward | 推理提升 | 高 |
| **Distillation** | 取決於目標模型 | 大 model 輸出 | 細 model ≈ 大 model | 高（數據工程） |

### 6.4 精調後嘅三種推理渠道 + 價格

精調完成唔等於用得——仲要揀「推理渠道」，**價格同計費方式差好遠**：

| 推理渠道 | 點計 | 適合 | 是否要「壓縮」產物 |
|---|---|---|---|
| **在線推理（模型單元）** | 包虛擬資源時長 | 穩定高用量、SLA 要求高 | ✅ 要（LoRA 產物需壓縮後先買到模型單元） |
| **按 token 後付費** | 精調後模型 ≈ **2–2.5×** 同參數基礎模型價格 | 用量波動、起步期 | ❌ 唔使壓縮（部分模型支援） |
| **批量推理** | 夜間離線跑，最平 | 離線大批量任務 | ✅ 要 |

**LoRA 精調後按 token 付費嘅參考倍率**：

| 基模 | 精調後按 token |
|---|---|
| `doubao-seed-2.0-mini` | 同窗口基礎模型 **2 倍** |
| `doubao-1.5` 系列 | 同窗口基礎模型 **2.5 倍** |

### 6.5 框架層接入精調模型

**VeADK `Agent.model_name` 直接指**：

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

> `model_name` 都接受 **list**（主模 + 回退）：主模唔可用時自動轉後備（如 `deepseek-r1-250528`），提高可用性。

**環境變數（Deploy 時用）**：

```bash
export MODEL_AGENT_NAME="ep-2026080100000-lora"
export MODEL_AGENT_API_KEY="sk-..."
export MODEL_AGENT_API_BASE="https://ark.cn-beijing.volces.com/api/v3"
```

**Zero-code Harness**：

```yaml
harness:
  harness_name: my-lora-faq
  cloud: volt
  model: ep-2026080100000-lora        # 精調後推理 endpoint 名
  tools:
    - web_search
  system_prompt: "你係公司客服，按 FAQ 知識庫回答。"
```

### 6.6 優化武器全圖（由零成本到高成本）

| 武器 | 類型 | 改啲咩 | 成本 | 幾時用 |
|---|---|---|---|---|
| **prompt / instruction 優化** | Prompt 層 | 語氣、格式、風格、少量規則 | 零 | 先做，八成場景夠用 |
| **output_schema / structured output** | Prompt 層 | 強制 JSON schema、欄位抽取 | 零 | 要穩定結構化輸出 |
| **compaction / context 管理** | Prompt 層 | 縮 context、排位、截斷策略 | 零 | Context 滿、成本壓力大 |
| **fallback model routing** | 架構層 | 主模掛時自動轉後備模型 | 零 | 提高可用性、壓成本 |
| **揀細 model** | 模型選擇 | 揀更平更細嘅基模 | 零／負 | 效果夠就揀細 |
| **LoRA** | 精調 | 領域知識 + 專用術語 + 穩定格式 | 低 | 大多數 vertical 場景 |
| **QLoRA** | 精調 | 同 LoRA，但 4-bit 量化基模 | 低（更低顯存） | 單卡／資源有限 |
| **全參數 SFT** | 精調 | 整個 domain 改寫、極限效果 | 高 | 數據極多、最後先用 |
| **DPO** | 精調（偏好） | 對齊偏好（好／壞回答揀優） | 中 | 要偏好對齊 |
| **RLHF / GRPO** | 精調（強化） | 推理能力、指令跟隨 | 高 | 要唔靠 prompt 嘅推理提升 |
| **Distillation** | 精調 | 大 model 輸出教細 model | 高（數據工程） | 細 model 做大 model 效果 |

**決策樹**：

```
想改 agent 行為？
├─ 只改語氣/格式/風格
│   └─ ➜ 改 system prompt（Agent.instruction）—— 零成本，先做
├─ 要結構化輸出（JSON schema、欄位抽取）
│   └─ ➜ 用 output_schema（Responses API）
├─ 要慳錢慳 context
│   └─ ➜ compaction / prompt 排位 / fallback list
├─ 領域知識 + 專用術語 + 穩定格式（仲係唔夠準）
│   └─ ➜ 先試 seed-2.0-mini LoRA（平、按 token、唔使壓縮）
├─ 要對齊偏好（好/壞回答揀優）
│   └─ ➜ DPO（LoRA）
├─ 要唔靠 prompt 嘅推理能力提升
│   └─ ➜ GRPO / RL（veRL + TrainingKit）
├─ 要細 model 做到大 model 效果、成本壓到最低
│   └─ ➜ Distillation（蒸餾：大 model 輸出 → SFT 經細 model）
└─ 真係改寫成個 domain
    └─ ➜ 全量 SFT + 在線推理（成本最高，最後先用）
```

> 來源：https://www.volcengine.com/docs/82379/1099459（模型精調概述）

---

## 7. 框架層效能優化武器（VeADK + AgentKit）

### 7.1 優化順序（由零成本排到貴）

1. **Context 工廠**：轉 RAG（唔好全文件塞）+ 睇緩存命中率 —— **零 code**。
2. **縮 prompt**：instruction 精簡、tool return 抽 key —— 少 code、冇 infra 影響。
3. **加壓縮**：`EventsCompactionConfig` + mini summarizer —— 少 code。
4. **調 Runtime**：`agentkit runtime update` CPU / mem / concurrency —— 有雲費，唔好隨便。
5. **拆 Agent + 並行**：A2A + `asyncio.gather` —— 工程量較大。
6. **評估守住**：任何改動過 `agentkit eval run` 先放心。

### 7.2 Context 緩存（Responses API）

方舟嘅 **Responses API context cache** 係最直接嘅 token 殺手。核心係**睇命中率**，同埋 **prompt 排位規則**（穩定嘅內容放前面，易變嘅放後面）。

### 7.3 Context 壓縮（Compaction）

```python
EventsCompactionConfig(compaction_interval=10)   # 每 10 輪先做一次 summary
```

對比「每輪 full summary」，summary call 可以慳約 **10×**。

### 7.4 Runtime 資源調優（唔使 re-build）

```bash
# 提高單實例資源
agentkit runtime update my-agent \
  --cpu-milli 2000 \
  --memory-mb 4096 \
  --max-concurrency 40 \
  --auto-release

# 或者加實例數（多實例要配持久化 DB）
agentkit runtime update my-agent --max-instance 5 --auto-release

# 開 APMPlus 監控
agentkit runtime update my-agent --apmplus --auto-release
```

> `--max-concurrency` 每 instance 預設 **20**。
> ⚠️ concurrency 升得快 = 同時間多 request = **唔一定慳**；跑得順但 cost 爆就應該返去搞 context，唔係一味加機。

### 7.5 並行 / 異步

- **多 Agent A2A**：用 A2A registry 做 parallel tool calls / 多個 downstream Agent 一齊跑。
- **`runner.run` 異步**：`asyncio.gather` 多 batch，唔好 for-loop 排住隊。
- **eval 並行**：`agentkit eval run --concurrency 10`（預設 5）縮短 CI turnaround。

### 7.6 五類 Cache 管理

| 類型 | 層 | 誰控制 |
|---|---|---|
| Token / Response cache | 框架層 | **直接控制**（`usage_metadata`、命中率 50–95%） |
| Input / Prefix cache | 引擎層 | 間接控制（RadixAttention / prefix tree / cache-aware prompting） |
| Memory / KV cache | GPU VRAM 層 | 托管唔使你管（PagedAttention / GQA / KV quant / streaming） |
| 隱式 cache（implicit cache） | 方舟平台 | 平台自動送嘅折扣 |
| `output_schema` 自動關緩存 | 方舟特性 | 準 vs 慳嘅取捨 |

> ⚠️ `output_schema` 會**自動關掉緩存**——呢個係「準確性 vs 成本」嘅明確取捨。

### 7.7 實例：客服 Agent「快同慳」前後對比

場景：客服 agent，20k turns/日，每 turn 平均 input 4k token、output 500。

| 優化前 | 優化後 | 慳 |
|---|---|---|
| 每輪全 context 重送 4k token | Responses cache 命中等 ~ 首輪 4k + 後續 ~600 | **~75%** |
| 每 turn 大 model | 主輪 `mini` + 難題 fallback `pro` | 大 model 用量 ~50%↓ |
| 每輪 full summary | `compaction_interval=10` | summary call ~10×↓ |
| context 塞成個 FAQ | RAG top_k=10 | token ~30%↓ |

**結果**：月成本大概 **-50%**，median latency 由 ~3s 落到 ~1.5s，`eval` 分**不跌反升**（因為 context 乾淨）。

> **呢個就係「優化 + 評估」嘅完整閉環示範**：每個改動都有分數守關，所以可以放心大力優化。

---

## 8. TrainingKit —— 大規模訓練優化（L1 深水區）

### 8.1 定位

TrainingKit 係建基於 ByteDance 大規模 AI 基建同 LLM 訓練經驗嘅 **AI Cloud Native 訓練套件**——用嚟喺 BytePlus GPU 集群高效開發模型，由 pre-training 到 RL post-training 都有齊。

**三條 Kit 分工**：

| Kit | 管咩 | 客群 |
|---|---|---|
| **AgentKit** | Agent 平台（runtime / tools / MCP / 記憶 / 可觀測） | 整 agent 應用嘅 developer |
| **ServingKit** | 推理 serving（模型上線、QPS、延遲） | 將模型行到生產嘅團隊 |
| **TrainingKit** | 模型訓練（pre-training + post-training / RL） | ML infra / 大模型團隊 |

### 8.2 三條大數

| 指標 | 數字 | 即係咩 | 為何重要 |
|---|---|---|---|
| **MFU**（Model FLOPs Utilization） | **> 60%** | GPU 理論算力有幾多用咗喺真訓練 | 高 MFU = 同樣資源練得快啲、慳錢 |
| **ETTR**（Effective Training Time Ratio） | **> 99%** | 計劃訓練時間入面幾多有成效行緊 | 99%+ = 幾乎唔使停工，萬卡級跑 30 日都唔呃你時間 |
| **RL throughput**（veRL HybridEngine） | **20×** | vs 其他開源框架 | RL 最燒錢又最慢，快 20× = 同預算試多好多輪 |

### 8.3 兩大架構：Pre-Training vs Post-Training

| 維度 | **Pre-Training** | **Post-Training / RL** |
|---|---|---|
| 做咩 | 由大規模語料由零訓練 / 大規模持續預訓練 | 用 RL 算法（PPO / GRPO）將模型調到識推理、跟指令 |
| 規模 | **10,000 節點**級 AI 集群 | 百萬核並發（rollout 燒 CPU） |
| 主要硬件 | 大量 GPU + **PFS 並行文件存儲** | GPU（訓練/推理）+ **彈性 Sandbox** |
| 通信 | **veCCL** 通信加速 | veCCL + 彈性 sandbox |
| CLI 關鍵 | 穩定運行 + 故障自愈 | 冷啟動快 + rolling 並發高 |
| 落地速度 | 慢（月計）、燒錢最狠 | 快啲（週計）、機會成本係 reward 設計 |

### 8.4 veRL 框架

| veRL 元件 | 作用 |
|---|---|
| **PPO** | 經典 RL，用 critic 模型估 value |
| **GRPO** | 唔使 critic，用 group 好／壞比對估算 reward。**推理（reasoning）主力** |
| **HybridEngine** | 混合多個訓練／推理框架加速 RL 循環 → **吞吐 20×** |
| **Sandbox（Code Sandbox）** | 彈性、加速嘅執行環境，畀 agent 喺 RL 中間跑碼／rollout → **150ms 冷啟動** |

### 8.5 三種方法嘅分工

| 方法 | 數據類型 | 優化緊咩 | TrainingKit 角色 |
|---|---|---|---|
| **SFT** | 標好嘅「問題→答案」 | 直接抄模型格式／風格 | 唔特別需要（方舟精調已夠） |
| **DPO** | 好／壞回覆配對 | 揀優，方向對但冇「分數」 | 方舟精調已支援 LoRA／全量 |
| **GRPO / RL** | **Rule-based reward** | 用「分數」夾硬去優化，將 chain-of-thought 拉長 | **TrainingKit 主場** |

> **關鍵洞察**：而家啲 reasoning 模型（包括 doubao-seed 系列自家嘅推理能力）**唔係 SFT 調出嚟，係 RL（GRPO 行 rule-based reward）「練」出嚟**。SFT 教「口脗」，RL 教「諗嘢」，兩者唔同層次。

### 8.6 訓練基建組件

| 層 | 元件 | 一句 |
|---|---|---|
| 算力 | **GPU Compute Service** | 專為訓練優化嘅 GPU 集群，Pre-Training 可到 10,000 節點 |
| 編排 | **VKE**（Vital Kubernetes Engine） | 容器編排，配 KEDA 做彈性伸縮 |
| 數據 | **PFS**（Parallel File Storage） | 並行文件存儲，餵得飽萬卡同時讀數據 |
| 通信 | **veCCL** | 自家集合通信庫，optimize 大規模 all-reduce |
| 通信 | **BCC / 模型 caching** | 通信加速 + 模型快取，RL 中間慳重覆傳輸 |
| 調度 | **topology-aware + NUMA affinity** | 考慮機櫃拓樸同 NUMA，減少跨節點通信 |

> 萬卡級訓練最大敵人係**通信**，唔係算力——卡多到某個位，卡與卡之間嘅 all-reduce 慢過你「停住等佢」，MFU 即刻跌。BytePlus 嘅賣點係自家 veCCL / BCC / caching 疊埋，先做到 MFU > 60%（一般開源棧 30–50% 已經偷笑）。

### 8.7 穩定性 / 可觀測性

| 能力 | 做咩 | 價值 |
|---|---|---|
| 診斷 + 即時故障告警 | 開機／運行期間自動偵測硬件／網絡異常 | 未斷先知 |
| **Auto-healing / 自主癒合** | 壞咗自動替補、自動重啟任務 | ETTR 99%+ 嘅來源 |
| 自動任務重啟 | 訓練 task crashed 自動接返 | 唔使半夜起身手動救 |
| **子秒級可觀測性** | 指標秒級出，睇到 GPU／通信／進度 | 快啲搵到瓶頸 |
| 全訓練生命週期監控 | 由數據、到訓練、到 rollout 全 cover | 一條管睇晒 |
| **Code-free instrumentation** | 一鍵啟動、唔使自己寫監控 code | 接入成本近零 |
| **跨棧問題偵測** | agent → 推理引擎 → service 全鏈路秒級定位 | RL 中間邊一環出事即刻知 |

> 來源：https://www.byteplus.com/solutions/ai-cloud-native-trainingkit

---

## 9. Observability —— 貫穿三層嘅量測底座

**唔量測就唔好話快，唔量測就唔知改得好唔好。** Observability 係 optimization + evaluation 嘅共同前提。

### 9.1 VeADK 內建 tracing（框架層）

VeADK 內建 tracing 捕捉每個 request——由接收用戶輸入，經過模型推理、tool call、memory 同知識庫讀寫，到產生回應——全部變成結構化 span data，透過 exporter 報去 Volcengine 或第三方平台。

**VeADK tracing 遵循 OpenTelemetry generative-AI semantic conventions**，欄位名對齊標準 span attributes，所以 trace data 可以直接 import 入任何 OpenTelemetry 兼容系統分析同可視化。

**核心概念**：

| 概念 | 說明 |
|---|---|
| **span** | 一個可追蹤嘅執行單元，記錄 name、start/end time、attributes、parent-child 關係。VeADK 為每個 request 建一棵 span tree，涵蓋 agent run、model call、tool execution 等節點，並按 generative-AI semantic conventions 標注 `gen_ai.operation.name`、`gen_ai.span.kind` 等屬性 |
| **`OpentelemetryTracer`** | 統一 tracing 入口。持有 exporter list，初始化時將每個 wire 入 tracing pipeline，並**自動附加一個 in-memory exporter** 做本地保留同 dump |
| **exporter** | 將 span data 送去特定 backend 平台。每個 exporter 針對一個 backend，可以單獨用或組合用 |

**四個內建 exporter**：

| Exporter | Class | 目標平台 | 用途 |
|---|---|---|---|
| **APMPlus** | `APMPlusExporter` | Volcengine APMPlus | traces + metrics |
| **Cozeloop** | `CozeloopExporter` | Cozeloop | **trace 觀察 + 評估（evaluation）** |
| **TLS** | `TLSExporter` | Volcengine TLS 日誌服務 | 集中日誌、長期留存 |
| **In-memory** | `InMemoryExporter` | 進程內記憶 | 本地 debug、dump（**自動附加，唔好手動加**） |

**基本用法**：

```python
import asyncio

from veadk import Agent, Runner
from veadk.memory.short_term_memory import ShortTermMemory
from veadk.tools.demo_tools import get_city_weather
from veadk.tracing.telemetry.exporters.apmplus_exporter import APMPlusExporter
from veadk.tracing.telemetry.opentelemetry_tracer import OpentelemetryTracer

exporters = [APMPlusExporter()]
tracer = OpentelemetryTracer(exporters=exporters)

agent = Agent(tools=[get_city_weather], tracers=[tracer])

runner = Runner(agent=agent, short_term_memory=ShortTermMemory())

asyncio.run(runner.run(messages="How is the weather in Beijing?", session_id="session_id_demo"))
```

**一個 tracer 可以掛多個 exporter**（同一批 span 報去多個平台）：

```python
from veadk.tracing.telemetry.exporters.apmplus_exporter import APMPlusExporter
from veadk.tracing.telemetry.exporters.cozeloop_exporter import CozeloopExporter
from veadk.tracing.telemetry.exporters.tls_exporter import TLSExporter
from veadk.tracing.telemetry.opentelemetry_tracer import OpentelemetryTracer

tracer = OpentelemetryTracer(
    exporters=[APMPlusExporter(), CozeloopExporter(), TLSExporter()]
)
```

**`OpentelemetryTracer` 參數**：

| 參數 | 類型 | 預設 | 說明 |
|---|---|---|---|
| `name` | `str` | `veadk_opentelemetry_tracer` | Tracer 標識，用於 logging 同命名 dump file |
| `exporters` | `list[BaseExporter]` | `[]` | Exporter list。`InMemoryExporter` **唔可以**明確加入，否則驗證失敗（會自動附加） |
| `apmplus_managed_externally` | `bool` | — | **唯讀屬性**。初始化時係否已存在 global `TracerProvider`。`True` 時 VeADK 會重用外部 provider 而唔覆寫，並**自動移除 `APMPlusExporter`** |

**環境變數開 exporter**：

| 環境變數 | 啟用 |
|---|---|
| `ENABLE_APMPLUS` | `APMPlusExporter` |
| `ENABLE_COZELOOP` | `CozeloopExporter` |
| `ENABLE_TLS` | `TLSExporter` |

> 三個都係 `false`（預設）時，`Agent` 唔會建立 tracer。要 trace 就要自己建 `OpentelemetryTracer` 並經 `tracers` 傳入。

**Content tracing（敏感資料場景）**：

| Config | 環境變數 | 類型 | 預設 | 說明 |
|---|---|---|---|---|
| `trace_content` | `OBSERVABILITY_OPENTELEMETRY_TRACE_CONTENT` | `bool` | `True` | 係否將 prompt、completion、tool input/output 內容寫入 span。設 `false` 就只保留非內容嘅 trace 資訊 |

```bash
export OBSERVABILITY_OPENTELEMETRY_TRACE_CONTENT=false
```

**本地 dump**：

```python
path = tracer.dump(user_id="user-1", session_id="session_id_demo")
print(f"trace written to {path}")
```

> 匯出嘅 JSON 每個 span 含：name、`span_id`、`trace_id`、start/end times、attributes、parent span。

> 來源：https://agentkit-f14c9eb5.mintlify.site/productions/veadk/preview/en/components/observability

### 9.2 CozeLoop —— trace + evaluation 二合一平台

`CozeloopExporter` 透過 OTLP (HTTP) 將 span data 報去 Cozeloop 平台。接上之後，你可以用 Cozeloop 嘅 **trace 功能觀察**，或用佢嘅 **evaluation 功能評估** agent。數據按 workspace（space）隔離。

**幾時用**：
- 你想喺 Cozeloop 觀察 agent 嘅 traces；
- 你想用 Cozeloop 嘅評估能力分析對話質量同工具使用效益；
- 你已經有 Cozeloop workspace 同 access token。

```python
from veadk.tracing.telemetry.exporters.cozeloop_exporter import (
    CozeloopExporter,
    CozeloopExporterConfig,
)

exporter = CozeloopExporter(
    config=CozeloopExporterConfig(
        endpoint="https://api.coze.cn/v1/loop/opentelemetry/v1/traces",
        space_id="your-cozeloop-space-id",
        token="your-cozeloop-token",
    )
)
```

**Cozeloop 連線配置**：

| Config | 環境變數 | 預設 | 說明 |
|---|---|---|---|
| `endpoint` | `OBSERVABILITY_OPENTELEMETRY_COZELOOP_ENDPOINT` | `https://api.coze.cn/v1/loop/opentelemetry/v1/traces` | Cozeloop OTLP endpoint (HTTP) |
| `space_id` | `OBSERVABILITY_OPENTELEMETRY_COZELOOP_SERVICE_NAME` | 未設時自動建預設 workspace | Workspace ID，用於數據隔離 |
| `token` | `OBSERVABILITY_OPENTELEMETRY_COZELOOP_API_KEY` | `""` | Access token；支援 personal access token、OAuth access token、service access token |

```bash
export OBSERVABILITY_OPENTELEMETRY_COZELOOP_ENDPOINT="https://api.coze.cn/v1/loop/opentelemetry/v1/traces"
export OBSERVABILITY_OPENTELEMETRY_COZELOOP_API_KEY="your-cozeloop-token"
export OBSERVABILITY_OPENTELEMETRY_COZELOOP_SERVICE_NAME="your-cozeloop-space-id"

# 或者一句搞掂
export ENABLE_COZELOOP=true
```

> `space_id` 取自環境變數 `OBSERVABILITY_OPENTELEMETRY_COZELOOP_SERVICE_NAME`；未設時 exporter 會用 `token` 做憑證自動建立一個預設 workspace。登入 Cozeloop 後，URL 中 `space` 之後嘅片段就係 workspace ID。
>
> 來源：https://agentkit-f14c9eb5.mintlify.site/productions/veadk/preview/en/components/observability/cozeloop

### 9.3 AgentKit 平台可觀測性（L3）

AgentKit 嘅 observability 系統由**三部分**組成：**basic monitoring（metrics）、application observability（traces）、logs**。支援由底層硬件資源到上層業務應用嘅分層監控，加上端到端日誌收集。

| 類型 | 目標 | 內容 | 適合 |
|---|---|---|---|
| **Basic monitoring** | **資源實例同組件**：gateway instances、agent runtimes、tools、MCP services、MCP toolsets、memories | 用多維 metric 同可視化 dashboard 實時顯示組件運行狀態；查服務健康、request count、資源使用趨勢、系統錯誤。主要用嚟**判斷底層資源本身有冇正常運作** | 資源健康檢查、容量評估、發佈後穩定性驗證 |
| **Application observability** | **agents 或業務應用** | 提供完整 call chains、session records、metric statistics and analysis，做到 agent 全流程細粒度可觀測。除咗部分基本監控能力，仲追蹤完整內部執行 | Agent 行為分析、除錯、優化 |
| **Logs** | 全棧 | 端到端日誌收集 | 事故調查 |

**監控頁面全集**（平台文檔）：

- Viewing agent runtime monitoring data
- Viewing tool monitoring data
- Viewing memory monitoring data
- Viewing MCP service monitoring data
- Viewing MCP toolset monitoring data
- Viewing gateway instance monitoring data
- Viewing model service monitoring data

**Runtime 層開關**：`Enabling/Disabling observability service`（console）或 `agentkit runtime update --apmplus`（CLI）。

> 來源：https://docs.byteplus.com/en/docs/agentkit/Observability_overview

### 9.4 用 observability 驅動優化（實務 checklist）

| 平台 | 用嚟睇 | 接入 |
|---|---|---|
| **APMPlus** | 模型調用次數、token 用量、操作耗時、異常次數、工具耗時；推理內容用 `reasoning` 標注 | `OpentelemetryTracer([APMPlusExporter()])` 或 `ENABLE_APMPLUS=true` |
| **Cozeloop** | trace + 評測 | `CozeloopExporter()` |
| **TLS** | 集中日誌、長期留存 | `TLSExporter()` |
| **InMemory** | 本地 debug，span JSON 落盤 | 自動附帶，唔使手加 |
| **CLI logs** | 快速睇 runtime | `agentkit runtime logs my-agent --limit 200` |

**Performance checklist**：睇 APMPlus「操作耗時」分佈 → 俾你知邊個 agent／邊個工具最慢 → 集中攻嗰嚿。

> ⚠️ `LOGGING_LEVEL=DEBUG` 會記錄模型輸出、思考內容、工具參數同結果——**生產環境記住轉 INFO**。

---

## 10. 決策總表：幾時用邊樣

### 10.1 評估方法選擇

| 情況 | 揀咩 |
|---|---|
| 開發期 iterate（未部署） | `veadk eval`（ADK / DeepEval）或 `veadk web` Eval tab |
| 改 prompt / 換 model 前後 | `agentkit eval run --dataset ...`（offline dataset eval） |
| 每次 deploy 前 | **CI eval**（`eval run` → `experiment show`，分數 < 門檻就停 pipeline） |
| 上線後持續監控 | **Studio 自動評測回流**（Good/Bad Case）+ Shadow 抽樣 |
| 想數據飛輪（真實 case 自動入集） | Studio「Auto-create evaluation sets」 |
| Agent / 多 agent、要睇軌跡同工具 | **ADKEvaluator** |
| RAG / LLM 輸出質量為主 | **DeepevalEvaluator**（GEval、Faithfulness、Relevancy 等） |
| 驗證外部系統狀態、非文字輸出、內部評分 API | **自訂 `BaseEvaluator`** |
| 揀基模 / 驗精調效果 | **ModelArk 模型評測系統**（預設 MMLU / 高考題 + 4 種評分方法） |
| 現有 agent 遷移去 AgentKit | **Migration effect evaluation**（6 維度、HTML 報告） |
| 團隊協作、跨版本比較、可視化 | **CozeLoop**（`veadk uploadevalset` + `CozeloopExporter`） |
| 高風險 / 合規場景 | 加**人工 / HITL** |

### 10.2 優化方法選擇

| 情況 | 揀咩 | 成本 |
|---|---|---|
| 只改語氣／格式／風格 | 改 system prompt（`Agent.instruction`）/ PromptPilot | 零 |
| 要結構化輸出（JSON schema） | `output_schema`（Responses API） | 零 |
| 要慳錢慳 context | context cache + compaction + RAG + fallback routing | 零 |
| 領域知識／術語／穩定格式 | LoRA（方舟精調） | 低 |
| 要對齊偏好 | DPO（LoRA 或全量） | 中 |
| 要唔靠 prompt 嘅推理提升 | GRPO / RL（Ark RL 或 Agent Lightning 或 TrainingKit veRL） | 高 |
| 細 model 做到大 model 效果 | Distillation | 高（數據工程） |
| 由零起私有模型 / 萬卡 pre-training | TrainingKit Pre-Training（PFS + veCCL + 10k nodes） | 最高 |
| 已部署 runtime 反應慢／成本高 | `agentkit runtime update` 調 CPU/mem/concurrency/instances | 雲費 |
| 想 agent 自動改善自己 | Studio Harness Sidecar（5 組件）+ LocalReflector 自反思 | 中 |
| 想系統自動畀優化建議 | Studio 自動評測 → Optimization Suggestions（priority × module） | 中 |

### 10.3 完整閉環（一張圖睇晒）

```
        ┌──────────────────────────────────────────────────────────┐
        │                    量測底座 (Observability)               │
        │  VeADK tracer (APMPlus/Cozeloop/TLS/InMemory)             │
        │  AgentKit 平台監控 (metrics + traces + logs)              │
        └──────────────────────────────────────────────────────────┘
                    │ 產生 trace / metric / log
                    ▼
   ┌─────────────────────────────────────────────────────────────┐
   │  1. OBSERVE  睇 trace：邊個 agent / 工具最慢、邊度出錯      │
   └─────────────────────────────────────────────────────────────┘
                    ▼
   ┌─────────────────────────────────────────────────────────────┐
   │  2. EVALUATE 建立分數基線                                  │
   │  AgentKit CLI : dataset → evaluator → target → experiment   │
   │  VeADK        : ADKEvaluator / DeepevalEvaluator / pytest    │
   │  ModelArk     : 模型評測（MMLU / 高考 / 4 種評分方法）        │
   │  Studio       : 自動評測回流（score ≥0.6 → Good Case）       │
   └─────────────────────────────────────────────────────────────┘
                    ▼
   ┌─────────────────────────────────────────────────────────────┐
   │  3. OPTIMIZE  按成本由低到高落手                            │
   │  L2 prompt → schema → compaction → routing → cache          │
   │  L2 PromptPilot → LocalReflector 自反思 → RL                │
   │  L1 LoRA → DPO → GRPO → Distillation → TrainingKit          │
   │  L3 Harness Sidecar（context governance / compression /      │
   │     answer verification / goal-task / MCP-resilience）       │
   └─────────────────────────────────────────────────────────────┘
                    ▼
   ┌─────────────────────────────────────────────────────────────┐
   │  4. RE-EVALUATE  同一 dataset 再跑，比分數                  │
   │  分數升 → 收貨 ｜ 分數跌 → 回滾（Regression guard）          │
   └─────────────────────────────────────────────────────────────┘
                    │
                    └──────────► 回到 1（持續迴圈）
```

---

## 11. 隱性成本（報價／規劃要記住）

| 成本項 | 出處 |
|---|---|
| **Eval 本身唔係免費** | LLM-as-judge 每 case 一次 model call（AgentKit evaluator 用 judge model；VeADK DeepEval 用 `judge_model`） |
| **Studio 自動評測** | 每輪對話一次評分 model call |
| **Shadow eval 抽樣** | 例如抽 10% 流量 = +10% 模型消耗 |
| **精調後模型推理** | ≈ 基礎模型 2–2.5×（按 token）或模型單元時長 |
| **RL 成本雙食** | 訓練成本（超大 GPU 集群）+ 推理 sandbox 成本，唔係淨訓練費 |
| **Distillation 數據工程** | 要大 model 生成數據、清洗、格式化、再 SFT，數據質量決定效果 |
| **Harness Sidecar 優化** | 相關增強行為喺 managed runtime 執行並訪問 model + MCP gateway |
| **Migration evaluation** | 要部署臨時 Runtime（Session TTL 由 1h 延到 2h） |
| **PII scan / guardrail** | 額外 LLM 消耗 |

---

## 12. 避雷清單

| 避雷點 | 詳情 |
|---|---|
| **精調唔入 Agent Plan** | 精調後模型默認**唔入訂閱**，係第二條收費線（按 token 或模型單元） |
| **唔好用「即將下線」基模做精調** | 白做 |
| **新基模未必即開精調** | 揀基模前睇「精調支援」標誌 |
| **在線／批量推理要壓縮產物** | LoRA 產物 ≥1.5GB 要壓縮先買到模型單元；按 token 唔使（部分模型） |
| **`output_schema` 會關掉 cache** | 準確性 vs 成本嘅明確取捨 |
| **`--target` 必須在線** | Case 失敗而冇 experiment-level error = runtime 冇回應，唔係 eval 配置問題 |
| **Dataset 唔好寫入 `output`** | `output` 由被評 target 喺實驗期間產生 |
| **Dataset schema 一建即固定** | Case 嘅 key 必須 match schema |
| **Migration evaluation 維度一上傳即鎖** | 唔可以中途改 |
| **Harness Sidecar 只支援 Volcengine 帳號** | BytePlus 帳號要留空先部署得 |
| **`LOGGING_LEVEL=DEBUG` 唔好落生產** | 會記錄模型輸出、思考內容、工具參數同結果 |
| **唔好為咗 concurrency 一味加機** | 跑得順但 cost 爆應該返去搞 context |
| **VeADK / AgentKit 冇微調 API** | 精調係 ModelArk 嘅事，框架層只係消費 `model_name` |
| **`InMemoryExporter` 唔好手動加** | 會導致初始化失敗（自動附加） |

---

## 13. 來源索引（全部實時抓取，2026-09-15）

| # | 主題 | URL |
|---|---|---|
| 1 | AgentKit CLI — Evaluation loop（官方完整流程） | https://agentkit-f14c9eb5.mintlify.site/productions/agentkit-cli/preview/en/workflows/evaluation |
| 2 | AgentKit CLI — eval run | https://agentkit-f14c9eb5.mintlify.site/productions/agentkit-cli/preview/en/commands/eval/run |
| 3 | AgentKit CLI — eval dataset | https://agentkit-f14c9eb5.mintlify.site/productions/agentkit-cli/preview/en/commands/eval/dataset |
| 4 | AgentKit CLI — eval evaluator | https://agentkit-f14c9eb5.mintlify.site/productions/agentkit-cli/preview/en/commands/eval/evaluator |
| 5 | AgentKit CLI — eval target | https://agentkit-f14c9eb5.mintlify.site/productions/agentkit-cli/preview/en/commands/eval/target |
| 6 | AgentKit CLI — eval experiment | https://agentkit-f14c9eb5.mintlify.site/productions/agentkit-cli/preview/en/commands/eval/experiment |
| 7 | AgentKit CLI — eval backend | https://agentkit-f14c9eb5.mintlify.site/productions/agentkit-cli/preview/en/commands/eval/backend |
| 8 | VeADK — Evaluation framework | https://github.com/volcengine/veadk-python/blob/main/docs/content/docs/framework/evaluation.en.mdx |
| 9 | VeADK — Continuous Optimization | https://github.com/volcengine/veadk-python/blob/main/docs/content/docs/framework/optimization.en.mdx |
| 10 | VeADK CLI — 全部命令（含 eval / prompt / uploadevalset / rl） | https://github.com/volcengine/veadk-python/blob/main/docs/content/docs/cli/veadk-cli.en.mdx |
| 11 | VeADK — Observability | https://agentkit-f14c9eb5.mintlify.site/productions/veadk/preview/en/components/observability |
| 12 | VeADK — Cozeloop exporter | https://agentkit-f14c9eb5.mintlify.site/productions/veadk/preview/en/components/observability/cozeloop |
| 13 | VeADK — Studio（自動評測 / Harness Sidecar / 遷移評估） | https://agentkit-f14c9eb5.mintlify.site/productions/veadk/preview/en/components/frontend/studio |
| 14 | VeADK 源碼 — `veadk-python[eval]` 依賴 | https://github.com/volcengine/veadk-python/blob/main/pyproject.toml |
| 15 | VeADK 源碼 — Studio 自動評測（`GOOD_SCORE_THRESHOLD=0.6`） | https://github.com/volcengine/veadk-python/blob/main/frontend/server/evaluation_automation/service.py |
| 16 | ModelArk — Model evaluation system | https://docs.byteplus.com/en/docs/ModelArk/1150779 |
| 17 | ModelArk — Creating model evaluation task | https://docs.byteplus.com/en/docs/ModelArk/1150782 |
| 18 | ModelArk — Viewing Evaluation Report | https://docs.byteplus.com/en/docs/ModelArk/1150783 |
| 19 | ModelArk — Evaluation dataset format description | https://docs.byteplus.com/en/docs/ModelArk/1150781 |
| 20 | ModelArk — Model fine-tuning overview | https://www.volcengine.com/docs/82379/1099459 |
| 21 | AgentKit — Observability overview | https://docs.byteplus.com/en/docs/agentkit/Observability_overview |
| 22 | AgentKit — Knowledge Q&A testing | https://docs.byteplus.com/en/docs/agentkit/Knowledge_qa_testing |
| 23 | TrainingKit — MFU / ETTR / 20× RL | https://www.byteplus.com/solutions/ai-cloud-native-trainingkit |

---

## 附錄 A：CLI 命令速查卡

```bash
# ══════════ AgentKit CLI：Eval loop ══════════
agentkit eval backend                                          # 睇用邊個 backend
agentkit eval backend --json
agentkit eval --cache-refresh backend                          # 繞過 7 日 cache
agentkit eval --verbose dataset list                           # 印完整 TEA request

agentkit dataset list
agentkit dataset show qa-set --items 50
agentkit dataset create --name qa-set --schema "input,reference_output"
agentkit dataset add qa-set --field "input=Q" --field "reference_output=A"
agentkit dataset add qa-set --file cases.json
agentkit dataset remove qa-set item-1 item-2 -y
agentkit dataset delete qa-set -y
agentkit dataset version list --dataset qa-set                 # TEA only
agentkit dataset version create 0.0.2 --dataset qa-set --description "..."  # TEA only
agentkit dataset update <dataset-id> --name qa-set-v2          # TEA only

agentkit eval evaluator template list
agentkit eval evaluator templates --type prompt
agentkit eval evaluator template show relevance
agentkit eval evaluator list
agentkit eval evaluator show relevance --evaluator-version 0.0.1
agentkit eval evaluator create --name relevance --from-template relevance --model ep-xxxxxxxx
agentkit eval evaluator create --name custom --prompt-file ./rubric.txt \
  --input-schemas input,output,reference_output --model 2
agentkit eval evaluator update-draft <id> --prompt-file ./rubric.txt   # TEA only
agentkit eval evaluator version list --evaluator relevance             # TEA only
agentkit eval evaluator version submit 0.0.2 --evaluator relevance     # TEA only
agentkit eval evaluator delete relevance -y

agentkit eval target list --name my-agent                      # TEA only
agentkit eval target version-list --source-target-id <id>       # TEA only

agentkit eval run --dataset qa-set --evaluator relevance \
  --evaluator-version 0.0.1 --target qa-agent --dry-run
agentkit eval run --dataset qa-set --evaluator relevance \
  --evaluator-version 0.0.1 --target qa-agent --concurrency 8
agentkit eval run --dataset qa-set --evaluator relevance --target my-agent \
  --map "evaluator.output <- target.actual_output" \
  --map "target.user_input <- dataset.question"

agentkit eval experiment list                                  # alias: exp
agentkit eval experiment show 75901xxxxxxxxxxxxx               # alias: get
agentkit eval experiment results 75901xxxxxxxxxxxxx --limit 20 --page 1

# CI 守關
EXP=$(agentkit eval run --dataset qa-set --evaluator relevance \
  --evaluator-version 0.0.1 --target qa-agent --json | jq -r .experimentId)
agentkit eval experiment show "$EXP" --json

# ══════════ VeADK CLI：Eval + Optimize ══════════
pip install "veadk-python[eval]"          # deepeval>=3.2.6 + google-adk[eval]>=1.34.0

veadk web                                 # Web UI（Eval tab 生成 evalset）
veadk web --port 8080
veadk web --oauth2-user-pool my-pool --oauth2-user-pool-client my-client

veadk eval --agent-dir ./my-agent --evalset-file ./eval.json --evaluator adk
veadk eval --agent-a2a-url http://url/invoke --evalset-file ./eval.json \
  --evaluator deepeval --volcengine-access-key AK --volcengine-secret-key SK

veadk uploadevalset --file ./my_eval_set.json \
  --cozeloop-workspace-id WS --cozeloop-evalset-id ES --cozeloop-api-key KEY

veadk prompt --path ./weather_reporter/agent.py \
  --feedback "希望提示詞能夠更加具體明確" \
  --api-key KEY --workspace-id WS

veadk rl init --platform ark --workspace veadk_rl_ark_project
veadk rl submit --platform ark
veadk rl init --platform lightning --workspace veadk_rl_lightning_project

# ══════════ AgentKit CLI：效能優化 ══════════
agentkit runtime update my-agent --cpu-milli 2000 --memory-mb 4096 \
  --max-concurrency 40 --auto-release
agentkit runtime update my-agent --max-instance 5 --auto-release
agentkit runtime update my-agent --apmplus --auto-release
agentkit runtime logs my-agent --limit 200
```

## 附錄 B：環境變數速查

```bash
# ── Eval gateway（AgentKit CLI）──
AGENTKIT_EVAL_HOST=agentkit.cn-beijing.volcengineapi.com
AGENTKIT_EVAL_SERVICE=agentkit
AGENTKIT_EVAL_REGION=cn-beijing
AGENTKIT_TEA_ACCOUNT_ID=<account-id>
EXTRA_HEADER="Name: Value;Name2: Value2"

# ── Observability exporter 開關（VeADK）──
ENABLE_APMPLUS=true
ENABLE_COZELOOP=true
ENABLE_TLS=true
OBSERVABILITY_OPENTELEMETRY_TRACE_CONTENT=false     # 敏感資料場景

# ── CozeLoop 連線（VeADK）──
OBSERVABILITY_OPENTELEMETRY_COZELOOP_ENDPOINT=https://api.coze.cn/v1/loop/opentelemetry/v1/traces
OBSERVABILITY_OPENTELEMETRY_COZELOOP_API_KEY=<token>
OBSERVABILITY_OPENTELEMETRY_COZELOOP_SERVICE_NAME=<space-id>
OBSERVABILITY_OPENTELEMETRY_COZELOOP_EVALSET_ID=<evalset-id>

# ── 模型（VeADK，含精調模型）──
MODEL_AGENT_NAME=ep-2026080100000-lora
MODEL_AGENT_MODEL_NAME=<model-name>
MODEL_AGENT_API_KEY=sk-...
MODEL_AGENT_API_BASE=https://ark.cn-beijing.volces.com/api/v3
MODEL_EMBEDDING_MODEL_NAME=<embedding-model>
MODEL_EMBEDDING_API_KEY=<key>
MODEL_JUDGE_MODEL_NAME=<judge-model>          # 評估用 judge

# ── Studio 持久化（自動評測快照需要）──
VEADK_STUDIO_TOS_BUCKET=<bucket>
VEADK_STUDIO_TOS_REGION=<region>

# ── 日誌 ──
LOGGING_LEVEL=INFO                            # 生產環境唔好用 DEBUG
```

---

*文檔版本：2026-09-15 · 所有命令、flag、數值、門檻均以實時抓取嘅官方文檔／源碼為準。CLI 參數同 evaluator 模板名會隨版本迭代，落地前建議 refetch。*
