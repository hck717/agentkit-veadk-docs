# VeADK + AgentKit Vector DB 與 Cache 管理指南

呢份文件教你點樣幫 client 揀 **知識庫（KnowledgeBase）後端**、**長期記憶（LongTermMemory）後端**，
同埋點樣靠 **Responses API 上下文緩存 + 上下文壓縮（Compaction）** 慳 AFP / 慳錢。

> ✅ **核心心法**：
> 1. **「後端」唔係一個**——KnowledgeBase 有 8 種 backend、LongTermMemory 有 7 種，揀錯會直接影響**價格、速度、可用性**。
> 2. **Serverless 後端（viking / context_search / openviking / mem0 / tos_context）唔使你哋裝 embedding**——服務端包辦，直接對 Detcomponent plan 內「向量化」費用。
> 3. **RAG 嘅 cost 其實喺「token 唔喺 vector」**——步驟 ① 檢索 → ② 全文塞入 context → ③ 模型讀晒。想慳錢就攻「上下文緩存」同「壓縮」，唔係攻 vector store。

---

## 0. 快睇：三個「儲存層」搞清楚

| 層 | 提供乜 | 貴邊度 | VeADK abstraction |
|---|---|---|---|
| **知識庫**（外部靜態資料 RAG） | 產品文檔、FAQ、法規文本做檢索 | 儲存 + 向量化 + 查詢 | `KnowledgeBase` |
| **長期記憶**（跨對話記住用戶） | 用戶偏好、事件、實體，跨 session 保持 | 儲存 + 向量化 | `LongTermMemory` |
| **短期記憶**（對話內 context） | 每輪 context、session | 純 model call（token） | `Runner`/session 內建 |

> RAG 同 LTM 都係「向量化 + 儲存 + 查詢」，但語義唔同：KB 係「靜態知識文件」，LTM 係「用戶動態畫像」。唔好混埋。

---

## 1. 知識庫 後端矩陣 — 揀邊個？

統一入口：`veadk.knowledgebase.KnowledgeBase(backend=...)`；冇論用邊個 backend，接住 `Agent(..., knowledgebase=kb)` 個 AI 就自動有 `load_knowledgebase` 工具。

| backend | 儲存 | 要唔要本地 embedding | 適合 | 開發 vs 生產 |
|---|---|---|---|---|
| `local` | 內存向量索引 | ✅ | 本地 debug（程序死咗 data 冇） | 開發 |
| `opensearch` | OpenSearch 向量庫 | ✅ | 已有自建/托管 OpenSearch | 生產（已有 infra） |
| `redis` | Redis (RediSearch) | ✅ | 低延遲自建向量 | 生產（已有 Redis） |
| `milvus` | Milvus collection | ✅ | 自建/托管 Milvus | 生產（已有 infra） |
| `tos_vector` | TOS 向量桶 | ✅ | 火山 TOS 物件向量 | 生產 |
| **`viking`** | VikingDB 知識庫（托管） | ❌ | **火山托管、服務端切分+向量化+檢索** | **生產推薦** |
| `context_search` | Context Search（托管 RAG） | ❌ | 火山托管、需 TOS 預簽名上傳 | 生產推薦 |
| `openviking` | OpenViking 資源目錄 | ❌ | 服務端資源解析同檢索 | 生產 |

**揀法重點：**
- **宿主度最緊要**：已有 OpenSearch/Redis/Milvus 咪用 `viking`，慳返遷移，但嗰啲要自己配 embedding + 計容量。
- **新起就 `viking` / `context_search`**：唔使買/管 embedding 模型，直接計「向量化費用」入方案。
- **添加資料**：`add_from_files` / `add_from_directory` / `add_from_text` 三種來源都得，跨 backend 唔同。

### 1.1 共同參數

| 參數 | 意義 |
|---|---|
| `backend` | `"local" \| "opensearch" \| "redis" \| "milvus" \| "tos_vector" \| "viking" \| "context_search" \| "openviking"` |
| `top_k` | 檢索返幾個最相似片段（預設 10；`search` 可臨時覆蓋） |
| `index` | 庫名/場景 ID；留空回退 `app_name` |
| `enable_profile` / `query_with_user_profile` | 開唔開「用戶畫像」檢索（後者**要 Viking 後端**） |

---

## 2. 長期記憶 後端矩陣

統一入口：`veadk.LongTermMemory(backend=...)`。**預設係 `opensearch`**（唔係 local！）。

| backend | 儲存 | 要唔要 embedding | 適合 | 注 |
|---|---|---|---|---|
| `local` | 進程內存 | ✅ | 本地 debug | **退出即冇**、唔能跨進程 |
| `opensearch` | OpenSearch 向量庫 | ✅ | 已有 infra | 預設值 |
| `redis` | Redis 向量庫 | ✅ | 低延遲 | — |
| `viking` | VikingDB 記憶 | ❌ | **生產推薦** | 支援**用戶畫像**；`viking_mem` 已棄用→自動轉 `viking` |
| `mem0` | Mem0 托管 | ❌ | 生產 | Mem0 負責抽取/儲存/檢索，`pip install mem0` |
| `openviking` | OpenViking 服務 | ❌ | 生產 | server 做策略 |
| `tos_context` | TOS Context control | ❌ | 生產 | 火山托管 |

**揀法重點：**
- 要 **multiprocess / 多實例共享** → 唔好用 `local`；部署 AgentKit Runtime 多實例時短期記憶都建議持久化 DB。
- `mem0`：用 Mem0 托管，`Mem0Config` + env `DATABASE_MEM0_*`。
- `viking`（BytePlus 模式）region 固定 `cn-hongkong`，`DATABASE_VIKING_REGION` 唔再有效；或改 `DATABASE_VIKING_RESOURCE_ID` 做多資源路由。
- `min_messages_threshold` / `min_time_threshold`（env `MIN_MESSAGES_THRESHOLD` / `MIN_TIME_THRESHOLD`）：自行定「幾多條 event / 幾耐先寫入 LTM」。預設累計 10 條 event 或間隔 60 秒觸發保存；**轉 session_id 時自動把上一 session 寫入 LTM**。

---

## 3. 記憶 / 知識庫嘅「成本放大器」：embedding 定「服務端」

**向量類後端**（local / opensearch / redis / milvus / tos_vector）要你**自己裝 extension + 配 embedding 模型**（`MODEL_EMBEDDING_API_BASE` / `MODEL_EMBEDDING_API_KEY`），每次檢索前都要計多一次 embedding 錢（`doubao-embedding-vision` 計 AFP）。

**托管後端**（viking / context_search / openviking / mem0 / tos_context）由**服務端做切分 + 向量化 + 檢索**，**唔使本地 embedding**——向量費用計入雲資源（第二三條線）而唔會 draw 你本地 GPU/CPU。

> Sales 一句：「想喺方案度掃走『自建向量庫 + embedding 模型』兩項成本，就揀 VikingDB / Context Search——服務端食晒，你只係買儲存同查詢用量。」

---

## 4. 上下文緩存（Responses API）— 慳錢主力

唔係落 database，而係**平台同 provider 之間嘅 token 復用**。VeADK Responses API 模式**默認開** session 上下文緩存：

- 系統自動儲存初始上下文，每輪動態更新；下一輪請求將「已緩存內容」+「新輸入」合併再送模型。
- 多輪對話 + 複雜工具調用 → 重複 token 明顯減少 → **慳 AFP**。

**睇命中率**：每輪 response event 嘅 `usage_metadata` 有：

```
cached_content_token_count   # 命中緩存嘅 token 數
prompt_token_count           # 當前輸入總 token 數
命中率 = cached / prompt
```

**⚠️ 自動關閉條件**：設咗 `output_schema` 就同緩存機制衝突，VeADK **自動關閉上下文緩存**。要做「結構化抽取」同「慳錢」就要權衡。

---

## 5. 上下文壓縮（Compaction）— 第二個慳錢位

長期 context 會越滾越長 → 128k+ 段 ×2 倍率（見定價 doc）。用 **`EventsCompactionConfig`** 控制幾時壓縮，再用 **`LlmEventSummarizer`** 指定用邊個模型做 summary。

```python
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.apps.llm_event_summarizer import LlmEventSummarizer

my_compactor = LlmEventSummarizer(
    model="doubao-seed-2-0-mini",        # 壓縮用細模型，慳 token
    system_instruction="用精簡粵語總結對話重點，保留用戶事實同已承諾事項。",
)

app = App(
    agents=[my_agent],
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=5,           # 每 5 次新調用壓縮一次
        max_events=50,                   # 超過幾多事件觸發
        max_tokens=8000,                 # 壓縮後最多幾多 token
        compactor=my_compactor,
    ),
)
```

**做壓縮係咪一定慳？**
- ✅ 長對話／工具多 → summary 令 context 縮短，慳下行 token。
- ❌ 每輪都壓 → 額外 model call 反而貴；同埋 summary 會**冇咗細節**（例如某對話中畀過用戶 ID / 引用冧巴）。

**經驗法則**：`compaction_interval` 大啲（例如 10–20）、用 `mini` 模型做 summarizer、總結唔好截走 tool 返回嘅關鍵 JSON。

---

## 6. 實作檢查清單（直接貼落方案）

| # | 動作 | 參考 |
|---|---|---|
| 1 | 揀 KB backend（新起→`viking` / `context_search`；已有 infra→對應） | §1 |
| 2 | 揀 LTM backend（多實例→唔好 `local`；要 product 級→`viking` / `mem0`） | §2 |
| 3 | 配 embedding env（向量類後端先要） | §3 |
| 4 | 開 Responses API context caching（唔設 `output_schema`） | §4 |
| 5 | 設 compaction config + mini summarizer | §5 |
| 6 | 用 `usage_metadata` 計命中率，校 threshold | §4 |

---

## 7. 成本估算範例（參考）

**RAG Chatbot（S3，見定價 doc）**：
- 檢索：`top_k=10`、每 query 一次 vector query。
- Context 塞入：10 條片段 × 平均 200 tokens = ~2k tokens/query，再加 user 輸入。
- 緩存命中：5 輪對話 → 第 2–5 輪約 70–90% prompt 命中（平台 cache）→ 慳 ~3–4 千 tokens/會話。
- 儲存：KB 10k docs → TOS/Viking 儲存 0.0015 元/GB/小時 起（見定價 doc §8）。

> ⚠️ 記憶落 `local` 後端喺 AgentKit Runtime 多實例下會「每 instance 各自一本」，session 甩出唔同機器就失憶——**如果 `run_sse` 返回 404，十有八九係 session 落咗第個 instance**；要持久化 DB（Viking/Redis/OpenSearch）多實例先穩。

---

## 8. 資料來源

| 來源 | URL | 日期 |
|---|---|---|
| VeADK KnowledgeBase 統一入口 + 後端矩陣 | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/knowledge | 頁面日 |
| Context Search 後端（TOS 預簽名上傳、無本地 embedding） | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/knowledge/context-search | 頁面日 |
| Milvus / OpenViking 知識庫 | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/knowledge/* | 2026-01xx |
| VeADK LongTermMemory 後端矩陣 + LTM | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/memory | 頁面日 |
| mem0 後端 | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/memory/mem0 | 頁面日 |
| VikingDB 記憶後端（BytePlus region 固定 cn-hongkong） | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/memory/vikingdb | 頁面日 |
| 上下文緩存 + `usage_metadata` + `output_schema` 衝突 | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/agent/prompt-management | 頁面日 |
| ADK App EventsCompactionConfig / LlmEventSummarizer | https://google.github.io/adk-python/app/ | 頁面日 |
| Studio 記憶/KB 後端 + LTM 寫入週期 | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/frontend/studio | 頁面日 |

> **免責**：AFP / token / 緩存命中率數字係參考估算，實戰以控制台「用量明細」同 `usage_metadata` 實測為準。

---

*Last audit date: 2026-08-13 · backend 清單同 env 會跟 SDK 版本變，做方案前對返當刻 docs。*