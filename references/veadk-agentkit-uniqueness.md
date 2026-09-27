# VeADK + AgentKit + BytePlus 獨特賣點全覽（vs 其他 provider）

呢份文件回答一條問題：**「我哋個 stack 到底有咩係人哋冇？」**——俾你 sales / 方案直接用，唔使佮估。

> ✅ **核心心法**：
> 1. **獨特 = 四層疊埋，唔係單一 feature**：VeADK（framework）+ AgentKit（平台）+ BytePlus（雲）+ 自家模型（doubao/Seed 家族）——**同一個供應商**，先係真正嘅「一體化」賣點。
> 2. **要分「真獨特」同「行貨」**：A2A / MCP / OTel / OAuth2 / RAG / cache 全部都係市場標準（行貨），攞嚟充當賣點會穿煲。§5 專登列出嚟。
> 3. **每個「獨特位」要講到「客戶見到咩」**：唔係為 tech 而 tech，係「慳幾多 $$ / 少幾多張單 / 幾快上線」。

---

## 0. 快睇：四層各有咩係人哋冇

| 層 | 真獨特（人哋冇） | 一句客戶價值 |
|---|---|---|
| **VeADK framework** | 基於 Google ADK 但火山托管；自帶 7×LTM + 8×RAG backend；`model_name` list 自動 fallback；默認上下文緩存 | 唔使自砌記憶/RAG，框架「諗埋」 |
| **AgentKit 平台** | `create_agentkit_app` 一 call 由框架上雲；CLI 全套；出站憑證托管（Agent Identity）；chain-hash 審計 7 年；zero-code Harness | 本地 → 上雲 → 審計一條龍 |
| **BytePlus 雲** | **AFP 封頂月費**；多模態獨家；GPU/sandbox 已包；隱式 cache；中文+粵語第一身 | 成本可預測，帳單不散 |
| **自家模型** | Seed 全梯度文字 + Seedream 圖 + Seedance 片 + TTS/ASR + 多模態向量**一個平台玩晒**（詳情 → **seedream / seedance tab**） | 唔使駁第三方圖/片/語音 API |

---

## 1. 心法：獨特唔係功能，係「四層同一間廠」

逐個 feature 比較，每間平台都有一兩樣做得好。但**冇一間好似 BytePlus 咁：框架 + 部署 + GPU + 模型全部第一方**。

| 你要砌嘅嘢 | BytePlus stack | Azure/AWS/Google | 自架（LangChain/LangGraph）|
|---|---|---|---|
| Framework | **VeADK**（基於 Google ADK） | 各家 SDK 各自為政 | 你用邊個都得但自己管版本 |
| 部署/Runtime | **AgentKit**（一 call 上雲） | Agent Service/AgentCore 分開買 | 自己攞 EC2/VM 行 |
| GPU/sandbox | **已包入 Plan** | PTU / EC2 H100 另開單 | 自己租 GPU |
| 模型（圖/片/語音） | **自家一條龍** | AWS 駁第三方、Azure 冇視頻 | 逐個供應商駁 |
| 帳單 | **一個數封頂** | 五張單浮動 | CPU/GPU/模型逐項 |
| 記憶/RAG/向量化 | 框架內建 backend | 各廠拆分 | 自己嵌 vector DB |

> **銷售一句**：「我哋嘅賣點唔係『某一粒 model 好勁』，係**成條 agent 鏈都係同一間廠**——framework、平台、GPU、模型，一齊買、一個數、一條 support 線。」

---

## 2. VeADK（framework）獨特位 — vs OpenAI Agents SDK / LangGraph / Google ADK

> 對照基準：最常被問嘅三個「自己都要寫嘢」嘅 framework。

### 2.1 基於 Google ADK，唔係自研 runtime

```python
from veadk import Agent   # 內部基於 google.adk 嘅 App / Runner
```

- VeADK 係**建基於 Google ADK（蚼底 `google.adk`）**嘅框架，唔係由零自研 runtime → **生態繼承 Google/ADK 大社群**（MCP、LongRunningFunctionTool、EventsCompactionConfig 等）。
- 但佢**唔止係 ADK fork**：疊加咗火山托管後端（模型、記憶、KB、可觀測性）。
- 對比：OpenAI Agents SDK（無 framework 層嘅記憶/KB abstraction）、LangGraph（有 abstractions 但要自己接 hosting/模型）、Google ADK（原生但**冇火山托管模型/Feishu/方舟後端**）。

### 2.2 自帶 7×LTM + 8×RAG backend（唔使自己砌 vector DB）

| 記憶維度 | 數量 | 例子 |
|---|---|---|
| LongTermMemory backend | **7 種** | local / opensearch / redis / viking / mem0 / openviking / tos_context |
| KnowledgeBase backend | **8 種** | local / opensearch / redis / milvus / tos_vector / viking / context_search / openviking |

- **托管後端（viking / context_search / openviking / mem0 / tos_context）唔使你裝 embedding**——服務端切分 + 向量化 + 檢索，直接計「雲資源向量化」費用。
- 對比：LangChain/LlamaIndex 要自己揀 vector store + embedding model + 自己管 migration；Azure AI Search / Bedrock KB 係**收費服務**（Bedrock KB 有 $345/月 floor）。

### 2.3 `model_name` 收 list → 自動 fallback

```python
agent = Agent(
    model_name=["doubao-seed-2-1-pro-260628", "deepseek-r1-250528"],
)
```

- 主 model 掛咗自動落第二個——**agent 帶自我修復**，唔使自己寫 retry / circuit breaker。
- 對比：多數 framework 要自己 try/except + 手動切 model。

### 2.4 默認上下文緩存（Responses API）

- VeADK Responses API 模式**默認開 session 上下文緩存**（`output_schema` 指定時先關閉）——慳錢主要靠呢度（見 vc tab §4）。
- 對比：自己砌 prompt 管理先做到同款 caching。

### 2.5 可選依賴組，唔使一支裝到肥晒

```bash
pip install "veadk-python[extensions]"  # 飛書 + Cozeloop + LlamaIndex
pip install "veadk-python[codex]"       # Codex 運行時
pip install "veadk-python[database]"    # Redis/MySQL/VikingDB/mem0
pip install "veadk-python[eval]"        # DeepEval
pip install "veadk-python[a2ui]"        # A2UI 富界面
pip install "veadk-python[harness]"     # Harness 服務
```

- 需要先裝——**唔會一支 package 拖晒全部重依賴**。對比大部分框架一裝全家。

### 2.6 `config.yaml` 一鍵，零 `.env` 噪音

```yaml
model:
  agent:
    provider: openai
    name: doubao-seed-2-1-pro-260628
    api_base: https://ark.cn-beijing.volces.com/api/v3/
    api_key: <your-api-key>
volcengine:
  access_key: <your-ak>
  secret_key: <your-sk>
```

- 一份 YAML 搞掂模型 + 火山鑒權；環境變數只是另類快速起動。
- 對比：多數框架要 `.env` + 環境變數 + secret 管理分開搞。

---

## 3. AgentKit（平台）獨特位 — vs Azure Foundry / Bedrock Agents / LangGraph Cloud / OpenAI Agents SDK

> 對照基準：市面上「agent 上雲」嘅主流做法。

### 3.1 由框架到上雲一 call：`create_agentkit_app`

- `veadk.studio.deploy` 或 `create_agentkit_app` 直接**把現有 VeADK Agent 包裝成 AgentKit 部署項目**——framework → 平台零 rewrite。
- 對比：Azure Foundry Agent Service / Bedrock AgentCore 要你用佢哋自己嘅 abstraction 重建 agent；LangGraph Cloud 用 LangChain API 綁死生態。

### 3.2 CLI 全套，單一工具由 init 到 destroy

```bash
agentkit init myagent
agentkit config
agentkit deploy myagent
agentkit runtime logs myagent --limit 200
```

- init（模板 / `--from-agent` 包裝）/ config / deploy / launch / invoke / status / destroy / runtime release / attach webshell / scp / mount / web preview / logs——一個 binary 搞掂成個 lifecycle。
- 對比：Azure/Bedrock **控制台 + 多 CLI** 分散；LangGraph Cloud **冇咁完整嘅本地→雲 workflow**。

### 3.3 出站憑證托管（Agent Identity）— secret 唔入 repo

- `VeIdentityFunctionTool` / `VeIdentityMcpToolset` 注入出站 API Key/OAuth；**自動緩存、刷新、輪換**；憑據唔寫入 code。
- ```python
  tool = VeIdentityFunctionTool(fn=call_crm_api, auth_config=api_key_auth("your-outbound-cred-name"))
  ```
- **Sales 一句**：「你哋出站嘅 key 唔會入 repo——Agent Identity 幫你轉緊，你哋啲 dev 唔使貼 secret 落 code。」——呢個同自架 LangGraph 最唔同。
- 對比：Azure Key Vault / AWS Secrets Manager 係**你要自己接**；Agent Identity 係 **framework 內建**。

### 3.4 出站認証覆蓋「機器對機器」同「用戶委託」

- OAuth2 M2M（服務之間）+ 用戶委託（用戶授權→自動 token 交換+刷新，撤銷提示重新授權）——**覆蓋成個 outbound 憑證光譜**。

### 3.5 入站身份一體化（AuthRequestProcessor + Runtime identity）

- 框架層：`AuthRequestProcessor`（VeIdentity 用戶池）直接掛 `run_processor`。
- Runtime 層：`create_agentkit_app(identity=...)` 喺 agent/tool 執行前驗證 + 綁定用戶身份；`/ping`/`/health`/`/metrics` exempt。
- 對比：Azure Entra / AWS Cognito 係**額外服務**要自己串。

### 3.6 內容安全 4 點 + PII（category 103）內建掛鈎

- `content_safety` 四點審查：Before Model / After Model / Before Tool / After Tool，借火山 LLM-FW。
- `category 103` = **敏感資訊（PII）實時偵測**（身份證、手機號）——入/出/工具三點都封。
- 對比：Azure Content Safety / AWS Guardrails 係**逐次計費**嘅額外服務（Bedrock $0.15/1K units）；LLM-FW 掛鈎內置 close-to-free。

### 3.7 chain-hash 審計 7 年 + 身份關聯

- Audit ≠ log：OTel span + session trace dump JSON + **chain-hash（hash 鏈，防篡改）**落 DB；TOS archive + PostgreSQL 保留 7 年；每 span 綁入站用戶（`identity=...`）。
- 對比：多數平台只有 logging；要「可重現 + 防篡改 + 保留期」要自己搭。

### 3.8 OTel 一條 trace 出多 exporter

```python
tracer = OpentelemetryTracer(exporters=[APMPlusExporter(), CozeloopExporter(), TLSExporter()])
```

- 一份 span 同時送 APMPlus / Cozeloop / TLS / InMemory——**唔使揀，可以疊**；仲有 `trace_content` 開關（敏感場景唔寫 prompt）。
- 對比：其他平台通常單一 observability 或者要自己串 exporter。

### 3.9 RBAC + IAM 一體

- Studio `--admin`/`--developer` 角色（admin 見全部、developer 見自己）；部署默認建 `VeADKFrontendServiceRole`/`Policy`，可用 `--iam-role` 指定。
- 對比：Azure/AWS 要自己在 IAM/Entra 另配。

### 3.10 zero-code Harness + sandbox

- `agentkit init my-agent -t harness`：**唔使寫 code** 開 harness；Harness 仲可指模型精調 endpoint（LoRA）。
- Sandbox 支援 CodeEnv / Private / tmux / YAML orchestration / model-login——測試環境一條龍。

---

## 4. BytePlus（雲）獨特位 — vs 各雲

> 呢層密集引用跨廠商對照（cmp tab §3.1/§5）——呢度只列「獨特位」，價做詳細陣列喺 cmp。

| 獨特位 | 係咩 | 人哋有冇 |
|---|---|---|
| **AFP 統一燃料** | 一個額度單位包起 tokens/工具/向量化 | 冇（各家逐項收） |
| **封頂月費** | Small ¥40 → Max ¥1,000 **封頂** | Azure/Bedrock 浮動；DeepSeek 純 API 冇包 |
| **GPU/sandbox 已包** | 唔使另開 EC2/Vertex GPU 單（H100 $10–11/h） | Azure PTU $2,448/月、AWS 另計 |
| **多模態獨家** | Seedance 2.0 / Seedream 只有 BytePlus 有 API | OpenAI 冇視頻、AWS 駁第三方、GEMINI Veo 另收 |
| **隱式 cache ~20%** | 自動 cache，唔使開（`output_schema` 先關） | Azure/Gemini 收費制；DeepSeek cache $0.0028 但手動 |
| **中文 + 粵語第一身** | doubao 中英+粵語表現 | 其他家要特登調 |
| **方舟托管第三方同價** | DeepSeek ¥1/¥2 同官方價 + 企業並發/TTFT保穩 | 直連 DeepSeek 並發/峰谷要自己搞 |
| **雙軌 Plan** | Coding Plan（按次）+ Agent Plan（AFP 封頂）分開 | 冇直接對應 |
| **ModelArk 免費 tokens** | 500K/LLM + 2M/視覺 + 企業 5M（國際版） | 百煉 1M×90日、Gemini Agent Compute 50h free—量級不同 |

**誠實講**：圖/影片好貴（Seedream ≈100 AFP/張、Seedance 2.0 ≈2,000 AFP/clip）——封頂但**好使就浮動**，報「上限 + buffer」。

---

## 5. 「獨特唔一定獨家」— 行貨一覧（唔好 over-sell）

以下全部都係**市場標準 / 各大廠都有**，攞嚟當賣點會穿煲：

| 行貨 | 邊個都有 |
|---|---|
| A2A protocol | Google 有、超大量 agent 互通 |
| MCP / toolset | OpenAI/Azure/Bedrock 全部支持 |
| OTel / tracing | 業界標準 |
| OAuth2 / JWT / SSO | 標準 |
| IAM / RBAC | 每家雲都有 |
| RAG / 知識庫 | 各家都有（收費方式唔同） |
| Cache / compaction | 各家都有 |
| model fallback | 各家 SDK 都有唔同程度 |
| sandbox / 代碼執行 | 多家有 |
| free tier | 各家都有 |
| function calling / streaming | 兩樣都係行貨 |

> **呢啲係「唔輸」嘅底線，唔係「贏」嘅理由。** 真正贏喺 §2–§4 嗰啲「一體化」位。

---

## 6. 四層疊埋 = 真獨特：「一包乾」checklist

| 你 client 要呢樣… | BytePlus stack | Azure | AWS | Google | 自架 |
|---|---|---|---|---|---|
| Framework（唔使自己揀 vector DB/記憶） | ✅ VeADK 內建 | ❌ 自己接 AI Search | ❌ 自己接 KB | ✅ Vertex 部分 | ❌ 自己揀 |
| 部署上雲（一 call） | ✅ `create_agentkit_app` | ⚠️ Agent Service 重建 | ⚠️ AgentCore 重建 | ⚠️ 自建 | ❌ 自己砌 |
| GPU/sandbox 已包 | ✅ 已入 Plan | ❌ PTU 另收 | ❌ EC2 另收 | ❌ Agent Compute 另計 | ❌ 自己租 |
| 圖/片/語音/向量一個供應商 | ✅ 自家 | ❌ 駁第三方 | ❌ 駁第三方 | ⚠️ Veo 但另收 | ❌ 逐個駁 |
| 出站 secret 托管（唔入 repo） | ✅ Agent Identity | ⚠️ Key Vault 自接 | ⚠️ Secrets Mgr 自接 | ⚠️ 自接 | ❌ 自己管 |
| Audit 7 年 + chain-hash | ✅ 內建 | ⚠️ 自己搭 | ⚠️ 自己搭 | ⚠️ 自己搭 | ❌ |
| 封頂月費可預測 | ✅ AFP | ❌ 浮動 | ❌ 浮動 | ❌ 浮動 | ❌ 逐項 |
| PII 內建攔截 | ✅ LLM-FW 103 | ⚠️ Content Safety 另收 | ⚠️ Guardrails 另收 | ⚠️ 另收 | ❌ |

> **結論**：呢張表就係 selling story——**人哋每一行都要自己砌/另收，BytePlus 係「✓ 內建」**。

---

## 7. 要誠實講嘅反面（定位文件必寫）

| 反面 | 影響 | 點處理 |
|---|---|---|
| **大陸數據主權** | 火山方舟係大陸服務（數據落大陸）；HK PDPO / 金融跨境對口要另傾 | 國際 BytePlus edition / Azure/AWS HK region 並列方案 |
| **超額浮動** | AFP 封頂但好使（Seedance、大量 OCR）超出按量浮動 | 報「上限 + buffer」 |
| **國際 SLA / 文檔 / 全球 region 弱** | 出海、24×7 全球 SLA 客戶要早知 | 用國際版/另一間做全球 |
| **FX** | ¥/$ 波動 | 打入 1 年期方案 |
| **圖/片貴** | Seedream ≈100 AFP/張、Seedance ≈2,000 AFP/clip | 先問 client 有冇多模態、鎖 tier（Large/Max） |
| **模型下線快** | `seed-2.0-pro/code`、`seedance-1.5-pro` 即將下線 | 新項目唔好用標「即將下線」模型 |

---

## 8. 一句市場定位

> **VeADK + AgentKit + BytePlus = 「成條 agent stack + 全部模型」同一間廠嘅一體化平台**——framework 唔使自砌、GPU 已包、多模態獨家、帳單一個數封頂。其他廠每樣都好，但你要自己嵌四、五個供應商先砌到同一嚿嘢；我哋係「**一個數、一條線、一個 support**」。唔喺人哋嘅戰場（全球合規、標價最低、最大模型數）硬撼，喺我哋嘅戰場（一體化、封頂、中文/粵語、多模態一條龍）贏。

---

## 9. 資料來源

| 來源 | URL | 日期 |
|---|---|---|
| VeADK API 參考（install/依賴/config/fallback/Responses API） | 本 repo `veadk-api.html` | 2026 |
| AgentKit CLI 指令大全 | 本 repo `agentkit-cli.html` | 2026 |
| 安全/RBAC/PII/Audit/Observability | 本 repo `veadk-agentkit-rbac-observability.html` | 2026 |
| Vector DB / Cache 管理（8×KB + 7×LTM backend） | 本 repo `veadk-agentkit-vector-cache.html` | 2026 |
| 跨廠商成本對照（AFP / 封頂 / 多模態結論） | 本 repo `veadk-vendor-cost-comparison.html` | 2026 |
| 模型可用性矩陣（Seed 家族 / Seedance tier 鎖位） | https://www.volcengine.com/docs/82379/2366394 | 2026 |
| 火山方舟 Agent Plan 套餐概覽 | https://www.volcengine.com/docs/82379 | 2026 |
| BytePlus ModelArk 方案（國際版免費 tokens） | https://www.byteplus.com/modelark | 2026 |
| 火山方舟 Coding Plan 概覽 | https://www.volcengine.com/docs/82379/1925114 | 2026 |

> **免責**：功能/型號細節係 2026-08-16 公開資訊快照，各平台可能已郁；**功能存在性以各平台官網/控制台為準**。行貨 vs 獨特位嘅判斷係定性（本 repo 觀點），引用前對返官方文檔。HK 定位內容係定性，落 contract 前同法務確認。

---

*Last audit date: 2026-08-16 · 模型/Plan 常常郁，引用前 refetch。*