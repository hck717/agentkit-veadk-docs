# VeADK + AgentKit 閘道 / AI Gateway 解構（AgentKit Gateway + BytePlus AI Gateway + 方舟 AI 加速網閘）

「閘道（Gateway）」喺 AI stack 入面係**所有流量嘅控制點**：邊啲 agent 可以 call 乜、用邊個 model、幾時 fallback、幾多 cache、點計量。BytePlus / Volcengine 有**三層閘**——工具閘、模型閘、API 閘——呢份文件一次過拆清楚三者分工同幾時用。

> **核心心法**：
> 1. **閘唔係「多咗一層嘢」，係「集中控制點」**：統一 entry → 統一 key 管理 → 統一用量 → 統一 fallback/緩存。
> 2. **喺 AgentKit / VeADK 框架層，你 call `model_name` 就自動行方舟 endpoint**——唔使你自己整閘。閘係俾**多供應商、多 project、要管人管數**嗰啲場景用。
> 3. **三隻閘各自為政**：工具閘（MCP）睇 `veadk-agentkit-tools-capabilities.md`，模型閘 / API 閘就係呢份。唔好撈亂。

---

## 0. 快睇：三層閘定位（30 秒記住）

| 閘 | 管啲咩 | BytePlus / Volcengine 產品 | 幾時用 |
|---|---|---|---|
| **① 工具閘（Tool Gateway / MCP Gateway）** | Agent 點 call 外部工具 / 數據源，REST ↔ MCP | **AgentKit Gateway**（MCP service / MCP toolset） | Agent 要連公司現有 API、第三方 MCP Server、Sandbox 工具 |
| **② 模型閘（Model / AI Gateway）** | 統一多模型入口、路由、fallback、緩存、限流 | **BytePlus API Gateway · AI Gateway**；**方舟 AI 加速網閘 / 邊緣大模型閘** | 多供應商 / 多模型、要自動 failover、要慳 cache、要睇清用量 |
| **③ API 閘（API Management）** | 成間公司 API 流量：編認證、限流、監控、版本 | **BytePlus API Gateway（APIG 主體）** | 企業級 API 管治、跨集群 north-south 流量、對外開放 API |

> **Sale 一句**：「BytePlus 一次過俾齊三層閘——AgentKit Gateway 管工具、AI Gateway 管模型、APIG 管成間公司 API。唔使自己砌三套嘢。」

---

## 1. 工具閘：AgentKit Gateway（MCP 統一入口）

AgentKit 內置一個 **MCP-compliant、high-performance gateway**，用嚟將**外部服務同數據源變成 agent-ready tools**：

> 官方原句（byteplus.com/product/agentkit）：*"An MCP-compliant, high-performance gateway connects external services and data sources, turning existing APIs into agent-ready tools."*

### AgentKit Gateway 做三件事

| 能力 | 點做 | 文件 |
|---|---|---|
| **REST API / OpenAPI → MCP tools** | 上傳 OpenAPI spec，Gateway 自動轉成 MCP tools，Agent 以 MCP 方式 call | Integrating existing REST API/OpenAPI as MCP tools |
| **接入現有 MCP Server** | 你已有 MCP server（第三方便可以），直接掛入 AgentKit Gateway，統一入面 | Integrating existing MCP Servers into AgentKit Gateway |
| **統一身分認證 + 監控** | 每個 MCP service / toolset 可配 inbound identity authentication、log、monitoring | Gateway / MCP service / MCP toolset management docs |

### 兩個核心單位：MCP Service vs MCP Toolset

| | **MCP Service** | **MCP Toolset** |
|---|---|---|
| 係啲咩 | 一個後端服務（一個 source of tools） | 手動揀好嘅一組 MCP tools，配 tool-calling 模式 |
| 點建立 | Create MCP service → 加 tools | Create MCP toolset → 加/減 MCP tools |
| 邊個用 | 一個 agent 直接接成個 service | 多個 agent 共享同一 group 嘅 tools，可控 tool 邊個 call 邊個唔 call |
| 認證 | 可設 inbound identity authentication | 可設 inbound identity authentication + tool calling mode |
| 監控 | MCP service monitoring | MCP toolset monitoring |

### 喺 stack 邊個位

```
Agent (runtime)
   │  MCP call
   ▼
AgentKit Gateway  ──(REST/OpenAPI)──► 公司現有 API / 第三方 REST 服務
   │     │  ──(MCP)──────────────► 外部 MCP Server
   │     └──(Sandbox)─────────────► Code/Browser/Skills Sandbox 工具
   ▼
VeADK / AgentKit SDK (MCPToolset / mcp service 接入)
```

> ✅ 對照：**工具 / 能力 tab**（`veadk-agentkit-tools-capabilities.md`）講 MCP/Tools/Skills/A2A 嘅**概念同點喺 code 用**；**呢份**講嗰個「閘」點建、點轉發、點認證、點監控——係平台營運視角。

---

## 2. 模型閘：BytePlus API Gateway · AI Gateway

BytePlus **API Gateway（APIG）** 有專屬 **AI Gateway** 子能力，將「模型接入」提升到「企業 API 管治」級別。

### AI Gateway 六大能力（全部內置插件式）

| 能力 | 做咩 | 對應 APIG 功能 |
|---|---|---|
| **AI multi-model proxy** | 一個入面、多個模型 / 多個 provider，統一 OpenAI 兼容協議 | AI Multi-Model Proxy |
| **AI Model Fallbacks** | 上游掛 → 自動行 fallback 模型（例如 2.0-pro → 2.0-lite），唔使改 client | AI Model Fallbacks |
| **LLM load-aware routing** | 按上游負載 / 延遲路由到最鬆嗰個（避免單一 provider 爆 TPM） | LLM Load-Aware Routing |
| **LLM session affinity** | 同一 session 綁定同一模型 instance（長時間 conversation 唔斷上下文） | LLM Session Affinity Routing |
| **MCP session persistence** | 經 APIG 嘅 MCP 流量做到 session 持續 | MCP Session Persistence |
| **Global rate limiting** | 成個閘統一限流，唔使逐模型逐 key 各自限 | Global Rate Limiting Plugin |

### 同「開源 AI Gateway」比較

| | BytePlus APIG AI Gateway | 自建開源（LiteLLM/AISIX/Bifrost 等） |
|---|---|---|
| 部署 | 托管，免運維 | 你自己行，要管高可用 |
| 流量管治 | APIG 全套：鑑權、限流、監控、日誌、版本出晒 | 要另一套嘢夾 |
| 模型接入 | Ark 原生 + OpenAI 兼容，識得方舟協議透傳 | 一般 OpenAI 兼容，方舟特殊 protocol 要自己 patch |
| LLM-aware 插件 | load-aware routing / session affinity 內置 | 要自己開發 |
| 適合 | 企業要管治、多 provider、要 SLA | 玩票、內部實驗、要極端客制 |

> ⚠️ APIG 係**要錢嘅獨立產品**（計 Gateway 實例 + 流量），而**方舟上嘅模型 call 本身**先係 Agent Plan / AFP 收費。閘同模型係兩張單——quote 畀客要分開講。

---

## 3. 方舟 AI 加速網閘（統一多模型入口 + 加速/緩存）

Volcengine **AI 加速網閘（DCDN 產品線下）**，以及**邊緣大模型閘（Edge AI Gateway）**，解決「call 好多個唔同 provider 嘅模型」嘅痛：**一個地址、OpenAI 兼容、自動 failover 同緩存**。

### 核心特性

| 特性 | 說明 | 影響 |
|---|---|---|
| **統一多模型入口** | 方舟、第三方供應商、自部署模型全部收到一個 `BaseUrl` | 客戶端淨係識一個 address，SDK 唔使改 |
| **兩大調用協議** | ① **OpenAI 兼容**（自帶 key 由閘管）；② **協議透傳**（保留供應商原生 API Key 同協議） | 透傳 = 淨係加速，冇緩存/路由/限流 |
| **語義緩存** | 相似請求喺邊緣直接回覆，唔使再 call 上游 model | **慳成本 + 慳延遲**（兩者都慳） |
| **負載均衡 / 主備容災** | 多條上游 model 之間分流，掛自動切 | 高可用 |
| **故障轉移 / 自動重試** | 上游 fail → 自動行 fallback / 重試 | 唔使 code 做 retry |
| **邊緣就近接入** | 全球邊緣節點就近收 request，送到最近上游 | 端側體驗（例如出海 app） |
| **支援 15+ 模型供應商** | 方舟 + 第三方 + 私有化部署模型 | 一個閘全覆蓋 |

### 接入方式：淨係換 endpoint

```python
from veadk import Agent

# 原本直接 call 方舟：
import os
os.environ["MODEL_AGENT_API_BASE"] = "https://ark.cn-beijing.volces.com/api/v3/"
os.environ["MODEL_AGENT_KEY"] = os.getenv("ARK_API_KEY")
agent = Agent(
    model_name="doubao-seed-2-1-pro-260628",
    model_provider="openai",      # 方舟係 OpenAI 兼容協議
    enable_responses=True,
)

# 行 AI 加速網閘：淨係換 API base + 閘 key，code 一行唔使改
os.environ["MODEL_AGENT_API_BASE"] = "<你的網閘實例 BaseUrl>"
os.environ["MODEL_AGENT_KEY"] = os.getenv("GATEWAY_API_KEY")
agent = Agent(
    model_name="doubao-seed-2-1-pro-260628",
    model_provider="openai",
    enable_responses=True,
)
```

> 🎯 **透傳模式記住**：協議透傳唔支援模型路由、語義緩存同限速——淨係「加速」。要齊功能，一定要行 OpenAI 兼容模式並喺閘配置 API Key。AgentKit Serving（agentkit build / deploy）揀 endpoint 時，都係喺部署配置入面填網閘 BaseUrl 就完事。

### 邊緣大模型閘（Edge AI Gateway）額外件事

- 部署喺**全球邊緣計算節點**，端側 app 就近接入，延遲明顯低。
- 支援四類**調用渠道**：平台預置智能體、平台預置模型、自有三方模型、自有三方智能體。
- 內置**語義緩存**減少回源；支援**故障轉移 + 調用順序配置**。
- 用「**網閘訪問密鑰**」做授權/鑑權/限流——一個 key 就管晒。

---

## 4. Coding Plan 網閘（AI Coding 專用）

方舟 **Coding Plan** 有個專門網閘，將多款 Code 模型（Doubao-Seed-Code、GLM、Kimi-K2.5 等）接入主流編程工具（Claude Code / Cursor / Cline / OpenCode / TRAE / Roo Code），**套餐額度喺所有工具之間共享**。

| 工具協議 | 必須用嘅 Base URL | 備註 |
|---|---|---|
| Anthropic 兼容工具 | `https://ark.cn-beijing.volces.com/api/coding` | 例如 Claude Code |
| OpenAI 兼容工具 | `https://ark.cn-beijing.volces.com/api/coding/v3` | 例如 Cursor / OpenCode |
| 模型 | `doubao-seed-2.0-code` / `glm-4.7` / `kimi-k2.5`；或 `ark-code-latest`（控制台統一管理，3–5 分鐘生效，支援 Auto 智能匹配） | 支援實時切模型 |

> ⚠️ **必讀避雷**：唔好用一般網閘 URL 去 call Coding Plan——咁樣唔會扣套餐額度，反而會**照 API 計費**，仲可能被當成違規使用導致訂閱停用。Coding Plan 一定要用專屬 URL。

---

## 5. 決策樹：我到底需唔需要「閘」？

```
我用緊啲咩？
│
├─ 淨係用 AgentKit + 方舟一個 provider（最常見）
│     └─ 唔使閘。framework 層 model_name 直連方舟，算力/計費由 Agent Plan 包。
│
├─ Agent 要 call 公司現有 REST API / 第三方 MCP server
│     └─ 用 AgentKit Gateway（MCP service / MCP toolset），唔使買第二樣嘢。
│
├─ 多 supplier / 多 model，怕掛、想統一 key、想慳 error retry
│     └─ 方舟 AI 加速網閘（統一入口 + fallback + 語義緩存）——最貼、最慳。
│
├─ 企業級：要管 API 認證、限流、監控、版本、跨集群流量
│     └─ BytePlus API Gateway（APIG）AI Gateway——管治第一優先。
│
└─ 係咪要你嘅 client / SDK 淨睇一個 endpoint 就搞掂晒所有模型
      └─ 全部都要——AI 加速網閘或者 APIG AI Gateway 都做到，視乎要唔要企業管治。
```

---

## 6. 同幾個 tab 嘅邊界（一圖分清楚）

| 呢份 tab | 其他 tab | 分界 |
|---|---|---|
| **閘道 Gateway** | ServingKit（`veadk-agentkit-serving-kit.md`） | ServingKit = **自建/私人模型上線跑推理**（vLLM/SGLang/Dynamo）；閘 = **統一入口控唔同 provider 嘅模型同工具**。自建咗模型都係掛喺閘後面俾人 call。 |
| **閘道 Gateway** | 工具 / 能力（`veadk-agentkit-tools-capabilities.md`） | 工具 tab 講 MCP/Tools/Skills **概念 + code 點用**；閘 tab 講 **平台營運**（點建閘、認證、監控）。 |
| **閘道 Gateway** | 安全 / 可觀測（`veadk-agentkit-rbac-observability.md`） | 閘係**執行入口**（認證/限流喺閘做）；安全 tab 係**成個 stack 嘅策略**（RBAC/PII/Audit/Guardrail）。閘閘住入，個別 agent 權限另計。 |
| **閘道 Gateway** | 計價（`veadk-agentkit-pricing.md`） | 模型 call 本身行 Agent Plan / AFP；閘行 APIG 獨立計費（攞得清清楚楚）。 |

---

## 7. 避雷 + 成本意識

> ⚠️ **避雷五連**：
> 1. **Coding Plan 一定用專屬 URL**，否則照計費 + 可能封。 （§4）
> 2. **協議透傳冇緩存冇路由冇限流**——淨係加速。見 §3。
> 3. **閘唔代替 key 管理責任**：閘集中咗 key，但泄密責任喺你；API Key 照樣要用環境變量，唔好 commit。
> 4. **模型 fallback 要同價位**：fallback 到平 model 慳錢，fallback 到貴 model 會喺你唔覺時爆成本——fallback list 排好「平 → 貴」。
> 5. **語義緩存唔係萬能**：高動態 prompt（用戶名、日期、隨機數）命中率低；系統 prompt 穩定先有得慳。
>
> 🎯 **慳錢角度**：行 AI 加速網閘，system prompt + 固定 prefix 行語義緩存，配合方舟隱式 cache（cached input ≈ 標準價 ~20%），命中嗰部分慳得好多。成本明細仍然睇 `veadk-agentkit-pricing.md`——**閘費同模型費係兩張單**。

---

## 8. 資料來源

| 來源 | URL | 日期 |
|---|---|---|
| AgentKit 產品頁（MCP gateway 原句） | https://www.byteplus.com/en/product/agentkit | 頁面日 |
| AgentKit Gateway overview | https://docs.byteplus.com/api/docs/agentkit/MCP_Overview | 2026-08-17 |
| Gateway FAQ | https://docs.byteplus.com/en/docs/agentkit/Gateway_FAQ | 2026-02-10 |
| BytePlus API Gateway · What is the AI Gateway | https://docs.byteplus.com/en/docs/apig/What_is_the_AI_Gateway | 2026-08-12 |
| AI Gateway 功能清單（Multi-Model Proxy / Fallbacks / routing / MCP） | https://docs.byteplus.com/en/docs/apig （AI Gateway 章節） | 頁面日 |
| Volcengine AI 加速網閘創建實例 | https://www.volcengine.com/docs/6559/2288086 | 2026-08-06 |
| Volcengine 邊緣大模型閘 FAQ | https://www.volcengine.com/docs/6893/1263408 | 2026 |
| 方舟 Coding Plan API 網閘（兩個 Base URL + ark-code-latest） | https://www.volcengine.com/article/37839、37843 | 2026 |
| 方舟 OpenAI 兼容接入（base_url / api_key / 模型開通） | https://therouter.ai/zh/blog/volcengine-ark-doubao-api-complete-guide/ | 2026-06 |

> **免責**：閘嘅功能、要唔要獨立訂閱、定價會隨 BytePlus / Volcengine 產品迭代而變；§3 語義緩存命中率、§2 fallback 行為屬官方特性描述，實際效果視乎 prompt 同流量。引用前 check 一遍最新文檔同價目。

---

*Last audit date: 2026-08-17 · Gateway 產品線（APIG AI Gateway、AI 加速網閘、邊緣大模型閘）功能同價格會隨產品迭代而變，引用前 check 一遍。*