# Security & Gateways — 方法論（AgentKit / VeADK project）

> 範圍：成個 workspace 嘅**安全 + 閘道**方法論。
> 概念源頭：`references/veadk-agentkit-gateway.md`（三層閘）＋ `references/veadk-agentkit-rbac-observability.md`（五軸安全）。
> 落地實作：`projects/fin_mate/security/`（D7，規則式、deterministic、零 LLM）+ 各 gateway 接入點。
> 驗證：`projects/fin_mate` 嘅 `make sec-eval`（42/42＋block-policy assertion）；閘道用 `make demo` / `make obs` 睇。

---

## 0. 一句話

**安全 = 每條數據路徑兩邊都有一道「過濾／閘」，且預設拒絕；閘道 = 數據喺進出系統嘅每個「出入口」嘅統一收發校驗點。** 我哋用「薄」而「可測試」嘅方法實作：規則式（rules-only）偵測＋role allowlist＋callback hook——唔自建 framework，全部用 veadk/ADK 原生 callback 位掛上去。

---

## Part A. 安全方法論

### A.1 五軸對照（reference → 本 project 落地）

來自 `references/veadk-agentkit-rbac-observability.md` 嘅五條安全軸，我哋逐條落地（狀態標明）。

| 軸 | reference 講嘅係 | fin_mate 落地（`projects/fin_mate/`） | 狀態 |
|---|---|---|---|
| 1 入站認證（Inbound） | 驗證「邊個入嚟」（OAuth／token／A2A auth） | `security/auth.py`：token→role（`.env` `FINMATE_TOKENS`，constant-time `_safe_eq`）；role 經 `security/hooks.role` contextvar 流入 gate | ✅ 簡版 |
| 2 出站憑證（Outbound） | agent 攞資源嗰陣嘅鑰匙管理（secret injection） | 唔做真 injection；改為 `security/filters.detect_sensitive` **偵測＋redact** secret（sk-/AKIA/AIza/ghp/Bearer/private key/password=…） | ✅ 偵測防洩 |
| 3 內容安全（Content Safety / PII） | 火山 LLM-FW 內容審查 | `security/filters.py`：PII（email／HK 電話／HKID／信用卡＋Luhn／passport）＋`redact_pii/redact_sensitive`（■ mask） | ✅ 規則版 |
| 4 Guardrail / Filter | 語義防護（LLM-FW）+ 硬規則 | `input_injection_filter`（`before_model_callback`，攔 prompt injection）＋`output_pii_filter`（`after_model_callback`，mask 輸出）＋`role_tool_gate`（`before_tool_callback`） | ✅ 三 hook 全掛 |
| 5 RBAC / Audit / Observability | 平台權限 + 審計 | RBAC：`security/gate.py` role×tool 矩陣；Audit：`observability.md`（transcript.jsonl 全 call 記錄）＋ OpenViking observer；回歸：`make sec-eval` | ✅ |

### A.2 原則

1. **Rules-only（deterministic）**：injection/PII/secret 偵測全部係編譯好嘅 regex，**零 LLM**、零成本、可精確測攔截率。語義判斷（LLM-FW）留接口，需要先加。
2. **Defense-in-depth**：同一道輸入要過「多閘」——`before_model_callback`（injection filter）→ `before_tool_callback`（role gate）→ `human_gate`（HITL，寫操作）→ `after_model_callback`（PII/secret redact 出返畀用戶）。blocked 唔會落入下一關（例如 HITL），見 `agent_build.py:93`。
3. **Default-deny**：`security/gate.py:32`——任何唔喺矩陣嘅 tool 只准 admin。未知＝拒。
4. **Auth 係 gate 嘅「身份輸入」**：token→`authenticate()`→role→`role()` contextvar→`role_tool_gate` 據 role 查矩陣。demo 用 `--token` 模擬正路。
5. **可驗證**：`make sec-eval` 對 4 個 deterministic golden set（injection/pii/secrets/authz，42 條）逐條斷言，最尾 check **所有越權 call 全 block**，走漏即 exit 1。

### A.3 攔截率即「測咩」

`eval/golden_datasets/security/` 定義咗「攻擊集」；`eval/run_security_eval.py` 直接打 filters＋gate（唔經 model）：

| set | n | 目標 | 結果（最新 run） |
|---|---|---|---|
| injection | 15 | 6 families（ignore_instructions／system_override／data_exfil／dev_mode／secrets_extract／role_jailbreak） | 15/15（100%） |
| pii | 10 | email／HK 電話／HKID／信用卡（Luhn）／passport ＋ 負例 | 10/10 |
| secrets | 7 | ark/sk／aws／gcp／gh／bearer／password 類 ＋ 負例 | 7/7 |
| authz | 10 | viewer<analyst<admin 越權矩陣（default-deny） | 10/10 |
| block-policy | — | 所有 golden 越權 call 必須全 block | OK |

> 呢批 set 係「活文件」：發現漏網 → 改 `security/filters.py` regex（eval 一路逼返出嚟）→ rerun `make sec-eval`。D7 開發時用呢個 loop 收窄咗 5 個真實 regex gap。

### A.4 Auth 白皮書

- **呢度用**：`FINMATE_TOKENS="viewer=<t>,analyst=<t>,admin=<t>"`（demo 用一大堆 static token）。
- **上線要用**：hash（而非原 token 落 DB）、short-lived JWT、A2A `AuthRequestProcessor`／OAuth 2.0。`security/auth.py` 只係示範「gate 點行」，唔係 production auth provider——呢個係有意識嘅取捨，見 D7_SECURITY.md §1。

---

## Part B. 閘道（Gateway）方法論

### B.1 三層閘定位（reference：`veadk-agentkit-gateway.md`）

| 層 | 做咩 | 位置 |
|---|---|---|
| 工具閘 (AgentKit Gateway / MCP) | 統一外部工具入口（MCP Service / Toolset） | agent ↔ 外部工具 |
| 模型閘 (BytePlus AI Gateway) | 統一多模型入口：quota／cache／fallback／負載均衡（六大內置插件） | app ↔ LLM |
| 方舟 AI 加速網閘 (Ark Edge) | 統一多模型 endpoint＋加速／緩存，**一行換 endpoint** | app ↔ Provider |

> 原則：**閘 = 換 endpoint 唔改 code**（reference §3：「淨係換 API base＋閘 key，code 一行唔使改」）。我哋沿用呢個 pattern：`_lib.load_env()` + `MODEL_AGENT_API_BASE/KEY`，換 provider 只改 `.env`。

### B.2 本 project 實際出現嘅「閘」（全部已有 code）

| 閘 | 喺邊 | 形態 | 驗證 |
|---|---|---|---|
| 模型接入閘 | `projects/fin_mate/agent_build.py` `model_name=[MODEL_PRIMARY, MODEL_BACKUP]`；experiments `_lib.ark_complete` ／ `engine_bench` | provider switch（Ark cloud ↔ Ollama `:11434` ↔ vLLM/SGLang 預留），LiteLLM 統一 | `make bench` 對照 |
| HTTP 服務閘（agent entry） | `veadk web`／Studio（`veadk studio`，port 8001） | ASGI `/run`、`/apps/*/sessions`（runbook：`agentkit_studio.md`） | `scripts/trace_all.py` |
| A2A agent 閘（inter-agent） | `multi_agent.py`（veadk `SequentialAgent`）；要轉真 A2A 用 `veadk.a2a.RemoteVeAgent`＋`ve_a2a_server`＋`A2AAuthMiddleware` | agent card + A2A 協定收發 | `make demo` |
| Vector 閘 | OpenViking `:1933` `/api/v1/*`（parse→embed→search） | 自架 vector 服務，server 端全權處理 | `make obs`（`/api/v1/observer/*`） |
| 觀測閘 | `otel-collector :4318` → Jaeger `:16686`；`scripts/trace_all.py` | OTLP span + trace dump + container logs 打包 | `make obs` |
| Structured-output 閘 | `experiments/schema_bench` + `risk_agent.output_schema` | Ark `text.format.json_schema`（strict）＝**數據契約** | `make schema-bench` |

### B.3 閘同安全嘅交匯（重點）

閘道唔單係「路由」，佢係**必然要設校驗嘅出入口**：

1. **入站閘 = auth 點**：人／agent 入嚟，`authenticate()` 定身份。
   - 我哋揀咗「**simple gate**」：callable token→role，因為 demo 唔使 HTTP 層。
   - A2A 真正上線要 `A2AAuthMiddleware`（JWT／OAuth）——reference 話明 inbound 唔可以淨靠信任網絡。
2. **工具閘 = RBAC 點**：`before_tool_callback` 按（tool, role）查 default-deny 矩陣；唔准入唔執行。
3. **模型閘 = filter 點**：LLM 出入都要清洗——入（injection）＋出（PII/secret）。
4. **數據契約閘 = output_schema**：structured output 唔淨止「靚」，係一個**閘**——唔合契約嘅輸出即 invalid（schema_bench 嘅 valid/parse/field_rate 就係契約遵守率）。

### B.4 決策樹簡版（reference §5）

- 得一個外部工具 → **唔使** MCP gateway，function tool 就夠（我哋而家係咁）。
- 多人並發＋多供應商＋要 quota/快取/熔斷 → 加 BytePlus AI Gateway。
- 想要「多 endpoint 一齊加速＋緩存」→ 方舟 AI 加速網閘（一行改 endpoint）。
- 多 agent 互 call（唔同語言/唔同 team）→ A2A（`RemoteVeAgent` + agent card + auth middleware）。

---

## Part C. 現狀總結

- **已落地**：三條安全 hook（in/out/tool）＋ token auth＋三級 role allowlist ＋ rules-only filter（39 條 regex，6 injection families＋5 PII＋9 secret）＋ 42/42 紅隊 eval ＋ 閘道接入點 6 個。
- **有意留白**：語義 guardrail（LLM-FW）、真 A2A auth middleware、真正的 secret vault／outbound credential injection——統統有接口／reference 對住，等有需要先開。
- **恆常命令**：`make sec-eval`（安全回歸）、`make demo`（入站→閘→委派全鏈）、`make obs`（閘點健康／trace）、`make bench`（模型閘對照）。