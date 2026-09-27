# AgentKit SDK 參考

呢份文件記錄晒 `agentkit-sdk-python`（PyPI 套件）嘅程式碼範例，用粵語解釋用途同用法。

---

## 安裝

```bash
# 已發佈版本
pip install "agentkit-sdk-python>=0.3.0"

# 可選：A2A 支援
pip install "agentkit-sdk-python[a2a]"
```

---

## AgentkitSimpleApp（基礎架構）

### 最簡單嘅程式

```python
import asyncio
from agentkit import AgentkitSimpleApp

simple_app = AgentkitSimpleApp(
    name="test_app",
    model_name="doubao-seed-2-1-pro-260628",
    api_key="<your-api-key>",
    api_base="https://ark.cn-beijing.volces.com/api/v3/",
)

response = asyncio.run(simple_app.invoke(
    text="用一句話介紹火山引擎。",
    uid="test_user",
    sid="test_session",
))
print(response.get_message())
# 輸出：「火山引擎係字節跳動旗下嘅企業級雲服務平台...」
```

### 流式輸出（SSE）

```python
import asyncio
from agentkit import AgentkitSimpleApp

simple_app = AgentkitSimpleApp(
    name="stream_app",
    model_name="doubao-seed-2-1-pro-260628",
    api_key="<your-api-key>",
    api_base="https://ark.cn-beijing.volces.com/api/v3/",
)

async def main():
    async for event in simple_app.invoke_stream(
        text="講個故仔",
        uid="test_user",
        sid="session-1",
    ):
        # event 可以係 Message、ToolCall、ToolResult、Error 等
        print(event)

asyncio.run(main())
```

### 帶工具嘅 App

```python
import asyncio
from agentkit import AgentkitSimpleApp
from google.adk.tools.tool_context import ToolContext

# 定義工具函數
def get_weather(location: str, unit: str = "celsius", tool_context: ToolContext = None) -> str:
    """獲取指定城市嘅天氣資訊

    Args:
        location: 城市名（例如：北京、上海）
        unit: 溫度單位（celsius/fahrenheit）
    """
    # 呢度模擬天氣查詢
    weather_data = {"北京": "晴天，25°C", "上海": "多雲，22°C"}
    return weather_data.get(location, f"{location} 嘅天氣數據暫未提供")

app_with_tools = AgentkitSimpleApp(
    name="weather_app",
    model_name="doubao-seed-2-1-pro-260628",
    api_key="<your-api-key>",
    api_base="https://ark.cn-beijing.volces.com/api/v3/",
    tools=[get_weather],
)

response = asyncio.run(app_with_tools.invoke(
    text="北京天氣如何？",
    uid="user-42",
    sid="session-1",
))
print(response.get_message())
```

### 帶記憶嘅 App

```python
import asyncio
from agentkit import AgentkitSimpleApp
from agentkit.memory import AgentkitMemory
from agentkit.knowledge import AgentkitKnowledge

# 記憶客戶端
memory = AgentkitMemory(
    host="http://localhost:8000",
    token="<your-token>",
)

app_with_memory = AgentkitSimpleApp(
    name="memory_app",
    model_name="doubao-seed-2-1-pro-260628",
    api_key="<your-api-key>",
    api_base="https://ark.cn-beijing.volces.com/api/v3/",
    memory=memory,
)
```

### 帶知識庫嘅 App

```python
import asyncio
from agentkit import AgentkitSimpleApp
from agentkit.knowledge import AgentkitKnowledge

# 知識庫客戶端
knowledge = AgentkitKnowledge(
    host="http://localhost:8000",
    token="<your-token>",
)

app_with_knowledge = AgentkitSimpleApp(
    name="knowledge_app",
    model_name="doubao-seed-2-1-pro-260628",
    api_key="<your-api-key>",
    api_base="https://ark.cn-beijing.volces.com/api/v3/",
    knowledge=knowledge,
    knowledge_query_intro="請利用知識庫回答用戶問題。",
)
```

### 帶 MCP 嘅 App

```python
import asyncio
from agentkit import AgentkitSimpleApp

app_with_mcp = AgentkitSimpleApp(
    name="mcp_app",
    model_name="doubao-seed-2-1-pro-260628",
    api_key="<your-api-key>",
    api_base="https://ark.cn-beijing.volces.com/api/v3/",
    mcp_service_host="http://localhost:8001",
    mcp_service_token="<your-mcp-token>",
)
```

### 完整參數（production-grade）

```python
import asyncio
from agentkit import AgentkitSimpleApp
from agentkit.memory import AgentkitMemory
from agentkit.knowledge import AgentkitKnowledge

full_app = AgentkitSimpleApp(
    name="production_agent",
    # LLM
    model_name="doubao-seed-2-1-pro-260628",
    api_key="<your-api-key>",
    api_base="https://ark.cn-beijing.volces.com/api/v3/",
    # Agent
    instruction="你係一個專業助手。",
    tools=[get_weather],
    max_input_tokens=4000,
    max_output_tokens=2000,
    # 附加
    memory=AgentkitMemory(host="http://localhost:8000", token="<token>"),
    knowledge=AgentkitKnowledge(host="http://localhost:8000", token="<token>"),
    knowledge_query_intro="請利用知識庫回答。",
    mcp_service_host="http://localhost:8001",
    mcp_service_token="<mcp-token>",
    # 回調
    on_start=lambda req: print(f"收到請求: {req}"),
    on_end=lambda req, resp: print(f"請求完成: {resp}"),
)
```

---

## AgentkitMCPApp（MCP 一鍵變 Agent）

### 基本用法

```python
import asyncio
from agentkit.mcp_app import AgentkitMCPApp

# 將 MCP Server 變成 Agent
mcp_app = AgentkitMCPApp(
    name="mcp_agent",
    model_name="doubao-seed-2-1-pro-260628",
    api_key="<your-api-key>",
    api_base="https://ark.cn-beijing.volces.com/api/v3/",
    mcp_service_host="http://localhost:8001",
    mcp_service_token="<mcp-token>",
)

response = asyncio.run(mcp_app.invoke(
    text="幫我查下數據庫用戶表有咩記錄",
    uid="user-42",
    sid="session-1",
))
print(response.get_message())
```

### @app.tool 裝飾器

```python
import asyncio
from agentkit.mcp_app import AgentkitMCPApp

mcp_app = AgentkitMCPApp(
    name="mcp_with_tools",
    model_name="doubao-seed-2-1-pro-260628",
    api_key="<your-api-key>",
    api_base="https://ark.cn-beijing.volces.com/api/v3/",
)

@mcp_app.tool
def get_stock_price(symbol: str) -> str:
    """獲取股票即時價格

    Args:
        symbol: 股票代號（例如：AAPL、GOOGL）
    """
    prices = {"AAPL": "150.25", "GOOGL": "2800.50"}
    return f"{symbol} 嘅即時價格係 ${prices.get(symbol, 'N/A')}"

response = asyncio.run(mcp_app.invoke(
    text="AAPL 股價幾多？",
    uid="user-42",
    sid="session-1",
))
print(response.get_message())
```

### @app.agent_as_a_tool 裝飾器

將一個子 Agent 封裝成工具，畀主 Agent 調用：

```python
import asyncio
from agentkit.mcp_app import AgentkitMCPApp

mcp_app = AgentkitMCPApp(
    name="main_agent",
    model_name="doubao-seed-2-1-pro-260628",
    api_key="<your-api-key>",
    api_base="https://ark.cn-beijing.volces.com/api/v3/",
)

@mcp_app.agent_as_a_tool(
    name="weather_search",
    description="搜索天氣資訊",
    model_name="doubao-seed-2-1-pro-260628",
    api_key="<your-api-key>",
)
async def weather_search_agent(text: str) -> str:
    # 呢個子 Agent 會收到 text 參數並執行
    return f"[天氣搜索結果: {text}]"

response = asyncio.run(mcp_app.invoke(
    text="今日北京天氣如何？用 weather_search 工具查詢",
    uid="user-42",
    sid="session-1",
))
print(response.get_message())
```

---

## AgentkitA2aApp（A2A 互操作性）

### 基本用法

```python
import asyncio
from agentkit.a2a_app import AgentkitA2aApp

a2a_app = AgentkitA2aApp(
    name="a2a_agent",
    model_name="doubao-seed-2-1-pro-260628",
    api_key="<your-api-key>",
    api_base="https://ark.cn-beijing.volces.com/api/v3/",
)

response = asyncio.run(a2a_app.invoke(
    text="Hello from A2A",
    uid="user-42",
    sid="session-1",
))
print(response.get_message())
```

### @app.agent_executor 裝飾器

```python
import asyncio
from agentkit.a2a_app import AgentkitA2aApp

a2a_app = AgentkitA2aApp(
    name="a2a_with_executor",
    model_name="doubao-seed-2-1-pro-260628",
    api_key="<your-api-key>",
    api_base="https://ark.cn-beijing.volces.com/api/v3/",
)

@a2a_app.agent_executor(name="math_executor")
async def execute_math(problem: str) -> str:
    """解數學題

    Args:
        problem: 數學問題描述
    """
    return f"解題完成: {problem}"

response = asyncio.run(a2a_app.invoke(
    text="用 math_executor 計算 25 * 4",
    uid="user-42",
    sid="session-1",
))
print(response.get_message())
```

### @app.task_store 裝飾器

```python
import json
from agentkit.a2a_app import AgentkitA2aApp

a2a_app = AgentkitA2aApp()

@a2a_app.task_store(name="file_task_store")
def save_task(task_data: dict) -> dict:
    task_json = json.dumps(task_data, ensure_ascii=False)
    print(f"[Task Store] Saving: {task_json}")
    return {"status": "saved", "data": task_data}
```

---

## 平台客戶端 API

### AgentkitMemory

```python
from agentkit.memory import AgentkitMemory

memory = AgentkitMemory(
    host="http://localhost:8000",
    token="<your-token>",
)

# 保存記憶
memory.save_memory(
    app_id="test_app",
    uid="user-42",
    memory_type="conversation_history",
    content="用戶話佢鍾意藍色。",
)

# 檢索記憶
history = memory.retrieve_memory(
    app_id="test_app",
    uid="user-42",
    memory_type="conversation_history",
    top_k=10,
)

# 刪除記憶
memory.clear_memory(
    app_id="test_app",
    uid="user-42",
    memory_type="conversation_history",
)
```

### AgentkitKnowledge

```python
from agentkit.knowledge import AgentkitKnowledge

knowledge = AgentkitKnowledge(
    host="http://localhost:8000",
    token="<your-token>",
)

# 查詢知識庫
results = knowledge.query(
    app_id="test_app",
    query="年假政策",
    top_k=5,
)

# 上傳文件（可選）
from agentkit.knowledge import AgentkitKnowledge
knowledge.add_document(
    app_id="test_app",
    file_path="./policy.pdf",
)
```

### AgentkitMCP

```python
from agentkit.mcp import AgentkitMCP

mcp_client = AgentkitMCP(
    host="http://localhost:8001",
    token="<your-mcp-token>",
)

# 列出可用工具
tools = mcp_client.list_tools()
for tool in tools:
    print(tool.name, tool.description)

# 調用工具
result = mcp_client.call_tool(
    tool_name="database_query",
    arguments={"query": "SELECT * FROM users", "params": {}},
)
```

### AgentkitRuntime

```python
from agentkit.runtime import AgentkitRuntime

runtime = AgentkitRuntime(
    host="http://localhost:8002",
    token="<your-runtime-token>",
    auto_reconnect=True,
    timeout_seconds=30,
)

# 註冊 Agent
runtime.register_agent(
    app_name="my_app",
    agent_type="simple",
    model_name="doubao-seed-2-1-pro-260628",
)

# 執行 Agent
response = runtime.invoke_agent(
    app_name="my_app",
    input="Hello",
    uid="user-42",
    sid="session-1",
)
```

---

## 完整 Production-Grade 範例

```python
import asyncio
from agentkit import AgentkitSimpleApp
from agentkit.memory import AgentkitMemory
from agentkit.knowledge import AgentkitKnowledge
from agentkit.mcp import AgentkitMCP
from agentkit.runtime import AgentkitRuntime
from google.adk.tools.tool_context import ToolContext

# 平台客戶端
memory = AgentkitMemory(host="http://demo-cn.agentkit.ai", token="<token>")
knowledge = AgentkitKnowledge(host="http://demo-cn.agentkit.ai", token="<token>")

# 自定義工具（含 tool_context 取用狀態）
def order_query(order_id: str, tool_context: ToolContext = None) -> str:
    """查詢訂單狀態

    Args:
        order_id: 訂單編號
    """
    user_id = tool_context.state.get("user_id", "unknown") if tool_context else "unknown"
    orders = {"ORD-001": "已發貨", "ORD-002": "處理中"}
    status = orders.get(order_id, "唔存在")
    return f"用戶 {user_id} 嘅訂單 {order_id} 狀態：{status}"

# 構建 Agent App
app = AgentkitSimpleApp(
    name="production_demo",
    model_name="doubao-seed-2-1-pro-260628",
    api_key="<your-api-key>",
    api_base="https://ark.cn-beijing.volces.com/api/v3/",
    instruction="你係一個專業嘅購物助手，用工具查訂單，用知識庫答 FAQ。",
    tools=[order_query],
    memory=memory,
    knowledge=knowledge,
    knowledge_query_intro="請利用知識庫幫手回答。",
    max_input_tokens=4000,
    max_output_tokens=2000,
    on_start=lambda req: print(f"[START] {req.uid} 查詢"),
    on_end=lambda req, resp: print(f"[END] 已回應用戶 {req.uid}"),
)

async def main():
    response = await app.invoke(
        text="ORD-001 訂單狀態？",
        uid="user-42",
        sid="session-1",
    )
    print(response.get_message())

asyncio.run(main())
```

---

## 重要提示

- `agentkit-sdk-python` 透過 `agentkit` 頂層 import（唔係 `agentkit_sdk`）
- 所有 App 類型（SimpleApp、MCPApp、A2aApp）都支援 `.invoke()` 同 `.invoke_stream()`
- 平台客戶端（Memory、Knowledge、MCP、Runtime）係獨立 REST 客戶端，連去 AgentKit Platform
- 用 `agent_as_a_tool` 可以整多層 Agent 結構（Agent 入面再 call Agent）
