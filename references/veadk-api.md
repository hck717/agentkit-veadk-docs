# VeADK API 參考

呢份文件記錄晒 VeADK（火山引擎智能體開發框架）嘅 Python 程式碼範例，用粵語解釋用途同用法。

---

## 安裝

```bash
# 已發佈版本（Preview 基線 1.0.9）
pip install "veadk-python==1.0.9"

# 預覽源碼（GitHub 主線）
git clone --depth 1 https://github.com/volcengine/veadk-python.git
cd veadk-python
uv venv --python 3.12
uv sync --all-extras
uv pip install -e .
```

### 可選依賴組

```bash
pip install "veadk-python[extensions]"    # 飛書渠道、Cozeloop、LlamaIndex
pip install "veadk-python[codex]"         # Codex 運行時
pip install "veadk-python[database]"      # Redis、MySQL、VikingDB、mem0
pip install "veadk-python[eval]"          # DeepEval 評測
pip install "veadk-python[a2ui]"          # A2UI 富界面
pip install "veadk-python[harness]"       # Harness 服務
```

---

## 配置模型

### config.yaml（推薦）

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

### 環境變數（快速起動）

```bash
export MODEL_AGENT_API_KEY="<your-api-key>"
export MODEL_AGENT_NAME="doubao-seed-2-1-pro-260628"  # 可選
export MODEL_AGENT_API_BASE="https://ark.cn-beijing.volces.com/api/v3/"  # 可選
```

---

## Agent 基本用法

### 最簡單嘅 Agent

```python
from veadk import Agent
import asyncio

agent = Agent()
res = asyncio.run(agent.run("用一句話介紹火山引擎。"))
print(res)
```

### 指定模型

```python
from veadk import Agent

agent = Agent(
    model_name="doubao-seed-2-1-pro-260628",
    model_provider="openai",
)
```

### Fallback 模型（主模型不可用時自動回退）

```python
agent = Agent(
    model_name=["doubao-seed-2-1-pro-260628", "deepseek-r1-250528"],
)
```

### 完整指令同描述

```python
agent = Agent(
    name="customer_support",
    description="處理客戶查詢嘅智能體",
    instruction="你係一個專業嘅客服助手，請用中文禮貌回覆。",
)
```

---

## Responses API（多模態 + 上下文緩存）

### 啟用

```python
from veadk import Agent

agent = Agent(enable_responses=True)
```

### 多模態輸入（圖片）

```python
import os
from google.genai import types
from google.genai.types import FileData

local_path = os.path.abspath("example.png")
message = types.UserContent(
    parts=[
        types.Part(text="描述一下呢張圖片"),
        types.Part(
            file_data=FileData(
                file_uri=f"file://{local_path}",
                mime_type="image/png",
            )
        ),
    ],
)
```

### 上下文管理（清除舊思維鏈）

```python
agent = Agent(
    enable_responses=True,
    model_extra_config={
        "context_management": {
            "edits": [
                {
                    "type": "clear_thinking",
                    "keep": {"type": "thinking_turns", "value": 1},
                }
            ]
        }
    },
)
```

---

## Runner（執行智能體）

```python
from veadk import Agent, Runner

agent = Agent(name="assistant")
runner = Runner(agent=agent, app_name="demo")

# 同步執行
res = await runner.run(messages="你好", user_id="user-42", session_id="session-1")

# 流式事件
async for event in runner.run_async(
    messages="講個故仔",
    user_id="user-42",
    session_id="session-1",
):
    print(event)
```

---

## 短暫記憶（ShortTermMemory / Session）

### Session 管理 API

你可以直接用 `runner.session_service` 或 `stm.session_service` 管理 Session：

```python
# 創建新 Session
session = await stm.create_session(
    app_name="my_app",
    user_id="user-42",
    session_id="session-1",
)

# 攞返現有 Session
session = await stm.get_session(
    app_name="my_app",
    user_id="user-42",
    session_id="session-1",
)

# 列出某用戶嘅 Session
sessions = await stm.list_sessions(
    app_name="my_app",
    user_id="user-42",
)

# 刪除 Session
await stm.delete_session(
    app_name="my_app",
    user_id="user-42",
    session_id="session-1",
)

# 追加事件到 Session
await stm.append_event(
    app_name="my_app",
    user_id="user-42",
    session_id="session-1",
    event=event,
)
```

### Backend 選擇

```python
from veadk.memory.short_term_memory import ShortTermMemory

# 本地記憶（程序重啟後消失）
stm = ShortTermMemory(backend="local")

# SQLite（單機持久化）
stm = ShortTermMemory(backend="sqlite", local_database_path="./stm.db")

# MySQL
stm = ShortTermMemory(backend="mysql", db_url="mysql://user:pass@host/db")

# PostgreSQL
stm = ShortTermMemory(backend="postgresql", db_url="postgresql://user:pass@host/db")
```

### 駁 Runner

```python
import asyncio
from veadk import Agent, Runner
from veadk.memory.short_term_memory import ShortTermMemory

stm = ShortTermMemory(backend="sqlite", local_database_path="./stm.db")
agent = Agent(name="memory_agent", instruction="記住用戶話畀你嘅資訊。")
runner = Runner(agent=agent, short_term_memory=stm, app_name="memory_demo")

async def main():
    sid = "user-42-chat"
    # 第一輪：自我介紹
    print(await runner.run(messages="我叫小明，最鍾意藍色。", session_id=sid))
    # 第二輪：Agent 記得上輪講過嘢（因為同一 session_id）
    print(await runner.run(messages="我叫咩名？鍾意咩顏色？", session_id=sid))

asyncio.run(main())
```

### 上下文壓縮（防止 session 太長）

```python
from google.adk.apps.app import App, EventsCompactionConfig

app = App(
    name="my_agent",
    root_agent=agent,
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=3,  # 每 3 輪壓縮一次
        overlap_size=1,         # 保留最後 1 個事件
    ),
)
```

自定義壓縮器（用 LLM 做摘要）：

```python
import os
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.apps.llm_event_summarizer import LlmEventSummarizer
from google.adk.models.lite_llm import LiteLlm

summarizer_llm = LiteLlm(
    model="volcengine/doubao-seed-2-1-pro-260628",
    api_key=os.environ["MODEL_AGENT_API_KEY"],
    api_base=os.environ.get("MODEL_AGENT_API_BASE",
        "https://ark.cn-beijing.volces.com/api/v3/"),
)

my_compactor = LlmEventSummarizer(
    llm=summarizer_llm,
    prompt_template="請總結呢段對話，保留關鍵實體同時間線。",
)

app = App(
    name="my_agent",
    root_agent=agent,
    events_compaction_config=EventsCompactionConfig(
        compactor=my_compactor,
        compaction_interval=5,
        overlap_size=1,
    ),
)
```

---

## 長期記憶（LongTermMemory）

### Backend 選擇

```python
from veadk.memory.long_term_memory import LongTermMemory

# 本地調試
ltm = LongTermMemory(backend="local", app_name="ltm_demo")

# 生產推薦：VikingDB
ltm = LongTermMemory(backend="viking", app_name="ltm_demo")

# Mem0
ltm = LongTermMemory(backend="mem0", app_name="ltm_demo")

# OpenSearch / Redis
ltm = LongTermMemory(backend="opensearch", app_name="ltm_demo")
ltm = LongTermMemory(backend="redis", app_name="ltm_demo")

# OpenViking / TOS Context
ltm = LongTermMemory(backend="openviking", app_name="ltm_demo")
ltm = LongTermMemory(backend="tos_context", app_name="ltm_demo")
```

### 綁定到 Agent

```python
from veadk import Agent, Runner
from veadk.memory.long_term_memory import LongTermMemory

ltm = LongTermMemory(backend="viking", app_name="support_agent")

agent = Agent(
    name="ltm_agent",
    instruction="如果答案可能喺過往對話入面，用 load_memory 工具搵返。",
    long_term_memory=ltm,
)
runner = Runner(agent=agent, app_name="support_agent")
```

### 手動保存會話

```python
await ltm.add_session_to_memory(completed_session)
```

### 手動檢索

```python
response = await ltm.search_memory(
    app_name="ltm_demo",
    user_id="user-42",
    query="favorite project",
)
print(response.memories)
```

### 自動保存（auto_save_session）

```python
agent = Agent(
    name="ltm_agent",
    auto_save_session=True,
    long_term_memory=LongTermMemory(backend="viking", app_name="ltm_demo"),
)
```

### 跨會話完整範例

```python
import asyncio
from veadk import Agent, Runner
from veadk.memory.long_term_memory import LongTermMemory

APP_NAME = "ltm_demo"
USER_ID = "user-42"

def build_runner() -> Runner:
    ltm = LongTermMemory(backend="local", app_name=APP_NAME)
    agent = Agent(
        name="ltm_agent",
        instruction="當用戶問起之前講過嘅嘢，用 load_memory 工具去回憶。",
        long_term_memory=ltm,
        auto_save_session=True,
    )
    return Runner(agent=agent, app_name=APP_NAME, user_id=USER_ID)

async def main():
    runner = build_runner()
    # Session 1：記錄事實
    print(await runner.run(
        messages="記低：我對花生過敏，而且我係素食者。",
        session_id="session-1",
    ))
    # Session 2（全新 session）：Agent 會 load_memory 記得返
    print(await runner.run(
        messages="幫我推薦一道啱我嘅菜。",
        session_id="session-2",
    ))

asyncio.run(main())
```

---

## 知識庫（KnowledgeBase / RAG）

### 基本用法（local Backend）

```python
from veadk.knowledgebase import KnowledgeBase

kb = KnowledgeBase(backend="local", index="company_faq")

# 加文字
kb.add_from_text([
    "公司標準年假為每年 15 天，入職滿一年起享受。",
    "經主管批准後，員工每週最多可 remote 2 天。",
])

# 加檔案
kb.add_from_files(["./docs/policy.pdf"])

# 加目錄
kb.add_from_directory("./docs")

# 直接檢索
entries = kb.search(query="年假", top_k=3)
for entry in entries:
    print(entry.content)
```

### 綁定到 Agent

```python
import asyncio
from veadk import Agent, Runner
from veadk.knowledgebase import KnowledgeBase

kb = KnowledgeBase(backend="local", index="company_faq")
kb.add_from_text("公司標準年假為每年 15 天，入職滿一年起享受。")

agent = Agent(
    name="kb_agent",
    instruction="請優先利用知識庫回答問題。",
    knowledgebase=kb,
)

runner = Runner(agent=agent, app_name="company_faq")
print(asyncio.run(runner.run(messages="年假有幾多日？")))
```

### Backend 選擇

```python
# 生產推薦：VikingDB
from veadk.knowledgebase import KnowledgeBase
kb = KnowledgeBase(backend="viking", index="my_kb")

# Context Search / OpenViking
kb = KnowledgeBase(backend="context_search", index="my_kb")
kb = KnowledgeBase(backend="openviking", index="my_kb")

# 自建向量庫
kb = KnowledgeBase(backend="opensearch", index="my_kb")
kb = KnowledgeBase(backend="redis", index="my_kb")
kb = KnowledgeBase(backend="milvus", index="my_kb")
kb = KnowledgeBase(backend="tos_vector", index="my_kb")
```

### KnowledgeBase 進階功能

```python
# 啟用知識庫畫像（enable_profile）
kb = KnowledgeBase(
    backend="viking",
    index="my_kb",
    enable_profile=True,               # 啟用用戶畫像
    query_with_user_profile=True,       # 檢索時結合用戶畫像
    name="customer_faq",                # 知識庫名（畀 Agent 睇）
    description="存儲客戶 FAQ 嘅知識庫",  # 描述（畀 Agent 知用途）
    top_k=10,                           # 預設返回相似片段數
)
```

---

## 工具（Tools）

### 網頁搜尋（web_search）

```python
import asyncio
from veadk import Agent, Runner
from veadk.tools.builtin_tools.web_search import web_search

agent = Agent(
    name="web_search_agent",
    instruction="當你需要最新資訊時，用 web_search 工具。",
    tools=[web_search],
)

runner = Runner(agent=agent)
response = asyncio.run(runner.run("杭州今日天氣點樣？"))
print(response)
```

### 自定義 Function Tool

```python
import asyncio
from typing import Any, Dict
from google.adk.tools.tool_context import ToolContext
from veadk import Agent, Runner

def calculator(
    a: float, b: float, operation: str, tool_context: ToolContext
) -> Dict[str, Any]:
    """簡單計算器

    Args:
        a: 第一個數字
        b: 第二個數字
        operation: add / subtract / multiply / divide
    """
    if operation == "add":
        return {"result": a + b, "operation": "+", "status": "success"}
    if operation == "subtract":
        return {"result": a - b, "operation": "-", "status": "success"}
    if operation == "multiply":
        return {"result": a * b, "operation": "*", "status": "success"}
    if operation == "divide":
        if b == 0:
            return {"status": "error", "message": "除數唔可以係 0。"}
        return {"result": a / b, "operation": "/", "status": "success"}
    return {"status": "error", "message": f"唔支援嘅運算: {operation}"}

agent = Agent(
    name="computing_agent",
    instruction="用 calculator 工具做用戶要求嘅運算。",
    tools=[calculator],
)

runner = Runner(agent=agent)
response = asyncio.run(runner.run("2 加 3 等於幾？"))
print(response)
```

### 用 ToolContext 共享狀態

```python
def message_checker(user_message: str, tool_context: ToolContext) -> str:
    call_count = tool_context.state.get("message_checker_calls", 0) + 1
    tool_context.state["message_checker_calls"] = call_count
    return f"Checked: {user_message.upper()} (call {call_count})"
```

### 長時運行任務（LongRunningFunctionTool）

```python
from google.adk.tools.long_running_tool import LongRunningFunctionTool

def big_data_processing(data_url: str) -> dict:
    return {
        "status": "pending",
        "data-url": data_url,
        "task-id": "big-data-processing-1",
    }

long_running_tool = LongRunningFunctionTool(func=big_data_processing)
agent = Agent(name="long_running_agent", tools=[long_running_tool])
```

### 更多 Built-in Tools

VeADK 仲提供其他 Built-in Tools：

```python
from veadk.tools.builtin_tools.web_search import web_search   # 網頁搜尋
from veadk.tools.builtin_tools.run_code import run_code       # 代碼沙箱
# from veadk.tools.builtin_tools.video_generation import video_generation  # 影片生成
# from veadk.tools.builtin_tools.image_generation import image_generation  # 圖片生成
# from veadk.tools.builtin_tools.document_understanding import document_understanding  # 文檔理解
```

### MCP Toolset

```python
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams

mcp_toolset = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://your-mcp-service.com/mcp",
        headers={"Authorization": "Bearer <token>"},
    ),
)

agent = Agent(
    name="mcp_agent",
    tools=[mcp_toolset],
)
```

---

## Runtime 後端

### ADK（預設）

```python
agent = Agent(name="assistant")  # 預設就係 ADK runtime
```

### Codex Runtime

```bash
pip install "veadk-python[codex]"
```

```python
from veadk import Agent
from veadk.runtime.codex import CodexRuntimeConfig

agent = Agent(
    name="coding_assistant",
    runtime="codex",
    model_name="doubao-seed-2-1-pro-260628",
    codex_runtime_config=CodexRuntimeConfig(
        sandbox="workspace_write",
        approval_mode="auto_review",
        network_access=True,
    ),
)
```

CodexRuntimeConfig 全部參數：

```python
CodexRuntimeConfig(
    sandbox="read_only",              # read_only / workspace_write / full_access
    approval_mode="deny_all",         # deny_all / auto_review
    network_access=False,
    workspace_root=None,
    reuse_workspace=False,
    reasoning_effort="medium",        # minimal / low / medium / high / xhigh
    personality="pragmatic",          # none / friendly / pragmatic
    max_tool_iterations=8,            # 1-64
    tool_timeout_seconds=120.0,
)
```

環境變數覆蓋：

```bash
export VEADK_CODEX_SANDBOX=full_access
export VEADK_CODEX_APPROVAL_MODE=auto_review
export VEADK_CODEX_NETWORK_ACCESS=true
```

### PiAgent Runtime

```python
agent = Agent(
    name="coding_assistant",
    runtime="piagent",
    model_name="doubao-seed-2-1-pro-260628",
)
```

環境變數：

```bash
export PIAGENT_BINARY=/path/to/piagent
export PIAGENT_INSTALL_DIR=~/.cache/veadk/piagent
export PIAGENT_TIMEOUT_SECONDS=600
```

---

## Run Processor

### 內置身份認證（AuthRequestProcessor）

```python
from veadk import Agent
from veadk.integrations.ve_identity import AuthRequestProcessor

# 基本用法：每次執行前做登入態校驗
agent = Agent(name="assistant", run_processor=AuthRequestProcessor())
```

`AuthRequestProcessor` 會喺每次 `runner.run()` 之前檢查請求 headers 嘅身份憑證，
確保只有已登入用戶可以調用 Agent。適合用喺生產環境嘅企業應用。唔 set 嘅話用預設
processor，乜都唔檢查。

### 自定義 Processor

```python
from veadk.processors.base_run_processor import BaseRunProcessor

class LoggingProcessor(BaseRunProcessor):
    def process_run(self, runner, message, **kwargs):
        def decorator(event_generator):
            async def wrapper():
                print(f"[START] 收到訊息: {message}")
                async for event in event_generator():
                    yield event
                print("[END] 執行完成")
            return wrapper
        return decorator
```

---

## 飛書 Channel

```python
from veadk import Agent, Runner
from veadk.extensions import FeishuChannelExtension

agent = Agent()
runner = Runner(agent=agent, app_name="feishu_demo")
channel = FeishuChannelExtension(runner=runner)
```

環境變數：

```bash
export TOOL_FEISHU_CHANNEL_APP_ID=...
export TOOL_FEISHU_CHANNEL_APP_SECRET=...
```

---

## 前端（Frontend / Studio / A2UI）

```python
from veadk import Agent

# 啟用 A2UI（富界面卡片）
agent = Agent(name="a2ui_agent", enable_a2ui=True)

# VeADK Web（本地調試）：pip install "veadk-python[web]" 然後 run
# VeADK Frontend（生產級 React 應用）
# VeADK Studio（完整智能體工作台）
```

---

## AgentKit 集成（create_agentkit_app）

VeADK 提供一個應用工廠，快速將 Agent 包裝成 AgentKit Runtime：

```python
from veadk import Agent
from veadk.integrations.agentkit import create_agentkit_app

root_agent = Agent(name="customer_support")
app = create_agentkit_app(root_agent)

# app 已經有晒 /invoke、/ping、/health 等端點
# 直接用 uvicorn 或者 app.run() 啟動
```

呢個工廠嚟自 VeADK README，適用於唔想用 AgentKit SDK 但要包裝 Agent 嘅情況。
