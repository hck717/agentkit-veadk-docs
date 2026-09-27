# 記憶 + 上下文管理（Memory & Context）— STM / LTM / KB 點流入 context · 實戰技巧

Agent 嘅「記憶」唔係一個箱——係**一條把「記得過嘅嘢」塞返入「而家個 context」嘅流水線**。呢份講**行為**（幾時寫入、點樣帶返、點控制 context window、同 cache 點夾），後端清單同 `backend="..."` 㩒法睇 **db tab**；佢哋係一對：**db tab 講「放邊度」，呢頁講「點流入、點慳」。**

> ✅ **核心心法**：
> 1. **記憶分三層，寫入時機唔同**：**STM** 記「今次 session」逐輪入 context；**LTM** 跨 session 自動寫入 + 自動帶返（threshold 控制）；**KB** 靜態知識靠檢索（`load_knowledgebase`）先入 context——**唔係成個塞入去。**
> 2. **context = 每輪 model 睇到嘅全部嘢**：instruction + few-shot + 歷史 + RAG 片段 + 工具定義 + 今次輸入。**佢越短 = 越快、越平、越細 KV**（128k+ 方舟有加倍率）。
> 3. **記憶同 cache 要一齊諗**：乾淨穩定嘅 prefix（memory 帶返嘅歷史放固定位）→ 命中 context cache → 慳真銀；亂排就白白重算。

---

## 0. 一句定位

| 問 | 答 |
|---|---|
| 「記住用戶」係咩意思 | 跨 session 記得你講過嘅嘢（LTM），唔使次次重複 |
| 「記住今次對話」 | 呢個 session 嘅每輪（STM），逐輪入 context |
| 「識答公司嘢」 | 靜態知識放 KB，要答先檢索（RAG），唔好全部塞 system |
| 「上下文管理」 | 控制每輪 context 由幾多嘢組成：啱啱好、唔爆、重複少 |
| 呢頁 vs db tab | db tab = 後端矩陣（`viking`/`mysql`…）；呢頁 = 寫/讀流程 + context 控制 + 技巧 |

> **Sale 一句**：「我哋唔係畀個 model 你——係畀佢『識記、識撿、識慳 context』嘅成套系統：LTM 跨 session 記住用戶，KB 揀啱 top_k 先入，context 壓得細，cache 命中率高——照住做，對話越長越平。」

---

## 1. 記憶三層總覽（flow 圖 + 幾時寫/幾時讀）

```
用戶講嘢 ──► [STM 短期會話]──每輪原樣入 context────────────────────────► model
                │
                └─ threshold（10 條 event / 60s）到咗 ──► 壓縮寫入 [LTM 長期記憶]
                                                              │
                    新 session 開場 ──► LTM 自動帶返過去嘢 ─► 入 context（頭部）
                                                              │
用戶問事實嘢 ──► [KB 知識庫] ── load_knowledgebase 檢索 top_k ─► 入 context（中段）
```

| 層 | 記咩 | 寫入時機 | 讀入時機 | 統一入口 |
|---|---|---|---|---|
| **STM 短期會話** | 今次對話每一輪（原樣） | 每輪 append | 每輪全帶 | `veadk.memory.short_term_memory.ShortTermMemory` |
| **LTM 長期記憶** | 用戶偏好 / 事件摘要（跨 session） | threshold 到點 / 轉 session 時自動 | 新 session 自動帶返 | `veadk.memory.long_term_memory.LongTermMemory` |
| **KB 知識庫** | 產品文檔 / FAQ / 法規（靜態） | 你自己入（`add_from_*`） | `load_knowledgebase` 工具按問題撿 top_k | `veadk.knowledgebase.KnowledgeBase` |

> 🎯 **最易錯**：想 LTM 幫你記，要**揀啱後端再綁定**（見 §3.2）——`local` 退出即冇；`opensearch` 預設要自己配 embedding；生產直接 `viking` / `mem0`。

---

## 2. STM 短期會話 ——「今次對話」逐輪入 context

### 2.1 行為

- 每輪 user/assistant 訊息、tool call 結果**原樣 append** 入 STM；下輪成個歷史帶入 context。
- **換 instance / 重啟就冇**（除非後端係 DB）——多實例部署（`min-instance > 1`）唔好用 `local`。
- context 越滾越長 → token 越多 + KV 越大 + 方舟 128k+ 加倍率 → **長 session 要配 compaction（§5）+ cache（§6）**。

### 2.2 後端（詳細清單喺 db tab §4.3）

| 幾時 | 揀 |
|---|---|
| 開發 / demo | `local` |
| 單機持久化 / 簡單 demo | `sqlite` |
| 自建 / RDS / 多實例 | `mysql` |
| 合規審計 / 自建 | `postgresql` |

```python
from veadk.memory.short_term_memory import ShortTermMemory

stm = ShortTermMemory(backend="sqlite", local_database_path="./stm.db")
```

> 💡 STM 佔嘅 token 通常係「歷史對話」最大浪——**慳錢優先睇呢層**（compaction / 切 session，見 §5）。

---

## 3. LTM 長期記憶 —— 跨 session 記住用戶（自動）

### 3.1 寫入（自動，threshold 控制）

- 對話進行中，按 threshold 累積後自動寫入 LTM：
  - `MIN_MESSAGES_THRESHOLD`：幾多條 event 先寫（預設約 **10**）
  - `MIN_TIME_THRESHOLD`：幾耐先寫（預設約 **60 秒**）
- **轉 `session_id` 時自動把上一 session 寫入 LTM**——「散場記得收嘢」。
- 摘要用**細模型**做（`doubao-seed-2-0-mini`），慳錢（見 ai-concepts §5.3）。

### 3.2 讀取（自動帶返 + 工具兜底）

- 新 session 開場，過去 events **自動帶返 context** → 用戶唔使重複講偏好。
- Agent 想「主動回想」→ 用 **`load_memory` 工具**（VeADK 內建）：

```python
from veadk.memory.long_term_memory import LongTermMemory
from veadk import Agent

ltm = LongTermMemory(backend="viking", app_name="support_agent")   # 生產推薦
agent = Agent(
    model_name="doubao-seed-2.1-pro-260628",
    long_term_memory=ltm,
    instruction="如果答案可能喺過往對話入面，用 load_memory 工具搵返。",
)
```

### 3.3 CLI 管理（AgentKit）

```bash
agentkit memory create --name user-mem --provider-type VIKINGDB_MEMORY   # 建記憶庫
agentkit config --memory_id mem-xxx                                       # 綁定 Runtime
agentkit memory list                                                       # 睇晒
```

> ⚠️ **LTM 唔係無限**：檢索返嚟嘅都係「片段」唔係「全文」——寫入時摘要會**冇咗細節**（用戶 ID / 引用冧巴 / 承諾），要 detail 嘅 domain 喺 summary instruction 度講明「保留 key fields」。

---

## 4. KB 知識庫 —— 靜態知識靠檢索，唔好全文入 system

### 4.1 兩種檢索

```python
from veadk import Agent
from veadk.knowledgebase import KnowledgeBase

kb = KnowledgeBase(backend="viking", index="my_kb", top_k=10)

# ① 自動工具：Agent 自己睇幾時撳 load_knowledgebase
agent = Agent(model_name="doubao-seed-2.1-pro-260628", knowledgebase=kb)

# ② 程式化：直接攞片段
hits = kb.search("公司年假有幾多日？", top_k=5)
```

### 4.2 揀 top_k 係 context 慳錢位

| top_k | context 用量 | 準 | 幾時 |
|---|---|---|---|
| 3–5 | 細 | 中 | high-precision、問題清楚 |
| 10 | 中 | 高 | 一般生產（預設） |
| 20+ | 大 | 邊際回落 | 要全面列舉（法規/審計） |

> 🎯 **KB 結果＝片段唔係答案**——Agent 仲要組織。所以 KB 唔係「識答」，係「material 供應商」；答得好唔好要睇 eval tab 嘅 RAG 檢索層（Faithfulness / Relevancy）。

---

## 5. 上下文管理（Context Management）——控制 model 每輪睇乜

### 5.1 context window 點樣被食（一個 request = 疊埋幾樣）

```
┌─ system / instruction（agent 人設）────────┐
├─ few-shot 例子 ────────────────────────────┤
├─ LTM 帶返嘅歷史總結 ───────────────────────┤
├─ KB top_k 檢索片段 ────────────────────────┤
├─ STM 歷史對話（越滾越長）──────────────────┤
├─ 工具 / MCP 定義 ──────────────────────────┤
└─ 今次用戶輸入 ─────────────────────────────┘
```

- **長 context = 貴 + 慢**：更多 input token + 更大 KV cache + 更慢 TTFT + 128k+ 加倍率 → **慳 context 就係慳真銀。**

### 5.2 六個槓桿（由平到貴）

| 工具 | 做法 | 慳幾多 | 成本 code | 幾時用 |
|---|---|---|---|---|
| **Context caching** | 重用已送過嘅 prefix | 多輪 50–90% | 0 | 默認、長 session（§6） |
| **Prompt 精簡** | instruction 寫短、LTM 唔好重複 system | 每輪幾百 token | 0 | 永遠 |
| **KB top_k** | 唔塞全文只塞 top_k | token ~30%+ | 少 | 知識題（§4.2） |
| **Tool return 收窄** | tool 內預先 summarize / 抽 key fields | 每輪 | 中 | tool 回大 JSON |
| **Compaction（壓縮）** | 長對話壓成 summary | 直接斬 token | 中（細 model call） | 長對話（10+ 輪） |
| **Session 切換** | 定期開新 session | 從頭計 | 0 | 主題跳躍 / 開始重 |

### 5.3 Compaction 深入

```python
from veadk import App, EventsCompactionConfig
from veadk.compact import LlmEventSummarizer

app = App(
    agents=[my_agent],
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=10,   # 幾多 event 做一次壓縮（唔好太密，3 反而貴）
        max_events=50,
        max_tokens=8000,
        compactor=LlmEventSummarizer(
            model="doubao-seed-2-0-mini",     # 細 model 做 summary，慳錢
            system_instruction="壓縮成精簡中文摘要，保留用戶事實、ID 同承諾事項。",
        ),
    ),
)
```

**壓縮係咪一定賺？**

| | 賺 | 唔賺 |
|---|---|---|
| 長對話 / 工具 call 多 | ✅ summary 縮 short context | |
| 每幾句就壓（interval=3） | | ❌ 額外 summary call 反而貴 |
| 要 exact detail（ID / 引用） | | ❌ summary 冇細節（寫明保留 key fields） |

> ⚠️ **Variant trap**：compaction 用細 model 慳錢，但**唔好慳到連用戶事實都冇咗**——summary instruction 寫清「點都要保留」嘅 fields。

### 5.4 反模式

| 反模式 | 點改 |
|---|---|
| 成個 KB 全文塞入 system | `load_knowledgebase` RAG 只塞 top_k |
| STM 歷史無限滾 | compaction + 定期切 session |
| LTM 帶返嘅 summary 同 system 重複 | 二選一，重複等於嘥 token |
| tool 回傳大 JSON 原樣入 context | tool 內 summarize / 抽 key fields |
| system prefix 每輪都改 | 穩定 prefix 先 cache 命中（§6） |

---

## 6. 同 Cache 協同（memory × cache 一齊諗）

- **穩定頭部 = cache 命中**：LTM 帶返嘅歷史 + system + tool schema 放**固定位置、固定內容** → prefix cache 命中（多輪 50–95%）→ 慳 token。
- **輾轉位**：memory 檢索回傳夾喺 prefix 中間、或者 prefix 每輪都唔同 → **全 miss**。
- **`output_schema` 會自動關 context cache**：要 structures 準 vs 慳，自己揀。
- 隱式 cache（方舟自動，~20% 起，128k+ 變異大）冇得關——用 `usage_metadata` 實測命中率（`cached_content_token_count / prompt_token_count`）。

> 💡 cache 文革堆野（五類 cache、三大引擎 paradigm、蝴蝶鏈）全部喺 **cache tab**。呢度只記一句：**記憶帶返嘅嘢放穩定 prefix → cache 至食到。**

---

## 7. 實戰技巧（Skills & Tricks）— 記憶 + 上下文

| # | 技巧 | 點解 / 點做 |
|---|---|---|
| 1 | **STM 多實例唔用 `local`** | 換 instance 即失憶；上 `sqlite`/`mysql` 先持久化 |
| 2 | **LTM 直接上托管 `viking` / `mem0`** | 唔使管 embedding；`local` 退出即冇、`opensearch` 要自己 embed |
| 3 | **threshold 唔好淨係信預設** | 高頻短對話調細 `MIN_TIME_THRESHOLD`；長任務調細 `MIN_MESSAGES_THRESHOLD` |
| 4 | **轉 session 一定要自動寫 LTM** | 零 code——但前提係綁咗 memory（`agentkit config --memory_id`） |
| 5 | **KB 永遠 top_k，唔好全文** | 全文入 system 係頭號反模式 |
| 6 | **summary 寫明「保留 key fields」** | 防 ID / 承諾細節被壓走 |
| 7 | **compaction interval 唔好低過 10** | <10 額外 call 反而貴（delta） |
| 8 | **memory 檢索結果放固定 prefix 位** | 保 cache 命中率 50–95% |
| 9 | **長 session 定時切 session** | 主題跳躍直接由頭開始，比硬壓慳 |
| 10 | **用 `usage_metadata` 睇命中 + 用量** | 數字講嘢，唔好估 |
| 11 | **`load_memory` 工具做主動回想** | instruction 講「答案可能喺過往對話，用 load_memory 搵」 |
| 12 | **測試用 `local`，上線轉托管後端** | 同一 code 換 backend 就切換，唔使改邏輯 |

---

## 8. Sales 一句 + 資料來源

### Sales 一句

> 「模型冇記憶，Agent 至有——LTM 跨 session 自動記住用戶，KB 揀啱片段先入 context，context 壓得細、cache 命中高，對話越長越平越準。你淨係要揀一次後端，寫 / 讀 / 壓縮我哋包辦。」

### 資料來源

| 來源 | URL | 日期 |
|---|---|---|
| VeADK 記憶管理（STM / LTM / KB 後端） | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/memory | 頁面日 |
| VeADK load-memory 工具用法 | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/tools/load-memory | 頁面日 |
| VeADK Context Search（托管 RAG） | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/knowledge/context-search | 頁面日 |
| AgentKit CLI（memory create / config --memory_id） | `references/agentkit-cli.md` | 2026-08 |
| VeADK API（STM / LTM / KB 構造 + load_memory） | `references/veadk-api.md` | 2026-08 |
| 記憶後端矩陣 + 揀法 | `references/veadk-agentkit-database-management.md` §4–5 | 2026-09-06 |
| Compaction / events config | `references/veadk-agentkit-ai-concepts.md` §5 | 2026-08 |
| Cache 五類 + 命中率 / 蝴蝶鏈 | `references/veadk-agentkit-cache-management.md` | 2026-08 |
| Context / cache / 128k+ 加倍率 | `references/veadk-agentkit-pricing.md` | 2026-08 |

> **免責**：threshold 預設值（10 條 event / 60 秒）、`load_memory` 工具名、backend 清單以 SDK 當刻版本為準——做方案前對返 VeADK preview docs。後端「要唔要自己配 embedding」見 db tab §4 矩陣。

---

*Last audit date: 2026-09-06 · 新 tab：記憶 + 上下文管理（配合 db tab 拆「後端」同「行為」）。threshold 同工具名跟 SDK 郁，落地前 refetch。*