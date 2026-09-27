# Invoice Processing Pipeline

5-Agent 發票處理系統，**VeADK + AgentKit** 最佳實踐：
**OCR → 翻譯 → 驗證 → 匯總 → 排版（Seedream）→ 審批**

## Quick Start

```bash
# Mock mode（唔需要 API key）
python main.py --mode single --invoice default
python main.py --mode batch

# Real mode（需要 config.yaml + API key）
python main.py --mode single --no-mock
```

## 配置 API Key

```bash
# 1. 填入 config.yaml（VeADK 官方推薦格式）
vim config.yaml

# 2. 安裝依賴
pip install -r requirements.txt

# 3. 行 real mode
python main.py --no-mock
```

VeADK 會自動讀取 `config.yaml`，唔需要 `.env` 或額外設定。

## 用真實發票測試（invoice_upload）

`invoice_upload/` 入面有真實發票相（iPhone 影嘅 **HEIC** 格式）。Vision API 唔收 HEIC，要**先轉做 JPG**：

```bash
cd invoice_upload
for f in *.HEIC; do sips -s format jpeg "$f" --out "${f%.HEIC}.jpg"; done
cd ..
```

跟住用 `--image` 指定相片行 real mode（`--invoice` 只係標籤，可用嚟分辨）：

```bash
python main.py --mode single --no-mock --invoice real1 --image invoice_upload/IMG_0403.jpg
python main.py --mode single --no-mock --invoice real2 --image invoice_upload/IMG_0404.jpg
```

> 提示：mock mode 唔會讀真相（照行 mock 數據），一定要用 `--no-mock`。轉出嚟嘅 JPG 已經入咗 `.gitignore`。

## 長期記憶（Long-Term Memory via OpenViking）

兩個 agent（OCR / Validation）用 `backend: openviking` 做長期記憶，由一個 **self-hosted OpenViking server** 提供
（embedding + VLM 都用同一個 BytePlus Ark API key，唔使額外訂閱）。記憶由 VeADK Runner 嘅
`auto_save_session=True` 自動寫入，Agent 側只做 `search_memory` 讀返之前嘅 correction patterns。

### 啟動 OpenViking server（開機自動）

已配置 launchd service，開機自動起 + 自動重啟：

```bash
# 手動啟動／停止／重啟
launchctl load   ~/Library/LaunchAgents/com.local.openviking-server.plist
launchctl unload ~/Library/LaunchAgents/com.local.openviking-server.plist
launchctl kickstart -k gui/$(id -u)/com.local.openviking-server
```

- 設定檔：`~/.openviking/ov.conf`（embedding/VLM provider、root_api_key、本地 storage）
- 資料：`~/.openviking/data/`（絕對路徑，唔隨 CWD 變）
- 健康檢查：`curl http://127.0.0.1:1933/health`
- 日誌：`/tmp/openviking-server.log`

### 建 account（root API key 唔可以訪問 tenant 資料）

`root_api_key` 只係 admin，SDK 連線要用 tenant user key。首次開 server 後行一次：

```bash
curl -s -X POST http://127.0.0.1:1933/api/v1/admin/accounts \
  -H "Authorization: Bearer <root_api_key>" \
  -H "Content-Type: application/json" \
  -d '{"account_id":"invoice","admin_user_id":"invoice-admin"}'
# 回傳 result.user_key 就係 config.yaml 入面 database.openviking.api_key
```

> 記住：`config.yaml` 嘅 `database.openviking.api_key` 係 account 創建時回傳嘅 user key；
> 如果刪咗 server 資料，要重建 account 並更新呢個值（root key 唔可以直接畀 Agent 用）。

### BytePlus 雲服務認證（TOS / VikingDB）

`.env`（已 gitignore）提供 `CLOUD_PROVIDER=byteplus` + `BYTEPLUS_ACCESS_KEY/SECRET_KEY`，
VeADK import 時自動 map 做 `VOLCENGINE_ACCESS_KEY/SECRET_KEY`：

```bash
CLOUD_PROVIDER=byteplus
BYTEPLUS_ACCESS_KEY=<access-key-id>
BYTEPLUS_SECRET_KEY=<secret-key>
```

> 注意：secret key **唔好自行 base64 decode** — 控制台顯示嘅值就係真正 secret。已驗證 TOS
> (`tos-ap-southeast-1.bytepluses.com` list_buckets 成功)。VikingDB 需要用 VikingMem.ping()
> 驗證，若回 `you have not placed an order yet` 即係未開通服務，唔係 key 問題。

## 連接 Lark / 飛書（審批通知 + 互動按鈕）

Frontend（`frontend/feishu.py`）已經駁好 Lark，三種模式由 config 自動 fallback：

1. **Lark webhook**（最簡單，單向通知）— 填 `config.yaml` `feishu.webhook.url`
2. **FeishuChannelExtension bot**（WebSocket 長連接，可收訊息）— 填 `TOOL_FEISHU_CHANNEL_APP_ID` / `TOOL_FEISHU_CHANNEL_APP_SECRET`（VeADK 讀呢兩個 env）
3. **互動按鈕 approve / reject** — 要將 `/feishu/callback` 公開（ngrok）+ 填 `feishu.approval.callback_url`

### 建立 Lark bot app

1. 去 **Lark Open Platform**（內地: `https://open.feishu.cn`，海外: `https://open.larksuite.com`）
   → **建立企業自建應用**（Create app）
2. 記低 **App ID** 同 **App Secret**（基礎資訊頁）
3. **應用能力 → 添加能力 → 機器人**，開 **啟用機器人**（發送訊息要用）
4. **權限管理 → 添加權限**（至少）：
   - `im:message`（發送單聊/群組訊息）
   - `im:message.group_at_msg`（群組 @ 回覆，如果 bot 要喺群度用）
   - `im:chat`（獲取群資訊，可選）
5. 發佈版本 → **審核通過**（或測試用 `沙盒應用/測試企業`）

### 配置（webhook 模式，最快）

Lark **群組 → 設定 → 群機器人 → 添加機器人 → 自訂機器人**，攞到 webhook URL 後：

```bash
# 方法 A：寫入 config.yaml（已 gitignore，唔會入 repo）
feishu:
  webhook:
    url: https://open.larksuite.com/open-apis/bot/v2/hook/<token>

# 方法 B：環境變數
export FEISHU_WEBHOOK_URL="https://open.larksuite.com/open-apis/bot/v2/hook/<token>"
```

啟動 frontend 測試：

```bash
python -m uvicorn frontend.app:app --port 8000
curl -X POST http://127.0.0.1:8000/upload -F file=@invoice_upload/IMG_0403.jpg
# 若 pending_review → Lark 會收到 interactive 審批卡片
```

### 互動按鈕（approve / reject）需要 callback URL

Lark 卡按鈕 callback 要一個**公網 HTTPS** endpoint：

```bash
ngrok http 8000          # 攞到 https://xxxx.ngrok.io
```

```yaml
feishu:
  approval:
    enabled: true
    callback_url: https://xxxx.ngrok.io/feishu/callback
```

Lark 控制台 → 機器人 → **事件與回調 → 請求地址** → 填 `https://xxxx.ngrok.io/feishu/callback`
（或喺卡片審批設置配 callback）。按鈕 value 帶 `task_id`，callback 會更新審批狀態並回覆 Lark 結果卡片。

### 注意

- `resolve_feishu_config()` 而家正確讀 **`TOOL_FEISHU_CHANNEL_APP_ID` / `TOOL_FEISHU_CHANNEL_APP_SECRET`**（VeADK
  `FeishuChannelExtension` 用呢兩個）；`FEISHU_APP_ID` / `FEISHU_APP_SECRET` 保留做 alias。
- `config.yaml` 入面嘅 `<your-...>` placeholder 會被自動當作未設定，唔會發去假 URL。

## Agent 架構

| Agent | Model | 功能 | A2A Executor |
|-------|-------|------|-------------|
| **1. OCR** | Seed 2.0 Mini (Vision) | 發票圖片 → 結構化 JSON | `ocr_executor` |
| **2. Translation** | Seed 2.0 Mini | 翻譯成統一語言 | `translation_executor` |
| **3. Validation** | Seed 2.0 Mini (Vision) | 自我驗證，對比原圖 | `validation_executor` |
| **4. Aggregation** | Seed 2.0 Mini | 多張發票標準化、加總 | `aggregation_executor` |
| **5. Formatting** | Seedream 5.0 | 原圖 → 模板化發票圖（~100 AFP/img） | `formatting_executor` |
| **6. Approval** | Seed 2.0 Mini | 人類審批 (HITL) | `approval_executor` |

> 所有 LLM agent 統一用 **Seed 2.0 Mini** + `reasoning_effort: none`（最低推理成本）。
> Formatting 唔行 LLM，係 deterministic Seedream `single_image_to_single` call：base64 原圖 +
> template prompt → `images/generations`。Mock mode 回 `mock_placeholder`，唔燒 AFP。

## Deploy（AgentKit CLI）

```bash
# 每個 Agent 獨立 deploy
ak deploy ocr-agent --app-name invoice-ocr
ak deploy translation-agent --app-name invoice-translation
ak deploy validation-agent --app-name invoice-validation
ak deploy aggregation-agent --app-name invoice-aggregation
ak deploy formatting-agent --app-name invoice-formatting
ak deploy approval-agent --app-name invoice-approval
```

或者本地行 A2A service：

```bash
AGENT_NAME=ocr_agent python agentkit_app.py
```

## A2A Drive Chain（單一 process，6 個 agent 掛載）

除咗上面 in-process 嘅 `a2a_orchestrator.py`，仲有一套**真實 A2A 協作**（Option A）：
每個 agent 都係一個 `A2AStarletteApplication`，掛載喺同一隻 FastAPI server 嘅路徑下，
orchestrator 用 `A2AClient` 逐個 `message/send` 驅動（drive chain）：
`/ocr/ → /translation/ → /validation/ → /aggregation/ → /formatting/ → /approval/`。

```bash
# 1. 起 server（mock 預設）
python -m a2a_pipeline.cli start --port 9901

# 2. 另一個 terminal：驅動成條 chain
python -m a2a_pipeline.cli run --mode single --invoice default
python -m a2a_pipeline.cli run --mode batch --invoices default invoice2

# 3. 用真實 ModelArk models + Seedream（--no-mock）
python -m a2a_pipeline.cli start --port 9901 --no-mock
python -m a2a_pipeline.cli run --mode single --base-url http://127.0.0.1:9901 --no-mock --image invoice_upload/IMG_0403.jpg
```

或者喺 code 度直接用：

```python
from a2a_pipeline.drive_chain import A2aDriveChain
chain = A2aDriveChain(base_url="http://127.0.0.1:9901")
result = chain.run_single("default")       # sync wrapper
# result = await chain.run_single_async("default")
```

- Server：`a2a_pipeline.server.build_server(mock=True, host, port)` → FastAPI，6 個 agent 各自有
  `/ocr /translation /validation /aggregation /formatting /approval` 子路徑 + `/.well-known/agent-card.json`。
- Executors：`a2a_pipeline.executors` 嘅 `InvoiceExecutor` base + 6 個 subclass，JSON text 入／出。
- Client gotchas：agent URL 要**加尾斜線**（`/ocr/`）；用 `MessageSendConfiguration(blocking=True)`
  等 Task 完成；response text 喺 `task.status.message.parts[].text`。
- `agentkit-run` subcommand = 單一 agent 以 AgentKit conversational app 方式起（mock=False）：

```bash
python -m a2a_pipeline.cli agentkit-run --agent ocr_agent --port 8080
```

### Formatting Agent 作為 MCP（Model Context Protocol）

Formatting agent 除咗喺 chain 入面，仲以 **MCP server**（`AgentkitMCPApp` / FastMCP
streamable-http）暴露 `format_invoice_image` tool，畀外部工具／agent 直接 call：

```bash
# 起 MCP server（mock 預設；--no-mock 用真 Seedream）
python -m a2a_pipeline.cli mcp-run --port 8001 --no-mock
# endpoint: http://127.0.0.1:8001/mcp

# 用 mcp CLI client 快速測試
mcp connect --transport streamable-http http://127.0.0.1:8001/mcp
```

Tool schema: `format_invoice_image(image_path, invoice_json, template="clean_business_invoice")`
→ 回傳 `FormattedInvoice`（`status` / `formatted_image_url` / `formatted_image_path` / `prompt`...）。
真實生成嘅圖會同時存落 `data/formatted/{invoice_stem}.jpg`（Seedream URL 24h 過期）。

## 目錄結構

```
invoice-pipeline/
├── config.yaml              # VeADK 配置（放入 API key）
├── agentkit.yaml            # AgentKit CLI 配置
├── agentkit_app.py          # AgentKit A2A 服務入口
├── requirements.txt
├── .gitignore
├── agents/
│   ├── base_agent.py        # Abstract base class
│   ├── models.py            # Data schemas (dataclasses)
│   ├── ocr_agent.py         # Agent1
│   ├── translation_agent.py # Agent2
│   ├── validation_agent.py  # Agent3
│   ├── aggregation_agent.py # Agent4
│   ├── formatting_agent.py  # Agent5 (Seedream 排版)
│   ├── approval_agent.py    # Agent6
│   └── configs/             # Per-agent YAML 配置
├── a2a_orchestrator.py      # In-process pipeline orchestration
├── a2a_pipeline/            # A2A orchestration package (single process)
│   ├── __init__.py          #   re-exports build_server / A2aDriveChain / executors
│   ├── executors.py         #   A2A executors (6 agents, JSON text I/O)
│   ├── server.py            #   Single-process A2A server (6 agents mounted)
│   ├── drive_chain.py       #   A2A drive-chain orchestrator (A2AClient)
│   ├── mcp_server.py        #   Formatting agent 作為 MCP server (AgentkitMCPApp)
│   └── cli.py               #   CLI: start / run / agentkit-run / mcp-run
├── main.py                  # CLI entry point
├── eval/                    # Evaluation scripts
├── deploy.sh                # Deployment script
└── README.md
```

## Tech Stack

| 層面 | 技術 |
|------|------|
| **Agent Framework** | VeADK (`veadk-python`) |
| **A2A Service** | AgentKit SDK (`agentkit-sdk-python[a2a]`) |
| **Deployment** | AgentKit CLI (`ak deploy`) |
| **LLM** | Seed 2.0 Lite / Mini |
| **Config** | `config.yaml`（VeADK 官方格式） |
| **Plan** | Agent Plan Medium (¥200/月, 100,000 AFP) |
