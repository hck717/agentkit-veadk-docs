# RAG 全攻略（揀檢索架構 · 揀 Ranker · 揀幾時用邊種）— Agentic / Corrective / Hybrid RAG 一次過

「RAG 點揀」唔係一條題，係**三條題**：① 揀邊種 **RAG 架構**（Naive → Agentic/Corrective Hybrid）；② 揀邊款 **檢索 + 重排（retrieval + rerank）**；③ 按**場景**（要快 / 要準 / 要balance / 要慳）落決定。呢份係全套參考，入面每個決定都配 `決策表格` + BytePlus / 方舟實例。

> **核心心法**：
> 1. **RAG 準唔準，八成喺「點切文件」同「點排結果」，唔係喺「用邊個 model」**——文件切得爛，再靚嘅 model 都救唔返。
> 2. **「檢索」就係 cheap 版、「重排」就係 accurate 版**：粗檢 top-50（快、平）→ 精排 top-10（準、貴）先餵 model。你揀嘅其實係「喺邊度落錢」。
> 3. **「揀邊種 RAG」=「揀幾多 intelligence 放喺 pipeline」**：越生動（agentic）越準但越貴越慢；越生硬（naive）越快越平但天花板低。

---

## 0. 先答三條最常問

1. **「我想最準」** → **Agentic / Self-RAG / Corrective RAG**：pipeline 識得自己決定「要唔要再撿、要唔要重寫 query、要唔要 fallback 去 web」；再加 cross-encoder rerank。
2. **「我想最快最平（又有基本水準）」** → **Advanced RAG + Hybrid（BM25+dense）+ RRF**，唔起 rerank，top_k 細（5–10）：一條直線、零 model-in-the-loop。
3. **「我想 balance（生產最常見）」** → **Advanced RAG + Hybrid + RRF + 可選 cross-encoder（只精排 top-50→10）**：準度同成本都有得調。

> **Sale 一句**：「由 Naive 起步，用 eval 話你知邊個位唔夠（檢得錯？排得矇？答得差？），再按單點 upgrade——唔好一次過砌 Agentic。」

---

## 1. RAG 架構全圖：十種 RAG 排好

### 1.1 由生硬到非常生動（intelligence / 成本 / 延遲由低到高）

| # | 架構 | 做法（一句） | 優/弱 | 幾時用 | 複雜度 |
|---|---|---|---|---|---|
| 1 | **Naive RAG** | 檢→塞→答，一條直線 | 極快極平／準度天花板低 | FAQ、demo、靜態文檔 | ⭐ |
| 2 | **Advanced RAG** | Naive + 預處理（chunk/清洗）+ 後處理（rerank/壓縮） | 明顯更準／多幾步要調 | 生產客服、法規檢索 | ⭐⭐ |
| 3 | **Hybrid RAG** | BM25 + Dense 並行，RRF 融合排名 | 精確詞 + 語義兩食／要管兩個索引 | 專名、型號、代碼多嘅語料 | ⭐⭐ |
| 4 | **Corrective RAG（CRAG）** | 檢完先「評分」——唔夠準就**重寫 query 或 fallback web**（唔會硬住用垃圾結果） | 抗錯、少 hallucination／要評分器 | 答案唔允許錯（法規/醫療/財報） | ⭐⭐⭐ |
| 5 | **Self-RAG** | Model 用 special token（`[Retrieve]/[Relevant]/[Supported]`）**自決幾時撿、幾時信、幾時補** | 靈活、貼 model／token 成本升、要支援模型 | 長對話、要連續自我修正 | ⭐⭐⭐ |
| 6 | **Agentic RAG** | 成個 pipeline 用 agent 行：路由、query 改寫、多跳、工具、迭代檢索全部自動 | 最靚、最慳 token（只 call 需要嘅）／最難調、要 ground truth 驗 | query 多變、多來源、多跳題目 | ⭐⭐⭐⭐ |
| 7 | **Graph RAG** | 抽 entity+relation 落圖，答關係題走圖搜尋 | 關係題超強／建立貴、更新難 | 知識圖譜、關係關連、合規 | ⭐⭐⭐ |
| 8 | **Modular RAG** | 積木自由組合（routing/改寫/HyDE/多跳/fusion） | 彈性最大／過度工程風險 | 複雜來源、意圖雜 | ⭐⭐⭐ |
| 9 | **HyDE** | 先叫 model 偽造「理想答案」再用嚟檢索 | 短/口語 query 都得／多一次 LLM call | 「個 query 就得幾個字」嘅場景 | ⭐⭐ |
| 10 | **Multimodal RAG** | 同時撿 文字+圖/表/圖像嘅 embedding | 識答「圖入面寫咩」／要 multimodal embedding（方舟 `doubao-embedding-vision`） | 文檔有圖表、PDF、合約掃描 | ⭐⭐⭐ |

> ⚠️ **冇一隻係「最好」**——係「邊個啱你嘅場景」。RAG 史上最貴嘅錯，就係一步到位砌 Agentic 而唔知 base case 係咩成績。

### 1.2 Agentic RAG 深入（最貴、最靚）

唔係「多咗一個檢索步驟」，係**用 agent 管成個 RAG pipeline**：

| 能力 | 做咩 | 慳/貴位 |
|---|---|---|
| **Query routing** | 按意圖送去 keyword / vector / graph / API | 慳：唔使每個 query 行晒全部 |
| **Query rewriting** | 口語 → 檢索友好（「上次講嗰間」→「XX公司」） | 準：第一跳已經中 |
| **Iterative / multi-hop retrieval** | 第一跳結果 → 第二跳再撿 | 準：兩層先答到 |
| **Tool use** | RAG 唔夠就 call 其他工具（計數、查庫、瀏覽器） | 慳/準：唔會硬答 |
| **Self-assessment** | 答題前問「證據夠唔夠」→ 唔夠補撿 | 抗錯：少 hallucination |

> **BytePlus / Volcengine 點落地**：Agentic RAG 嘅「agent 層」用 **VeADK/AgentKit**（`Agent` + 工具 + KB 工具），「檢索層」用 **KnowledgeBase（VikingDB / context_search）**，評分/改寫 call **方舟模型**（`doubao-seed-2.0-mini/lite` 就夠做 router/rewriter，慳）。

```python
from veadk.knowledgebase import KnowledgeBase, Ranker
kb = KnowledgeBase(backend="viking", top_k=10, index="faq-docs",
                   reranker=Ranker(embedding_model="doubao-embedding-vision"))
agent = Agent(..., knowledgebase=kb, tools=[Calculator(), Fetcher()])
# agent 自動：route → 撿 → (唔夠)重寫 query → 撿 → (仲唔夠)call tool → 答
```

### 1.3 Corrective RAG（CRAG）深入

| 環節 | 做咩 |
|---|---|
| **評分器（Evaluator）** | 對撿出嚟嘅 docs 判斷係咪「真係相關 / 唔相關 / 半信半疑」 |
| **確認相關** | 畀 pass，直接塞入生成 |
| **半信半疑** | 做知識抽取（knowledge refinement，抽走無關段落）再生成 |
| **完全唔行** | 唔用檢索結果 → **fallback 去 web 搜尋 / 重寫 query 重撿**——絕唔硬住用垃圾 |

> 同 Self-RAG 分別：CRAG 係**「檢索後」**嘅補救（results 打分再補），Self-RAG 係**「生成全程」**嘅自我管理（幾時撿/信/補都由 model 決定）。兩者可以疊。
>
> 🎯 要上 CRAG，最抵做法：**評分器用最平嘅 model／規則**（相關性 threshold + `Ranker` 分數），唔好一開頭就用大 model 評——慳。

### 1.4 RAPTOR / 多跳 / 呢啲「升級積木」幾時值得

| 積木 | 做咩 | 幾時值得 | 唔抵位 |
|---|---|---|---|
| **RAPTOR** | 將 chunks 遞歸聚類+總結成樹，由上層總結開始撿 | 長文檔、要大局觀答案 | 建立貴，FAQ 級唔值得 |
| **Multi-hop** | 多跳檢索 | 問題要兩層先答 | 一跳答到就唔好 |
| **Query 改寫 / HyDE** | 改靚 query | 用戶講得鬆散 | prompt 本身好清晰就唔需要 |

---

## 2. 檢索（Retrieval）類型 — 揀檢索器

### 2.1 六款檢索法

| 檢索法 | 運作 | 強項 | 弱項 | 幾時用 |
|---|---|---|---|---|
| **Sparse（BM25/TF-IDF）** | 詞頻統計計分 | 精確詞、型號、代碼、條款、人名 | 唔識同義詞/意譯 | 有準確術語、首輪粗檢 |
| **Dense（bi-encoder）** | 各自 embedding → cosine/dot | 語義、意譯（「點退貨」→「refund policy」） | 專名/代碼易 miss | 語義主幹 |
| **Hybrid（Sparse+Dense）** | 兩邊並行 | 兩者兼得 | 要管兩個索引 | **預設建議** |
| **RRF（融合排名）** | 排名 → `score=Σ 1/(k+rank)` | 融合唔怕量綱唔同 | 唔加權（只睇排位） | 混合檢索後融合 |
| **Vector hybrid（meta filter）** | 向量 + metadata（過濾日期/來源/租戶）過濾 | 精準縮池、多租戶 | 語料要帶 metadata | 企業/多租戶 |
| **Cross-encoder 精排** | query+doc 一齊入 model 打分 | **最準** | 每對 forward，慢 + 錢 | **只精排 top-k**（50→10） |

### 2.2 混合三式（Hybrid 點溝）

| 溝法 | 做法 | 效果 | 註 |
|---|---|---|---|
| **要求 AND** | 兩邊都有先得 | 太嚴、漏召回 | 少用 |
| **併集 + RRF** | 兩邊各出排名，RRF 融合 | 召回 + 排序都掂 | **最常用**（`k≈60`） |
| **加權平均分** | 分數加權埋埋 | 量綱唔同難平衡 | 唔建議（RRF 穩好多） |

> 🎯 **唔好自己發明融合**：用 RRF（睇 rank 唔睇分數），唔使理量綱、好穩。

### 2.3 BytePlus / 方舟檢索落地

- **托管 RAG**：`KnowledgeBase(backend="viking" | "context_search")` → 方舟服務端食晒（chunk/向量/索引）；context_search 重做過 RAG 管治。
- **自建檢索**：揀向量類後端（OpenSearch/Milvus），自己配 `embedding_model`（如 `doubao-embedding-vision`）。
- **粗→精**：`top_k=10`（內建，無 rerank）→ 要準就加 `Ranker(embedding_model="doubao-embedding-vision")`。
- 後端矩陣/成本全部睇 **`veadk-agentkit-vector-cache.md`**（記憶/知識庫 tab）；DB 後端睇 **`veadk-agentkit-database-management.md`**。

---

## 3. 重排（Rerank）類型 — 揀精排器

### 3.1 Rerank 係咩、點解要

「檢到」≠「排得啱」。**粗檢打大池（top-50）→ 精排縮細池（top-10）→ 先餵 model**。

### 3.2 Rerank 五類

| 類型 | 做法 | 準度 | 速度 | 成本 | 幾時用 |
|---|---|---|---|---|---|
| **唔 rerank** | 淨係用檢索分數排（top_k） | 中 | ★★★★★ | 0 | 夠用就算、要快 |
| **RRF / rank fusion** | 排名融合（無 model） | 中上 | ★★★★★ | 0 | Hybrid 後融合、慳錢 |
| **Cross-encoder** | query+doc 一齊打分（如 `bge-reranker`、`qwen3-reranker`、Cohere Rerank） | **最高** | ★★ | 高（50 對 forward） | 生產準度優先 |
| **LLM-as-reranker** | 叫 model 逐對/ listwise 評（RankGPT 式） | 高 | ★ | **最高** | 少量但超關鍵 query |
| **Late-interaction（ColBERT）** | token 級互動、預先算好 | 高 | ★★★ | 中 | 大語料（>1M）縮放 |

### 3.3 精排份量（唔好 over-engineer）

| 你嘅準度問題 | 精排份量 |
|---|---|
| 「檢到冇中 → 完全漏」 | 係**檢索**問題（改 chunk / 改 mixing / 加改寫），唔係 rerank |
| 「檢到啱，但頭幾條唔係最貼」 | 先加 **RRF**（零成本）；仲唔夠先上 **cross-encoder top-50→10** |
| 「長文件頂住晒，答唔到其中一段」 | 係 **chunk/rerank** 兩回事——rerank 高分唔等於答到，要睇評估 |

> ⚠️ **rerank 唔係默認、有錢**：VeADK 內建 `top_k` 檢索無自動 rerank。租客共享計費（AFP）下精排 50 對=50 次 model forward——先評估（`veadk-agentkit-performance.md` eval 節）再決定值唔值。

---

## 4. 場景揀選：速度 / 準確 / 平衡 / 成本 大表

> 「要快定要準定要慳」→ 呢度一表到題。括號內係 pipeline 必列位。

| 目標 | 架構 | 檢索 | 重排 | Chunk | top_k | 約略相對 | 一句 |
|---|---|---|---|---|---|---|---|
| 🚀 **Best Speed（遊戲延遲敏感）** | Naive / Advanced | 純 Dense 或純 BM25（單一） | **唔 rerank** | Fixed 256–512 | 3–5 | 最快、最平 | 用戶等唔到，唔好攞 50 條嚟排 |
| 🎯 **Best Accuracy（答案唔允許錯）** | **Agentic / Self-RAG / CRAG** + Advanced | **Hybrid + RRF** | **Cross-encoder 50→10**（+ 可選 LLM 複查） | Semantic / Recursive 細粒 | 10–20 | 最準、最貴 | 錯一條都唔得：評分→補撿→fallback 全開 |
| ⚖️ **Balance（生產默認）** | Advanced RAG | **Hybrid（BM25+dense）+ RRF** | **可選 cross-encoder**（50→10，先試無） | Recursive 512/100 | 10 | 中快中準 | 一條直線，準度唔夠先逐步加 |
| 🪙 **Best Cost（量巨大、邊際要慳）** | Naive + 靜態 | 純 BM25（零 embedding/rerank call） | **唔 rerank** | Fixed 256 | 3–5 | 最平（百萬 query 都頂得順） | prompt 前綴固定→食 cache（`veadk-agentkit-cache-management.md`） |
| 🧩 **Multi-source / 意圖雜** | **Agentic / Modular**（routing + 改寫 + 多跳） | Route 去唔同檢索器（keyword/vector/API） | 尾站 cross-encoder | Recursive | 10×hop | 中高 | 一個 agent 自動揀「行邊條路」 |
| 🕸️ **關係題 / 合規關連** | **Graph RAG** | 圖搜尋（entity→relation） | 可選 | Entity+Relation | 圖 hop | 高建置 | 「A 同 B 幾多關連」呢類先值 |
| 📄 **有圖表/掃描/PDF** | Advanced + **Multimodal** | Multimodal embedding（`doubao-embedding-vision`） | Cross-encoder | Fixed+table-aware | 10 | 中 | 答案要睇埋圖/表，唔係淨文字 |
| 🏢 **企業/多租戶** | Advanced | Dense + **metadata filter**（來源/日期/租戶） | 可選 | Recursive | 10 | 中 | 精準縮池 + 權限隔離 |

### 4.1 決策樹（由「目標」入，30 秒到題）

```
想要咩？
├─ 最快最平 → Naive/Advanced + 單一檢索 + 唔 rerank（Dense 或 BM25）
├─ 平衡（走唔錯）→ Advanced + Hybrid + RRF（+ 可選 cross-encoder）
├─ 最準（錯唔起）→ Agentic/Self-RAG/CRAG + Hybrid + cross-encoder rerank
├─ 關係題 → Graph RAG
├─ 意圖雜/多來源 → Agentic/Modular（routing/改寫/多跳）
├─ 有圖表/掃描 → Multimodal（doubao-embedding-vision）
├─ 多租戶 → Dense + metadata filter
└─ 量巨大要慳 → Naive + BM25 純檢索 + 固定 prompt 前綴食 cache
```

### 4.2 「升級順序」路徑（唔好一步到位）

```
1. Naive 起步（內建 KB 即得）＋ eval baseline 比分
2. 加 RRF 融合（零 model 成本）→ 睇有冇改善
3. 加 Recursive/Semantic chunk（切文件改善）
4. 加 cross-encoder rerank top-50→10（最明顯準度跳）→ 量錢
5. 再加 Model-in-the-loop（改寫/router/評分）→ 變 Agentic/CRAG
每步都要 eval 對比分（`veadk-agentkit-performance.md` eval），唔好亂加。
```

---

## 5. 實作速查（VeADK / AgentKit）

```python
from veadk.knowledgebase import KnowledgeBase, Ranker

# ① Balance（生產默認）：VikingDB + reranker
kb = KnowledgeBase(backend="viking", top_k=10, index="faq",
                   reranker=Ranker(embedding_model="doubao-embedding-vision"))

# ② 最慳：托管 RAG 唔配 rerank（服務端食晒，零自建）
kb_cheap = KnowledgeBase(backend="context_search", top_k=5, index="docs")

# ③ 要 metadata 過濾（多租戶）：向量後端 + 帶 metadata 嘅 doc
kb_mt = KnowledgeBase(backend="opensearch", top_k=10, index="tenant-a")
kb_mt.add(..., metadata={"tenant": "a", "date": "2026-08"})
```

> 後端揀法、成本放大器（embedding 定「服務端」）詳見 **`veadk-agentkit-vector-cache.md`**；評估點做睇 **`veadk-agentkit-performance.md`**；CRAG 嘅內容安全可接 **`veadk-agentkit-rbac-observability.md`**（Guardrail/Input-Output Filter）。

---

## 6. 避雷 + 成本意識

> ⚠️ **避雷七連**：
> 1. **一律開最靚架構**＝燒錢又慢。由 Naive 開始 + eval 量度。
> 2. **唔識分「檢錯」同「排矇」**：漏就要改檢索/chunk，排位唔啱先改 rerank。
> 3. **rerank 記唔住會計錢**：50 對 = 50 次 forward。先試 RRF（免費），再諗 cross-encoder。
> 4. **Graph RAG 建置貴**：關係題先值。普通 FAQ 唔好。
> 5. **Agentic 唔設上限**＝無限 loop 燒 token。一定要設 hop 上限 + 每跳有 ground truth 驗。
> 6. **CRAG 評分器啡晒**：評分器用最平 model／分數 threshold，唔好一嚟用大 model。
> 7. **Hybrid 唔用 RRF**：直接加權平均分 → 量綱唔同、唔穩。
>
> 🪙 **慳錢 key**：固定 prompt 前綴（system + 工具描述）排頭 → 命中 provider/framework 上下文緩存（隱式 ~20%、可達 50–95%）→ 大 query 量成本跌一大截，見 **`veadk-agentkit-cache-management.md`**。

---

## 7. 資料來源

| 來源 | URL | 日期 |
|---|---|---|
| RAG 架構對比（Naive/Advanced/Modular/Graph/Hybrid 基礎） | `references/veadk-agentkit-ai-concepts.md` §1/§3（內部概念） | 2026 |
| Correction RAG（CRAG）學術｜Self-RAG 學術 | arXiv 2301.13597 / 2310.11511 | 2024 |
| RAPTOR（遞歸樹/總結） | arXiv 2401.18059 | 2024 |
| HyDE（hypothetical document embeddings） | arXiv 2212.10496 | 2023 |
| ColBERT（late-interaction） | arXiv 2004.12832 | 2020 |
| RRF（Reciprocal Rank Fusion，`k≈60`） | Cormack et al. SIGIR 2009 | 2009 |
| Agentic RAG 工程實務（routing/rewrite/multi-hop/self-assess） | 業界 practice 綜合（2025–2026） | 2026 |
| VeADK KnowledgeBase/Ranker + embedding_model | `references/veadk-agentkit-vector-cache.md`（記憶/知識庫 tab） | 2026 |
| 成本／AFP（精排計費、context cache） | `references/veadk-agentkit-pricing.md` + `veadk-agentkit-cache-management.md` | 2026 |

> **免責**：個別架構（Agentic/CRAG/Self-RAG/RAPTOR）為學術 + 業界 practice 綜合，唔係 BytePlus 官方術語；VeADK 內建係「托管 RAG + Ranker + agent 工具」層。定價同功能引用前 check 一遍最新文檔。

---

*Last audit date: 2026-08-17 · RAG 架構術語同方舟產品功能會隨迭代而變（尤其 `Ranker`/`context_search`），引用前 check 一遍。*