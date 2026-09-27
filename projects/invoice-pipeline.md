# Invoice Processing Pipeline — Project Plan

呢個 project 係一個多 Agent 嘅發票處理系統，用 A2A 通訊串連 5 個獨立 Agent，
每個 Agent 可以獨立 deploy、獨立 eval。最終目標係 Upload 發票 → 自動提取 →
翻譯 → 自我驗證 → 匯總 → 人類審批。

---

## 整體流程

```
[Upload] ──── TOS (Object Storage)
   │
   ▼
Agent1 — OCR Agent             提取發票上嘅文字，轉成結構化 JSON
   │                           模型：Seed 2.0 Lite（多模態 Vision）
   │ A2A
   ▼
Agent2 — Translation Agent     將提取咗嘅 field 翻譯成統一語言
   │                           模型：Seed 2.0 Mini / BytePlus Translate API
   │ A2A
   ▼
Agent3 — Validation Agent      自我驗證：對比原始圖確認 OCR 正確，有錯就修正
   │                           模型：Seed 2.0 Lite（多模態 Vision）
   │ A2A
   ▼
Agent4 — Aggregation Agent     將多張已驗證發票標準化、加總、cross-reference
   │                           模型：Seed 2.0 Mini
   │ A2A
   ▼
Agent5 — Approval Agent        人類審批（VeADK Frontend + Feishu 通知）
   │                           用 A2UI 顯示發票 + 提取結果 + 驗證報告
   │ HITL
   ▼
[Done / Rejected / Edited]
```

---

## Agent 角色詳情

### Agent1：OCR Agent

| 項目 | 細節 |
|------|------|
| **角色** | 將發票圖片轉成結構化數據 |
| **模型** | **Seed 2.0 Lite** (極速模型 1× AFP) — Agent Plan Medium 可用，支援 Vision + 文字 |
| **工具** | 無需額外 tools，靠模型本身 vision capability |
| **輸入** | 發票圖片（JPEG / PNG / PDF），經 **TOS** 儲存做持久化 |
| **輸出** | `raw_invoice.json` — `invoice_number`, `date`, `vendor`, `amount`, `tax`, `currency`, `line_items[]`, `detected_language` |
| **A2A** | 完成後 call Agent2 endpoint，傳 `raw_invoice.json` + TOS 圖 key |
| **Eval** | 同 ground truth 對比 field-level accuracy |
| **AFP/5張batch** | ~25 AFP |
| **日後升級** | 換 `seed-2-0-pro-260324`（標準模型 3× AFP）提升手寫辨認率 |

```python
# ocr_agent.py — 概念
from veadk import Agent
from agentkit.a2a_app import AgentkitA2aApp

a2a = AgentkitA2aApp(name="ocr_agent", model_name="seed-2-0-lite-260228")
agent = Agent(
    name="ocr_extractor",
    model_name="seed-2-0-lite-260228",  # 極速模型 1× AFP — Agent Plan Medium
    instruction="Extract all invoice fields from the image. Output as JSON with detected_language.",
)
```

### Agent2：Translation Agent

| 項目 | 細節 |
|------|------|
| **角色** | Detect language → 將所有 field 翻譯成統一語言（如英文） |
| **模型** | **Seed 2.0 Mini** (極速模型 1× AFP)，或 **BytePlus Translate API**（專用翻譯服務，計費獨立） |
| **輸入** | Agent1 嘅 `raw_invoice.json` + `detected_language` |
| **輸出** | `translated_invoice.json` — 每個 field 有 `value`（翻譯後） + `original`（保留原文） |
| **Eval** | BLEU score、numeric preservation rate（唔可以改錯數字！） |

```python
# translation_agent.py — 概念（Seed 2.0 Mini LLM — 極速模型 1× AFP）
agent = Agent(
    name="translator",
    model_name="seed-2-0-mini-260428",
    instruction="""Translate all text fields of the invoice to English.
    Keep numeric fields (amount, tax, invoice_number) exactly as-is.
    Output format: {{"field": {{"value": "translated", "original": "原文"}}}}""",
)

# 或者 BytePlus Translate API（直接 call API，無需消耗 AFP）
# from byteplus.translate import TranslateClient
# client = TranslateClient(ak="<ak>", sk="<sk>")
# result = client.translate(text="有限公司", target_lang="en")
```

### Agent3：Validation Agent

| 項目 | 細節 |
|------|------|
| **角色** | **Corrective self-validation** — 攞返原圖，比對 extracted + translated data 確認正確 |
| **模型** | **Seed 2.0 Lite** (極速模型 1× AFP，多模態 Vision睇圖) + rule-based check（amount sum, date format） |
| **輸入** | `translated_invoice.json` + 原圖 |
| **驗證項目** | amount = line items 加總？date 係 valid？vendor name 對唔對得返圖？currency 合理？ |
| **修正機制** | 發現問題 → inspect 圖上對應區域 → 修正 → 記錄 `correction_log` |
| **輸出** | `validated_invoice.json` + `validation_report.json`（confidence score、改過咩、點解改） |
| **Eval** | Bug-finding rate、false positive rate、correction accuracy |

```python
# validation_agent.py — 概念
agent = Agent(
    name="self_validator",
    model_name="seed-2-0-lite-260228",  # 極速模型 1× AFP — 多模態 Vision
    instruction="""Compare extracted invoice data against the original image.
    Check: amount vs line_items sum, date validity, vendor name match, currency consistency.
    If discrepancy found, correct the field and log the correction reason.""",
)
```

### Agent4：Aggregation Agent

| 項目 | 細節 |
|------|------|
| **角色** | 食入多張已驗證發票，做標準化、cross-reference、加總 |
| **模型** | **Seed 2.0 Mini** (極速模型 1× AFP) — 純文字 task，Mini 夠用 |
| **輸入** | `List[validated_invoice.json]`（同一個 batch） |
| **輸出** | `aggregated_report.json` — `total_amount`, `itemized_summary`, `discrepancies[]`, `currency_converted`, `duplicate_flags[]` |
| **Eval** | 總和誤差率、duplicate detection 準確率 |

```python
# aggregation_agent.py — 概念
agent = Agent(
    name="aggregator",
    instruction="""Standardize and aggregate multiple invoices.
    Flag duplicates (same invoice_number), calculate totals, detect discrepancies.""",
)
```

### Agent5：Approval Agent (Human-in-the-Loop)

| 項目 | 細節 |
|------|------|
| **角色** | 將結果呈現畀人類 reviewer，處理 approve / reject / edit |
| **模型** | **Seed 2.0 Lite** (極速模型 1× AFP) 判斷 anomaly + **Feishu/Lark** 推送審批通知 |
| **A2UI** | `enable_a2ui=True` — VeADK 內置 rich card UI，顯示發票資料 + 驗證報告 |
| **HITL flow** | Agent 識別 anomaly → 標記需審批 → Frontend 顯示 → 人類動作 → Agent 繼續 downstream |
| **輸出** | `approval_result.json` — `status` (approved/rejected/edited), `reviewer_notes`, `approved_by` |
| **Eval** | Approval throughput、human override rate、anomaly detection precision/recall |

```python
# approval_agent.py — 概念
from veadk import Agent, Runner
from veadk.integrations.agentkit import create_agentkit_app

agent = Agent(
    name="approval_agent",
    enable_a2ui=True,
    instruction="""Flag suspicious invoices for human review.
    Present invoice data, validation report, and aggregated summary in the A2UI.
    Wait for human approval before marking as complete.""",
)
```

---

## A2A 通訊設計

每個 Agent 用 `AgentkitA2aApp` 包裝，透過 A2A protocol 串連：

```python
# 每個 agent 獨立一個 service，互相 call A2A endpoint
# Flow: Agent1 → Agent2 → Agent3 → Agent4 → Agent5

# Agent1 完成後 auto-invoke Agent2
@a2a_ocr.agent_executor(name="ocr_agent")
async def ocr_flow(image_data: dict) -> dict:
    raw = await ocr_agent.run_async(messages=image_data["base64"])
    # 自動 call Agent2 嘅 A2A endpoint
    translated = await call_a2a_agent("translation-agent", raw)
    return translated
```

### Error Handling & Loopback

Agent3 發現 OCR 錯誤時可以 loopback 返 Agent1 嘅特定區域 re-OCR：

```
Agent3 發現 amount 唔對 → call Agent1 re-OCR (只限 amount 區域)
                        → Agent1 返新結果
                        → Agent3 再驗證
                        → 連續 3 次錯就 flag 畀人類
```

---

## Deployment 策略

每個 Agent 獨立 deploy，可以唔同 model、唔同 scale：

```bash
# 用 ModelArk Managed Agents 或 AgentKit CLI 逐個 deploy
ak deploy ocr-agent --app-name invoice-ocr
ak deploy translation-agent --app-name invoice-translation
ak deploy validation-agent --app-name invoice-validation
ak deploy aggregation-agent --app-name invoice-aggregation
ak deploy approval-agent --app-name invoice-approval

# 每個 agent 有自己的 config.yaml
ak config set --app-name invoice-ocr MODEL_AGENT_NAME="seed-2-0-lite-260228"
ak config set --app-name invoice-translation MODEL_AGENT_NAME="seed-2-0-mini-260428"
ak config set --app-name invoice-validation MODEL_AGENT_NAME="seed-2-0-lite-260228"
ak config set --app-name invoice-approval FEISHU_NOTIFICATION_ENABLED="true"

# 日後 upgrade path：逐個 agent 換 model 名就得
# ak config set --app-name invoice-ocr MODEL_AGENT_NAME="seed-2-0-pro-260324"  # 升級到標準模型
```
```

---

## Evaluation 策略

每個 Agent 有獨立 eval dataset 同指標：

| Agent | Eval Dataset | 主要指標 | 次要指標 |
|-------|-------------|---------|---------|
| **OCR** | 100 張人工標注發票（多語言、多格式） | Field F1 | Character Error Rate, field-level precision/recall |
| **Translation** | 50 張多語言發票配 expected translation | BLEU score | Numeric preservation rate (必須 100%) |
| **Validation** | 50 張人工注入錯誤發票（改金額、改日期等） | Bug-finding rate | False positive rate, correction accuracy |
| **Aggregation** | 20 batches（每 batch 3-5 張） | 總和誤差率 | Duplicate detection accuracy |
| **Approval** | 模擬審批場景 + 歷史數據 | Anomaly precision/recall | Throughput (approvals/hour) |

```bash
# 每個 agent 可以獨立 run eval
python eval/ocr_eval.py --test-data eval/test_data/ground_truth/
python eval/validation_eval.py --test-data eval/test_data/error_injected/
```

---

## Production Infrastructure

### 1. Database — 每層用咩 Backend

| Component | Backend | 用途 |
|-----------|---------|------|
| **STM (Session)** | PostgreSQL / MySQL（生產） / SQLite（開發） | 存每個 invoice batch 嘅 session 狀態、提取進度 |
| **LTM (長期記憶)** | **VikingDB**（生產）/ **OpenViking**（國內）/ SQLite（開發） | 跨 session 記 vendor 特徵、OCR 糾正模式、用戶翻譯偏好 |
| **KnowledgeBase** | **VikingDB** / **OpenViking** | 存 invoice template 庫、vendor 地址簿、稅率表 |
| **Artifacts** | **TOS**（Volcengine Object Storage） | 原始發票圖、提取 JSON、驗證報告、審批記錄 |
| **Metadata** | PostgreSQL | Agent logs、eval results、deployment config |
| **Cache** | Redis | 短暫快取 OCR 結果、translation cache |

```python
# configs/ocr.yaml — Agent1 Database 配置
short_term_memory:
  backend: postgresql
  db_url: postgresql://user:pass@pg-internal.vpc:5432/invoice_stm
  session_ttl_hours: 24

long_term_memory:
  backend: viking
  app_name: invoice_ltm
  index: vendor_patterns
  host: vikingdb-internal.vpc
  port: 8080

knowledge_base:
  backend: viking
  index: invoice_templates

storage:
  backend: tos
  bucket: invoice-artifacts
  region: cn-beijing
  internal_endpoint: true  # 用內網 endpoint
```

### 2. ShortTermMemory — Session 管理

每個 invoice batch 係一個 session，跟 batch_id：

```python
from veadk.memory.short_term_memory import ShortTermMemory

# 生產 — PostgreSQL
stm = ShortTermMemory(
    backend="postgresql",
    db_url="postgresql://user:pass@pg-internal.vpc:5432/invoice_stm",
    session_ttl_hours=24,        # 24h 後自動 expiry
    cleanup_interval_minutes=60,  # 每小時清過期 session
)

# 開發 — SQLite
stm_dev = ShortTermMemory(
    backend="sqlite",
    local_database_path="./stm_dev.db",
)

# Session CRUD 用法
session = await stm.create_session(
    app_name="invoice_pipeline",
    user_id="user-42",
    session_id="batch-20260730-001",  # batch_id
    metadata={
        "batch_size": 5,
        "uploaded_at": "2026-07-30T10:00:00Z",
        "status": "processing",
    },
)

# 跨 session 進度追蹤
progress = await stm.get_session("invoice_pipeline", "user-42", "batch-20260730-001")
# → { ..., "status": "awaiting_approval", "current_agent": "agent5" }
```

Session expiry & 清理策略：

```yaml
session_policy:
  ttl: 24h                    # batch 有效期
  extended_if_active: true    # 審批中自動延長
  cleanup_cron: "0 * * * *"  # 每小時清理
  max_sessions_per_user: 100  # 每人最多 100 個 active session
```

### 3. LongTermMemory — 跨 Session 學習

Agent3 (Validation) 發現嘅 OCR 錯誤可以記住，下次同 vendor 唔再犯：

```python
from veadk.memory.long_term_memory import LongTermMemory

ltm = LongTermMemory(
    backend="viking",
    app_name="invoice_ltm",
    embedding_model="seed-2-0-lite-260228",  # BytePlus embedding
)

# Agent3 記錄糾正模式
await ltm.save_memory(
    user_id="system",
    memory_type="ocr_correction_pattern",
    content={
        "vendor": "ABC Logistics",
        "field": "amount",
        "error_pattern": "commas_ignored",
        "correction": "1,234.56 → 1234.56",
        "confidence": 0.95,
    },
)

# Agent1 OCR 前查詢相關糾正模式
patterns = await ltm.search_memory(
    query="ABC Logistics amount comma",
    memory_type="ocr_correction_pattern",
    top_k=5,
)
```

LTM 數據 retention 策略：

```yaml
ltm_policy:
  retention_days: 365         # 保留一年
  min_confidence: 0.7         # 低信心唔記
  dedup_threshold: 0.95       # 重複記錄 threshold
  auto_archive: true          # 舊 data 自動 archive 去 TOS
```

### 4. Context Management — Session 上限同壓縮

```python
from google.adk.apps.app import App, EventsCompactionConfig

app = App(
    name="ocr_agent",
    root_agent=agent,
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=5,    # 每 5 輪壓縮一次
        overlap_size=2,           # 保留最後 2 個 events
    ),
    max_session_messages=100,     # session 上限 100 條 msg
)

# 生產 context 策略
context_policy:
  max_input_tokens: 8000          # 每輪最大 input tokens
  max_output_tokens: 4000         # 每輪最大 output tokens
  window_strategy: sliding        # sliding window / summary / hybrid
  window_size: 20                 # 保留最近 20 條 message
  summary_model: seed-2-0-lite   # 用輕量模型做摘要
```

### 5. Security

| 層面 | 措施 |
|------|------|
| **A2A Internal** | A2A 端點行 internal VPC + mTLS，唔出 public internet |
| **API Keys** | 用 **Volcengine IAM** 管理；A2A 之間傳 JWT token |
| **身份驗證** | `AuthRequestProcessor` — 每次 `runner.run()` 前驗證用戶身份 |
| **Invoice Data** | TOS bucket 行 server-side encryption；圖片用 pre-signed URL |
| **Feishu HITL** | Feishu 審批 bot 經 OAuth 2.0 授權 |
| **ModelArk API** | API key 限 IP whitelist，只限 VPC 內 IP call |
| **審計日誌** | 所有 Agent 動作寫 audit log 去 PostgreSQL |

```python
# A2A internal security
@a2a_ocr.agent_executor(name="ocr_agent")
async def ocr_flow(image_data: dict, auth: dict) -> dict:
    # JWT 驗證
    if not verify_jwt(auth["token"], role="service"):
        raise PermissionError("Invalid A2A token")
    
    # AuthRequestProcessor 驗證 user identity
    user_id = auth.get("user_id")
    return await runner.run(messages=image_data, user_id=user_id)

# security.yaml
security:
  a2a_auth:
    type: mTLS
    cert_path: /etc/certs/a2a-client.pem
    key_path: /etc/certs/a2a-key.pem
    ca_path: /etc/certs/ca.pem
  
  api_key_management:
    provider: iam              # Volcengine IAM
    rotation_days: 90
    auto_rotate: true
  
  auth_processor:
    enabled: true
    provider: ve_identity      # Volcengine Identity
    cache_ttl_seconds: 300
```

### 6. Access Control (RBAC)

```yaml
rbac:
  roles:
    - name: uploader
      permissions: [upload_invoice, view_own_batch]
    - name: reviewer
      permissions: [view_batch, approve_invoice, reject_invoice, edit_invoice]
    - name: admin
      permissions: [all, manage_users, view_audit_log, delete_batch]
  
  rate_limiting:
    upload: "100/hour per user"
    approve: "500/hour per user"
    api: "1000/minute per app"
  
  # 每個 Agent 對應嘅最小權限
  agents:
    ocr_agent: [service_account]
    translation_agent: [service_account]
    validation_agent: [service_account]
    aggregation_agent: [service_account]
    approval_agent: [reviewer, admin]       # HITL 先有人類 role
```

### 7. Network Architecture

```
                      ┌──────────────────────┐
                      │   Internet / VPN      │
                      │   (User Upload)       │
                      └──────────┬───────────┘
                                 │
┌────────────────────────────────┼────────────────────────────┐
│                     VPC (Internal)                         │
│                                                             │
│  ┌──────────┐   A2A (mTLS)   ┌──────────┐    ┌──────────┐  │
│  │ Agent1   │◄──────────────►│ Agent2   │... │ Agent5   │  │
│  │ (OCR)    │                │ (Trans)  │    │ (Approval)│  │
│  └────┬─────┘                └────┬─────┘    └────┬─────┘  │
│       │                          │                │         │
│       ▼                          ▼                ▼         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Internal Services                       │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │   │
│  │  │ TOS      │  │ VikingDB │  │ PostgreSQL│          │   │
│  │  │ (Object) │  │ (Vector) │  │ (Meta)   │          │   │
│  │  └──────────┘  └──────────┘  └──────────┘          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Egress Only                             │   │
│  │  ModelArk API ──► api.byteplus.com (whitelisted)    │   │
│  │  Feishu Bot  ──► open.feishu.cn                     │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

Firewall 規則：

```
# 只允許內網 VPC 互通
inbound:
  - from: vpc_cidr (10.0.0.0/16)
    to: agents (port 8080-8090)
    protocol: tcp
  
  - from: load_balancer
    to: ingress_gateway (port 443)
    protocol: tcp

outbound:
  - to: api.byteplus.com (port 443)
    purpose: ModelArk API calls
  - to: open.feishu.cn (port 443)
    purpose: Feishu notification
  - to: tos-cn-beijing.volces.com (port 443)
    purpose: TOS API
  - all_other_egress: denied
```

### 8. Evaluation Infrastructure

```yaml
# eval 基礎設施
eval_pipeline:
  # CI eval — 每次 code change 自動跑
  ci:
    trigger: on_push / nightly
    scope: [ocr_eval, translation_eval, validation_eval]
    test_data: eval/test_data/
    threshold:
      ocr_field_f1: 0.85
      translation_bleu: 0.75
      validation_bug_finding_rate: 0.90
  
  # 離線 eval — 定期跑全面 eval
  offline:
    trigger: weekly
    scope: [all]
    test_data:
      - eval/test_data/ground_truth/          #已知 ground truth
      - eval/test_data/regression/            # regression test set
      - eval/test_data/adversarial/           # 對抗測試（錯誤注入）
  
  # 生產監控 — 持續 monitoring
  monitoring:
    type: shadow_eval                          # shadow eval 唔影響 production
    sample_rate: 0.1                          # 10% 流量做 eval
    metrics:
      - ocr_field_f1
      - validation_detection_rate
      - approval_throughput
      - human_override_rate

# Ground truth 管理
ground_truth:
  storage: TOS bucket (gt-invoice-data)
  format: |
    {
      "image_key": "invoices/001.jpg",
      "fields": {
        "invoice_number": "INV-2026-001",
        "date": "2026-07-30",
        "amount": 1234.56,
        ...
      },
      "lang": "zh",
      "notes": "handwritten date, partially occluded stamp"
    }
  versioning: true                            # ground truth 有版本控制
  review_process: "每季由 domain expert 審核更新"
```

### 9. OpenTelemetry — Distributed Tracing

每個 Agent 入口/出口 inject OpenTelemetry spans，Trace 成條 A2A chain：

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

tracer = trace.get_tracer("invoice-pipeline")

@a2a_ocr.agent_executor(name="ocr_agent")
async def ocr_flow(image_data: dict, ctx: dict) -> dict:
    with tracer.start_as_current_span("ocr_extraction") as span:
        span.set_attribute("batch_id", ctx.get("batch_id"))
        span.set_attribute("invoice_count", len(image_data.get("invoices", [])))
        result = await runner.run(messages=image_data)
        ctx["trace_id"] = trace.get_current_span().get_span_context().trace_id
        return await call_a2a_agent("translation-agent", result, ctx)
```

```yaml
opentelemetry:
  exporter: otlp
  endpoint: http://otel-collector:4318
  service_name: invoice-pipeline
  sampling_rate: 1.0
  baggage:
    - environment: production
    - region: cn-beijing
  exporters:
    - type: jaeger
      endpoint: http://jaeger:14250
    - type: cloudwatch
      log_group: /opentelemetry/invoice-traces
```

### 10. Full Auditing — 不可竄改 Audit Trail

每個 Agent action 寫 audit record，鏈式簽名防止篡改：

```python
@audit_log(action="invoice.ocr.extract")
async def ocr_extract(image: bytes) -> dict:
    ...
```

```yaml
audit:
  store:
    type: dual_write
    primary: postgresql
    archive: tos
    archive_cron: "0 0 * * 0"
  retention:
    online_days: 90
    archive_years: 7                     # Financial data — 7 年
  immutability:
    chain_hash: true                      # 鏈式 hash 鏈
    signing_key: /etc/keys/audit-signing.pem
  record_structure:
    audit_id, timestamp, agent, action, actor, resource
    input_hash, output_hash, trace_id, decision
    compliance_metadata:
      data_residency: cn-beijing
      retention_period_days: 2555
      pii_redacted: true
    signature: ecdsa-sig:...
  invoice_specific:
    include_original_image_hash: true
    include_extracted_data_diff: true
```

### 11. Error Handling — Retry / Circuit Breaker / DLQ

```yaml
error_handling:
  retry:
    max_attempts: 3
    backoff: exponential
    retryable_errors:
      - timeout
      - rate_limit
      - service_unavailable
    non_retryable:
      - invalid_input
      - auth_failed
      - pii_detected

  circuit_breaker:
    failure_threshold: 5
    reset_timeout_seconds: 30
    half_open_max_requests: 3

  dlq:
    store: tos
    bucket: invoice-dlq
    alert_on_enqueue: true
    manual_replay_endpoint: /admin/dlq/replay

  partial_failure:
    strategy: continue_with_errors       # Batch 內部分失敗唔停
    max_failure_rate: 0.3
    deadletter_per_component: true
```

```python
@circuit_breaker(name="seed_llm_api", failure_threshold=5)
@retry(max_attempts=3, backoff="exponential")
async def call_ocr_model(image: bytes) -> dict:
    return await agent.run_async(messages=image)
```

### 12. Secrets Management

```yaml
secrets:
  provider: vault                          # HashiCorp Vault
  auth_method: kubernetes
  rotation:
    default: 90d
    high_risk: 30d
    auto_rotate: true
  paths:
    model_api_key: vault://projects/invoice/ocr/api_key
    tos_credentials: vault://shared/tos/credentials
    postgresql_url: vault://shared/postgresql/invoice_url
    feishu_bot_token: vault://projects/invoice/feishu/bot_token
```

```python
from hvac import Client
vault = Client(url=os.environ["VAULT_ADDR"], token=os.environ["VAULT_TOKEN"])
secret = vault.secrets.kv.v2.read_secret_version(path="projects/invoice/ocr/api_key")
os.environ["MODEL_AGENT_API_KEY"] = secret["data"]["data"]["api_key"]
```

### 13. PII Detection

Invoice = 公司地址、電話、稅號、銀行帳戶 — 必須 scan：

```python
from byteplus.pii_detector import PIIDetector

pii = PIIDetector(api_key="<key>", region="ap-southeast-1")

async def pii_scan(invoice_data: dict) -> dict:
    result = pii.detect(
        text=json.dumps(invoice_data),
        types=["PERSON_NAME", "PHONE", "EMAIL", "ADDRESS", "TAX_ID", "BANK_ACCOUNT"],
        redaction_policy="mask",
    )
    invoice_data["pii_report"] = {
        "found_items": result["detected"],
        "redacted_fields": result["redacted"],
        "risk_level": result["risk_score"],
    }
    return invoice_data
```

```yaml
pii:
  scan_points:
    - after_ocr
    - after_translation
    - before_aggregation
    - before_hitl
  actions:
    high_risk: [auto_redact, flag_for_review]
    medium_risk: [mask_fields]
    low_risk: [log_only]
  redaction_method:
    type: mask
    unmask_for_roles: [admin, compliance]
```

### 14. Prompt Filtering & Shield

```yaml
prompt_shield:
  provider: byteplus_modelark_shield
  pre_filter:
    enabled: true
    categories:
      - prompt_injection
      - jailbreak
      - toxicity
      - sensitive_topics
    action: block
  post_filter:
    enabled: true
    categories:
      - hallucinated_pii
      - harmful_content
    action: mask_or_block
  invoice_rules:
    - pattern: BANK_ACCOUNT
      action: block_and_alert
    - pattern: CREDIT_CARD
      action: block_and_alert
    - pattern: PASSPORT_NUMBER
      action: block_and_alert
```

### 15. Cost Management

```yaml
agent_plan: medium                        # ¥200/月，100,000 AFP
# Agent Plan Medium 限制：
# - 極速模型 (Seed 2.0 Mini/Lite): 1× AFP
# - 標準模型 (Seed 2.0 Pro): 3× AFP
# - 生圖/視頻 (Seedream/Seedance): 高消耗，睇官方 AFP 表
# - 聯網搜索 Harness: 150 次/月

cost_management:
  tracking:
    provider: byteplus_billing_api (Agent Plan AFP)
    dimensions: [agent_name, model_name, project_id, user_id]
  budget:
    monthly_limit: "¥200 (Medium Plan)"
    per_batch_alert: "¥20"                  # ~10,000 AFP
    alert_channels: [feishu, email]
  monthly_afp_forecast:
    total_available: 100,000 AFP
    daily_20_batch_cost: ~26,400 AFP        # ~26% of Medium
    headroom: ~73,600 AFP                    # 仲有 73% 空間
  optimization:
    cache_strategy:
      identical_prompt_cache: true
      cache_store: redis
      cache_ttl_hours: 24
    model_selection:
      default: seed-2-0-mini-260428         # 極速模型 1× AFP
      vision: seed-2-0-lite-260228          # 極速模型 1× AFP
      upgrade_if_needed: seed-2-0-pro-260324  # 標準模型 3× AFP
```

### 16. Logging — Structured Logging

```yaml
logging:
  format:
    type: json
    fields: [timestamp, level, service, trace_id, span_id, user_id, batch_id, message, duration_ms]
  levels:
    default: info
    audit: info
    pii: warn
    error: error
  sinks:
    - type: stdout
    - type: file
      path: /var/log/invoice-pipeline/
      rotation: 100MB
      retention: 30d
    - type: elasticsearch
      endpoint: https://es-internal.vpc:9200
      index_pattern: "logs-invoice-{YYYY-MM-DD}"
```

```python
import structlog
logger = structlog.get_logger()
logger.info("ocr_extraction_complete", batch_id="batch-001", num_invoices=5, duration_ms=2340)
```

### 17. CI/CD Pipeline

```yaml
# .github/workflows/invoice-pipeline.yml
name: Invoice Pipeline CI/CD
on:
  push:
    branches: [main, develop]
    paths: ['agents/**', 'tools/**', 'eval/**']
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubicloud
    steps:
      - uses: actions/checkout@v4
      - name: Unit tests
        run: pytest tests/unit/ --cov=agents/ --cov-fail-under=85
      - name: Integration tests
        run: docker compose up -d && pytest tests/integration/
      - name: CI eval
        run: |
          python eval/ocr_eval.py --ci --threshold 0.85
          python eval/translation_eval.py --ci --threshold 0.75
          python eval/validation_eval.py --ci --threshold 0.90
      - name: Security scan
        run: trivy image --severity HIGH,CRITICAL --exit-code 1 && snyk test --all-projects

  deploy-staging:
    needs: [test]
    if: github.ref == 'refs/heads/develop'
    steps:
      - run: |
          ak deploy ocr-agent --app-name invoice-ocr-staging
          ak deploy translation-agent --app-name invoice-translation-staging

  deploy-production:
    needs: [test]
    if: github.ref == 'refs/heads/main'
    steps:
      - run: ak deploy ocr-agent --app-name invoice-ocr-canary --canary 0.1
      - name: Health check
        run: ak health --app invoice-ocr-canary --timeout 30s && ak eval run --app invoice-ocr-canary --test-set eval/test_data/smoke.json
      - name: Full rollout
        run: ak deploy ocr-agent --app-name invoice-ocr && ...

  cost-track:
    schedule: "0 6 * * 1"
    steps:
      - run: python scripts/check_budget.py --project invoice
```

### Updated 檔案結構

```diff
  invoice-pipeline/
  ├── agents/
  │   ├── ocr_agent.py
  │   ├── translation_agent.py
  │   ├── validation_agent.py
  │   ├── aggregation_agent.py
  │   ├── approval_agent.py
  │   └── configs/
+ │       ├── ocr.yaml              ← 加 DB/STM/LTM config
+ │       ├── translation.yaml
+ │       ├── validation.yaml
+ │       ├── aggregation.yaml
+ │       ├── approval.yaml
+ │       └── security.yaml          ← 新增
  ├── infra/
+ │   ├── network.tf                 ← Terraform VPC/firewall
+ │   ├── rbac.yaml                  ← RBAC 配置
+ │   └── eval_pipeline.yaml         ← CI eval pipeline
  ├── a2a_orchestrator.py
  ├── frontend/
  │   └── app.py
  ├── eval/
  │   ├── ocr_eval.py
  │   ├── translation_eval.py
  │   ├── validation_eval.py
  │   ├── aggregation_eval.py
  │   ├── approval_eval.py
  │   └── test_data/
  │       ├── ground_truth/
  │       ├── multi_lang_invoices/
  │       ├── error_injected/
+ │       ├── regression/             ← 新增
+ │       └── adversarial/            ← 新增
  ├── deploy.sh
  └── README.md
```

```
invoice-pipeline/
├── agents/
│   ├── ocr_agent.py              # Agent1
│   ├── translation_agent.py      # Agent2
│   ├── validation_agent.py       # Agent3
│   ├── aggregation_agent.py      # Agent4
│   ├── approval_agent.py         # Agent5
│   └── configs/
│       ├── ocr.yaml
│       ├── translation.yaml
│       ├── validation.yaml
│       ├── aggregation.yaml
│       └── approval.yaml
├── a2a_orchestrator.py           # A2A flow 編排
├── frontend/
│   └── app.py                    # VeADK Frontend 啟動
├── eval/
│   ├── ocr_eval.py
│   ├── translation_eval.py
│   ├── validation_eval.py
│   ├── aggregation_eval.py
│   ├── approval_eval.py
│   └── test_data/
│       ├── ground_truth/         # 100 張 ground truth
│       ├── multi_lang_invoices/  # 多語言發票
│       └── error_injected/       # 人工注入錯誤
├── deploy.sh
└── README.md
```

---

## 技術棧總結

| 層面 | 採用技術 |
|------|---------|
| **Agent Framework** | VeADK (`veadk-python`) |
| **A2A Communication** | AgentKit SDK (`agentkit-sdk-python[a2a]` → `AgentkitA2aApp`) |
| **Deployment** | ModelArk Managed Agents / AgentKit CLI (`ak deploy`) |
| **Subscription** | **Agent Plan Medium** (¥200/月, 100,000 AFP) |
| **LLM / Vision (default)** | **Seed 2.0 Lite** (極速 1× AFP, Vision+Text) |
| **LLM (lightweight)** | **Seed 2.0 Mini** (極速 1× AFP, text-only) |
| **Translation** | **Seed 2.0 Mini** LLM 或 **BytePlus Translate API** (獨立計費) |
| **Frontend / HITL** | VeADK A2UI + **Feishu/Lark** 審批通知 |
| **Object Storage** | **TOS**（Volcengine Object Storage） |
| **Vector DB** | **VikingDB** / **OpenViking** |
| **Relational DB** | PostgreSQL（STM session / audit log / metadata） |
| **Cache** | Redis |
| **API Layer** | **ModelArk**（BytePlus / Volcengine Ark） |
| **Security** | VeADK `AuthRequestProcessor` + **Volcengine IAM** + mTLS A2A + Service Mesh (Istio) |
| **Network** | VPC internal + egress-only to BytePlus API |
| **Identity** | **Volcengine Identity** (ve_identity) |
| **Observability** | **OpenTelemetry** (Jaeger + CloudWatch) |
| **Logging** | Structured JSON logging → Elasticsearch / Loki |
| **Audit** | Dual-write (PostgreSQL + TOS), chain-hash immutable |
| **Secrets** | **HashiCorp Vault** + auto-rotation |
| **PII** | **BytePlus PII Detector** (mask + flag) |
| **Content Safety** | **BytePlus ModelArk Shield** (pre + post filter) |
| **Cost** | BytePlus billing API + budgets + caching |
| **Eval** | CI eval pipeline + shadow eval + ground truth versioning |
| **Testing** | Unit (pytest, 85% cov) + Integration + Load (k6) + Chaos |
