# VeADK + AgentKit 工具 / 能力參考 — Functions / MCP / A2A / Skills

呢份文件講 Agent 點樣「攞到對外能力」——即係所謂嘅 **工具層**。一個 agent 淨係識 chat 唔算 agent：要係「隻手」得，先可以攞資料、執行操作、同人哋嘅系統同其他 agent 協作。呢度由淺入深：先睇 **Function calling / 內建 tools**（agent 自己嘅手），再睇 **MCP**（標準化插頭，接外部 tool server）、**A2A**（agent 之間團隊分工）、同埋 **Skills**（師傅手法：可複用指令/流程）。

一句講晒：**MCP = 標準插頭，A2A = 團隊分工，Skills = 老師傅手法**，夾埋先係真正嘅 agent 平台，唔係得個 chat。呢份配合 `agentkit-cli.md`（mcp service / skill / sandbox 指令）、`veadk-api.md`（Agent(tools=...) / MCPToolset）、`agentkit-sdk.md`（A2aApp / MCPApp）同 `veadk-agentkit-ai-concepts.md` §9 一齊睇；安全嗰層（guardrail / filter）淨係帶過，主要落喺安全 tab。

---

## 0. 一句定位 + 快睇（Tools vs Skills vs MCP vs A2A）

| 能力 | 係咩 | 幾時用 | 例子（BytePlus/Volcengine） |
|---|---|---|---|
| **Function calling / Tools** | Agent 直接 call 嘅可執行函式（內建或自訂） | 單一私有函數、agent 自己嘅手 | VeADK `web_search`、`run_code`；`@agent.tool` 自訂 |
| **MCP（Model Context Protocol）** | **標準化工具接口**，接外部 tool server | 接入第三方 / 內部現成工具、跨 agent 重用 | `MCPToolset` 接入；`agentkit mcp service` |
| **A2A（Agent-to-Agent）** | Agent 之間嘅通訊協議 | 多 agent 分工、pipeline / 平行任務 | Invoice Pipeline 五 agent、Movie Generator |
| **Skills** | 預包裝指令/流程 bundle（唔淨係函式） | 跨 agent 共用嘅工作流程 / 語氣 / 格式 | `agentkit skill`、`agentkit onboard` |

> 🎯 **記法**：Tools 係「單手動作」，MCP 係「標準插頭」，A2A 係「成隊人」，Skills 係「師傅嘅手法」。四樣唔係互相取代，係**層層疊**。

---

## 1. Function Calling / 內建 Tools — Agent 隻手

### 1.1 概念

Function calling = Model 喺生成過程中出 JSON tool call，由框架執行函式、將結果塞返 context 再繼續生成。呢個係 agent「識做嘢」嘅最底層機制，同一個 model 喺 VeADK 就係 `Agent(tools=[...])`。

### 1.2 Built-in tools 一覽

VeADK 內建咗成批工具，唔使自己寫 API 整合：

| 工具 | 做咩 | 幾時用 |
|---|---|---|
| `web_search` | 網頁搜尋 | Agent 要最新資訊 / 外部資料 |
| `web_fetch` | 攞指定 URL 嘅網頁內容 | 有明確網址要讀內容 |
| `document_compressor` | 壓縮長文檔先入 context | 文件太長、慳 token |
| `run_code` / `run_python` | 沙箱執行 Python 代碼 | 計數、分析、處理檔案 |
| `image_generation` | 用 **Seedream** 生圖 | 角色參考圖、mood board（~100 AFP/img）· 詳情 → seedream tab |
| `video_generation` | 用 **Seedance** 生片 | 每個 scene 一條 clip（~2,000 AFP/clip）· 詳情 → seedance tab |
| `document_understanding` | 文檔理解（PDF/掃描件） | 契約、發票、長文件抽取 |
| TTS / ASR | 火山語音（合成 / 識別） | 語音入出、配音 |

### 1.3 自訂 Function Tool

```python
import asyncio
from google.adk.tools.tool_context import ToolContext
from veadk import Agent, Runner

def calculator(a: float, b: float, operation: str) -> dict:
    """簡單計算器
    Args:
        a: 第一個數字
        b: 第二個數字
        operation: add / subtract / multiply / divide
    """
    if operation == "add":
        return {"result": a + b, "status": "success"}
    return {"status": "error", "message": f"唔支援嘅運算: {operation}"}

agent = Agent(
    name="computing_agent",
    instruction="用 calculator 工具做用戶要求嘅運算。",
    tools=[calculator],
)
response = asyncio.run(Runner(agent=agent).run("2 加 3 等於幾？"))
```

> ✅ **Docstring 最重要**：Model 靠 function name + docstring 決定幾時 call、傳咩參數，所以 `Args:` 一定要寫得清。

### 1.4 ToolContext + LongRunningFunctionTool

`ToolContext` 提供共享狀態畀工具之間傳嘢（例如計 call 次數、記 user_id）；長任務就包一層 **LongRunningFunctionTool**，即刻回 `pending` + `task-id`，由框架異步追蹤，唔使阻塞成條 thread：

```python
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.long_running_tool import LongRunningFunctionTool

def message_checker(user_message: str, tool_context: ToolContext) -> str:
    count = tool_context.state.get("message_checker_calls", 0) + 1
    tool_context.state["message_checker_calls"] = count
    return f"Checked: {user_message.upper()} (call {count})"

def big_data_processing(data_url: str) -> dict:
    return {"status": "pending", "data-url": data_url, "task-id": "big-data-1"}

agent = Agent(name="hybrid_agent",
              tools=[message_checker, LongRunningFunctionTool(func=big_data_processing)])
```

> 🎯 幾時用 built-in，幾時自訂？「攞最新資料」→ `web_search`；「計數/處理」→ `run_code`；「有現成 API」→ 自訂 function tool 或 MCP（§2）。

---

## 2. MCP（Model Context Protocol）深入版

### 2.1 MCP 係咩、解決咩問題

MCP = Model Context Protocol，**開放標準工具協議**（JSON-RPC 2.0）。冇 MCP 之前，每個 tool 都係自家協議，CRM / Slack / DB 各自寫一個 integration，接得越多越係地獄；MCP 將「工具 = 一個 server 暴露 tools/resources/prompts」變成標準，**一次接入、任何 MCP client 都用得**（2024+ 業界事實標準）。

### 2.2 三種 Transport

| Transport | 通道 | 幾時用 |
|---|---|---|
| **stdio** | 本地 process，透過 stdin/stdout 通訊 | 本地開發、同機 sidecar |
| **SSE（Server-Sent Events）** | HTTP 事件流 | 舊款遠端 MCP（逐步淘汰） |
| **HTTP（Streamable HTTP）** | 現代遠端 MCP 標準 | **公網 / 生產主流** |

### 2.3 Client vs Server（邊個係邊個）

```
Agent（MCP client） ←── JSON-RPC 2.0 ──→ MCP server（工具 / 資源 / prompts）
```

| 角色 | 做咩 | 喺 stack 邊度 |
|---|---|---|
| **MCP client** | Agent 側接入外部 server，攞 tools 入 context | VeADK `MCPToolset`；`AgentkitMCPApp` |
| **MCP server** | 開放自己嘅工具俾人駁 | `agentkit mcp service` 部署嘅鏡像 |

### 2.4 接入例子（VeADK）

```python
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams
from veadk import Agent

mcp_toolset = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://your-mcp-service.com/mcp",
        headers={"Authorization": "Bearer <token>"},
    ),
)
agent = Agent(name="mcp_agent", tools=[mcp_toolset])
```

AgentKit SDK 仲有 `AgentkitMCPApp` — MCP service 一鍵變 Agent，配合 `@mcp_app.tool` / `@mcp_app.agent_as_a_tool`（連子 agent 都可以當 tool）。

### 2.5 AgentKit CLI — 自己開 MCP Server

```bash
# 公網 + API Key
agentkit mcp service create \
  --name customer-tools \
  --image-url cr-cn-beijing.volces.com/agentkit/customer-tools:latest \
  --inbound-api-key-name primary-key \
  --env LOG_LEVEL=INFO

# 私網（internal VPC，唔出公網）
agentkit mcp service create --name internal-tools \
  --image-url cr-cn-beijing.volces.com/agentkit/internal-tools:latest \
  --network private --vpc-id vpc-xxxxx --subnet-id subnet-xxxxx

# 自訂 JWT 認證
agentkit mcp service create --name jwt-protected-tools \
  --image-url cr-cn-beijing.volces.com/agentkit/jwt-tools:latest \
  --inbound-auth custom-jwt --inbound-discovery-url https://... --inbound-allowed-client web-client

agentkit mcp service list / show customer-tools / delete customer-tools
agentkit add tool ...          # 將某個 tool 綁定到 agent / harness
```

### 2.6 安全（深探喺安全 tab）

| 風險 | 防護 |
|---|---|
| MCP server 認證 | AK-SK / OAuth2 / JWT（`--inbound-auth`） |
| 憑證注入 | Agent Identity 托管 + 自動輪換，**唔入 repo** |
| 過度授權 | 最小權限：每個 agent 只掛要用嘅 tools（toolset） |
| 入參 / 返回 | `content_safety` Before/After Tool（見 §5） |

> ⚠️ **Remote MCP 好處**：tools 唔使同 agent 同一部 server——agent 喺任何地方跑，都 call 同一個 MCP endpoint。但公開 endpoint 就一定要有認證，唔好裸奔。

---

## 3. A2A（Agent-to-Agent）— 多 Agent 協作

### 3.1 A2A 係咩、同 MCP 分別

A2A（Agent2Agent，Google DeepMind 主導嘅開放協議）係** agent ↔ agent** 嘅通訊，配合 **agent registry** 做服務發現。同 MCP 嘅分野一條線講清：

| | **MCP** | **A2A** |
|---|---|---|
| 關係 | **Agent → tool**（我 call 你嘅工具） | **Agent → Agent**（我俾成個任務你） |
| 粒度 | 單一 function | 成個 agent / 專責任務 |
| 編排 | 無 | Registry + pipeline / parallel |
| 例子 | MCPToolset 接 CRM | Invoice Pipeline OCR → 翻譯 → 驗證 |

### 3.2 喺 stack 點落地

CLI 用 harness 加 A2A registry；SDK 用 `AgentkitA2aApp` 將 agent 包成 A2A service：

```bash
# 加 A2A Registry（top-k 檢索 agent）
agentkit add harness --name my-harness --registry-space-id as-xxx --registry-top-k 3

# 註冊已部署 harness 到 A2A（public / private）
agentkit add harness --name my-harness \
  --register-self --register-space-id as-xxx --register-network-type public
```

```python
from agentkit.a2a_app import AgentkitA2aApp

a2a_app = AgentkitA2aApp(name="ocr_agent", model_name="seed-2-0-lite-260228")

@a2a_app.agent_executor(name="ocr_agent")
async def ocr_flow(image_data: dict) -> dict:
    raw = await ocr_agent.run_async(messages=image_data["base64"])
    return await call_a2a_agent("translation-agent", raw)   # 再 call 下一隻
```

### 3.3 Project 例子（見 projects 目錄）

| Project | Pipeline | 點解用 A2A |
|---|---|---|
| **Invoice Pipeline** | OCR → 翻譯 → 驗證 → 匯總 → HITL 審批 | 每個 agent 獨立 deploy / 獨立 eval；驗證 agent 可 loopback 叫 OCR 重讀 |
| **Movie Generator** | 研究 → 劇本 → 分鏡 → 每 scene 生片 → 合併 | Agent4（video gen）**平行**生成 N 條 clip，橫向 scale |

### 3.4 同步調用 + 並行（performance 參考）

```python
import asyncio

storyboard = await storyboard_agent.run_async(messages=script)

# 平行：N 個 scene 同時 call video-gen agent
tasks = [
    call_a2a_agent(f"video-gen-agent-{i % NUM_INSTANCES}", scene)
    for i, scene in enumerate(storyboard["scenes"])
]
clip_results = await asyncio.gather(*tasks)
```

---

## 4. Skills — 複用 Prompt 工程

### 4.1 Skill 係咩

**Skills** = 預包裝嘅「指令 / 流程」bundle：唔淨係一個函式，而係成段 instructions + 可選工具 + 檔案模板，畀其他 agent 攞去用。AgentKit 用 `agentkit skill` 管理（見 README / `agentkit-cli.md` §Skills）：

```bash
agentkit skill list / show sk-xxxxxxxx / versions sk-xxxxxxxx
agentkit skill spaces            # 技能空間
agentkit onboard                 # 安裝內置技能包
```

### 4.2 Skills vs Tools

| | **Tools** | **Skills** |
|---|---|---|
| 本質 | 可執行函式（做嘢） | 指令 / 流程（點做） |
| 載體 | Code / API call | Instructions + 模板 + 可選 tools |
| 複用單位 | 一次 call | 成個工作流程 |
| 例子 | `web_search` | 「寫定期報告」嘅成套路數 |

### 4.3 例子

- **定期報告 skill**：包「格式 + 每週 summary 步驟 + 用邊啲 data source」，任何 agent 收到報告任務即套用。
- **客服語氣 skill**：包「語氣規則 + 唔講啲咩 + 返工時間話術」，所有客服 agent 共享同一人設。

> 🎯 揀錯嘅訊號：同一個 workflow 喺幾隻 agent 度 copy-and-paste 咗第三次——嗰陣就應該抽做 skill。

---

## 5. Guardrail / Input-Output Filter（工具層要知道嘅安全）

呢度淨係帶過：**Guardrail**（攔有害 / 敏感內容，火山 LLM-FW 四點 Before/After Model + Before/After Tool）同 **Filter**（清潔 input/output、PII masking）係安全範疇嘅嘢，同工具層最密切嗰個位係 **Before/After Tool**——工具 call 前 check 入參、工具返回後 scrub PII。

> ⚠️ 工具係 agent 唯一「對外出手」嘅位，所以 guardrail 四點入面，**Before/After Tool** 就係工具層直接安全控制。詳細內容（LLM-FW categories、過濾機制、授權輪換）睇 `veadk-agentkit-rbac-observability.md`（安全 tab）。

---

## 6. 揀工具嘅決策樹 + Sales 一句

```
要外部能力？
├─ 又要 language model 生成 → 直接用 agent（唔使 tool）
├─ 要攞資料/執行操作（DB/API/網頁）→ function tool（veadk Agent(tools=...)）
├─ 已有現成工具 server（第三方/內部）→ MCP client 接入
├─ 要俾其他人/agent 用自己嘅能力 → MCP server 或 A2A registry
└─ 要另一隻 agent 完成專責任務 → A2A
```

| Trigger | 用 | 詳見 |
|---|---|---|
| 攞最新資訊 / 計數 / 生圖生片 | Built-in tools（`web_search` / `run_code` / seedream / seedance） | §1 |
| 單一私有函數 | 自訂 function tool | §1.3 |
| 長任務唔想 block | `LongRunningFunctionTool` | §1.4 |
| 接外部 / 內部現成工具 | MCP client（`MCPToolset` / `AgentkitMCPApp`） | §2 |
| 開放自己工具俾人 | `agentkit mcp service` | §2.5 |
| 多 agent 分工 / 平行 | A2A（`AgentkitA2aApp` + registry） | §3 |
| 重複 workflow 複用 | Skills（`agentkit skill`） | §4 |

> **Sale 一句**：「Agent 嘅價值喺『隻手』——MCP 係標準插頭，A2A 係團隊分工，Skills 係老師傅手法。三樣夾埋先係真正嘅 agent 平台，唔係得個 chat。」

---

## 7. 資料來源

| 來源 | URL | 日期 |
|---|---|---|
| VeADK API 參考（Tools / MCP Toolset / ToolContext / LongRunningFunctionTool / built-in tools） | `references/veadk-api.md` | 2026-07-30 |
| AgentKit SDK 參考（A2aApp / A2aAgent / Tool / MCPApp / agent_as_a_tool） | `references/agentkit-sdk.md` | 2026-07-30 |
| AgentKit CLI 指令大全（mcp service / skills / sandbox） | `references/agentkit-cli.md` | 2026-07-31 |
| AI 概念百科 §9（MCP / Tools / Skills 概念） | `references/veadk-agentkit-ai-concepts.md` | 2026-08-17 |
| MCP 規範官方 | https://modelcontextprotocol.io | 頁面日 |
| A2A Protocol 官方（Google DeepMind） | https://a2a-protocol.org | 頁面日 |
| BytePlus AgentKit 官方 | https://www.byteplus.com/solutions/ai-cloud-native-agentkit | 頁面日 |

> **免責**：MCP transport（stdio / SSE / HTTP）、A2A registry、built-in tools 清單以各官方文檔同當刻 SDK 版本為準；spec 常改，引用前 refetch。

---

*Last audit date: 2026-08-17 · 工具清單 / MCP / A2A 規格常常郁，引用前 refetch。*