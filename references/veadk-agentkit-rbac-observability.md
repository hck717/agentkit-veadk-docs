# VeADK + AgentKit 安全 / 可觀測（ServingKit 睇全 — RBAC / PII / Audit / Observability / Guardrail / Filter）

呢份文件係一套 Agent 方案嘅「安全 + 合規 + 可觀測性」地圖。
唔係單純 function list——係要教你**幫 client 砌一套行得、審得、爆得（出事查得返）**嘅生產環境。

> ✅ **核心心法**：
> 1. **安全分「入、出、內容、攔截、過濾、平台」五條**：入站認證（邊個入嚟）、出站憑證（去邊度攞野）、內容安全（乜嘢過嚟）、Guardrail 攔有害（四點 + 多層防禦）、Input/Output Filter 過濾入出（PII 遮蔽）、平台 RBAC（邊個管）。
> 2. **Audit（審計）唔等於 logging**：audit 係「重現 + 簽名 + 保留」，logging 係「睇 log」。invoice 方案講 7 年保留要咁樣解。
> 3. **可觀測性唔使揀，可以疊**：APMPlus + Cozeloop + TLS 同一份 span 一次過送出；仲有內容追蹤開關（`trace_content`）。
> 4. **真銀嘅隱性成本**：安全本身接近免費，但 audit + shadow eval + PII scan 會**推高 model 消耗**（見 pricing doc §10）。

---

## 0. 快睇：五條安全軸

| 軸 | 答邊條問題 | 主力元件 |
|---|---|---|
| **入站認證** | 「邊個可以 call 我個 agent？」 | API Key / OAuth2 / JWT / VeIdentity 用戶池 |
| **出站憑證** | 「agent 去攞第三方 API 嘅 key 邊度保管？」 | Agent Identity（出站憑證托管 + 自動輪換） |
| **內容安全** | 「模型入/出有冇 PII / 有害內容？」 | `content_safety` 基於火山 LLM-FW（category 103 = 敏感資訊） |
| **Guardrail / Filter** | 「攔得住有害嘅入同出？」 | LLM-FW 四點審查 + 多層防 prompt injection + Input/Output Filter |
| **平台 RBAC** | 「邊個可以開 Runtime / 改 Studio？」 | Studio `--admin`/`--developer` + IAM |

另外**橫切一層：可觀測性**（trace/metrics/log）服務晒上面五條——出事靠佢。

---

## 1. 入站認證（Inbound）— 驗證邊個入嚟

VeADK 支援 **API Key** 同 **OAuth2**（單點登入 + JWT）兩類：

| 方式 | 做法 | 適合 |
|---|---|---|
| **API Key** | Runtime 用 API Key 鑒權；Studio 顯示時預設 mask（`****`） | 機器對機器、快速 |
| **OAuth2 / VeIdentity 用戶池** | 用戶登入用戶池 → JWT → Runtime 認得 | 人類用戶、有 SSO 要求 |
| **Custom JWT** | `custom-jwt` + OIDC Discovery URL + allowed client | 已有自有 IdP |

**VeADK 框架層直接接 `AuthRequestProcessor`**（VeIdentity）：

```python
from veadk.integrations.ve_identity import AuthRequestProcessor

agent = Agent(name="assistant", run_processor=AuthRequestProcessor())
```

**AgentKit Runtime 層**（`create_agentkit_app`）新增 `identity` 參數：AgentKit 喺 agent 或工具代碼執行前**驗證並綁定入站用戶身份**；`/ping` 健康檢查**排除**在身份綁定之外。要用呢個功能要 `agentkit-sdk-python>=0.8.2`。

> ⚠️ `/ping` 健康檢查、`/health`、`/metrics` 一類 exempt path 要諗清楚——健康檢查唔應該俾身份檢查擋住，但**唔好**將業務接口都當 exempt。

**A2A 調用下游**：可傳入站 `X-Ve-TIP-Token` + Bearer JWT；下游用入站 JWT 返回 `401` 時回退到 M2M OAuth2 重試一次。

---

## 2. 出站憑證（Outbound）— agent 攞野嘅鑰匙

Agent Identity（火山一站式身份與權限平台）負責：**加密保管 API Key 與 OAuth 令牌，憑據唔寫入 code，自動緩存、刷新與輪換**。

| 認證方式 | 點用 | 注 |
|---|---|---|
| **API Key**（出站） | 控制台建憑證 → `VeIdentityFunctionTool` / `VeIdentityMcpToolset` 注入 | 普通函數工具用前者，MCP 工具集用後者 |
| **OAuth2 M2M** | 建 M2M 用戶池客戶端 → 換 JWT | 服務之間（機器對機器） |
| **OAuth2 用戶委託** | 用戶首次授權 → Agent Identity 自動完成 token 交換 + 刷新 | 用戶撤銷後調用報錯，要提示重新授權 |

```python
# 出站憑證注入範例（概念）
tool = VeIdentityFunctionTool(
    fn=call_crm_api,
    auth_config=api_key_auth("your-outbound-cred-name"),
)
```

> **Sales 一句**：「我哋嘅出站 key 唔會入你個 repo，Agent Identity 幫你轉緊、你哋自己人唔使貼 secret 落 code。」——呢個係同自架 LangGraph 最唔同嘅位。

---

## 3. 內容安全（Content Safety / PII）— 用火山 LLM-FW

`content_safety` 掛喺 agent 執行流程嘅回調上，借**火山大模型應用防火牆（LLM-FW）**做四點審查：

| 審計點 | 幾時 | 攔乜 |
|---|---|---|
| Before Model | 入 model 前 | 用戶輸入有冇攻擊 / PII |
| After Model | model 出咗 | 輸出有冇敏感資訊 |
| Before Tool | 工具 call 前 | 入參有冇問題 |
| After Tool | 工具返嚟 | 返回有冇 PII |

**LLM-FW 一級分類（節錄）**：

| 代碼 | 策略 | 一句 |
|---|---|---|
| 101 | 模型濫用 | 防止詐騙 / 違法 prompt |
| **103** | **敏感資訊（PII）** | **實時偵測輸入輸出嘅隱私數據（身份證、手機號）並攔截** |
| 104 | 提示詞攻擊 | 防越獄 / DAN mode / 系統提示詞外洩 |
| 106 | 通用話題控制 | 敏感話題（例：推股票）——**預設唔開，要自己配** |
| 107 | 算力消耗 | 惡意重複輸出攻擊（累積 pattern 先觸發） |

**配置**：先買 LLM-FW 實例、加資產、攞 AppID → `TOOL_LLM_SHIELD_APP_ID` 或 `config.yaml` 嘅 `tool.llm_shield.app_id` → 掛回調。

```python
from veadk.tools.builtin_tools.llm_shield import content_safety

agent = Agent(
    name="robot",
    before_model_callback=content_safety.before_model_callback,
    after_model_callback=content_safety.after_model_callback,
    before_tool_callback=content_safety.before_tool_callback,
    after_tool_callback=content_safety.after_tool_callback,
)
```

> ⚠️ **category 103 就係你要答 client「PII 點算」嗰嚿**——直接答：「入/出/工具三個點都過 LLM-FW 103，敏感資料一被偵測就攔。」
> ⚠️ 106 話題控制**唔係默認**——要 PII 保護一定要開 103，要敏感話題控制記住加 106。

---

## 4. Guardrail（攔有害 / 敏感內容）— 多層防禦

### 4.1 概念：guardrail 係「安全」，filter 係「乾淨」

- **Guardrail**：攔有害 / 違法 / PII——目標係**安全**。
- **Filter**：過濾入出內容——目標係**乾淨**（見 §5）。
- 兩者有重疊但目標唔同；production **兩個都要**。

> ✅ §3 嘅 `content_safety` 四點回調 = Guardrail 嘅**一級防線**（LLM-FW）。本節再加：**多層防禦策略** + **同其他家比較**。

### 4.2 防 prompt injection 嘅多層防禦

| 層 | 做法 | 點解 |
|---|---|---|
| ① 內容安全 | LLM-FW category **104**（提示詞攻擊） | 攔越獄 / DAN / system prompt 外洩 |
| ② 輸入隔離 | 唔好將外部內容同指令混埋（分隔符 / 指令重申） | 降低注入成功率 |
| ③ 權限最小化 | tool 權限收窄（Agent Identity 只授需要嘅） | 被注入都做唔到壞事 |
| ④ 輸出過濾 | After-Model 審查（見 §5） | 擋住敏感資料外洩 |
| ⑤ 監控 | OTel / APMPlus 異常偵測 | 事後發現 + 響應 |

> ⚠️ **冇單一銀彈**——prompt injection 靠多層防守。104 係第一層，但唔好依賴佢做唯一防線。

### 4.3 vs 其他家

| | BytePlus（LLM-FW） | Azure Content Safety | Bedrock Guardrails |
|---|---|---|---|
| 接入 | 框架掛鈎（`content_safety` 回調） | 另接服務 | 另接服務 |
| 計費 | **內置接近免費** | 逐次計 | $0.15/1K units（in+out 各一） |
| PII 實時 | category 103 四點 | 有 | 有 |

> **Sale 一句**：「Guardrail = 喺 agent 面前架個防火牆，唔係淨係睇 output——四個點（入 model / 出 model / 入工具 / 出工具）都過 LLM-FW，再加 prompt injection 多層防禦。我哋嘅 LLM-FW 計費接近免費，唔似 Azure / Bedrock 逐次收。」

---

## 5. Input / Output Filter（過濾入 / 出）— 雙向乾淨

### 5.1 概念：兩邊都要擋

| 種類 | 過濾乜 | 幾時用 |
|---|---|---|
| **Input filter（入）** | 唔想 agent 見嘅內容（黑白名單 / prompt injection 字樣 / 過長截斷 / 語言） | 公開入口、多租戶 |
| **Output filter（出）** | 唔想俾用戶見嘅內容（mask 電話 / 合規敏感詞 / 格式清理 / 品牌管控） | 有 PII 輸出、品牌 |
| **PII masking** | 偵測並遮罩個人資料（電話 / 身份證 / email） | 合規（金融 / 健康） |
| **Rate / abuse filter** | 用量限制、惡意重複 | 防濫用、防爆單 |

### 5.2 過濾機制對比

| 機制 | 原理 | 優點 | 弱點 | 幾時用 |
|---|---|---|---|---|
| **Regex / 規則** | 字串 pattern | 快、平、可預測 | 假陽性 / 假陰性 | 電話 / email / 特定詞 |
| **ML 偵測** | 模型分類 | 語意、揸唔定都捉到 | 貴、要 model | PII / 有害內容（LLM-FW） |
| **遮蔽（mask）** | 偵測後換 `*` | 保留其餘 | 要另做還原流程 | 日誌 / trace 出街 |
| **審批（HITL）** | 人睇過先放 | 最準、可控 | 慢、貴 | 高風險 |

### 5.3 喺 stack 點做

| 要做 | 用 | 見 |
|---|---|---|
| 內容安全（Guardrail 一級） | LLM-FW 四點 + category 103 | §3 / §4 |
| Prompt injection 防禦 | category 104 + 輸入隔離 + 權限最小化 | §4.2 |
| Trace 唔寫敏感嘢 | `OBSERVABILITY_OPENTELEMETRY_TRACE_CONTENT=false` | §7 |
| Logging 唔洩 prompt | `LOGGING_LEVEL=INFO`（DEBUG 會記 prompt / 輸出 / 工具參數） | §7 |
| 出站憑證唔入 repo | Agent Identity（托管 + 自動輪換） | §2 |
| PII 遮蔽出街 | Output filter / mask（金融 / 健康合規） | §5.1 |

> **Sale 一句**：「入 filter 擋『啲客傳咩入嚟』，出 filter 擋『我哋 agent 講咩出街』。兩邊都要，唔好只做一邊——trace 同 log 都係『出街』。」

---

## 6. 平台 RBAC（Studio / Frontend）— 邊個管

`veadk studio` / `veadk frontend` / `veadk studio deploy` 支援基於角色嘅訪問控制：

| 角色 | 可以 | 設定 |
|---|---|---|
| **admin** | 全部 Runtime + 管理 Studio / 部署 | `--admin "bob@example.com,alice"` |
| **developer** | 自己創建嘅 Runtime + 開發工具 | `--developer "carol@example.com"` |
| （普通用戶） | 只可用被指派嘅 Runtime | 冇 `--admin`/`--developer` 時預設 |

- 唔同角色喺「管理智能體」頁面同選擇器嘅**可見性**都唔同：admin 見全部，developer/普通用戶只見到自己創建。
- 同一身份同時喺兩個名單 → **admin 優先**。
- 角色對應埋 Studio「技能生成」呢類進階能力（Dev Sandbox 技能生成只對 developer / admin 開放）。

**底層仲有 IAM**：`veadk studio deploy` 默認建 `VeADKFrontendServiceRole` + `VeADKFrontendPolicy`；生產環境應該審查權限範圍，要收窄就用 `--iam-role` 指定預先配好嘅 Role。

> ⚠️ 部署默認 Role 有**廣泛權限**（可開 AgentKit Runtime + 雲資源）。上線前一定要由管理員收窄或用自有 IAM Role。

---

## 7. Audit（審計）— 出事要重現 + 簽名 + 保留

**Audit ≠ log**。Audit 要能答：「邊個、幾時、做咗乜、個模型見到乜、最後係咪一致。」

| Audit 要求 | 用邊樣做 | 注意 |
|---|---|---|
| 記錄 agent 每一步 | OTel span + TLS 集中日誌 | `trace_content` 默認記錄 prompt/completion/工具入出 |
| 可重現 | `runner.run` + session trace dump 落 JSON | `tracer.dump(user_id, session_id)` 出 span JSON |
| 防篡改 | chain-hash（invoice 方案嘅概念） | 喺 DB 存 hash 鏈，唔係淨係 log |
| 保留 7 年 | TOS archive + PostgreSQL 寫入 | 儲存計費（見 pricing doc §8） |
| 身份關聯 | `create_agentkit_app(identity=...)` | 每個 span 綁到入站用戶 |

**實務**：APMPlus / Cozeloop 留近期 trace（熱儲存）；TLS 做集中長期留存；invoice 方案嘅 chain-hash + TOS archive 做合規層。三層唔衝突，可以同時開。

---

## 8. Observability — trace / metrics / log 三合一

**統一入口 `OpentelemetryTracer`**：持有一組 exporter，自動附加一個內存 exporter 用嚟本地落盤。

| Exporter | 目標 | 用嚟 |
|---|---|---|
| `APMPlusExporter` | 火山 APMPlus | trace + 指標（模型調用次數 / token 用量 / 操作耗時 / 異常 / 工具耗時），`reasoning` 內容單獨標注 |
| `CozeloopExporter` | Cozeloop | 鏈路觀測 + 評測 |
| `TLSExporter` | 火山日志 TLS | 集中存儲、長期留存、跨服務分析 |
| `InMemoryExporter` | 進程內存 | 本地 debug、`dump` 落 JSON（自動附加，唔可以手加） |

```python
from veadk.tracing.telemetry.exporters.apmplus_exporter import APMPlusExporter
from veadk.tracing.telemetry.exporters.cozeloop_exporter import CozeloopExporter
from veadk.tracing.telemetry.exporters.tls_exporter import TLSExporter
from veadk.tracing.telemetry.opentelemetry_tracer import OpentelemetryTracer

tracer = OpentelemetryTracer(
    exporters=[APMPlusExporter(), CozeloopExporter(), TLSExporter()]
)
agent = Agent(tools=[...], tracers=[tracer])
```

**唔使寫 code 嘅方式**（環境變數自動掛載）：

```bash
export ENABLE_APMPLUS=true
export ENABLE_COZELOOP=true
export ENABLE_TLS=true
```

**內容追蹤開關**（敏感數據場景）：
- `OBSERVABILITY_OPENTELEMETRY_TRACE_CONTENT=false` → span 只保留結構 + 耗時，**唔寫 prompt/completion/工具入出**。
- 涉及 PII 嘅生產環境建議關（或者同 PII 遮罩併用）。

**複用全局 TracerProvider**：初始化時已存在全局 provider → VeADK 複用佢並自動移除 `APMPlusExporter`（當佢已負責），其他 exporter 照註冊。查 `tracer.apmplus_managed_externally` 確認。

**Logging（應用日誌）**：自 1.0.5 用 Python 標準庫 `logging`（唔再 Loguru）。`veadk` namespace，預設 stdout。`LOGGING_LEVEL`（預設 `DEBUG`）控制；**DEBUG 會記錄模型輸出、思考、工具參數/結果，生產記得轉 INFO**。

```bash
export LOGGING_LEVEL=INFO
```

```python
import logging
logging.getLogger("veadk").setLevel(logging.INFO)
app_logger = logging.getLogger("company_assistant")
```

**CLI 快速睇**：`agentkit runtime logs my-agent --limit 200`。

---

## 9. 一頁式「開到盡」配置示例

```python
# 安全 + 合規 + 觀測 全開（概念組裝）
from veadk import Agent, Runner
from veadk.integrations.ve_identity import AuthRequestProcessor
from veadk.tools.builtin_tools.llm_shield import content_safety
from veadk.tracing.telemetry.opentelemetry_tracer import OpentelemetryTracer
from veadk.tracing.telemetry.exporters.apmplus_exporter import APMPlusExporter
from veadk.tracing.telemetry.exporters.tls_exporter import TLSExporter

tracer = OpentelemetryTracer(exporters=[APMPlusExporter(), TLSExporter()])

agent = Agent(
    name="compliant_bot",
    run_processor=AuthRequestProcessor(),                # 入站身份
    before_model_callback=content_safety.before_model_callback,   # Guardrail（LLM-FW 103）
    after_model_callback=content_safety.after_model_callback,
    before_tool_callback=content_safety.before_tool_callback,
    after_tool_callback=content_safety.after_tool_callback,
    tracers=[tracer],                                    # 可觀測性
)
```

對應 AgentKit Runtime 層：`create_agentkit_app(root_agent=..., identity=...)` 加返身份邊界；deploy 用 `--admin`/`--developer` 鎖 Studio；出站用 `VeIdentityFunctionTool`。

> Input / Output Filter（§5）喺呢個基礎上再加：public endpoint 加 regex/ML filter 做過濾；output 端加 PII mask；trace 開關 `TRACE_CONTENT=false` 搵敏感嘢。

---

## 10. 隱性成本（Sales 必讀）

| 項目 | 間接成本 |
|---|---|
| Content-safety 四點 callback | 每次多一次 LLM-FW API call（價格極低，但次數多） |
| PII scan / mask | 每次多一次 API call / token 處理 |
| Audit trace 全開（`trace_content=true`） | span payload 增大 → 儲存/流量 |
| TLS 長期留存 + TOS archive | 儲存計費（0.0015 元/GB/小時 起） |
| Shadow eval（10% 流量） | **+10% 模型消耗**（見 pricing doc §10） |
| Guardrail（LLM-FW） | 接近免費（內置），但 category 106/107 開咗多一條路 |
| Input/Output Filter | regex/ML filter 有自己嘅 infra 成本；PII mask 額外處理 |
| RBAC / IAM / secrets | 純軟件，冇直接雲費（自架 Vault 另計） |

> 報價金句：「安全係『集中做、唔分開買』——但 audit 7 年留存 + shadow eval 一定要計入隱性 +%。」詳見 `veadk-agentkit-pricing.md` §10。

---

## 11. 資料來源

| 來源 | URL | 日期 |
|---|---|---|
| 入站認證（API Key / OAuth2 / JWT） | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/security/inbound | 頁面日 |
| 出站認證（Agent Identity / VeIdentityFunctionTool / M2M） | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/security/outbound | 頁面日 |
| 內容安全（LLM-FW / category 101-107） | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/security/content-safety | 頁面日 |
| Agent Identity 官方文檔 | https://www.volcengine.com/docs/86848/2080920 | 頁面日 |
| `create_agentkit_app` `identity` 參數（需 sdk>=0.8.2） | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/deploy/agentkit | 2026-xx（1.0.10） |
| Studio RBAC（`--admin`/`--developer`）/ IAM Role | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/frontend/studio | 頁面日 |
| 可觀測概述 + 全部 Exporter + `trace_content` | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/observability | 頁面日 |
| APMPlus（指標 + `reasoning`） | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/observability/apmplus | 頁面日 |
| 應用日誌（stdlib logging / LOGGING_LEVEL） | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/observability/logging | 頁面日 |
| InMemoryExporter / `dump` 落盤 | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/observability/inmemory | 頁面日 |
| Guardrail / Input-Output Filter | `references/veadk-agentkit-ai-concepts.md` §10/§11（概念深入版） | 2026-08-17 |
| 隱性成本 / shadow eval | `references/veadk-agentkit-pricing.md` | 2026-08-09 |

> **免責**：Guardrail / Filter 嘅多層防禦策略係最佳實踐建議，唔係產品保證。LLM-FW category 開關以方舟控制台當刻為準。各模型/功能存在性以方舟控制台當刻為準。

---

*Last audit date: 2026-08-17 · Guardrail / Filter 內容由 `veadk-agentkit-ai-concepts.md` §10/§11 整合至此；RBAC 名單、exempt path、Audit 保留週期按項目要求再收緊。*