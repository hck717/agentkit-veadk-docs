# 資料庫管理（Database Management）— 本地 vs 雲端 · SQL / Vector / NoSQL · 記憶三層

Agent 唔止要 model——佢要讀、寫、查、記。呢份文件講清楚：**喺 BytePlus + AgentKit + VeADK 嘅 stack 入面，幾時用邊種資料庫、本地定雲端、點接線**；記憶管理（**短期會話 / 長期記憶 / 知識庫**）每個後端點撳，同埋**知識庫檢索 / 長期記憶檢索**點流入 agent。

> ✅ **核心心法**：
> 1. **一個 agent 方案通常唔止用一種 DB**——SQL 管事務事實、Vector 管語義、Redis 管快取、MongoDB 管文件、TOS 管歸檔。混搭先係正路。
> 2. **記憶分三層，各管各背**：**短期會話**（STM）記住今次對話、**長期記憶**（LTM）跨 session 記住用戶、**知識庫**（KB）管靜態知識做 RAG——後端支持範圍唔一樣（見 §4–5 矩陣）。
> 3. **托管 vs 自建嘅取捨**：托管（RDS / NDB / VikingDB / Context Search）慳維運但月費高；自建慳月費但要人手管 backup / patch / scaling。

---

## 0. 一句定位 + 本地 vs 雲端總覽

### 0.1 本地（Local）vs 雲端（BytePlus Managed）

| 維度 | 本地（自建 / 單機） | 雲端（BytePlus 托管） |
|---|---|---|
| **資料庫類型** | SQLite、自建 PostgreSQL / MySQL、本地 Redis | RDS MySQL、NDB MySQL、Cache for Redis、MongoDB、VikingDB、Milvus、TOS |
| **Data locality** | 喺自己機 / VPC | 喺 BytePlus 可用區 |
| **Latency** | 零網絡延遲 | 同 VPC <1ms；跨可用區 1-3ms |
| **合規** | 數據完全唔出域（政府 / 銀行） | 睇 region（cn-hongkong / cn-beijing） |
| **成本** | 硬件 + 自己維 | 托管月費；慳人力 |
| **維運** | 自己 backup / patch / scaling | 平台包辦（自動備份 / replica） |
| **多實例共享** | ❌ SQLite 各一本 | ✅ 所有實例讀同一個 |
| **幾時用** | 開發 / demo / 單機 / 合規唔出域 | 生產、多實例、要 SLA |

**取捨速查**：本地 demo → SQLite；單機 + 合規唔出域 → 自建 PostgreSQL；多實例 / 要 SLA → 托管；語義搜尋 / RAG → VikingDB 或 OpenSearch / Redis。

> **Sale 一句**：「本地起步零成本，但一講多實例 / SLA / 合規，就要上雲端——BytePlus 成套 RDS / NDB / VikingDB / Context Search 擺晒，揀邊個就得。」

---

## 1. SQL（關係型）— BytePlus RDS / NDB / PostgreSQL

| 你要做咩 | 點解 SQL |
|---|---|
| 用戶資料、訂單、交易 | 要 ACID 事務（一半寫入唔得） |
| 審計日誌 + chain-hash | 要防篡改、保留 7 年 |
| 合規要求（政府 / 銀行） | ACID + 可審計 + 可立約 |

| 產品 | 一句 | 兼容性 |
|---|---|---|
| **RDS for MySQL** | 可靠 / 彈性 / 易用嘅關係型 DB 服務 | 完全兼容原生 MySQL |
| **NDB for MySQL** | 新一代自研雲原生關係型 DB | 100% 兼容 MySQL 8.0 引擎 |
| **自建 PostgreSQL** | 本地 VM 安裝 | 合規唔出域 / 預算有限 |

**ACID vs BASE**：SQL 保證 atomicity / consistency / isolation / durability——審計 / 訂單 / 用戶唔可以「一半寫入」。KV / Vector / Object 係 BASE（最終一致、可用性優先）。

> ⚠️ **審計要用 ACID**——chain-hash（hash 鏈防篡改）+ 7 年保留 → 要落 SQL，唔可以落 Vector / KV。
> 💡 短期會話（STM）想落 SQL？`sqlite` / `mysql` / `postgresql` 後端例子見 §4.3。

---

## 2. Vector DB（語義）— VikingDB / Milvus / OpenSearch

### 2.1 BytePlus Vector DB 產品

| 產品 | 一句 | 幾時用 |
|---|---|---|
| **VikingDB** | 雲原生向量數據庫（2025-04 launch）；存 / 檢索海量高維向量 | RAG / 記憶 / 推薦 / 搜尋 / 標註 / 客服 |
| **Milvus for VectorDB** | 托管 Milvus | 已有 Milvus 生態 / 自建想上托管 |
| **自建 OpenSearch** | 開源搜尋引擎 + 向量 | 已有 OpenSearch infra |

### 2.2 VikingDB 深入

- **2025-04 launch**：cloud-native vector DB，存 / 檢索 massive high-dimensional vectors。
- 支援：RAG、recommendation、search、memory、labeling、customer service；APIs / SDKs / SaaS（collection、data import、index、search、embedding）。
- **Region**：BytePlus 模式下固定 `cn-hongkong`。

### 2.3 嵌入 vs 托管：成本放大器

向量類後端（local / opensearch / redis / milvus / tos_vector）要**自己配 embedding 模型**（`MODEL_EMBEDDING_API_BASE` / `MODEL_EMBEDDING_API_KEY`），每次檢索計多一次 embedding AFP；托管後端（viking / context_search / openviking / mem0 / tos_context）**服務端做切分 + 向量化 + 檢索**，向量費入雲資源，唔 draw 你本地 GPU。

> **Sale 一句**：「想喺方案度掃走『自建向量庫 + embedding 模型』兩項成本，就揀 VikingDB / Context Search——服務端食晒，你只係買儲存同查詢用量。」

> 💡 每個後端嘅 VeADK 例子見 §4.4（長期記憶）同 §4.5（知識庫）。

---

## 3. NoSQL — Redis / MongoDB / TOS

### 3.1 Cache for Redis（KV / 熱 session）

Session 快取（<1ms 高吞吐）、熱數據 cache、已有 Redis 直接用做 LTM / KB 向量（例子見 §4.4 / §4.5）。

> ⚠️ Redis 向量後端要**自己配 embedding**（計多一次 AFP）。唔想管就用 VikingDB 托管。

### 3.2 Document Database for MongoDB（文件型）

電商產品目錄 + 庫存（文件 schema 靈活、sharded cluster 彈性）、社群貼文 + 地理索引（geo-indexing）、半結構化日誌（JSON-like）。

> ✅ **BytePlus MongoDB 特點**：完全兼容原生 MongoDB；DTS 不停機遷移；sharded cluster 水平擴展；geo-indexing 支援社交 / 地理場景。

### 3.3 TOS — Tinder Object Storage（物件存儲）

圖片 / 影片 assets（大檔、低成本）、審計 archive 7 年（冷存儲平大容量）、RAG 源文件（配合 `context_search` / `tos_vector` / `tos_context`）。

---

## 4. 記憶管理（Memory Management）—— 三層 + 檢索

VeADK 記憶系統分三層，**每層有唔同後端、唔同檢索方式**：

| 層 | 管咩 | 檢索點 | 統一入口 |
|---|---|---|---|
| **短期會話（STM）** | 今次對話 context、session | 每輪直接入 context | `veadk.memory.short_term_memory.ShortTermMemory` |
| **長期記憶（LTM）** | 用戶偏好 / 事件，跨 session | AgentKit 自動帶返（見 §4.2） | `veadk.memory.long_term_memory.LongTermMemory` |
| **知識庫（KB）** | 靜態知識文件做 RAG | `load_knowledgebase` 工具 / `kb.search`（見 §4.1） | `veadk.knowledgebase.KnowledgeBase` |

### 4.1 知識庫檢索（KnowledgeBase Retrieval）

兩種檢索方法，揀其一：

```python
from veadk import Agent
from veadk.knowledgebase import KnowledgeBase

kb = KnowledgeBase(backend="viking", index="my_kb", top_k=10)
kb.add_from_directory("./docs")                       # 入資料

# 方法 ① 自動工具：接落 Agent → 自動有 load_knowledgebase 工具
agent = Agent(model_name="doubao-seed-2.1-pro-260628", knowledgebase=kb)
# 喺對話度 Agent 自己睇幾時撳 knowledgebase → 攞相關片段 → 塞 context → 答

# 方法 ② 程式化：直接用 kb.search 攞返相關片段
hits = kb.search("公司年假有幾多日？", top_k=5)       # → 片段列表
```

> 🎯 檢索結果 = **相關片段**，唔係答案。Agent 攞返片段之後再組織成答——所以要 evaluate「片段切唔切題」（see eval tab RAG 檢索層）。

### 4.2 長期記憶檢索（Long-Term Memory Retrieval）

**LTM 檢索係自動嘅，唔使自己寫**：

- 對話進行中，AgentKit 按 threshold（`MIN_MESSAGES_THRESHOLD` / `MIN_TIME_THRESHOLD`，預設約 10 條 event 或 60 秒）累積後**寫入 LTM**。
- **轉 `session_id` 時自動把上一 session 寫入 LTM**；新 session 開場，過去嘅 events 自動帶返 context → 用戶唔使重複講偏好。
- 操作層面用 CLI 管理：`agentkit memory create --name user-mem --provider-type VIKINGDB_MEMORY`，再由 `agentkit config --memory_id mem-xxx` 綁定 Runtime。

> ⚠️ **想攞返用戶歷史，就要揀啱 LTM 後端**：`local` 退出即冇、`opensearch` 要自己配 embedding——生產多人 / 冚 session 直接上 **`viking` / `mem0`**（見 §4.4）。

### 4.3 短期會話（Short-Term Session / STM）後端

**概覽**：STM 記住「今次對話」——每輪 context、session 資料。AgentKit Runtime instance 之間唔共享，**多實例部署（`min-instance > 1`）要持久化 DB**，唔好 `local`。

| 後端 | 例子 | 備註 |
|---|---|---|
| **本地記憶（local）** | `ShortTermMemory(backend="local")` | 重啟 / 換 instance 即冇；開發 demo |
| **SQLite 存儲** | `ShortTermMemory(backend="sqlite", local_database_path="./stm.db")` | 單機持久化、零配置 |
| **MySQL 存儲** | `ShortTermMemory(backend="mysql", db_url="mysql://user:pass@localhost:3306/agent_db")` | 自建 / RDS |
| **PostgreSQL 存儲** | `ShortTermMemory(backend="postgresql", db_url="postgresql://user:pass@localhost:5432/agent_db")` | 自建 / 合規審計 |

```python
from veadk.memory.short_term_memory import ShortTermMemory

stm = ShortTermMemory(backend="sqlite", local_database_path="./stm.db")
```

> ✅ PostgreSQL / MySQL = ACID 全套，chain-hash 審計可以自己砌；壞處：backup / replication / failover 全自己搞。

### 4.4 長期記憶（Long-Term Memory / LTM）後端

**概覽**：跨 session 記住用戶。**預設係 `opensearch`**（唔係 local！）；`min_messages_threshold` / `min_time_threshold` 決定幾時寫入。

| 後端 | 例子 | 要 embedding | 備註 |
|---|---|---|---|
| **本地記憶（local）** | `LongTermMemory(backend="local", app_name="my_agent")` | ✅ | **退出即冇**、唔能跨進程；開發 |
| **VikingDB 存儲** | `LongTermMemory(backend="viking", app_name="my_agent")` | ❌ | **生產推薦**；支援用戶畫像；region 固定 `cn-hongkong`；`viking_mem` 已棄用→自動轉 `viking` |
| **mem0 存儲** | `LongTermMemory(backend="mem0", app_name="my_agent")` | ❌ | 第三方托管；`pip install mem0` + `Mem0Config`（env `DATABASE_MEM0_*`） |
| **OpenSearch 存儲** | `LongTermMemory(backend="opensearch", app_name="my_agent")` | ✅ | 預設值；已有 infra |
| **Redis 存儲** | `LongTermMemory(backend="redis", app_name="my_agent")` | ✅ | 低延遲自建 |
| **OpenViking 存儲** | `LongTermMemory(backend="openviking", app_name="my_agent")` | ❌ | 生產；server 做策略 |
| **TOS ContextBucket 存儲** | `LongTermMemory(backend="tos_context", app_name="my_agent")` | ❌ | 火山托管 context |

```python
from veadk.memory.long_term_memory import LongTermMemory

ltm = LongTermMemory(backend="viking", app_name="my_agent")   # 生產推薦
```

> 🎯 要 **multiprocess / 多實例共享** → 唔好用 `local`；要**用戶畫像**（檢索時按人篩）→ 淨係 Viking 有（見 §4.5）。

### 4.5 知識庫（KnowledgeBase / KB）後端

**概述**：靜態知識文件做 RAG（產品文檔 / FAQ / 法規）。統一入口 `veadk.knowledgebase.KnowledgeBase(backend=..., index=...)`；入資料 `add_from_files` / `add_from_directory` / `add_from_text`；接住 `Agent(..., knowledgebase=kb)` 就自動有 `load_knowledgebase` 工具（見 §4.1）。

| 後端 | 例子 | 要 embedding | 備註 |
|---|---|---|---|
| **本地記憶存儲（local）** | `KnowledgeBase(backend="local", index="my_kb")` | ✅ | 內存向量索引；程序死咗 data 冇 |
| **OpenSearch 存儲** | `KnowledgeBase(backend="opensearch", index="my_kb")` | ✅ | 已有 infra |
| **Redis 存儲** | `KnowledgeBase(backend="redis", index="my_kb")` | ✅ | 低延遲自建 |
| **TOS 向量庫存儲（tos_vector）** | `KnowledgeBase(backend="tos_vector", index="my_kb")` | ✅ | 用緊火山 TOS |
| **VikingDB 知識庫存儲** | `KnowledgeBase(backend="viking", index="my_kb", ...)` | ❌ | **生產推薦**；服務端切分+向量化+檢索；用戶畫像 |
| **Milvus 存儲** | `KnowledgeBase(backend="milvus", index="my_kb")` | ✅ | 自建 / 托管 Milvus、大規模 |
| **OpenViking 存儲** | `KnowledgeBase(backend="openviking", index="my_kb")` | ❌ | 服務端資源解析同檢索 |
| **Context Search 存儲** | `KnowledgeBase(backend="context_search", index="my_kb")` | ❌ | 托管 RAG；需 TOS 預簽名上傳 |

```python
from veadk.knowledgebase import KnowledgeBase

# 生產推薦：VikingDB 知識庫（含用戶畫像檢索）
kb = KnowledgeBase(
    backend="viking",
    index="my_kb",
    enable_profile=True,              # 啟用用戶畫像
    query_with_user_profile=True,     # 檢索時結合用戶畫像（限 Viking）
    top_k=10,
)
```

> 🎯 **enable_profile / query_with_user_profile 唔係度度有**——只有 VikingDB 後端先支援「用戶畫像」檢索。揀 OpenSearch / Redis / Milvus 嘅話冇呢個功能。

---

## 5. 後端矩陣（一張表）

融合 STM / LTM / KB 全部 backend，揀之前睇呢張：

| backend | STM | LTM | KB | 要本地 embedding | 幾時揀 |
|---|---|---|---|---|---|
| `local` | ✅ | ✅ | ✅ | ✅ | 開發 debug（退出即冇） |
| `sqlite` | ✅ | — | — | — | 單機持久化 |
| `mysql` | ✅ | — | — | — | 自建 / RDS |
| `postgresql` | ✅ | — | — | — | 自建 / 合規審計 |
| `opensearch` | — | ✅ | ✅ | ✅ | 已有 infra（LTM 預設值） |
| `redis` | ✅ | ✅ | ✅ | ✅ | 低延遲自建 |
| `milvus` | — | — | ✅ | ✅ | 大規模 |
| `tos_vector` | — | — | ✅ | ✅ | 火山 TOS |
| `viking` | — | ✅ | ✅ | ❌ | **生產推薦**、支援用戶畫像 |
| `mem0` | — | ✅ | — | ❌ | 第三方托管 |
| `context_search` | — | — | ✅ | ❌ | 托管 RAG、需 TOS 預簽名 |
| `openviking` | — | ✅ | ✅ | ❌ | 生產 |
| `tos_context` | — | ✅ | — | ❌ | 火山托管 |

**揀法速查**：

| Trigger | STM | LTM | KB |
|---|---|---|---|
| 開發 / demo | `sqlite` / `local` | `local` | `local` |
| 多實例 / 要 SLA | `postgresql` / `mysql` | `viking` / `mem0` | `viking` |
| 已有 Redis | — | `redis` | `redis` |
| 合規唔出域 | 自建 PostgreSQL | 自建 OpenSearch | `local` 或自建 Milvus |

---

## 6. 決策框架（幾時用邊種）

### 6.1 場景 → DB 對照

| 場景 | 揀 | 唔揀 |
|---|---|---|
| 用戶 / 訂單 / 審計（ACID） | SQL（RDS MySQL / NDB / PostgreSQL） | Vector / KV |
| 語義搜尋 / RAG / 知識庫 | Vector DB（VikingDB / Context Search / OpenSearch / Redis） | SQL |
| 記憶（跨 session） | `viking` / `mem0`（托管）或 `opensearch` | `local` |
| 短期會話（生產多實例） | SQLite 以外嘅持久化 DB（SQL / Redis） | 本地 `local` |
| 熱 session / 快取 | Redis（Cache for Redis） | MongoDB |
| 電商產品 / 庫存 / 社群 | MongoDB（sharded + geo-indexing） | SQLite |
| 圖片 / 影片 / 7 年 archive | TOS | SQL |
| 關係問答（A 關連 B） | Graph DB（第三方） | 單一 DB |

### 6.2 一個 stack 同時用幾種

| 嘢 | 儲邊度 | 點解 |
|---|---|---|
| 用戶 / 訂單 / 審計寫入 | RDS MySQL / PostgreSQL | ACID + chain-hash |
| 審計 archive 7 年 | TOS | 平、大容量冷存儲 |
| 向量 / 語義記憶（LTM/用戶畫像） | VikingDB | 托管、唔使管 embedding、用戶畫像 |
| 知識庫 RAG | VikingDB / Context Search | 托管、服務端向量化 |
| 短期會話（多實例） | PostgreSQL / Redis | 持久化 + <1ms |
| Session 熱數據 | Cache for Redis | <1ms 低延遲 |
| 產品目錄 / 庫存 | MongoDB | 文件 schema 靈活 + sharded |

### 6.3 「一個 DB 打天下」陷阱

> ⚠️ **每個資料類型都有唔同嘅平快準特性**——用 SQL 做向量搜、用 Redis 做 7 年 archive、用 MongoDB 做 ACID 事務，全部唔啱。混搭先係正路，同埋**一個方案唔止用一種 DB**係正常嘅。

### 6.4 本地 vs 雲端嘅最後決策線

```
你要多實例共享？
  ├─ Yes → 雲端托管（RDS / NDB / VikingDB / Cache for Redis / MongoDB / TOS）
  └─ No → 你要合規唔出域？
              ├─ Yes → 本地自建（PostgreSQL / MySQL / OpenSearch）
              └─ No → 雲端托管（慳維運）
```

---

## 7. Sales 一句 + 資料來源

### Sales 一句

> 「Agent 唔係得個 model——佢同你嘅數據打交道。SQL 管冷硬事實，Vector 管語義，Redis 管手快，MongoDB 管文件，TOS 管歸檔；記憶三層（短期 / 長期 / 知識庫）每個後端 VeADK 一句搞掂——成套 BytePlus + VikingDB 一間過攞齊，唔使自己砌。」

### 資料來源

| 來源 | URL | 日期 |
|---|---|---|
| BytePlus 產品總覽 | https://byteplus.com/en/product/list | 頁面日 |
| VikingDB（雲原生向量數據庫） | https://byteplus.com/en/product/VectorDatabase | 2025-04 launch |
| VikingDB API Overview | https://docs.byteplus.com/api/docs/VikingDB/Overview | 頁面日 |
| RDS for MySQL | https://byteplus.com/product/rds-mysql | 頁面日 |
| NDB for MySQL | https://byteplus.com/product/ndb-for-mysql | 頁面日 |
| Document Database for MongoDB | https://byteplus.com/product/mongodb | 頁面日 |
| VeADK 記憶管理（短期會話 / 長期記憶後端） | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/memory | 頁面日 |
| VeADK 長期記憶 mem0 後端 | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/memory/mem0 | 頁面日 |
| VeADK 長期記憶 VikingDB 後端 | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/memory/vikingdb | 頁面日 |
| VeADK 知識庫（後端 + 檢索） | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/knowledge | 頁面日 |
| Context Search 後端（TOS 預簽名上傳） | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/knowledge/context-search | 頁面日 |
| VeADK API 參考（STM / LTM / KB 後端） | `references/veadk-api.md` | 2026-08 |
| AgentKit CLI（knowledge / memory create） | `references/agentkit-cli.md` | 2026-08 |
| AI 概念百科 §7 Vector DB + §8 Database | `references/veadk-agentkit-ai-concepts.md` | 2026-08 |
| Vector DB 與 Cache 管理指南（後端 + 緩存 + 壓縮） | `references/veadk-agentkit-vector-cache.md` | 2026-08-13 |

> **免責**：VikingDB 價格 / region 以官方控制台為準；本 doc 唔含計價承諾（見 pricing doc）。各產品功能存在性以 BytePlus 官網當刻為準。

---

*Last audit date: 2026-09-06 · 按官方記憶三層（短期會話 / 長期記憶 / 知識庫）重組後端例子 + 檢索節。backend 清單同 env 會跟 SDK 版本變，做方案前對返當刻 docs。*