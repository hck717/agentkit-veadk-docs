# AgentKit CLI 指令大全

呢份文件記錄晒所有 `agentkit`（alias `ak`）指令，用粵語解釋用途、參數同用法。

---

## 安裝 & 快速開始

### 安裝

```bash
curl -fsSL https://agentkit-cli.tos-cn-beijing.volces.com/install.sh | sh
# 或者用 wget
wget -qO- https://agentkit-cli.tos-cn-beijing.volces.com/install.sh | sh
```

裝完之後，`agentkit` 同 `ak` 兩個 binary 會放喺 `~/.local/bin/`。驗證：

```bash
agentkit --help
agentkit tree          # 印晒成個命令樹
agentkit tree --all    # 連參數同選項都展開
agentkit tree --json   # 機器可讀格式
```

### 登入方式（二選一）

**方式一：AK/SK（管理操作必用）**

```bash
export VOLCENGINE_ACCESS_KEY=your_ak
export VOLCENGINE_SECRET_KEY=your_sk
export VOLCENGINE_REGION=cn-beijing   # 可選，預設 cn-beijing
```

**方式二：SSO（只用嚟 invoke）**

```bash
agentkit login <sso-address>          # 瀏覽器登入
agentkit auth login                   # 同上
agentkit whoami                       # 睇當前身份
agentkit auth whoami
agentkit logout                       # 登出
agentkit auth logout
```

SSO Profile 管理：

```bash
agentkit auth profile set my-profile \
  --issuer https://example.com \
  --client-id abc123 \
  --role-trn trn:... \
  --provider-trn trn:... \
  --region cn-beijing

agentkit auth profile list
agentkit auth profile show my-profile
```

---

## 專案初始化（init）

### 模板模式

```bash
agentkit init my-agent                      # 互動式揀模板
agentkit init my-agent -L python -t basic   # 直接指定
agentkit init my-agent -L python -t basic_stream
agentkit init my-agent -L python -t a2a
agentkit init my-agent -t harness
agentkit init . -y -f                       # 當前目錄，跳過提示，強制覆蓋
agentkit init --list-templates              # 列出可用模板
agentkit init -l                            # 列出可用語言同模板（同上）
```

自定義 Agent 屬性：

```bash
agentkit init my-agent -t basic \
  --agent-name "高級助理" \
  --description "具備聯網同代碼執行能力" \
  --system-prompt "你係一個專業嘅助手" \
  --model-name "doubao-pro-32k" \
  --tools "web_search,run_code"
```

### 包裝模式（--from-agent）🆕

將現有 VeADK Agent 定義包裝成可部署嘅 AgentKit 項目：

```bash
agentkit init --from-agent ./my_agent.py
agentkit init my_bot --from-agent ./weather_agent.py
agentkit init -f ./my_agent.py --agent-var my_custom_agent
agentkit init chat_bot --from-agent ./chat_agent.py --wrapper-type stream
```

### 項目結構

```
my-agent/
├── agentkit.yaml       # 核心部署配置
├── requirements.txt    # Python 依賴
├── my_agent.py         # 入口檔案
├── .dockerignore
└── .github/workflows/deploy.yml  # CI/CD
```

---

## 配置（config）

### 交互式模式（預設，首次配置推薦）

```bash
agentkit config
```

佢會一步步問你：Agent 名、入口檔案、描述、Python 版本、依賴檔、部署模式、環境變數。

### 非交互式模式（CI/CD 用）

```bash
agentkit config \
  --agent_name myAgent \
  --entry_point agent.py \
  --description "天氣查詢助手" \
  --launch_type cloud \
  --image_tag v1.0.0 \
  --region cn-beijing \
  -e MODEL_AGENT_NAME=ep-xxxxx \
  -e MODEL_AGENT_API_KEY=sk-xxxxx
```

### 環境變數兩層級

```bash
# 應用級（所有模式共享）
agentkit config -e API_KEY=shared-key -e MODEL_ENDPOINT=https://...

# Workflow 級（僅當前模式）
agentkit config --workflow-runtime-envs DEBUG=true
```

### 全局配置（~/.agentkit/config.yaml）🆕

```bash
# 初始化
agentkit config --global --init

# 設定值
agentkit config --global --set cr.instance_name=team-cr
agentkit config --global --set tos.bucket=team-bucket

# 睇配置
agentkit config --global --show
```

### Runtime 綁定資源

```bash
agentkit config \
  --memory_id mem-xxx \
  --knowledge_id kb-xxx \
  --tool_id tool-xxx \
  --mcp_toolset_id mcp-ts-xxx

# 解綁
agentkit config --memory_id ""
```

### 預覽 & 睇當前配置

```bash
# 預覽變更（唔保存）
agentkit config --entry_point agent.py --image_tag v2.0 --dry-run

# 睇當前配置
agentkit config --show
```

### Runtime 網絡配置（Cloud/Hybrid）

```bash
# 私網
agentkit config \
  --runtime-network-mode private \
  --runtime-vpc-id vpc-xxxxx \
  --runtime-subnet-id subnet-xxxxx \
  --runtime-enable-shared-internet-access
```

---

## 構建 & 部署

### Build（打包 Docker 镜像）

```bash
agentkit build
agentkit build --regenerate-dockerfile   # 強制重新生成 Dockerfile
agentkit build --platform linux/amd64    # 指定目標架構（預設 auto）
agentkit build --config-file agentkit.yaml  # 指定配置檔
```

自定義 Docker 構建（喺 `agentkit.yaml` 加）：

```yaml
docker_build:
  base_image: "python:3.12-slim"
  build_script: "scripts/setup.sh"
```

### Deploy（完整流程）

```bash
# 一鍵 config → build → apply
agentkit deploy --name my-agent --region cn-beijing --project demo

# 分階段
agentkit deploy config --name my-agent --force
agentkit deploy build
agentkit deploy apply

# 部署飛書機器人
agentkit deploy --name my-agent --im-feishu \
  --im-feishu-app-id <id> \
  --im-feishu-app-secret <secret>
```

### Launch（一鍵 build + deploy）

```bash
agentkit launch
```

呢個命令會自動做：render Dockerfile → 打包上傳 TOS → 準備 CR → Pipeline 構建 → 部署到 Runtime。

---

## Runtime 管理

### 基本操作

```bash
agentkit runtime list                    # 列出所有 runtime
agentkit runtime list --project demo
agentkit runtime show my-agent           # 睇詳情
agentkit runtime show my-agent --rev 3   # 睇某個版本
```

### 刪除

```bash
agentkit runtime delete my-agent --yes
agentkit destroy                         # 喺項目目錄一鍵拆除
agentkit destroy my-agent --yes
```

### 日誌 & 終端

```bash
agentkit runtime logs my-agent --limit 200
agentkit runtime attach my-agent         # 交互式終端（Ctrl-] 脫離）
```

### 版本管理

```bash
agentkit runtime versions my-agent
agentkit runtime release my-agent --rev 3
agentkit runtime release my-agent --no-wait
```

### 更新配置

```bash
agentkit runtime update my-agent \
  --cpu-milli 1000 \
  --memory-mb 2048 \
  --min-instance 1 \
  --max-instance 5 \
  --max-concurrency 10 \
  --model-agent-name "doubao-seed-1-6" \
  --knowledge-id kb-xxx \
  --memory-id mem-xxx \
  --tool-id tool-xxx \
  --mcp-toolset-id mcp-ts-xxx \
  --envs-json '[{"Key":"K","Value":"V"}]' \
  --auto-release
```

---

## 調用 Runtime（invoke）

```bash
agentkit invoke my-agent -m "你好，介紹一下你自己"
agentkit invoke my-agent -m "hello" -u user-42 -s session-1
agentkit invoke my-agent -m "hi" --rev 3
agentkit invoke my-agent -m "test" --token <jwt> --json
```

---

## 知識庫（knowledge / kb）

```bash
# 列表
agentkit knowledge list
agentkit knowledge list --project demo

# 詳情
agentkit knowledge show kb-12345678

# 創建
agentkit knowledge create --name docs-kb --provider-type viking

# 加文件
agentkit knowledge add docs-kb ./docs ./README.md
agentkit knowledge add docs-kb --url https://example.com/guide.pdf --doc-type pdf

# 更新
agentkit knowledge update kb-12345678 --description "更新後嘅文檔庫"

# 刪除
agentkit knowledge delete kb-12345678 --yes
```

---

## 記憶庫（memory / mem）

```bash
# 列表
agentkit memory list

# 詳情
agentkit memory show m-12345678

# 創建
agentkit memory create --name user-mem --provider-type MEM0
agentkit memory create --name viking-mem --provider-type VIKINGDB_MEMORY

# 更新
agentkit memory update m-12345678 --description "更新後嘅記憶"

# 刪除
agentkit memory delete m-12345678 --yes
```

---

## MCP 服務（mcp service）

```bash
# 列表
agentkit mcp service list

# 詳情
agentkit mcp service show customer-tools

# 創建（公網 + API Key）
agentkit mcp service create \
  --name customer-tools \
  --image-url cr-cn-beijing.volces.com/agentkit/customer-tools:latest \
  --inbound-api-key-name primary-key \
  --env LOG_LEVEL=INFO

# 私網
agentkit mcp service create \
  --name internal-tools \
  --image-url cr-cn-beijing.volces.com/agentkit/internal-tools:latest \
  --network private \
  --vpc-id vpc-xxxxx \
  --subnet-id subnet-xxxxx

# 自訂 JWT
agentkit mcp service create \
  --name jwt-protected-tools \
  --image-url cr-cn-beijing.volces.com/agentkit/jwt-tools:latest \
  --inbound-auth custom-jwt \
  --inbound-discovery-url https://... \
  --inbound-allowed-client web-client

# 刪除
agentkit mcp service delete customer-tools
```

---

## 沙箱（sandbox）

### 管理工具

```bash
# 創建沙箱工具
agentkit sandbox create --tool-type CodeEnv --tool-name dev-code --cpu 4

# 自訂 Private 工具
agentkit sandbox create \
  --tool-type Private \
  --tool-name private-dev \
  --image-url cr.example.com/agentkit/custom-sandbox:latest

# 刪除工具或會話
agentkit sandbox delete --tool-id tool-123 --session-id dev --force
agentkit sandbox delete --tool-name private-dev --force

# 列出本地緩存會話
agentkit sandbox list
```

### 配置

```bash
agentkit sandbox config --set tool-type=CodeEnv --set session-id=dev
agentkit sandbox config --list
```

### Dockerfile 模板

```bash
agentkit sandbox init --template code-web-server --output Dockerfile.sandbox
agentkit sandbox init    # 預設 skill 模板
```

### 構建自訂沙箱鏡像

```bash
agentkit sandbox build \
  --project-dir . \
  --dockerfile Dockerfile \
  --image-name custom-sandbox
```

### 執行命令

```bash
# 交互式終端
agentkit sandbox exec --session-id dev --command "npm test"
agentkit sandbox exec --session-id dev --mode tmux

# 非交互式（JSON 輸出）
agentkit sandbox shell --session-id dev --command "python --version"

# YAML 編排執行
agentkit sandbox run --config agentkit-sandbox-run.yaml
agentkit sandbox run --dry-run
```

### 傳檔案

```bash
agentkit sandbox scp ./local.txt sandbox:/home/gem/local.txt --session-id dev
agentkit sandbox scp sandbox:/home/gem/result.json ./result.json --session-id dev
```

### Web 預覽 & TOS Mount

```bash
agentkit sandbox web --session-id dev --no-open
agentkit sandbox mount --tool-id tool-123 --session-id dev
```

### A2A 調用沙箱 Agent

```bash
agentkit sandbox invoke --tool-id skill-tool-123 --prompt "總結項目結構"
agentkit sandbox invoke --tool-id skill-tool-123 --prompt "長任務" --async
```

### 注入 Codex/Claude 憑證

```bash
agentkit sandbox codex-login --session-id dev --provider codex
agentkit sandbox model-login --session-id dev --provider claude
```

---

## 評測（eval）

`eval` 前綴可以省略，即 `agentkit dataset ...` = `agentkit eval dataset ...`。

### Dataset

```bash
agentkit dataset list
agentkit dataset show qa-set --items 50
agentkit dataset create --name qa-set --schema "input,reference_output"
agentkit dataset add qa-set --field "input=法國首都是？" --field "reference_output=巴黎"
agentkit dataset add qa-set --file ./cases.json
agentkit dataset remove qa-set item-1 item-2 -y
agentkit dataset delete qa-set -y
```

### Evaluator & Run

```bash
agentkit evaluator list
agentkit eval run --dataset qa-set --runtime my-agent
agentkit eval experiment list
agentkit eval experiment show <experiment-id>
```

---

## Skills

```bash
agentkit skill list
agentkit skill show sk-xxxxxxxx
agentkit skill versions sk-xxxxxxxx
agentkit skill spaces
agentkit skill delete sk-xxxxxxxx --yes
agentkit onboard    # 安裝內置技能
```

---

## Harness（agentkit add / list / delete）

```bash
# 建立 harness 配置
agentkit add harness --name my-harness \
  --model-name doubao-seed-1-6-250615 \
  --tools web_search,web_fetch \
  --system-prompt "You are a helpful assistant."

# 加知識庫
agentkit add harness --name my-harness \
  --knowledgebase-type viking \
  --knowledgebase-project my-project

# 加 A2A Registry
agentkit add harness --name my-harness \
  --registry-space-id as-xxx \
  --registry-top-k 3

# 加 OAuth2 認證
agentkit add harness --name my-harness \
  --discovery-url "https://..." \
  --allowed-id client-id-1

# 啟用結構化工具調用 & 每輪注入工具定義（提高多輪穩定性）
agentkit add harness --name my-harness \
  --structured-tool-calls \
  --include-tools-every-turn

# 註冊當前項目已部署嘅 harness 到 A2A
agentkit add harness --name my-harness \
  --register-self \
  --register-space-id as-xxx \
  --register-network-type public

# 列出 harness runtime
agentkit list harness
agentkit list harness --output json --quiet
agentkit list harness --no-color          # 關閉彩色輸出
agentkit list harness --limit 100         # 每批拉取數量

# 管理 API Key 憑證
agentkit add credential --type api-key --name my-openai-key --api-key $OPENAI_API_KEY
agentkit list credentials
agentkit delete credential my-openai-key
```

---

## 其他常用指令

```bash
agentkit migrate        # 遷移現有 Agent 應用
agentkit upgrade        # 檢查並升級 CLI 版本
agentkit docs           # 喺瀏覽器開文檔
agentkit status         # 睇已部署 Agent 狀態同端點
agentkit status my-agent --json   # JSON 格式輸出詳細狀態
```
