# VeADK + AgentKit AI 概念百科（字典・索引）— RAG / Decoder / Ranker / Cache / Context / Memory / VectorDB / Database / MCP / Guardrail / Filter / 模型選擇 / Eval / 推理引擎

呢份係全套 VeADK / AgentKit / BytePlus 文件嘅 **AI 概念字典＆索引**。每個概念都用 **幾句講清楚**（概念係咩 → 對比 → 幾時用），**實體落喺 BytePlus / Volcengine（方舟）點落地**，再指去**專屬 Tab** 睇深度。寫得深，係要你唔止識「揀」，仲識**點解**——sales / 方案工程師要答得住 client 問「點解唔揀嗰個」。

> ✅ **核心心法**：
> 1. **九成方案問題唔喺概念，喺「揀錯層」**：喺 framework 層控制 context / cache / memory；底層引擎你唔使掂（方舟包辦）。知道「邊層係我話事」比識晒名詞重要。
> 2. **每個概念都有一條「決策線」**：唔好死背功能，記「幾時用邊個」嘅 trigger，同埋「揀錯嘅代價係咩」。
> 3. **成本意識要落地**：每個選擇都問一句「呢個選擇令 AFP / token / GPU 多定少」（見 `veadk-agentkit-pricing.md`）。技術揀錯 = 帳單揀錯。
> 4. **引用關係**：呢份係**字典／索引**（Q3 決策：每概念淺講 + 指去專屬 Tab 深探）。專屬 Tab 見下表。

---

## 0. 概念字典・索引 — 全 doc 地圖結構

> 🎯 呢張表係成個 doc 嘅總入口：**概念（喺邊層）→ 幾句即要 → 專屬 Tab（要深度就去）→ 字典條目#（呢份淺講）**。「專屬 Tab」= 要深度時跳去；「字典條目」= 留喺度快速 refresh。

| 概念 | 幾句即要 | 專屬 Tab（link filename） | 字典條目# |
|---|---|---|---|
| **RAG 類型**（Naive / Advanced / Agentic / Corrective / Self-RAG / Hybrid / Graph / Modular） | 由「檢索→生成」一條直線，精到 agent 全自動（路由/改寫/多跳/自評）；Graph 答關係題 | `veadk-agentkit-rag-guide.md` | §1 |
| **Chunking** | 切文件決定檢索準唔準嘅頭號隱形因素（size / overlap 取捨） | — | §1.3 |
| **Decoder / 生成**（sampling：greedy / beam / temperature / top-k / top-p / min-p） | 決定「穩 vs 創意 vs 快」；T<1 穩、T>1 創意 | — | §2 |
| **Structured output** | 保證輸出合 JSON schema；`output_schema` 會自動關上下文緩存 | — | §2.3 |
| **Speculative decoding** | 細模型估 N 個 → 大模型 verify → 吞吐 2–3×、質量不變 | — | §2.4 / §14.5 |
| **Ranker**（BM25 / Dense / RRF / Cross-encoder） | 粗檢 50 → 精排 10；BM25 強專名、Dense 強語義、RRF 融合、Cross-encoder 最準最慢 | — | §3 |
| **Cache 三層**（KV-Cache / Provider Prefix / Framework Context） | ①慳算力，②③慳錢；框架默認開 session 緩存 | `veadk-agentkit-cache-management.md` | §4 |
| **Context 管理 / Compaction** | 控制 prompt 唔好爆；壓縮長對話成 summary（細模型做，慳錢） | — | §5 |
| **Memory**（STM / LTM / KB） | STM 內部、LTM 跨 session（viking / mem0）、KB 外部知識 | `veadk-agentkit-vector-cache.md` | §6 |
| **Vector DB** | 向量索引（HNSW 主流）；托管 VikingDB / 自建 Milvus / OpenSearch | `veadk-agentkit-database-management.md` | §7 |
| **Database**（SQL / NoSQL / ACID） | Agent 方案要多種 DB：PG 事務 + TOS 大檔 + Vector 語義 + Redis 熱數據 | `veadk-agentkit-database-management.md` | §8 |
| **MCP / Tools / Skills / A2A** | 工具標準化（MCP 事實標準）、Skills 重複流程、A2A 多 agent 互通 | `veadk-agentkit-tools-capabilities.md` | §9 |
| **Guardrail** | 安全：攔有害 / 違法 / PII（火山 LLM-FW 四點審查） | `veadk-agentkit-rbac-observability.md` | §10 |
| **Input / Output Filter** | 乾淨：過濾入出、PII mask、trace/log 開關 | `veadk-agentkit-rbac-observability.md` | §11 |
| **模型選擇（模型梯度）** | 唔好一粒走天涯：mini 高頻 / pro 難題 / fallback list 自修復 | `veadk-agentkit-pricing.md` | §12 |
| **Eval** | 改嘢就要有量度：Offline / Shadow / CI / Studio 回流 | `veadk-agentkit-evaluation.md` | §13 |
| **vLLM / SGLang 引擎** | 底層點快（prefill→decode、continuous batching、KV-Cache）；托管包辦 | `veadk-agentkit-serving-kit.md` | §14 |
| **KV-Cache** | Transformer attention 中間值；食 VRAM；GQA / 量化 / 分頁慳 | `veadk-agentkit-serving-kit.md` | §14.4 |
| **量化（Quantization）** | 權重 / KV 壓縮精度換速度記憶（FP8/INT8） | `veadk-agentkit-serving-kit.md` | §14 |
| **LoRA / 精調**（LoRA / SFT / DPO / RLHF） | 用少量數據適應特定任務；方舟模型精調 SFT / DPO / GRPO | `veadk-agentkit-finetune-optimize.md` | §12.7 |
| **Hardware** | GPU / 部署選型；托管唔使掂、自建先講 | `veadk-agentkit-hardware.md` | §14 |
| **Deployment / Harness** | 上線架構、runtime 資源、A2A harness | `veadk-agentkit-serving-kit.md` | §14.9 |
| **訓練 TrainingKit** | 由零開始訓練模型 / dataset / grader | `veadk-agentkit-training-kit.md`（精調 / 優化 tab） | §12.8 |

### 0.2 一條主線：一單 request 由頭到尾做咗啲咩

```
用戶輸入
  │
  ▼
① 入站認證 (API Key / OAuth2 / JWT)          ← sec tab
  │
  ▼
② Input filter / Guardrail Before-Model      ← §10/§11
  │
  ▼
③ Context 組裝：system + few-shot + RAG top_k + 歷史(cache) + 新輸入   ← §5
  │
  ▼
④ 模型選擇 (mini/pro/... 或 fallback list)    ← §12
  │
  ▼
⑤ 引擎：prefill → decode（continuous batching / KV-cache / spec-decode）← §14
  │
  ▼
⑥ 生成策略 (greedy/sampling/structured)       ← §2
  │
  ▼
⑦ Output filter / Guardrail After-Model       ← §10/§11
  │
  ▼
⑧ 工具/MCP call → 結果 → 再入 context（loop）  ← §9
  │
  ▼
⑨ 記憶寫入 (LTM) / 可觀測 (OTel/APMPlus)       ← §6 / sec tab
  │
  ▼
⑩ Eval (shadow/CI) 判定質量                    ← §13
```

> **呢條線係全份文件嘅骨架**——每一個概念都係呢條線上嘅一個環節。答 client 問題時，沿住條線講「邊個環節出事」。

---

## 1. RAG 類型 — 揀邊隻檢索架構

### 1.1 概念：RAG 係咩、解決咩問題

RAG（Retrieval-Augmented Generation）= **生成前先檢索**：唔靠 model 記住一切，而係從外部知識庫拎相關片段塞入 prompt 再生成。

**點解要 RAG（vs 直接問 model）**：

| 問題 | 純 model | RAG |
|---|---|---|
| 知識凍結喺訓練日 | 答唔到新嘢 / 會亂嗡 | 檢最新文件答 |
| 內部文件唔會入訓練 | 唔知 | 檢自己嘅 KB |
| 引用 / 來源出處 | 亂作 | 可以帶出處 |
| 資料更新 | 要重訓 / 無得 | 換文件即生效 |
| 成本 | 要長 context 塞晒 | 只塞 top_k 片段，慳 token |

### 1.2 RAG 核心零件（五件）

| 零件 | 做咩 | 關鍵設定 | 見 |
|---|---|---|---|
| **Chunking** | 將文件切段 | chunk size / overlap / 切法 | §1.3 |
| **Embedding** | 文字 → 向量 | embedding model / 維度 | §7 |
| **Index / Vector DB** | 儲存 + 搜尋向量 | backend / 索引演算法 | §7 |
| **Retrieval** | 拎 top_k | 檢索法（BM25/dense/hybrid） | §3 |
| **Generation** | 塞入 prompt 生成 | context 組裝 / rerank | §3/§5 |

### 1.3 Chunking — RAG 準唔準嘅頭號隱形因素

| 切法 | 做法 | 優點 | 弱點 | 幾時用 |
|---|---|---|---|---|
| **Fixed-size** | 固定 N token 切（如 200/400） | 簡單、均勻 | 切斷語意 | 快起 / demo |
| **Recursive** | 按段落 / 標題 / 句子層級切 | 保留結構 | 長度不均 | 文檔有結構 |
| **Semantic** | 按語意邊界切（embedding 相似度找斷點） | 每塊語意完整 | 貴、要再嵌一次 | 準度敏感場景 |
| **Document-based** | 一文件一 chunk | 上下文完整 | 可能太長 | 短文件 |

**chunk size / overlap 經驗**：

- **chunk 太大**：塞咗無關內容 → 檢索唔準 + 塞爆 context（貴）。
- **chunk 太細**：語意斷裂 → 檢索到但唔完整。
- 建議起點：**256–512 token / chunk，overlap 50–100**；再用 eval 校準（§13）。
- 對照：VeADK `KnowledgeBase` 用**托管後端（viking / context_search）時服務端自己切分**——你唔使理 chunk 細節（好處），但想自訂就落向量類後端自己管。

> **BytePlus / Volcengine 點落地**：用火山方舟托管 RAG，chunk / embedding / index 全部有平台代管。

```python
from veadk.knowledgebase import KnowledgeBase
kb = KnowledgeBase(backend="viking", top_k=10, index="product-docs")
kb.add_from_directory("docs/")
agent = Agent(..., knowledgebase=kb)   # 自動有 load_knowledgebase 工具
```
> 呢度 `backend="viking"` 即係火山方舟 **VikingDB**，向量化用 `doubao-embedding-vision`（多模態向量）；**服務端負責切分 + 向量化 + 檢索**，你唔使自己管 chunk 細節。要再準就加 reranker（§3）。Graph RAG 唔係內建——要就去 Context Search 托管 RAG 或自建。

### 1.4 五種 RAG 架構深入對比

| 類型 | 做法 | 優點 | 弱點 | 適合 | 複雜度 |
|---|---|---|---|---|---|
| **Naive RAG** | 「檢索 → 塞入 prompt → 生成」一條直線，無 pre/post 處理 | 簡單、快、夠用 | 唔識處理複雜關係、更新慢、準度天花板低 | FAQ、產品文檔、新手 | ⭐ |
| **Advanced RAG** | Naive + **預處理（chunk/清洗/索引優化）+ 後處理（rerank/壓縮/去重）** | 準度明顯升 | 多咗幾步要調（chunk/rerank threshold） | 生產客服、法規檢索 | ⭐⭐ |
| **Modular RAG** | 揀積木自由組合（query 改寫、routing、fallback、fusion、多跳） | 彈性最大、可逐件換 | 過度工程風險、難 debug | 複雜 query、多來源 | ⭐⭐⭐ |
| **Graph RAG** | 抽 entity + relation 落圖，答關係題 | 超強於「A 關連 B 幾次」類問題 | 建立貴、更新難 | 知識圖譜、合規關連 | ⭐⭐⭐ |
| **Hybrid（BM25 + Dense）** | 關鍵字 + 向量並行，融合排名 | 覆蓋精確匹配 + 語義 | 要管兩個索引 | 有專有名詞 + 語義並存語料 | ⭐⭐ |

### 1.5 Modular RAG 入面嘅可選積木

| 積木 | 做咩 | 幾時加 |
|---|---|---|
| **Query 改寫** | 將口語 query 改寫成更易檢索嘅查詢 | 用戶講得鬆散（「上次講嗰單嘢」） |
| **Query routing** | 按意圖送去唔同檢索器（BM25 / vector / 圖） | 多種資料、意圖混雜 |
| **HyDE** | 先讓 model 偽造一個理想答案再檢索 | 短 query 檢索唔到好嘢 |
| **多跳（Multi-hop）** | 第一跳結果拎去第二跳檢索 | 問題要兩層先答到 |
| **Fallback** | 檢索零結果 → 改策略重檢 | 長尾 query |
| **重排序** | rerank（見 §3） | 要準度 |
| **壓縮** | 塞入前壓縮檢索內容 | context 會爆 |

### 1.6 幾時揀邊個（決策樹）

| Trigger | 揀 | 唔揀 |
|---|---|---|
| 靜態 FAQ / 文檔、想快上線 | Naive（用內建 KB 即得） | 唔好 Graph |
| 準度唔夠、專有名詞多 | Advanced（+rerank） | 唔好跳去 Modular |
| query 多變、多來源、意圖雜 | Modular（路由 / 改寫） | 唔好過度工程 |
| 關係題（「A 同 B 有咩關係」「幾次」） | Graph RAG | Naive 答唔到關係 |
| 同時有精確詞 + 語義需求 | Hybrid（BM25 + dense + RRF） | 單一檢索 |
| 每樣都想要但想先簡 | Advanced 起步，需要再加積木 | 一步到位 Modular（難 debug） |

> **Sale 一句**：「RAG 準唔準，八成喺『點切文件』同『點排結果』，唔係喺『用邊個模型』。文件切得爛，再靚嘅 model 都救唔返。」

---

## 2. Decoder / 生成策略 — 點樣出 token

### 2.1 概念：decoding 係咩

LLM 輸出本質係「逐 token 揀機率」：given 前面嘅 token，模型計出「下一個 token 嘅機率分佈」，再由 **decoding 策略**決定實際出邊個。

```
P(next_token | 前面所有 token) → 機率分佈 → decoding 策略 → 揀 token
```

- **決定「穩 vs 創意 vs 快」** 就喺呢一步。
- 兩個維度：**取樣策略**（揀邊個 token）+ **約束**（結構化輸出）。

### 2.2 常用取樣策略對比

| 策略 | 原理 | 優點 | 弱點 | 適合 |
|---|---|---|---|---|
| **Greedy（貪婪）** | 每次都揀最高機率 token | 穩定、可重現、快 | 單調、會重複、冇創意 | 抽取 / 分類 / 翻譯 |
| **Beam Search** | 同時保留 N 條 top 路徑，最後揀最好 | 更一致、全局較優 | 貴（N× decode）、仍唔夠創意 | 翻譯 / 摘要 / 需要一致性 |
| **Temperature（T）** | 將 logits 除 T 再 softmax；T<1 收窄、T>1 放寬 | 一個旋鈕控制創意 | 唔單獨用，配合 sampling | 調節「穩/創意」光譜 |
| **Top-k** | 只喺機率最高嘅 k 個 token 入面抽 | 排除長尾垃圾 token | k 揀得唔好就太窄/太闊 | 配 temperature 用 |
| **Top-p（nucleus）** | 累積機率到 p 先進入抽籤池 | 動態、比 top-k 好 | 細語料偶爾唔穩 | 對話 / 文案（常用默認） |
| **Min-p** | 排除機率低於「最高機率×p」嘅 token | 更平滑 | 較新、生態未齊 | 創意寫作 |
| **Repetition penalty** | 罰已出過嘅 token | 減少 loop/重複 | 會影響自然度 | 長文防 loop |

> **BytePlus / Volcengine 點落地**：喺 `doubao-seed-2.0-mini` 上用 `factory`-style API 透傳取樣參數。

```python
# factory / 方舟 Chat Completions：temperature、top_p、max_tokens 係 API 參數，SDK 可透傳
response = model.chat(
    model="doubao-seed-2.0-mini",
    messages=[{"role": "user", "content": "寫一段產品文案"}],
    temperature=0.9,     # 創意
    top_p=0.95,          # nucleus
)
```
> ⚠️ 喺 VeADK / 方舟，**取樣參數唔係你直接控制**（greedy/temperature 係 model API 參數，SDK 可透傳但 Plan 場景通常默認）。**真正你控制嘅係「邊個 model + 結構化要求」**——呢個先係你嘅槓桿。

### 2.3 約束式生成（Structured / Constrained output）

| 做法 | 原理 | 優點 | 幾時用 |
|---|---|---|---|
| **Function calling / tool call** | model 出 JSON tool call 結構 | 內建、標準 | 想 model 自己揀工具 |
| **`output_schema`** | 指定輸出 JSON schema | 保證結構 | ⚠️ **會自動關上下文緩存**（見 §4） |
| **Constrained decoding（引擎級）** | 引擎直接強制 grammar/schema | 唔使 retry、零 parse 錯 | 大量結構化 API（SGLang 強項） |
| **JSON mode（API）** | 平台保証輸出係 JSON | 較鬆 | 要 JSON 唔需要嚴格 schema |

**兩條路線嘅取捨**：

```
路線 A：generate → parse → retry（軟）     → 有機會 retry 幾次，慢 + 貴
路線 B：engine constrained（硬）           → 零 retry，快，但引擎支援（SGLang）
```

> **BytePlus / Volcengine 點落地**：Structured output 用 **Responses API 嘅 `output_schema`**（VeADK `Responses` 模式）。

```python
response = agent.chat(
    "提取呢單發票嘅字段",
    output_schema={
        "type": "object",
        "properties": {
            "invoice_no": {"type": "string"},
            "amount": {"type": "number"},
        },
        "required": ["invoice_no", "amount"],
    },
)
```
> ⚠️ 用 `output_schema` 會**自動關上下文緩存**（§4）——要權衡「準 vs 慳」。大量結構化 API 就靠引擎級 constrained decoding（§14，SGLang 強項）。

### 2.4 Speculative decoding —「快」嘅秘密

- 原理：**細 model 一口氣估 N 個 token → 大 model 一次過 parallel verify** → 啱晒一次收 N 個。
- 效果：throughput 2–3×、latency 降、**質量幾乎不變**（verify 兜底）。
- 變體：Classic draft model / Medusa（尾加平行 head）/ EAGLE（feature-level）/ Self-speculative。
- **喺托管（方舟）你唔使揀**——引擎自動做（見 §14）。識嘅用途：答 client「點解 token/s 咁高」。

### 2.5 幾時揀邊個（決策）

| 場景 | 用 |
|---|---|
| 客服答覆（要穩定、可審計） | 低 T + greedy（或默認） |
| 文案 / 創意 | 高 T + top-p sampling |
| 翻譯 / 摘要 | beam（要一致） |
| 一定要合 JSON schema | `output_schema`（⚠️ 關 cache）/ structured output |
| 量產 / 吞吐壓力 | 靠 spec-decode + 細 model（§14/§12） |

---

## 3. Ranker — 檢索結果點排

### 3.1 概念：檢索 ≠ 答案

RAG 檢索完，**唔係即刻用**——「檢到」同「排得啱」係兩件事。**Rerank** 係 Advanced RAG 嘅核心升級：先粗檢 top-50，再精排到 top-10，先塞入 model。

```
粗檢（快，攞大池） →  精排（準，篩細池） →  塞入 context
BM25 + dense top-50    cross-encoder top-10
```

### 3.2 Ranker 類型對比

| 類型 | 做法 | 優點 | 弱點 | 幾時用 |
|---|---|---|---|---|
| **BM25（關鍵字）** | 統計（TF-IDF 家族，詞頻+文檔頻率） | 快、精確詞好、零 model | 唔識語義 / synonym | 有準確術語、首輪粗檢 |
| **Dense / Bi-encoder** | 各自 embedding → cosine/dot | 語義強 | 專名/代碼易 miss、要管向量 | 語義搜尋主幹 |
| **Hybrid + RRF** | 兩邊分數合併排名（見公式） | 兩者兼得 | 要管兩索引 | 預設建議（§1.7 hybrid RAG） |
| **Cross-encoder** | 模型直接讀 query+doc 打分 | **最準** | 最慢（每 doc 一次 forward） | **只精排 top-k**（如 50→10） |
| **ColBERT（late interaction）** | token 級互動、預先算 | 準 + 可縮放 | 要特製索引 | 大規模語料精排 |

### 3.3 深入：BM25 vs Dense vs RRF 點解要混合

- **BM25 強**：精確匹配（「EULA 第 3.2 條」呢類專名、代碼、型號）——dense embedding 成日 miss 呢啲。
- **Dense 強**：同義詞、意譯（「點樣退貨」→ 文檔寫「refund policy」）——BM25 完全無。
- **RRF（Reciprocal Rank Fusion）**：兩邊各出排名，融合分數：

```
score(doc) = Σ ( 1 / (k + rank_i(doc)) )    # k ≈ 60
```

- 唔使理兩邊分數量綱（唔係加權平均分），只睇排名——穩。

### 3.4 Cross-encoder 深入：點解最準、點解慢

- **Bi-encoder**：query 同 doc **分開** embed → 比較（一次預算，快，但資訊獨立）。
- **Cross-encoder**：query + doc **一齊入** model 打分（可睇到語義互動，準，但每對 doc 一次 forward）。
- 所以正路：**粗選用 bi-encoder/BM25（快），精排用 cross-encoder（準）**——兩個階段分工。

### 3.5 標準 pipeline（Advanced RAG）+ 成本

```
BM25 + Dense 並行檢索 (top 50)  →  RRF 融合  →  Cross-encoder rerank (top 10)  →  塞入 context
```

| 步驟 | 數量級 | 成本 |
|---|---|---|
| 檢索 | 1 次 vector query | 平（viking 托管計「向量化」） |
| Cross-encoder rerank | 50 對 query+doc | **每對要 model forward** → 計錢（如計 AFP / 第三方） |
| Context 塞入 | top-10 × 200 token ≈ 2k token | 計 input token |

> **BytePlus / Volcengine 點落地**：VeADK `Ranker` 用 embedding_model 做 rerank（火山方舟模型）。

```python
from veadk.knowledgebase import Ranker
ranker = Ranker(embedding_model="doubao-embedding-vision")  # 用方舟多模態向量做精排
kb = KnowledgeBase(backend="viking", top_k=10, index="product-docs", reranker=ranker)
```
> ⚠️ **rerank 唔係默認**——VeADK 內建 `top_k` 檢索（預設 10）冇自動 rerank。要精度先加 `Ranker(embedding_model="doubao-embedding-vision")`——同 embedding 一樣有錢（計 AFP，見 pricing doc）。

### 3.6 幾時揀邊個（決策）

| Trigger | 揀 |
|---|---|
| 有準確術語（型號 / 代碼 / 條款） | 一定要混合 BM25（唔好用純 dense） |
| 語義搜尋為主（口語 / 意譯） | dense 主 + BM25 補 |
| 語料大（>1M docs） | ColBERT 或 分層粗選→精排 |
| 想最快 | 純 BM25 / 純 dense（唔 rerank） |
| 想最準 | hybrid + cross-encoder（願付精排錢） |

> **Sale 一句**：「檢索唔等於答案。你先粗檢 50 條，再用精排模型篩到 10 條，先係『餵到 model 面前』嗰 10 條——呢個先係準嘅關鍵。但精排有錢，要先講。」

---

## 4. Cache 管理 — 慳重複 token 嘅三層

> 💡 深度見專屬 Tab：`veadk-agentkit-cache-management.md`。呢度係字典級 + 落地。

### 4.1 概念：三層 cache，各管各

| 層 | 係咩 | 儲喺邊 | 控制權 | 慳咩 |
|---|---|---|---|---|
| **① 引擎 KV-Cache** | Transformer attention 中間值（K/V 向量） | GPU VRAM | 托管自動 | 唔使重算 attention（引擎層） |
| **② Provider Prefix / Context Cache** | 平台對相同前綴 / 上下文複用 token | provider 側 | 自動 + `usage_metadata` 睇命中 | **慳 token 錢** |
| **③ Framework Context Caching** | VeADK Responses API session 緩存 | 框架 | 默認開，`output_schema` 會關 | **慳重複 input token** |

> 三層唔好撈亂：① 慳算力，②③ 慳錢。sales 講「cache」要講得清係邊層。

### 4.2 KV-Cache 深入（引擎層）

```
KV memory ≈ 2 (K+V) × num_layers × num_heads × head_dim × 2 bytes × tokens × concurrent requests
```

- 長 context + 高並行 = KV 食 VRAM 爆燈（同權重大細差唔多，甚至更大）。
- 引擎層慳法：GQA/MQA（共享 KV 頭）、KV 量化（FP8/INT8）、PagedAttention/RadixAttention（見 §14）、streaming（H2O/SnapKV）。
- **你嘅槓桿**：context 越短 → KV 越細 → 平台 VRAM 需求低 → 平台可以更平（正正解釋 128k+ 雙倍率，見 pricing doc）。

### 4.3 Provider / Framework Context Cache 深入

- **機制**：平台記憶已送過嘅 prompt 前綴；下輪 request 只送「新增部分」+ cache token 平價/半價計。
- **VeADK 默認開** session 上下文緩存（Responses API 模式）。
- **睇命中率**：

```
usage_metadata:
  cached_content_token_count   # 命中
  prompt_token_count           # 實際送 model
命中率 = cached / prompt
```

- 多輪對話理想 **50–95%**；低過 50% → 檢查係咪每輪塞咗大 object（例如成個 file 入 tool return）。

> **BytePlus / Volcengine 點落地**：Responses API 上下文緩存。

```python
# 每輪對話自動開 Context Caching（VeADK Responses API 默認）
resp = agent.chat("繼續跟進上單退款")
print(resp.usage_metadata)
# cached_content_token_count ≈ 大部分 prompt → 命中率 50–95%
```
> 長 context（128k+）命中後會更抵；`output_schema` 會**自動關**呢個緩存。SDK / 日志會透出 `cached_content_token_count` 俾你驗命中率。隱式 cache（平台對已送過嘅前綴）命中率 ~20% 起跳，128k+ 前綴命中率變異更大——用 `usage_metadata` 實測為準（見 cache tab）。

### 4.4 Cache-aware prompting（令命中率自動升）

| 動作 | 點解 |
|---|---|
| **System / instruction 穩定** | system 部分 = 緩存區，穩定先命中 |
| **動態內容放 prompt 後面** | 前面變 = 成個 prefix miss |
| 唔好每輪塞大 object | 塞咗就強制重送 |
| 唔好每次 run 都重放成串歷史 | 靠 session cache / compaction（§5） |
| 結構化需求少用 `output_schema` | `output_schema` 會關緩存（要權衡） |

### 4.5 幾時開幾時關

| 場景 | 開 / 關 |
|---|---|
| 多輪客服、長 prompt、工具多 | ✅ 開（默認） |
| 要 `output_schema` 強制結構 | ⚠️ 自動關——衡量「準 vs 慳」 |
| 每輪 context 都唔同（一次性） | 開咗都冇命中，無損失 |

---

## 5. Context 管理 — prompt 唔好爆

### 5.1 概念：context window 點樣被食

一個 agent request 嘅 context = 幾樣嘢疊埋：

```
┌─ system / instruction（agent 人設）────────┐
├─ few-shot 例子 ────────────────────────────┤
├─ RAG top_k 檢索片段 ───────────────────────┤
├─ 歷史對話（越滾越長）───────────────────────┤
├─ 工具 / MCP 定義 ──────────────────────────┤
└─ 今次用戶輸入 ─────────────────────────────┘
```

- **長 context = 貴 + 慢**：更多 input token（慳錢位）+ 更大 KV cache（平台 VRAM）+ 更慢 TTFT（prefill 久）。
- 方舟定價 **128k+ 有加倍率**（見 pricing doc）→ **慳 context 就係慳真銀**。

### 5.2 工具對比（按成本由低到高）

| 工具 | 做法 | 慳幾多 | 成本 | 幾時用 |
|---|---|---|---|---|
| **Context caching** | 重用已送過嘅前綴 | 多輪 50–90% | 0 code | 默認、長 session |
| **Prompt 精簡** | instruction 寫短 | 每輪慳幾百 token | 0 | 永遠（instruction 係 system 一部分） |
| **RAG top_k** | 唔塞全文只塞 top_k | token ~30%+ | 少 code | KB 場景（唔好全文入 system） |
| **Tool return 收窄** | tool 內預先 summarize/抽 key | 每輪 | 中 code | tool 回大 JSON |
| **Compaction（壓縮）** | 長對話壓成 summary | 直接斬 token | 額外 summary model call | 長對話（10+ 輪） |
| **Session 切換** | 定期開新 session | 從頭計 | 0 | 主題跳躍 / 重 context 開頭 |

### 5.3 Compaction 深入

```python
app = App(
    agents=[my_agent],
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=10,   # 唔好太密（如 3）→ 額外 summary call 反而貴
        max_events=50,
        max_tokens=8000,
        compactor=LlmEventSummarizer(
            model="doubao-seed-2-0-mini",  # 用細 model 做 summary，慳錢
            system_instruction="壓縮成精簡中文摘要，保留用戶事實同已承諾事項。",
        ),
    ),
)
```

**做壓縮係咪一定慳？**

| | 慳 | 唔慳 |
|---|---|---|
| 長對話 / 工具多 | ✅ summary 縮短 context | |
| 每輪都壓（interval=3） | | ❌ 額外 summary call 反而貴 |
| 要 detail（用戶 ID / 引用冧巴） | | ❌ summary 冇咗細節 |

> ⚠️ **Summary 會冇細節**（用戶 ID / 引用冧巴 / 承諾細節）——要 detail 嘅 domain 唔好壓太勁，或 summary 寫明保留 key fields。

### 5.4 反模式（見 performance doc §5）

| 反模式 | 點改 |
|---|---|
| 成個 KB 全文塞入 system | 用 `load_knowledgebase` RAG 只塞 top_k |
| tool 回傳大 JSON 唔諗就入 context | tool 內預先 summarize / 抽 key fields |
| 一個 agent 做十件事 | 拆 agent（抽取 / 驗證，A2A 平行） |
| 每次 run 重放成串歷史 | session cache + 壓縮，或切 session |
| 所有輪都問大 model | 前端規則 / gateway 先 handle 簡單查詢 |

### 5.5 幾時用邊個（決策）

| Trigger | 用 |
|---|---|
| 長 session 對話 | caching + compaction |
| KB 問答 | RAG top_k（唔好全文） |
| 工具多、回傳大 | tool return 收窄 |
| 主題跳躍 | 切 session |
| 高準度結構化 | 犧牲 cache（`output_schema`）|

> **BytePlus / Volcengine 點落地**：compaction 用方舟**細模型**做 summary（`doubao-seed-2-0-mini` 0.5× 基礎係數，慳錢），見上面 code。Context 長度 → 直接影響方舟 128k+ 雙倍率，所以「慳 context 就係慳真銀」（見 pricing doc）。

---

## 6. Memory 管理 — 跨 session 記住用戶

> 💡 深度見專屬 Tab：`veadk-agentkit-vector-cache.md`。呢度係字典級 + 落地。

### 6.1 概念：記憶分三層，職責唔同

| 層 | 係咩 | 儲存 | 幾時要 |
|---|---|---|---|
| **STM（短期）** | 對話內 context | Runner/session 內建（進程內 / DB） | 單 session 內連續 |
| **LTM（長期）** | 跨 session 記用戶偏好 / 事件 / 實體 | Vector DB / 托管 | 要「記得上次」 |
| **KB（知識庫）** | 靜態外部知識 RAG | Vector DB / 托管 | 要答產品 / 法規 |

> 補充：**記憶唔係一個 blob**——有語義分別：
> - **Episodic（事件）**：做過咩（「上星期問過退款」）
> - **Semantic（語義）**：偏好 / 事實（「佢鍾意繁體」）
> - **Procedural（程序）**：點做（佢個 workflow）
>
> LTM 多數做 episodic + semantic；procedural 通常靠 instruction / tools 保持。

### 6.2 LTM 7 種後端（見 vector-cache doc §2）

| backend | 要唔要本地 embedding | 適合 | 幾時揀 |
|---|---|---|---|
| `local` | ✅ | 開發 debug | **生產唔好用**（多實例各自一本 → 失憶） |
| `opensearch` | ✅ | 已有 infra | 已用 OpenSearch（默認值） |
| `redis` | ✅ | 低延遲自建 | 已有 Redis |
| `viking` | ❌ | **生產推薦**、支援用戶畫像 | 新起 / 要 profile（region 固定 cn-hongkong） |
| `mem0` | ❌ | 托管、Mem0 負責抽取 | 想第三方托管 |
| `openviking` | ❌ | 服務端策略 | 生產 |
| `tos_context` | ❌ | 火山托管 | 生產 |

> ⚠️ **多實例 AgentKit Runtime + `local` = session 甩落第部機就失憶**（`run_sse` 返回 404 多數係呢個）。要持久化就唔好用 `local`。

### 6.3 幾時寫入 LTM（寫入週期）

- `min_messages_threshold` / `min_time_threshold`：幾多 event / 幾耐先寫入（預設 10 條 event 或 60 秒）。
- 轉 `session_id` 時**自動把上一 session 寫入 LTM**。
- 寫入越頻密：記憶越新，但 **embedding + 儲存錢越多**——用 threshold 平衡。

### 6.4 記憶成本意識

| 動作 | 成本 |
|---|---|
| LTM 寫入 | embedding（`doubao-embedding-vision` 計 AFP）+ 儲存（GB·h） |
| 每次檢索記憶 | 1 次 vector query |
| 檢索結果塞入 context | 計 input token |
| 用戶畫像檢索 | `enable_profile` / `query_with_user_profile`（**限 Viking 後端**）|

### 6.5 幾時用邊個（決策）

| Trigger | 揀 |
|---|---|
| 單 session 連續問答 | STM（內建） |
| 要「記得上次」（客服回頭客） | LTM（viking / mem0） |
| 要答外部知識 | KB（§7） |
| 只要本地試 | `local`（唔好上生產） |
| 已有 OpenSearch/Redis | 用返（慳遷移，但自己配 embedding） |

> **BytePlus / Volcengine 點落地**：LTM 生產用 **VikingDB（方舟托管）** 或 **mem0**。

```python
from veadk.memory import LTM
ltm = LTM(backend="viking", index="user-memory")   # 方舟 VikingDB 托管
# 或 ltm = LTM(backend="mem0")                      # 第三方托管抽取
app = App(agents=[agent], ltm=ltm)
```
> `viking` / `mem0` / `openviking` / `tos_context` 唔使自己配 embedding（服務端抽取）；`local` / `opensearch` / `redis` 要自己配（每個 backend 每次檢索多計一次 embedding 錢）。用戶畫像 `enable_profile` 只得 Viking 後端有。

---

## 7. Vector DB — 揀向量索引

> 💡 深度見專屬 Tab：`veadk-agentkit-database-management.md`。呢度係字典級 + 落地。

### 7.1 概念：向量點樣被搜

- **Embedding**：文字/圖 → N 維向量（語義近 = 向量近），方舟用 `doubao-embedding-vision`。
- **索引演算法** 決定「點樣快咁搵 nearest neighbour」：

| 演算法 | 原理 | 優點 | 弱點 | 幾時用 |
|---|---|---|---|---|
| **Brute-force（掃描）** | 逐個計距離 | 最準 | 慢（O(N)） | 細資料集（<100k） |
| **HNSW** | 多層圖搜尋 | 快、準度好 | 建索引慢、食記憶 | **主流默認** |
| **IVF** | 先分桶再入桶搜 | 慳記憶、可擴 | 精度稍低 | 超大資料集 |
| **PQ / Scalar quant** | 壓縮向量 | 慳記憶 | 精度 trade-off | 記憶緊 |
| **Disk-based ANN** | 落磁碟 | 唔爆 RAM | 慢 | 極大資料集 |

### 7.2 距離 / 相似度指標

| 指標 | 幾時用 |
|---|---|
| **Cosine** | 語義檢索主流（方向最重要，唔理長度） |
| **Dot** | 向量已 normalize 時 = cosine |
| **Euclidean（L2）** | 想重視 magnitude |
| **Inner product** | 特定 embedding 模型建議 |

### 7.3 後端矩陣（VeADK KnowledgeBase / LTM 共通概念）

| backend | 類型 | 要唔要本地 embedding | 幾時揀 |
|---|---|---|---|
| `local` | 內存向量索引 | ✅ | 開發 debug |
| `opensearch` | OpenSearch | ✅ | 已有 infra |
| `redis` | RediSearch | ✅ | 低延遲自建 |
| `milvus` | Milvus collection | ✅ | 已有 Milvus / 大規模 |
| `tos_vector` | TOS 物件向量 | ✅ | 用緊火山 TOS |
| **`viking`** | **VikingDB（托管）** | ❌（服務端切分+向量化+檢索） | **生產推薦、新起** |
| `context_search` | **托管 RAG** | ❌ | 托管 RAG、需 TOS 預簽名上傳 |
| `openviking` | OpenViking 資源目錄 | ❌ | 生產 |

### 7.4 揀法（決策）

| Trigger | 揀 |
|---|---|
| 已有 OpenSearch / Redis / Milvus | 用返對應 backend，慳遷移（但要自己配 embedding → 每檢索一次計多一次 embedding 錢） |
| **新起 / 想走托管** | **`viking` / `context_search`**（唔使自己管 embedding → 掃走「自建向量庫 + embedding 模型」成本） |
| 只要 local 試嘢 | `local` |
| 超大規模（>100M 向量） | milvus / 專用 ANN |
| 低延遲熱數據 | redis |

> **BytePlus / Volcengine 點落地**：新起走**托管 VikingDB**，自建先 Milvus / OpenSearch。

```python
# 托管 RAG（VikingDB / Context Search）— 方舟服務端食晒
kb = KnowledgeBase(backend="viking", index="product-docs", top_k=10)
# 自建（要自己配 embedding_model）
kb = KnowledgeBase(backend="milvus", index="product-docs", embedding_model="doubao-embedding-vision")
```
> `doubao-embedding-vision` 係火山方舟多模態向量模型（計 AFP，見 pricing doc）。自建後端每次檢索都要自己 embed → 多計一次 embedding 錢；托管後端（viking/context_search）服務端包辦向量化 + 檢索，你只買儲存 + 查詢用量。

> **Sale 一句**：「想喺方案度掃走『自建向量庫 + embedding 模型』兩項成本，就揀 VikingDB / Context Search——服務端食晒，你只係買儲存同查詢用量。」

---

## 8. Database — 揀資料庫類型

> 💡 深度見專屬 Tab：`veadk-agentkit-database-management.md`。呢度係字典級 + 落地。

### 8.1 概念：agent 方案要用「幾種」DB，唔係一種

| 類型 | 用途 | 例子（喺 stack） | 幾時揀 |
|---|---|---|---|
| **Relational（關係型）** | 結構化事務、審計 | PostgreSQL（audit 7 年 / chain-hash 存） | 有 schema、要事務 / 合規 |
| **Vector DB** | 語義檢索 | VikingDB / OpenSearch / Milvus / Redis | RAG / LTM |
| **Object Store（物件）** | 大檔案、archive | TOS（audit archive、video/圖 assets） | 影片/圖/7 年歸檔 |
| **Key-Value / Cache** | 快取、session | Redis | 低延遲熱數據 |
| **Graph DB** | 關連題 | （第三方，如 Neo4j） | Graph RAG |

### 8.2 深入：ACID vs BASE —— 點解審計要用關係型

- **ACID**（PostgreSQL）：原子性、一致性、隔離、持久——審計 / 訂單 / 用戶唔可以「一半寫入」。
- **BASE**（KV / 向量 / 物件）：最終一致、可用性優先——語義搜尋 / 快取 / 檔案 OK。
- **Agent 審計要求**（見 sec tab）：chain-hash（hash 鏈防篡改）+ 7 年保留 → 落 **PostgreSQL（寫入）+ TOS（archive）**。

### 8.3 一個方案點樣同時用幾種（示例）

| 嘢 | 儲邊度 | 點解 |
|---|---|---|
| 用戶 / 訂單 / 審計寫入 | PostgreSQL | ACID + chain-hash |
| 審計 archive 7 年 | TOS | 平、大容量 |
| 向量 / 記憶 | Viking | 托管向量 |
| session 熱數據 | Redis | 低延遲 |
| 關係問答 | Graph（第三方） | 關係題 |

### 8.4 幾時用邊個（決策）

| 你要做咩 | 揀 |
|---|---|
| 用戶 / 訂單 / 審計（要 ACID） | PostgreSQL |
| 語義搜尋 / 記憶 | Vector DB（§7） |
| 影片、圖片、7 年 log archive | TOS |
| 熱 session / 快取 | Redis |
| 關係問答 | Graph DB |

> **BytePlus / Volcengine 點落地**：用火山資料庫服務一體化。

```python
# 火山方舟 / BytePlus 產品（產品名隨版本郁，落地前查控制台）
# PostgreSQL 事務/審計  →  RDS MySQL / NDB MySQL（火山雲）
# 大檔案 / 7 年 archive →  TOS（火山物件儲存）
# 快取 / session          →  Redis（火山雲）
# 向量語義              →  VikingDB（火山方舟托管）
# 關連題                →  Graph DB（第三方 Neo4j）
```
> 審計 chain-hash 落 **RDS/NDB MySQL（PostgreSQL 系）**、大檔落 **TOS**、向量落 **VikingDB**、熱數據落 **Redis**——一個方案「幾種 DB 並存」先係正路，唔好一種打天下。產品名 / 型號隨版本郁，落地前查雲控制台（詳見 db tab）。

> ⚠️ **唔好「一個 DB 打天下」**——每個資料類型都有唔同嘅平快準特性，混埋就樣樣差。

---

## 9. MCP / Tools / Skills — Agent 點攞外部能力

> 💡 深度見專屬 Tab：`veadk-agentkit-tools-capabilities.md`。呢度係字典級 + 落地。

### 9.1 概念：由 Function calling 到 MCP 到 Skills

| 概念 | 係咩 | 標準 | 幾時用 |
|---|---|---|---|
| **Function calling** | model 出 JSON tool call | 各家內建 | 單一私有函數 |
| **MCP（Model Context Protocol）** | **標準化**工具協議 | **業界事實標準（2024+）** | **接入外部服務 / 生態** |
| **Toolset** | 一組工具打包 | 自家 | 同域工具分組 |
| **Skills** | 預包裝能力（流程/指令+工具） | 各家（AGENTS.md 類） | 跨 agent 共用工作流 |
| **A2A（Agent2Agent）** | agent 之間互通 | Google 主導 | pipeline / 平行 agent |

### 9.2 MCP 深入：client / server / transport

```
Agent（MCP client） ←── JSON-RPC 2.0 ──→ MCP server（工具 / 資源 / prompts）
        (stdio / SSE / HTTP)
```

- **MCP server** 暴露三類能力：**Tools**（可執行）、**Resources**（可讀資料）、**Prompts**（可重用 prompt）。
- **一次接入、多 agent 重用**：CRM / Slack / 網頁 / DB 各自寫一個 server，任何 MCP client 都用得。
- 生態大（2026 已有大量現成 server）→ 唔使自己由零寫。

### 9.3 喺 VeADK / AgentKit

```python
from veadk.tools.mcp import MCPToolset
# 接入 MCP server（外部工具）
# MCP service：自己開 MCP server 俾人哋用
# LongRunningFunctionTool：長任務異步工具
# A2A registry：多 agent 跨服務通訊
```

- CLI 內建工具：`--tools "web_search,run_code"`。
- **A2A 深入**：agent 之間用 A2A 協議通訊（`invoke` / `subscribe`），配合 registry 做 pipeline（見 invoice / movie project）。

> **BytePlus / Volcengine 點落地**：`agentkit mcp service` 開 MCP server，client 用 `MCPToolset` 接入。

```bash
# 開 MCP server（將內部工具/資源暴露成標準 MCP，俾任何 MCP client 用）
agentkit mcp service --name crm --tools "query_customer,book_meeting"
```

```python
from veadk.tools.mcp import MCPToolset
tools = MCPToolset(server="crm")          # 接入 MCP server
agent = Agent(..., tools=[tools])          # 或 --tools "web_search,run_code"
# A2A：多 agent 跨服務通訊（invoke / subscribe）+ registry 做 pipeline
```
> 要深度（MCP/Tools/Skills/A2A 全解）→ 工具/能力 tab：`veadk-agentkit-tools-capabilities.md`。

### 9.4 工具安全（見 sec tab）

| 風險 | 防護 |
|---|---|
| 工具 call 入參有毒 | `content_safety` Before Tool |
| 工具返回有 PII | `content_safety` After Tool |
| 出站 key 洩漏 | **Agent Identity（托管 + 自動輪換，唔入 repo）** |
| 用戶授權出站 | OAuth2 用戶委託 + 撤銷提示 |

### 9.5 幾時揀邊個（決策）

| 你個 agent 要… | 用 |
|---|---|
| 接外部 API（CRM / Slack / 網頁） | MCP（標準） |
| 內部私有函數 | Function calling / 自訂 tool |
| 一組工具成個包 | Toolset |
| 重複工作流俾幾隻 agent 用 | Skills |
| 幾隻 agent 分工合作 | A2A |
| 長任務（file processing） | `LongRunningFunctionTool` |

---

## 10. Guardrail — 攔有害 / 敏感內容

> 💡 深度見專屬 Tab：`veadk-agentkit-rbac-observability.md`（安全/Filter/Guardrail 深探）。呢度係字典級 + 落地。

### 10.1 概念：guardrail 係「安全」，filter 係「乾淨」

- **Guardrail**：攔有害 / 違法 / PII（安全）。
- **Filter**：過濾入出（乾淨，見 §11）。
- 兩者有重疊但目標唔同；production 兩個都要。

### 10.2 四點審查（VeADK 借火山 LLM-FW）

| 審查點 | 幾時 | 攔乜 |
|---|---|---|
| **Before Model** | 入 model 前 | 用戶輸入攻擊 / PII |
| **After Model** | model 出咗 | 輸出敏感資訊 |
| **Before Tool** | 工具 call 前 | 入參問題 |
| **After Tool** | 工具返嚟 | 返回 PII |

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

### 10.3 LLM-FW 一級分類（節錄）

| 代碼 | 策略 | 一句 |
|---|---|---|
| 101 | 模型濫用 | 詐騙 / 違法 prompt |
| **103** | **敏感資訊（PII）** | **實時偵測身份證 / 手機號等並攔截** |
| 104 | 提示詞攻擊 | 防越獄 / DAN / system prompt 外洩 |
| 106 | 通用話題控制 | 敏感話題（預設唔開，要自己配） |
| 107 | 算力消耗 | 惡意重複輸出攻擊（累積 pattern 先觸發） |

> ⚠️ **要 PII 保護一定要開 103**；要敏感話題控制記住加 106（唔係默認）。

### 10.4 深入：防 prompt injection 嘅多層防禦

| 層 | 做法 |
|---|---|
| ① 內容安全 | LLM-FW 104（提示詞攻擊） |
| ② 輸入隔離 | 唔好將外部內容同指令混埋（分隔符 / 指令重申） |
| ③ 權限最小化 | tool 權限收窄（Agent Identity 只授需要嘅） |
| ④ 輸出過濾 | After-Model 審查（§11） |
| ⑤ 監控 | OTel / APMPlus 異常偵測 |

### 10.5 vs 其他家

| | BytePlus（LLM-FW） | Azure Content Safety | Bedrock Guardrails |
|---|---|---|---|
| 接入 | 框架掛鈎（`content_safety` 回調） | 另接服務 | 另接服務 |
| 計費 | **內置接近免費** | 逐次 | $0.15/1K units（in+out 各一） |
| PII 實時 | category 103 四點 | 有 | 有 |

> **BytePlus / Volcengine 點落地**：Guardrail 直接借**火山 LLM-FW**（火山方舟內容審核）。

```python
from veadk.tools.builtin_tools.llm_shield import content_safety
agent = Agent(
    name="robot",
    before_model_callback=content_safety.before_model_callback,  # Before Model
    after_model_callback=content_safety.after_model_callback,    # After Model
    before_tool_callback=content_safety.before_tool_callback,    # Before Tool
    after_tool_callback=content_safety.after_tool_callback,      # After Tool
)
```
> 想開 103（PII）/ 106（話題控制）要喺火山 LLM-FW 控制台配 category。要深度 → sec tab：`veadk-agentkit-rbac-observability.md`。

---

## 11. Input / Output Filter — 過濾入出

### 11.1 概念：兩邊都要擋

| 種類 | 過濾乜 | 幾時用 |
|---|---|---|
| **Input filter（入）** | 唔想 agent 見嘅內容（黑白名單 / prompt injection 字樣 / 過長截斷 / 語言） | 公開入口、多租戶 |
| **Output filter（出）** | 唔想俾用戶見嘅內容（mask 電話 / 合規敏感詞 / 格式清理 / 品牌管控） | 有 PII 輸出、品牌 |
| **PII masking** | 偵測並遮罩個人資料（電話 / 身份證 / email） | 合規（金融 / 健康） |
| **Rate / abuse filter** | 用量限制、惡意重複 | 防濫用、防爆單 |

### 11.2 過濾機制對比

| 機制 | 原理 | 優點 | 弱點 | 幾時用 |
|---|---|---|---|---|
| **Regex / 規則** | 字串 pattern | 快、平、可預測 | 假陽性 / 假陰性 | 電話 / email / 特定詞 |
| **ML 偵測** | 模型分類 | 語意、揸唔定都捉到 | 貴、要 model | PII / 有害內容（LLM-FW） |
| **遮蔽（mask）** | 偵測後換 * | 保留其餘 | 要另做還原流程 | 日誌 / trace 出街 |
| **審批（HITL）** | 人睇過先放 | 最準、可控 | 慢、貴 | 高風險（見 A2UI HITL） |

### 11.3 喺 stack 點做

| 要做 | 用 |
|---|---|
| 內容安全 | LLM-FW（§10）四點 + category 103 |
| Prompt injection 防禦 | category 104 + 輸入隔離 |
| Trace 唔寫敏感嘢 | `OBSERVABILITY_OPENTELEMETRY_TRACE_CONTENT=false`（span 只留結構+耗時） |
| Logging 唔洩 prompt | `LOGGING_LEVEL=INFO`（DEBUG 會記 prompt / 輸出 / 工具參數） |
| 出站憑證唔入 repo | Agent Identity（sec tab） |

> **BytePlus / Volcengine 點落地**：Input/Output Filter 部分靠 LLM-FW（火山），部分靠 env 開關（OBSERVABILITY/LOGGING）。

```bash
# 火山 LLM-FW（§10）負責 ML 偵測（有 category 103 / 104）
# env 開關負責「過濾咩嘢出街」：
OBSERVABILITY_OPENTELEMETRY_TRACE_CONTENT=false   # trace 只留結構+耗時
LOGGING_LEVEL=INFO                                  # 唔記 prompt / 輸出 / 工具參數
```
> Filter 深度（含 HITL / A2UI）→ sec tab：`veadk-agentkit-rbac-observability.md`。

> **Sale 一句**：「入 filter 擋『啲客傳咩入嚟』，出 filter 擋『我哋 agent 講咩出街』。兩邊都要，唔好只做一邊——trace 同 log 都係『出街』。」

---

## 12. LLM 模型選擇 — 揀模型梯度

> 💡 價/AFP 深度見專屬 Tab：`veadk-agentkit-pricing.md`；精調深度見 `veadk-agentkit-finetune-optimize.md`；訓練深度見 `veadk-agentkit-training-kit.md`。

### 12.1 概念：模型唔係一粒，係一梯

- 一個生產 agent 應該用**多個梯度**配合（快/平做高頻，強做難題），唔好一粒走天涯。
- 仲要考慮：**context 長度、多模態、第三方生態、下線風險**。

### 12.2 文字模型梯度（方舟 / Agent Plan）

| 檔次 | 模型 | 特點 | 幾時用 |
|---|---|---|---|
| **極速** | `doubao-seed-2.0-mini` | 0.5× 基礎係數、快、平 | **高頻默認**（客服每一輪 / summary） |
| **標準** | `doubao-seed-2.0-lite` | 混合層 | 一般任務 |
| **進階** | `doubao-seed-2.1-turbo` | 256k ctx、編碼/主推 | 編碼、中量任務 |
| **進階** | `doubao-seed-2.0-pro` / `2.1-turbo` | 推理 | 難題、deep reasoning |
| **旗艦** | `doubao-seed-evolving` | 1024k ctx、Coding/Agent 旗艦 | 重度 agent / 長文 |
| **第三方** | `glm-5.2` / `minimax-m2.7/m3` / `kimi-k2.6/k2.7-code/k3` / `deepseek-v4-flash/pro` | 方舟托管同價 | 想用特定生態 |

> 更新對照（2026 當刻）：最新由 `doubao-seed-2.0-*` 推展到 **`doubao-seed-2.1-*` / `evolving`**；第三方新增 **`glm-5.2`、`minimax-m2.7/m3`、`kimi-k2.6/k2.7-code/k3`、`deepseek-v4-flash/pro`**。模型名常常郁，落地前 refetch（pricing doc）。

### 12.3 多模態 + 向量

| 類型 | 模型 | 幾時用 |
|---|---|---|
| 圖片生成 | `doubao-seedream-5.0-lite`（~100 AFP/張） | 生圖（貴，先問）· **詳情 → seedream tab** |
| 視頻生成 | `doubao-seedance-2.0`（~2,000 AFP/clip） | 生片（**只有 Large/Max Plan**）· **詳情 → seedance tab** |
| 語音 | `doubao-seed-tts-2.0` / `asr-2.0` | 語音入出 |
| 向量化 | `doubao-embedding-vision` | RAG / 記憶（多模態向量） |

### 12.4 組合拳：fallback list（慳錢 + 穩定）

```python
agent = Agent(
    model_name=["doubao-seed-2.1-pro", "deepseek-r1-250528"],
)
```

- 主 model 掛咗自動落第二個——**agent 帶自我修復**。
- 或者策略性：`["doubao-seed-2.0-mini", "doubao-seed-2.0-pro"]` → 高頻 mini，難題先 fallback pro → **慳一半以上**。

> **BytePlus / Volcengine 點落地**：fallback list 好實際，見上面 code。要穩 → `["...mini","doubao-seed-2.0-pro"]` 呢類「熱身+兜底」組合。

### 12.5 模型下線風險（誠實）

| 模型 | 狀態 |
|---|---|
| `doubao-seed-2.0-pro` / `2.0-code` | **即將下線**，新項目唔好用（呢個 context 正正反映下線風險） |
| `seedance-1.5-pro` | 即將下線 |
| `deepseek-v4-flash/pro` / `kimi-k3` | 嘗鮮/體驗版，繁忙會限流，要 fallback |
| `kimi-k3` | **只有 Medium+ Plan 先用得** |

> ⚠️ **模型下線風險 = 你 fallback list 嘅存在理由**：2.0-pro/2.0-code 即將下線，新項目改用 2.1 系 / evolving；實驗版（deepseek-v4 / kimi-k3）繁忙限流，要留 fallback。**唔好鑿死一個即將下線嘅模型落 production**。

### 12.6 揀模型決策

| 場景 | 揀 |
|---|---|
| 高頻 / 對話 / summary | **mini**（0.5× + 唔使行全 context） |
| 一般 / 中量 | lite |
| 編碼 / 主推 | turbo |
| 難題 / 推理 / 長文 | pro / evolving |
| 創意圖 / 片 | seedream / seedance（**鎖 Large/Max**） |
| 第三方生態 | glm / kimi / deepseek（方舟托管同價） |
| 想穩 | fallback list（`["mini","pro"]`） |

### 12.7 LoRA / 精調（深探 → finetune tab）

> 💡 深度全解（LoRA / SFT / DPO / RLHF）→ `veadk-agentkit-finetune-optimize.md`。

- **LoRA**：得 adapter（低秩）注入，幾 MB 唔使重訓全權重，輕量個人化。
- **SFT / DPO / RLHF**：有監督 / 偏好 / 強化 三級，愈深愈貴。
- 商業決策：**先試 RAG / prompt（0 成本）→ 唔夠先 LoRA（輕）→ 先至 SFT 全量**。

> **BytePlus / Volcengine 點落地**：火山方舟**模型精調**（SFT / DPO / GRPO）。

```python
# 方舟精調入口（深探見 finetune tab）
# SFT：用你嘅 dataset 微調 doubao-seed-2.0-mini
# DPO / GRPO：偏好 / 強化，以 grader 評分
```
> 精調係「最後一招」——先試 RAG / prompt 優化（0 成本）再諗 LoRA / SFT。深度 → `veadk-agentkit-finetune-optimize.md`。

### 12.8 訓練 TrainingKit（深探 → 精調 / 優化 tab）

> 💡 深度全解（由零開始訓練）→ `veadk-agentkit-training-kit.md`。精調係「喺基礎模型上加少少」，訓練係「由數據集起」；商業上絕大多數只會落到精調。

> **Sale 一句**：「唔好一個 model 走天涯——高頻用 mini 慳一半，難題先上 pro。粒度選對 = 帳單砍半。」

---

## 13. Evaluation — 守住質量

> 💡 深度見專屬 Tab：`veadk-agentkit-evaluation.md`（評估 / 評測 tab）。呢度係字典級 + 落地。

### 13.1 概念：改嘢就要有量度

- 性能 / 成本優化（§4/§5）每改一版，都要**有 eval 守著**——慳到飛起但 accuracy 跌晒等於白做。
- Eval 四件事：**Dataset（測咩）→ Evaluator（點評）→ Experiment（點跑）→ Regression（點守）**。

> 💡 深度見專屬 Tab：`veadk-agentkit-evaluation.md`（評估 / 評測 tab）；CI/回歸配合 `veadk-agentkit-performance.md`。

### 13.2 幾時用邊種 eval

| 類型 | 做法 | 幾時用 |
|---|---|---|
| **Offline / dataset eval** | 固定集 + evaluator 打分 | 每次改 prompt / 模型 |
| **Shadow eval** | 上線流量抽 10% 平行評分 | 想唔影響用戶嚟監控 |
| **CI eval** | `eval run` 入 pipeline | 每次 deploy 前 |
| **Studio 自動回流** | 每輪對話自動評分，Good/Bad Case 落返 eval 集 | 持續數據飛輪 |

### 13.3 Evaluator 類型對比

| Evaluator | 原理 | 優點 | 弱點 | 幾時用 |
|---|---|---|---|---|
| **字面匹配（BLEU/ROUGE）** | n-gram 重疊 | 快、平、可重現 | 唔睇語義 | 翻譯 / 摘要基準 |
| **Embedding 相似度** | 比語義距離 | 快、語義 | 唔識要點精 | 粗略回歸 |
| **LLM-as-judge** | 用 model 評分（相關性/完整性） | 準、可自訂 rubric | 貴、要校準 | **主流**（`agentkit eval run --evaluator 相关性`） |
| **參考對照（reference）** | 對住 golden answer | 客觀 | 要造 golden | 有標準答案 |
| **人工 / HITL** | 人評 | 最準 | 貴、慢 | 高風險 / 小集 |

### 13.4 流程（AgentKit CLI）

```bash
agentkit dataset create --name qa-set --schema "input,reference_output"
agentkit dataset add qa-set --file ./cases.json
agentkit eval run --dataset qa-set --evaluator 相关性 --target my-agent --json
```

- 一次多個 `--evaluator`（相關性 / 完整性）加權。
- 回傳 `experimentId` → `eval experiment get / results`（CI 用）。
- `--concurrency 10` 縮短 turnaround。
- **Studio 自動回流**：部署開「自動創建評測集」→ 每輪對話自動評分（0–1，≥0.6 入 Good Case）→ Good/Bad Case 落返 `{agent}_good_case`/`{agent}_bad_case` → 數據飛輪。

> **BytePlus / Volcengine 點落地**：AgentKit CLI `agentkit eval run`。

```bash
agentkit dataset create --name qa-set --schema "input,reference_output"
agentkit dataset add qa-set --file ./cases.json
agentkit eval run --dataset qa-set --evaluator 相关性 --target my-agent --json
```
> evaluator「相关性」= 方舟 LLM-as-judge；`--concurrency 10` 縮短 turnaround；回傳 `experimentId` 餵 CI。深度（含 Studio 自動回流）→ perf tab：`veadk-agentkit-performance.md`。

### 13.5 Eval 嘅隱性成本

| 成本 | 出處 |
|---|---|
| Shadow eval 10% 流量 | = +10% 模型消耗 → **計入報價 buffer**（pricing doc §10） |
| Studio 自動評測 | 每輪評分 model call |
| PII scan | 額外 LLM-FW 消耗 |

> **Sale 一句**：「性能優化唔使講『應該快少少』——我哋用 eval 每改一版都畀分，慳錢之餘有實績。」

### 13.6 幾時用邊個（決策）

| Trigger | 揀 |
|---|---|
| 每次改 prompt / 模型 | Offline dataset eval |
| 想唔影響用戶監控 | Shadow eval（10%） |
| 每次 deploy 前 | CI eval（`eval run`） |
| 想數據飛輪 | Studio 自動回流 |

---

## 14. vLLM / SGLang 級數 — 底層推理引擎

> 💡 深度見專屬 Tab：`veadk-agentkit-serving-kit.md`（引擎 / ServingKit）；硬件見 `veadk-agentkit-hardware.md`。
> **托管（方舟）你唔使揀引擎**——呢章係要你「識引擎點行」，sales 答「點解 token/s 咁高」「點解 cache 咁慳」用。

### 14.1 概念：一單 request 喺引擎內部

```
prefill（讀 prompt、計首 token，compute-bound）
    → decode（逐 token 出，memory-bound）
```

- **TTFT** 由 prefill 決定 → 大 prompt / 長 context = prefill 耐 = TTFT 大。
- 引擎層優化全部針對呢兩個階段：**慳 prefill（cache / 分頁）、加速 decode（spec-decode）、唔好 idle（continuous batching）**。

### 14.2 三寶：Continuous Batching / KV-Cache 管理 / Speculative Decoding

| 引擎技術 | 原理 | 效果 |
|---|---|---|
| **Continuous batching** | 任何 sequence 出完即刻插下一個 request（舊式要等成批） | 單 GPU RPS 高 **~20×** |
| **PagedAttention（vLLM）** | KV-Cache 拆 page 按需分配（好似 OS page table） | 碎片慳、單 GPU 頂更多 |
| **RadixAttention（SGLang）** | 前綴樹自動複用**任何共享 prefix** | 多租戶 / 多 agent 高共享更慳 |
| **Prefix caching** | 相同 prompt 前綴 KV 直接複用 | 慳 prefill + 慳錢 |
| **Speculative decoding** | 細 model 估 N 個 → 大 model parallel verify | 吞吐 **2–3×**、latency 降 |
| **Structured output** | 引擎層強制 JSON Schema | 唔使 generate→parse→retry |
| **Multi-LoRA** | 單引擎動態切多個 LoRA adapter | 輕量個人化唔使開多 deployment |
| **Chunked prefill** | 長 prompt 分塊 prefill，減少 block decode | 長 context 唔阻塞 |

### 14.3 Continuous Batching 深入

- 舊式：request 集齊一批 → 跑完 → 停 → 再集下批（**GPU 有 idle**）。
- vLLM：**任何 sequence 出完 token 即刻插下一個 request 接力** → GPU 幾乎 100% 無空撳。
- 效果：單 GPU RPS 比舊式 batching 高 ~20×（2026 benchmark 參考）。

### 14.4 KV-Cache 管理深入

```
KV memory ≈ 2 (K+V) × num_layers × num_heads × head_dim × 2 bytes × tokens × concurrent requests
```

- 例子：7B 模型、8k context、同時 100 request → KV 可以食**幾 GB 到十幾 GB VRAM**（同權重差唔多甚至更大）。
- **點慳**：

| 方法 | 原理 | 效果 |
|---|---|---|
| GQA / MQA | 多 query 頭共享少數 KV 頭 | KV 慳 4–8× |
| KV Quantization | FP8/INT8 存 | 慳 ~2× |
| PagedAttention / RadixAttention | 分頁 / 前綴複用 | 慳碎片 / 重算 |
| H2O / SnapKV（streaming） | 唔留全部 token | 長 context 大減（精度 trade-off） |
| Context caching（provider） | 同 prefix 複用 | 你慳 token 錢（框架層可見） |

> **同 framework 層接軌**：你控制嘅最直接嘢係「**context 唔好咁長**」——context 短 = KV cache 細 = 平台 VRAM 需求低 = 平台可以更平而唔將成本轉嫁你（見 §5）。

### 14.5 Speculative Decoding 深入

```
1. 細 draft model 一口氣估 N 個 token（快）
2. 大 model 一次過 verify 呢 N 個 token（parallel）
3. 啱晒 → 收 N 個；有錯 → 錯位重估
```

- 效果：throughput 2–3×、latency 降、**質量幾乎不變**。
- 變體：Classic draft model / Medusa（尾加平行 head）/ EAGLE（feature-level）/ Self-speculative。
- **同 prefix caching 有協同**：prefix 命中高 → spec-decode 更加食糊。所以你嘅「stable system prompt」間接幫引擎。

### 14.6 vLLM vs SGLang（2026 參考）

| | **vLLM** | **SGLang** |
|---|---|---|
| 發跡 | 柏克萊 / 雲上大規模 | 內核編譯派（LMDeploy 出身） |
| KV 管理 | **PagedAttention**（分頁） | **RadixAttention**（前綴樹） |
| Prefix 複用 | ✅（v0.6+ 自動） | ✅ 天生係主菜 |
| Structured output | ✅ constrained decoding | ✅ 引擎內建、較順 |
| Multi-LoRA | ✅ | ✅ 更順（優勢） |
| Spec-decode | ✅ 2–3× | ✅ 2–3× |
| 成熟度 / 生態 | 最廣、文件最多 | 年輕但性能屢破 |
| **適合** | 一般 Host API、大量獨立 request | 高共享 prefix、多 LoRA、結構化輸出多 |

### 14.7 其他引擎一眼睇（自建先啱用）

| 引擎 | 一句 | 適合 |
|---|---|---|
| TensorRT-LLM（NVIDIA） | 閉源/NVIDIA 優化，同 T4/A100/H100 深度 tune | 單一模型、性能榨到盡 |
| llama.cpp | CPU/小 GPU 都得、唔使大 engine、GGUF 量化 | 本地 demo、edge（四方對決 → cache tab §2.6；詳情 §2.4） |
| xLLM | BytePlus / ModelArk 全自研企業級引擎 | PD 分離 + MoE（ServerKit 主打；詳情 → cache tab §2.5） |
| TGI（HF） | HuggingFace 出品、老牌 | 已用 HF 生態 |
| Ollama / vLLM local | dev 便利 | 開發/測試 |

### 14.8 幾時揀（**僅自建**；托管方舟包辦）

| 考慮 | 揀 |
|---|---|
| 大量獨立 request、要穩 | vLLM |
| 大量共享 prompt / 多租戶 / multi-LoRA | SGLang |
| 結構化輸出為主 | SGLang（engine 級約束） |
| 單一模型榨到盡 | TensorRT-LLM |
| 本機 demo / edge | llama.cpp / Ollama |
| 多模型混合 | vLLM 或 SGLang（multi-LoRA 更勝） |

> ⚠️ 呢張表**唔影響 AgentKit 方案**——AgentKit 方案引擎由方舟包辦。**你要講嘅故事**：「引擎 == 我哋買嘅『會自己 batch + 分頁 + spec-decode 嘅 server』，你俾錢買 Agent Plan 已經打包咗呢啲技術。」

### 14.9 喺 AgentKit / VeADK 情境：底層引擎你唔使掂

| AgentKit/VeADK 你控制 | 引擎（唔使控制） |
|---|---|
| `model_name`（`doubao-seed-2-0-mini` 等） | 點 serve、點 batch、點 prefill |
| context / compaction / Responses cache | KV-Cache 大小、PagedAttention 頁 |
| `usage_metadata`（cached/prompt count） | prefix cache 命中與否 |
| Runtime `--cpu-milli/--memory-mb/--max-concurrency` | engine 內 thread/batch 排隊 |
| `--apmplus` 觀測（操作耗時） | prefill/decode 比例 |

> **BytePlus / Volcengine 點落地**：托管方舟 = ServingKit（vLLM / SGLang / Dynamo 打包）。

```python
# 你唔使揀引擎——Agent Plan 已包 vLLM / SGLang / Dynamo
agent = Agent(model_name="doubao-seed-2.0-mini")  # 你只控制 model_name + context + cache
```
> 引擎 / ServingKit / Deployment / Harness 深度 → serv tab：`veadk-agentkit-serving-kit.md`。硬件（GPU 選型）→ `veadk-agentkit-hardware.md`。量化（FP8/INT8）係引擎層慳 KV / 權重記憶嘅技術，托管自動處理，見 §14.4。

### 14.10 引擎詞彙速查

| 詞 | 一句 |
|---|---|
| Prefill | 讀 prompt、計首 token（compute-bound） |
| Decode | 逐 token 出（memory-bound） |
| KV-Cache | 留住之前 token 嘅 attention 中間值 |
| PagedAttention | vLLM 嘅 KV 分頁，慳碎片 |
| RadixAttention | SGLang 嘅 prefix 樹複用 |
| Continuous batching | 唔落 idle、即插 next request → RPS 20× |
| Prefix caching | 相同前綴複用 → framework 緩存命中的解說 |
| Speculative decoding | 細 model 估 + 大 model verify → 2–3× |
| Medusa / EAGLE | Speculative 變體（唔使額外 draft model） |
| GQA / MQA | 共享 KV 頭，慳 KV 記憶 |
| Chunked prefill | 長 prompt 分塊 prefill，少 block decode |

---

## 15. 總結：一頁決策表

| 問題 | 揀邊個 | 詳見 |
|---|---|---|
| 資料接入 | Naive / Advanced / Modular / Graph / Hybrid | §1 |
| 生成 | Greedy / Beam / Sampling / Structured | §2 |
| 排檢索 | BM25 + Dense → RRF → Cross-encoder | §3 |
| 慳 token | Context caching + Compaction + RAG top_k | §4 / §5 |
| 記憶 | STM + LTM（viking/mem0 生產） | §6 |
| 向量庫 | 新起→viking/context_search；已有→對應 backend | §7 |
| 資料庫 | PG 事務 + TOS 大檔 + Vector 語義 | §8 |
| 工具 | MCP 外部 / Function 私有 / A2A 多 agent | §9 |
| 安全 | LLM-FW 四點 + 103 | §10 |
| 過濾 | Input/Output + PII mask + trace 開關 | §11 |
| 模型 | mini 高頻 / pro 難題 / seedance 片（Large/Max） | §12 |
| 質量 | Offline + CI + Shadow + Studio 回流 | §13 |
| 引擎 | 托管唔使揀；自建先 vLLM vs SGLang | §14 |

**決策三問**（任何方案都先答呢三條再講技術）：
1. **邊層話事？**——呢個問題喺 framework 層控制（context / cache / memory）定係引擎層（托管包辦）？答啱層先落手。
2. **慳定準？**——每個 cache / rerank / 模型選擇都係「慳 token / GPU」同「準度」嘅拉鋸，邊個行先？
3. **點證明？**——改完有冇 eval 分數守著？（§13）冇 = 等於冇改。

---

## 16. 資料來源

| 來源 | URL | 日期 |
|---|---|---|
| 概念字典（本文件） | `references/veadk-agentkit-ai-concepts.md` | 2026-08-17 |
| Vector / Cache / Memory 深度（記憶、RAG、緩存） | `references/veadk-agentkit-vector-cache.md` | 2026-08-13 |
| 工具 / 能力深度（MCP / Tools / Skills / A2A） | `references/veadk-agentkit-tools-capabilities.md` | 2026 |
| 精調 / 優化深度（LoRA / SFT / DPO / RLHF/GRPO） | `references/veadk-agentkit-finetune-optimize.md` | 2026 |
| 性能 Playbook（cache / compaction / model selection / eval） | `references/veadk-agentkit-performance.md` | 2026-08-13 |
| Cache 管理深度 | `references/veadk-agentkit-cache-management.md` | 2026 |
| 硬件深度 | `references/veadk-agentkit-hardware.md` | 2026 |
| 資料庫管理深度（Vector / RDS / NDB / Redis / Mongo / TOS） | `references/veadk-agentkit-database-management.md` | 2026 |
| 引擎 / ServingKit 深度（vLLM / SGLang / Dynamo） | `references/veadk-agentkit-serving-kit.md` | 2026 |
| 訓練 TrainingKit 深度 | `references/veadk-agentkit-training-kit.md` | 2026 |
| 安全 / RBAC / PII / Audit / Observability（Guardrail / Filter） | `references/veadk-agentkit-rbac-observability.md` | 2026 |
| 模型矩陣 / AFP / 價 | `references/veadk-agentkit-pricing.md` | 2026-08 |
| 獨特賣點（自家模型 / 一體化） | `references/veadk-agentkit-uniqueness.md` | 2026-08 |
| vLLM 官方（PagedAttention / continuous batching / prefix caching） | https://docs.vllm.ai | 頁面日 |
| SGLang 官方（RadixAttention / structured output / multi-LoRA） | https://docs.sglang.ai | 頁面日 |
| RAG 綜述（Naive / Advanced / Modular / Graph / HyDE） | arXiv / 業界綜述 | 2023–2026 |
| RRF / Cross-encoder rerank / ColBERT 最佳實踐 | 業界（HuggingFace / Weaviate） | 2024–2026 |
| Speculative decoding 綜述（Medusa / EAGLE） | https://arxiv.org/abs/2211.17192（Classic）/ projects | 頁面日 |
| GQA：Multi-Query Attention 變體 | https://arxiv.org/abs/2305.13245 | 2023 |
| KV-Cache 量化（KV quant） | https://github.com/vllm-project/vllm/blob/main/docs/features/kv_quantization.md | 頁面日 |

> **免責**：效能倍數（RPS 20×、spec 2–3×）、命中率（cached/prompt 50–95%、隱式 ~20%）、AFP 折算、KV 記憶估算係參考估算，以實戰 `usage_metadata` + 控制台「用量明細」為準。各模型/功能存在性、價、Plan 門檻（如 seedance 只限 Large/Max、kimi-k3 只限 Medium+）、下線狀態以方舟控制台當刻為準（本文 2.0-pro/2.0-code 下線風險屬 2026-08 參考）。

---

*Last audit date: 2026-08-17 · 模型/Plan/引擎版本常常郁，引用前 refetch。*
