# VeADK + AgentKit Cache 管理（類型）— 五類 cache 點慳、邊個控制

呢一份係「**Cache 管理（類型）**」tab：唔講 GPU 揀機、唔講 vector backend，**淨係將成個 cache 世界一次過 catalogue**——由 framework/provider 計費層一路落到 engine/GPU VRAM 層，逐類拆開：**暫存咩、喺邊層、邊個控制、慳咩、點量度、點優化**。

呢份係「分拆」出嚟嘅 cache 內容，收集自：`veadk-agentkit-hardware.md` §5–§7、`veadk-agentkit-vector-cache.md`、`veadk-agentkit-ai-concepts.md` §4、`veadk-agentkit-serving-kit.md`，再補返 **Volcengine 方舟隱式 cache** 同 **output_schema 自動關緩存** 兩個計費特性。

> **核心心法**：
> 1. **cache 唔係一個，係一梯**：token/response（計費）→ input/prefix（引擎）→ memory/KV（GPU VRAM）→ 隱式（方舟計費）→ output_schema（開關）。**層層唔同，慳法同槓桿都唔同**。
> 2. **喺托管（AgentKit + 方舟）你真正直接控制嘅得 framework 層**（Responses 緩存 + prompt 排位 + compaction）；引擎/KV 層你係「間接影響」，GPU 層你完全唔使掂。
> 3. **慳錢係蝴蝶效應**：你 prompt 排得靚 → prefix 命中 → 引擎唔重算 → KV 需求降 → VRAM 壓力細 → 平台成本降（正正解釋 128k+ 加倍率）。**由 framework 層開始。**

---

## 0. KV Cache 底層——點解要 cache（先讀呢節）

> 講 cache，要由最底層開始：**LLM 推理引擎點解非 cache 唔可，係由「自注意力矩陣計算」推到「硬體瓶頸」推到「OS 級記憶體抽象」**。SOSP 2023 嘅 vLLM（PagedAttention）同 LMSYS 嘅 SGLang（RadixAttention）就係喺呢兩個位嘅架構突破——**先識點解，先真正用得慳。**

### 0.1 咩係 KV Cache？

**Attention 原生計算**：標準 Transformer decoder 計 Attention 嘅核心公式係

```
Attention(Q, K, V) = softmax( Q · Kᵀ / √d_k ) · V
```

在 autoregressive 生成，模型係**逐 token 生成**嘅。假設生成緊第 `t` 個 token：

- 當前只需要第 `t` 個 token 嘅 Query 向量（`q_t`）同過去**所有歷史 token**（`1…t`）嘅 Key（`K`）同 Value（`V`）做 attention 打分。
- 歷史 token（`1…t−1`）嘅權重喺推理時已凍結 → 佢哋喺各層計出嚟嘅 `K`、`V` **完全唔變**。
- 若唔 cache，生成第 `t` 個 token 就要由第 1 個 token 重新做一次前向傳播（`O(t²)` 冗餘計算）。
- 所以將**每層歷史嘅 `K`、`V` 存喺 GPU 顯存**，每步只需計當前 token 嘅 `q_t / k_t / v_t`，並將 `k_t / v_t` 追加落 cache，計算量即刻變 `O(t)`。

**KV Cache 代價：顯存黑洞 + Memory-Bound**。KV Cache 顯存公式：

```
Size = 2 × layers × kv_heads × head_dim × seq_len × precision_bytes
```

以 **LLaMA-3-70B**（80 層、8 個 KV head、head_dim 128、FP16=2 bytes）為例，**單個並發 request 喺 8k 長度就要約 2.6 GB**；64 個並發 request 淨係 KV Cache 就佔 **166 GB** HBM。LLM 推理仲分兩個截然不同階段：

| 階段 | 做咩 | 瓶頸 |
|---|---|---|
| **Prefill（首字 / prefill）** | 成段 prompt 並行矩陣乘 | **Compute-Bound（算力受限）** |
| **Decode（逐字）** | 每次只讀寫少量 token，但要將成個大模型權重 + 全量 KV Cache 搬去暫存器 | **Memory-Bound（記憶體頻寬受限）** |

> 🎯 一句記住：**cache 唔係「揀嘅」，係「冇得唔 cache」**——唔 cache 就 `O(t²)` 重算；cache 咗就食爆 VRAM + 撞 memory-bound。成個 cache 管理世界就係同呢兩條死線搏。

### 0.2 早期傳統 Serving 嘅痛點

喺專用推理系統出現前（原始 HuggingFace / 早期 FasterTransformer），KV Cache 管理極原始、以**靜態連續分配**（Contiguous Buffer）為主：

- **靜態連續顯存分配**：系統唔知用戶會生成幾多個 token，只能**以模型最大長度（如 2048 / 4096）預先喺 GPU 申請一大嚿連續記憶體**。
- **嚴重記憶體浪費（超過 60%–80% 顯存虛耗）**：
  - **內部碎片（Internal Fragmentation）**：預留 4k 長度，但用戶講 200 字就停 → 大半空著。
  - **預留浪費（Reservation Waste）**：解碼未生成嘅 token 空間都要提前霸咗。
  - **外部碎片（External Fragmentation）**：唔同長度請求頻繁申請/釋放**連續**記憶體 → 顯存千瘡百孔 → 大請求分配唔到。

> ⚠️ 呢 60–80% 浪費，正正係上文 `cache tab` 一直講「KV 食 VRAM 爆燈」嘅源頭——**唔係模型大，係 cache 管理原始**。

### 0.3 vLLM 嘅突破——PagedAttention（OS 式分頁）

UC Berkeley 團隊喺 **SOSP 2023** 提出 **vLLM + PagedAttention**（詳見 §3.1）：

> **核心思想：借鑒作業系統虛擬記憶體分頁（Paging）**
> - 將 KV Cache 切做固定大小區塊（**KV Blocks / Pages**，例如每塊 16 / 32 token）。
> - 喺硬體層面，呢啲 block **唔需要連續**放喺 GPU，而係透過一張**邏輯→物理映射表**（Block Table）動態定址。
> - 專門手寫 CUDA Kernel（PagedAttention），計 attention 時按 Block Table **跳躍讀取分散嘅顯存區塊**。

```text
[ 邏輯 Block Table ]                    [ 物理 GPU 顯存 (非連續) ]
Logical Block 0 (Token 0~15)   ──映射──►  Physical Block #7
Logical Block 1 (Token 16~31)  ──映射──►  Physical Block #2
Logical Block 2 (Token 32~47)  ──映射──►  Physical Block #19
```

**價值與突破**：

- **消滅碎片**：顯存浪費率由 ~70% 降至 **<4%**，GPU 可塞 2–4× 並發 batch → 吞吐大升。
- **寫時複製（Copy-on-Write）**：多 request 共享前綴（Beam Search / Parallel Sampling）可共享底層同一物理 block，直到要寫新 token 先觸發複製。

### 0.4 SGLang 嘅突破——RadixAttention（樹狀前綴複用）

vLLM 解決了「**單一 request 內**」嘅碎片；但現代 **Agent 應用充斥跨 request 前綴共用**（多輪對話、system prompt 重複、few-shot、ToT 分支）。每次新 request，傳統系統都將相同 prompt 重跑一次 prefill。LMSYS **SGLang** 用 **RadixAttention（基數樹自動前綴快取）** 解決（詳見 §3.2）：

```text
               [ Root ]
                  │
    "You are a helpful assistant..." (共用 System Prompt)
                  │
         ┌────────┴────────┐
         │                 │
    (用戶 A: 對話輪次 1)    (用戶 B: 對話輪次 1)
         │                 │
    (用戶 A: 對話輪次 2)    (用戶 B: 對話輪次 2)
```

- **將 KV Cache 管理結構化成 Radix Tree（基數樹 / 壓縮字典樹）**：每個節點 = 一段連續 token 嘅 KV Cache。
- **自動發現與複用（Zero-Config Prefix Caching）**：新 request 拎 token 序列走訪樹狀節點，凡匹配到嘅前綴節點**直接攞現成 KV 跳過 prefill**；只有未匹配嘅分歧尾綴先要 prefill。
- **統一快取 + 逐出策略**：顯存滿 → 樹扮 LRU 快取池，優先逐出**葉節點**（引用計數 0 + 最久未訪問），**保留高頻公共前綴**（system prompt）。
- **價值**：多輪對話 / agent 工具鏈工作負載下，**TTFT（首字延遲）降數倍**，慳好多 prefill 算力。

### 0.5 xLLM 及其他新一代快取管理

除 vLLM / SGLang，業界對 KV Cache 有好多工程探索（詳見 §3.5 / §4）：

- **xLLM / 自研推理核心（分層架構優化）**：大型雲端廠商（位元組、阿里等）自研引擎針對自家硬體/架構客製：
  - **PD 分離（Prefill-Decode Disaggregation）**：Prefill 節點打滿算力計首字，之後用高速 **RDMA** 將 KV Cache 直接送到專責逐字輸出嘅 Decode 節點——**解決兩者對算力/頻寬需求唔同引起嘅資源競爭**。
- **Hierarchical Cache（層級快取：GPU HBM → Host RAM → NVMe SSD）**：GPU 滿唔直接丟，非同步將唔活躍 context **Swap-out** 去主機 RAM 甚至 NVMe SSD（DeepSpeed-FastGen / vLLM Chunked Swap），新 request 再換入。
- **壓縮與量化（KV Cache Quantization & Pruning）**：
  - **FP8 / INT4 量化**：K/V 由 FP16/BF16 壓至 INT4/INT8/FP8 → KV 佔用降至 **1/2～1/4** → batch 成倍升。
  - **稀疏 KV（StreamingLLM / H2O）**：長文推理只留 attention 權重極高嘅「Heavy Hitters」+ 最開頭嘅 **Sink Tokens**，中間唔常駐——**用固定長度換無限上下文**。

### 0.6 主流架構橫向對比

| 維度 | 原始連續分配（Naive） | vLLM（PagedAttention） | SGLang（RadixAttention） |
| :--- | :--- | :--- | :--- |
| **底層資料結構** | 靜態連續 Tensor | 邏輯–物理分頁映射表（Block Table） | 動態基數樹（Radix Tree） |
| **顯存碎片控制** | 極差（60%–80% 碎片浪費） | 極佳（<4%） | 極佳（繼承分頁 + 動態管理） |
| **前綴快取機制** | 無 | 後期引入 Hash-based APC（Hash 比對） | **原生樹狀檢索**（自動匹配任意長度公共前綴） |
| **最擅長業務場景** | 單次短文本基準測試 | 通用高吞吐批量離線推理 | **複雜 Agent 工作流、多輪對話、結構化輸出** |

> 💡 呢三行就係成個 docs 一直講「**vLLM = 高吞吐 batch、SGLang = prefix 重嘅 agentic**」嘅根——由 block 對齊（vLLM）vs token 粒度樹狀（SGLang）分化出嚟。托管方舟收埋引擎（xLLM 主打），你真實要知嘅係：**任何引擎都要 stable prefix 先行到 cache**（§6）。

---

## 1. Cache 類型總覽（一張地圖）— 5 類表

一次過睇晒成個 cache 世界有幾種「cache」，各屬邊層：

| 類 | 暫存咩 | 層 | 你控制 | 慳咩 |
|---|---|---|---|---|
| **① Token / Response cache** | 已計過、唔使重計嘅 prompt token（同 session 前綴） | provider 計費 / framework（Responses API 上下文緩存） | ✅ 直接（默認開、`output_schema` 會關） | **慳 token 錢**（命中率 50–95%） |
| **② Input / Prefix cache** | 相同 prompt **前綴**嘅 KV（system、tool schema） | 引擎層（vLLM PagedAttention / SGLang RadixAttention / 本地 llama.cpp 另計） | ⚠️ 間接（prompt 排位） | **慳 prefill（唔使重算）** |
| **③ Memory / KV cache** | Decode 期間嘅 Key/Value | GPU VRAM | ❌ 托管；自建可 GQA/量化/streaming | **慳 VRAM / 並行** |
| **④ 隱式 cache** | cached input ≈ 標準價 **~20%**，自動、不可關 | Volcengine / 方舟計費特性 | ❌ 自動（冇得控制） | **慳計費**（方舟 implicit cache 概念） |
| **⑤ output_schema 自動關緩存** | 設 `output_schema` → 同緩存機制衝突 → **自動關 context cache** | framework / Responses API | ✅（你自己選擇「準 vs 慳」） | 取捨：**畀準度、冇咗慳錢** |

> **一句分清**：「①②③ 係『點慳油』（慳算力/慳錢），④ 係平台自動送嘅折扣，⑤ 係一個你會唔小心跌入嘅『陷阱開關』。三層唔好撈亂——sales 講『cache』要講得清係邊一層。」

---

## 2. Token / Response Cache（框架層，直接控制）— usage_metadata、命中率 50–95%

**暫存咩**：已送過、唔使重計嘅 prompt token（同 session 前綴）。**屬於 provider 計費層 + framework 層**——你喺呢層係**直接控制**。

- VeADK Responses API 模式 **默認開** session 上下文緩存；每輪 `usage_metadata` 有 `cached_content_token_count` / `prompt_token_count`。
- **機制**：平台記憶已送過嘅 prompt 前綴；下輪 request 只送「新增部分」+ cache token 平價/半價計。多輪對話 + 複雜工具調用 → 重複 token 明顯減少 → **慳 AFP**。
- **命中率高 = 慳 token 錢**。

**睇命中率**（每輪 response event 嘅 `usage_metadata`）：

```
cached_content_token_count   # 命中緩存嘅 token 數
prompt_token_count           # 當前輸入總 token 數
命中率 = cached / prompt
```

**目標**：多輪對話理想 **50–95%**；低過 50% → 檢查係咪每輪塞咗大 object（例如成個 file 入 tool return）。

**你控制嘅（§6 詳述）：**
- 唔好每輪塞大 file / 大 tool return 入 context。
- `output_schema` 會**自動關緩存**（取捨「準確 vs 慳」，見 §5）。
- 動態嘢放 prompt 後面；system 前綴保持穩定（見 §7 蝴蝶鏈）。

> **Sale 一句**：「token cache 係『同樣一批鐵，你點樣唔使重跑』——呢個先係你方案度日日見錢嘅位。命中率 50–95%，認清佢先算慳到。」

---

## 3. Input / Prefix Cache（引擎層，間接控制）— RadixAttention / prefix tree / cache-aware prompting

**暫存咩**：相同 prompt 前綴（system prompt、tool schemas）嘅 **KV**。**屬於引擎層**，你係**間接控制**。

> 💡 **先分清楚四大引擎 paradigm**：**vLLM / SGLang / llama.cpp / xLLM** 代表現代 LLM 推理主流路線——**vLLM = 企業級高吞吐 serving、SGLang = prefix 重嘅 agentic 執行、llama.cpp = 邊緣 / 消費級便攜部署、xLLM = BytePlus 自研企業級（PD 分離 + MoE）**。各自嘅 KV-cache 策略完全不同，下面 §3.1–3.5 逐個拆，§3.6 一表睇晒。

- **引擎 prefix caching**：**SGLang RadixAttention** 用**前綴樹**自動複用**任何共享 prefix**；vLLM **PagedAttention / Automatic Prefix Caching** 把 KV cache 拆頁按需分配、hash 對齊複用；llama.cpp（本地線）就靠 slot 制 cache + disk 快照；**xLLM（BytePlus）用 xTensor「邏輯連續 / 物理離散」+ global KV 管理**。
- **呢層命中 = 引擎唔重算 = 平台成本降**（慳 prefill，減 TTFT）。
- **你嘅槓桿 = cache-aware prompting（stand嘢唔好亂郁）**：

### 3.1 vLLM 深入（PagedAttention + Automatic Prefix Caching）

**邊樣嘢**：vLLM 係開源高吞吐推理引擎（企業級 serving 代表，BytePlus ServingKit / 方舟底下常用）。設計起點：傳統推理 **60–80% GPU memory 嘥咗喺 KV cache 嘅內部／外部碎片**——所以佢成個核心係「點樣把碎片化嘅 VRAM 用到盡」：

| vLLM 機制 | 做咩 | 同 cache 嘅關係 |
|---|---|---|
| **PagedAttention** | KV cache 拆做 block 分頁，按需分配（似 OS 虛擬記憶體） | **慳碎片 + 提高 batch 吞吐**；唔係「唔重算」 |
| **Automatic Prefix Caching** | 每個 KV block 記住 prefix hash；request 入嚟先查有冇 hash 相同嘅 blocks → 直接複用 | **慳 prefill**：相同系統 prompt / 工具 schema 唔使重算 |
| **Chunked Prefill** | 長 prefill 拆開同 decode 混跑 | 降低長 request 霸住 GPU 嘅問題 |
| **Copy-on-Write（CoW）** | parallel sampling（beam search、`n>1`）嘅 sibling 路徑共享同一批 physical prompt block，岔開先複製 | 慳 multi-sample 嘅重複 KV |

**詳細 lifecycle**：

1. **動態接手 + 調度**：request 入 async engine，**唔係 request 層 batch，係 iteration 層 batch**（continuous batching）——prefill request 同 active decode 喺同一執行 cycle 交錯跑。
2. **分頁分配**：引擎當 VRAM 係 OS 虛擬記憶體。每條 sequence 嘅 KV cache 斬做**固定邏輯 block**（通常 16 / 32 token），token 一路出，`BlockAllocator` 一路**非連續**派 physical frame。
3. **PagedAttention 執行**：標準 MHA kernel 要連續記憶體，vLLM 用客製 GPU kernel（CUDA / Triton）直接收一條 **page table**（block pointer 陣列），generate 期間**就地 gather 跨碎片嘅 K/V**、零 memory copy。
4. **釋放 / Forking**：并行 sampling 用 **CoW**——sibling 路徑共享前段 physical prompt block，出到分歧 token 先分支複製。

**命中條件（關鍵）**：vLLM prefix cache 以 **block 為單位**（例如 16 token / block），命中要 **前綴完全一致 + 對齊 block 邊界**。所以：

- system prompt / tool schema **喺頭上、一字唔改先命中**；
- 中間加咗個 timestamp / session id → 之後全部 miss；
- 長度唔到一個 block（<16 token）嘅共享尾巴命中唔到。

### 3.2 SGLang 深入（RadixAttention — 前綴樹複用嘅鼻祖）

**邊樣嘢**：SGLang 主打複雜 agentic workflow（多輪對話、RAG 共享 system prompt、多 agent、constrained decoding）——**prefix 重**嘅執行場景。佢嘅 `RadixAttention` 用 **radix tree（前綴樹）** 管理 KV cache：

| SGLang 機制 | 做咩 | 同 vLLM 分別 |
|---|---|---|
| **RadixAttention** | 所有 request 嘅 prefix 記喺一棵樹度，**任何共享前綴自動複用**，唔淨係 block 邊界整齊先得 | **token 粒度**命中，唔使對齊 block（vLLM 要） |
| **LRU / weighted eviction** | cache 滿就剪走唔常用嘅 leaf，**保留 common root**（system / tool schema） | 唔係成棵清，root 長命 |
| **多輪 session reuse** | 同一會話唔使重傳歷史，直接複用舊 KV | 多輪對話慳晒 prefill |
| **Compressed grammar FSM** | regex 編譯成跳轉 FSM 喺 GPU 直接 mask invalid token | 結構化輸出零 Python 折返 |

**詳細 lifecycle**：

1. **Radix tree lookup**：SGLang 喺 **CPU host memory** 維持一棵 global radix tree（compressed trie），索引緊 GPU memory 上所有 KV block。prompt 入嚟 → scheduler 沿樹搵**最長匹配 prefix**。
2. **Zero-prefill 複用**：如果 token 0–2048（例如共享 system prompt + 注入 context）已經喺樹度，直接複用佢哋嘅 KV，**跳過嗰啲 token 嘅矩陣運算** → TTFT 大降。
3. **Chunked 執行 + 快 decode**：淨係 prefill 分歧嗰段 tail（例如新 user 問題）。配 EAGLE 等優化嘅 spec-decode + 加速結構化輸出。
4. **逐葉 eviction**：GPU memory 到 watermarks，**唔係成條 request 清走**，係 **LRU tree eviction** 剪 leaf 節點、留住 common root（例如常駐 system instruction / tool schema）。

**強項場景**：長 system prompt + 好多 request 共享 + 長 context 多輪——SGLang 喺綁幾多前綴 reuse 上出名準。

### 3.3 vLLM vs SGLang — prefix cache 高手對決

| | vLLM | SGLang |
|---|---|---|
| **KV 核心** | PagedAttention（分頁） | RadixAttention（radix 樹） |
| **prefix 複用粒度** | block 級（要對齊） | token 級（樹狀，靈活） |
| **多輪 reuse** | 有（automatic prefix caching） | 有（+ session 層更徹底） |
| **適合一啲** | 高吞吐、並行 request 多、主流兼容廣 | 長 context、低延遲、prefix 高度共享 |
| **托管你睇唔睇到** | 方舟/ServingKit 底下，你唔使選 | 方舟/ServingKit 底下，你唔使選 |

> 🎯 **托管結論**：方舟 / BytePlus ServingKit 底下你**揀唔到引擎都冇需揀**——但要知道**兩種引擎都要「穩定 prefix」先行到 cache**。所以無論用邊個，最抵嘅動作都係 **system/tool schema 穩定放頭、動態嘢推後**（下面張表）。

**你嘅槓桿 = cache-aware prompting（stand嘢唔好亂郁）**：

| 動作 | 點解 |
|---|---|
| **System / instruction 穩定** | system 部分 = 緩存區，穩定先命中 |
| **動態內容放 prompt 後面** | 前面變 = 成個 prefix miss |
| **首段放「永不變嘅」** | tool schema 唔好每輪改、唔好加 session id/timestamp 落 prefix |
| 唔好每次 run 都重放成串歷史 | 靠 session cache / compaction |
| 結構化需求少用 `output_schema` | `output_schema` 會關緩存（要權衡） |

> 爛鬼例子：system prompt 每輪加 timestamp / session id → prefix 唔同 → KV-cache 唔會 hit → 每次都重新計算。

> ⚠️ **托管方案你唔會親眼見到 prefix cache**，但 `usage_metadata` 嘅 cached count 就係呢層嘅「影子」。

### 3.4 llama.cpp 深入（GGUF + 混合 CPU/GPU 邊緣推理）

**邊樣嘢**：llama.cpp 係 **pure C/C++、零依賴** 嘅推理框架（底層 `ggml`），主打硬件多樣性 + 量化——代表**便攜 / 邊緣 / 消費級**嗰條線。呢層引擎睇落咁「basic」，但對 cache 一樣有自己打法：

| llama.cpp 機制 | 做咩 | 同 vLLM / SGLang 分別 |
|---|---|---|
| **GGUF `mmap` 直讀** | 模型封入 GGUF（k-quants / IQ-quants / Q4_K_M 等 block 量化），支援直接 memory-mapping 載入 | 秒級載入、host RAM 需求極低；「節儉」主力喺**權重量化**，唔係 KV 管理 |
| **KV cache：static contiguous / ring-buffer** | 傳統上一條固定連續 KV buffer，長度跟 `-c`；支援 ring-buffer shifting 做無限生成；slot 制 sequence context 做細規模 batch | 冇 PagedAttention 咁細致嘅分頁，靠「預霸 + 移位」 |
| **`cache_prompt`（prefix 複用）** | llama-server 同一 slot 下，新 request 攞共用前綴 → 淨係 prefill 唔同尾段（default true，前綴一致先得） | 唔似 SGLang 樹狀；只認頭段 prefix |
| **`--cache-reuse N`** | 就算共享片段唔喺最前（例如 RAG 中段 document），只要 ≥N token 對得上，都用 KV shifting 複用（default 0 = off） | vLLM/SGLang 冇嘅「中段移位複用」；落地建議 256 |
| **`--prompt-cache` / `--slot-save-path`** | 將 prompt state / slot KV 存去 disk，server 重開都慳返 prefill | 「cache 落 disk」——平台層冇呢招（平台係記憶體 + 計費） |
| **`-ngl / --n-gpu-layers` 混合計算** | 前 N 層 offload 落 GPU（Metal / CUDA / Vulkan / SYCL），其餘行 CPU（AVX-512 / NEON） | exec 期間用 `ggml` DAG build compute graph，**無 Python / heavy runtime 喺 loop** |

> ⚠️ **定位**：llama.cpp **唔係 ServingKit 引擎**——佢係「客自己喺 MacBook / Raspberry Pi / Jetson / Android 上跑」嘅線（見 §3.7）。托管方舟嘅「cache」喺平台層（§5），同呢個無關。但佢示範咗一件事：**cache 都可以係 disk 上嘅嘢**，唔淨係 GPU VRAM。

### 3.5 xLLM 深入（BytePlus 自研 — PD 分離 + 邏輯連續 / 物理離散 KV）

**邊樣嘢**：**xLLM** 係 **BytePlus / ModelArk 全自研**嘅企業級推理框架（ServingKit 主打引擎），刻意同 vLLM / SGLang 呢啲開源引擎「同台但自家牌」。核心係 **service / engine 解耦** + **PD / EPD 分離**，主打大規模 MoE（DeepSeek 級）部署：

| xLLM 機制 | 做咩 | 同 vLLM / SGLang 分別 |
|---|---|---|
| **xTensor 記憶管理（邏輯連續 / 物理離散）** | KV 用「logically contiguous, physically discrete」結構：token produce 時按需派 physical page，並**預測下一 token 所需 page 提前 mapping**；request 完成後即刻重用 | 同 PagedAttention 一樣唔要連續 VRAM，但加咗「前瞻 mapping + 即時重用」，碎片衝突更少 |
| **PD / EPD 分離** | Prefill(_Encode)-Decode 拆做獨立 instance 池，動態調度；multimodal 用 EPD 三段分離 | vLLM/SGLang 本身冇內建 PD 分離（要自己砌）；ServingKit 係用「xLLM = PD 分離開箱即用」賣點 |
| **Global KV Cache 管理（分佈式）** | 分佈式架構提供**global KV cache 管理**，跨 instance 高效用 AI accelerator 記憶體 | D-KV（disaggregated KV）同族——KV 唔黐死喺某張卡 |
| **Multi-layer pipeline（異步排程疊算）** | CPU 排程同 accelerator 運算重疊（CPU 預排下批、placeholder 佔位）、MoE dispatch/combine 同 compute 用 dual-stream 重疊 | 主打「滅 computational bubble」——唔單止 batch 得滿，係排程疊到滿 |
| **Adaptive graph mode** | 細 kernel 自動 fuse 成單一 compute graph 一次 dispatch；多 graph caching 慳 compile | 減 kernel launch overhead，動態長度都 keep |
| **Speculative decoding + EPLB / DP 負載平衡** | 優化 spec-decode 一朝出多個 token；MoE 按 expert 歷史 load 動態平衡（EPLB） | 大 model 專用優化，唔係細引擎可以鬥 |

> ✅ **BytePlus 落點（呢個先係你要知嘅）**：方舟 / ServingKit 底下，**xLLM 就係「自家引擎」**。DeepSeek-R1 用 PD 分離部署，官方 benchmark 對開源版 SGLang **throughput 最高 +5×**（最低 2 台 Hopper 機起）；xLLM Technical Report 報 Qwen 系列 TPOT 相同下 throughput 達 **1.7× MindIE / 2.2× vLLM-Ascend**。對客嘅故事：**「你買 Agent Plan，個 server 唔止 batch + 分頁，仲係 BytePlus 自己 tune 到 PD 分離 + MoE 負載平衡嘅引擎」**。

### 3.6 四方對決 — vLLM vs SGLang vs llama.cpp vs xLLM（架構比較）

| 維度 | **vLLM** | **SGLang** | **llama.cpp** | **xLLM** |
|---|---|---|---|---|
| **核心定位** | 大型生產 serving：高吞吐、獨立 request 大流量 | 複雜 agentic workflow + 多輪 + 高 prefix 共享 | 便攜性 + 本地 / 邊緣部署，量化到盡 | **BytePlus 企業級 serving：PD 分離開箱即用、大規模 MoE** |
| **核心創新** | PagedAttention（OS 式分頁） | RadixAttention（樹狀 prefix 複用） | GGUF 量化 + 混合 CPU/GPU 計算 | **xTensor DMA + PD/EPD 分離 + EPLB** |
| **KV cache 策略** | 動態 block 分頁分配 | 跨所有 request 嘅 radix tree | ring-buffer / 預分配 sequence slot（可落 disk） | **邏輯連續 / 物理離散 + 前瞻 mapping + global KV 管理** |
| **Batching 機制** | Continuous（iteration 層）batching | Cache-aware continuous batching | Continuous batching（server 模式，較細規模） | Continuous + **multi-layer 異步排程疊算** |
| **量化類型** | AWQ / GPTQ / FP8 / INT8 / Marlin | FP8 / AWQ / GPTQ / BitsAndBytes | **GGUF K-quants（Q2_K–Q8_0）+ IQ quants + EXL2** | FP8 為主（ByteDance 生態，MoE 優化） |
| **硬件 target** | 數據中心 GPU（NVIDIA/AMD）、TPU、Gaudi | 數據中心 GPU（NVIDIA/AMD） | Apple Silicon、CPU（x86/ARM）、消費級 GPU | 數據中心 GPU（**NVIDIA Hopper 起**，PD 分離要 ≥2 台）、國產加速器 |
| **Codebase** | Python + CUDA / C++ / Triton | Python + CUDA / C++ / Triton | **Pure C/C++（零外部依賴）** | C/C++（scale 獨立 repository） |
| **結構化輸出** | Outlines / Guided Decoding | Native FSM jump-forward grammar | GBNF Grammars（C++ 直接評估） | 同 SGLang 兼容（托管環境你唔經手） |
| **BytePlus 落點** | 方舟/ServingKit 收埋，你唔使選 | 方舟/ServingKit 收埋，你唔使選 | 自建本地 / edge；唔喺 ServingKit | **方舟/ServingKit 自研主打引擎（PD 分離賣點）** |

> 🎯 **托管結論（重申）**：方舟底下引擎 **收埋咗，你唔使揀**——而 BytePlus 自家主打嘅係 **xLLM**（PD 分離 + MoE 優化）；vLLM / SGLang 同場做兼容。llama.cpp 係另一條客自己跑嘅線。無論邊個引擎，cache 都要 **stable prefix** 先行到（§3.3 張表照用）。你唯一真正直接控制嘅依然係 **prompt 排位 + `usage_metadata`**。

### 3.7 揀邊個（**僅自建 / 本地先啱用**；托管方舟包辦）

| 場景 | 揀 | 點解 |
|---|---|---|
| 獨立 request 嘅 API serving（企業 ChatGPT wrapper）、要 K8s 標準編排（KServe / Helm）+ 深度 metrics（Prometheus / OTel） | **vLLM** | iteration 層連續 batching、並發 c>30 時 token throughput 係維度；生態最熟 |
| 多 agent + tool calling（plan-and-solve / ReAct / AutoGen），**70%+ context** 係重複歷史 / system / tool 描述 | **SGLang** | radix tree 一次算、全家共享；多輪 + 結構化輸出最順 |
| 高 prefix-share RAG：好多人 query 同一篇 10k-token 大 document | **SGLang** | document 嘅 KV 一次計，之後所有並發 query 攞同一份 |
| 嚴格 JSON 抽取 pipeline（高吞吐、複雜 schema） | **SGLang** | regex FSM masking，無 Python 折返樽頸 |
| **BytePlus / 方舟托管大規模（DeepSeek / MoE、PD 分離、要開箱即用）** | **xLLM（方舟包辦）** | 自家引擎：PD 分離開箱即用、EPLB MoE 負載平衡；你只需知「佢喺後面」 |
| 消費級硬件（MacBook Unified Memory / 冇 VRAM 嘅 PC） | **llama.cpp** | Metal / 混合計算，放唔落全精度 model 都跑到 |
| Edge / 嵌入式（Raspberry Pi、Jetson、Android、機械人） | **llama.cpp** | 超輕量 C++ binary，無 Python runtime 依賴 |
| 70B 級大 model 要大縮先放得落（Q4_K_M / IQ3） | **llama.cpp** | 對高量化容忍度最高 |

> ⚠️ 記住：呢張表「揀引擎」只係**自建**先要諗；**托管方舟收埋引擎（主打 xLLM）**——你買 Agent Plan 已經打包晒「會自己 batch + 分頁 + spec-decode + PD 分離嘅 server」。**llama.cpp 係俾「想喺自己機度跑 demo / edge」嗰種客講嘅故事。**

---

## 4. Memory / KV Cache（GPU VRAM 層，托管唔使你管）— PagedAttention / GQA / KV quant / streaming

**暫存咩**：Decode 期間嘅 Key/Value（attention 中間值）。**屬於 GPU VRAM 層**，托管你**完全唔使管**；自建先要自己優化。

Transformer 每次出 token 都要留住之前嘅 **Key/Value** 做 attention——呢個 KV cache 係**長 context 嘅記憶體食電怪**，隨 **sequence 長度 + 並行 request 數**線性暴漲：

```
KV memory ≈ 2 (K+V) × num_layers × num_heads × head_dim × 2 bytes × tokens × concurrent requests
```

- **長 context + 高並行 = KV 食 VRAM 爆燈**（同權重大細差唔多，甚至更大）。例子：7B 模型、8k context、同時 100 request → KV 可以食幾 GB 到十幾 GB VRAM。
- **正正解釋 128k+ 加倍率**（見 pricing doc §「AFP 係數」）——長 context 唔止 prompt 計費貴，仲令引擎要更多 VRAM、平台要開更多卡。

**引擎層慳法**（自建先要你管；托管方舟自動掂）：

| 方法 | 原理 | 效果 |
|---|---|---|
| **GQA / MQA** | 多 query 頭共享少數 KV 頭 | KV 慳 **4–8×** |
| **KV quantization** | FP8/INT8 存 KV | 慳 ~2× |
| **PagedAttention / RadixAttention** | 分頁 / 前綴複用 | 慳碎片 / 唔重算 |
| **Streaming（H2O / SnapKV）** | 唔留全部 token | 長 context 大減（**精度 trade-off**） |
| **Context caching（provider）** | 同 prefix 複用 | 你慳 token 錢（框架層可見） |

> 🎯 **你嘅唯一間接影響 = context 短**：context 短 = 單 request KV 需求細 = 平台可以更多並行同價 pack = 平台可以更平而唔將成本轉嫁你。呢個先係你 review「context 唔應該咁長」背後嘅 infra story。

---

## 5. 隱式 Cache + output_schema（Volcengine 方舟特性）

### 5.1 方舟隱式 cache（implicit cache）— 平台自動送嘅折扣

方舟（Volcengine）喺計費層有一個**隱式 cache** 概念：**cached input ≈ 標準價嘅 ~20%**，**自動、不可關**（見 pricing/vendor 比較 doc）。呢個係平台自己幫你記低重複嘅 input 段，計費時自動打折——你**冇嘢要做、亦冇得控制**，純粹係「平台幫你慳」。

**cached input 到底係咩（計費層嘅「喺 cache 嗰啲 token」）**：

| 層 | 點樣叫做「cached」 | 你睇唔睇到 |
|---|---|---|
| **引擎層（§3）** | 引擎複用咗 prefix 嘅 KV（冇重算 prefill） | 托管睇唔到 |
| **計費層（呢節）** | 平台將重複 input 段標做 cached input → 按 ~20% 收 | usage_metadata 嘅 `cached_content_token_count` |
| **兩層嘅關係** | 引擎命中唔保證計費必定打折；計費打折通常嚟自「平台層面見到重複 input」 | — |

一句講晒：**「cached input」= 你 request 入面嗰啲「 platform 話『我見過呢舊嘢』而用平價收費嘅 input token」**。所以想睇「慳咗幾多」，唔好睇 sampler degree，睇**每次 response 嘅 `usage_metadata`**：

```
cached_content_token_count   # 被平台標做 cached → 平價收費嘅 token 數
prompt_token_count           # 加埋全部 input token
慳咗 = cached × (標準價 - 差別)
```

**點令 cached input 多（間接）**：都和上面 §3 一樣——**保持 prompt 前綴穩定**（system prompt / tool schema 唔好塞 timestamp、唔好亂改次序）。前綴愈穩定 → 平台見到重複 input 愈多 → 平價收費部分愈大。

> ⚠️ 呢啲係**估算數字**（~20% cached input 折扣、同命中率 50–95%），**唔係官方公開公式**。真錢以方舟計費頁 + 控制台「用量明細」為準——明確定價先睇 pricing doc 同方舟官方文檔。

### 5.2 隱式 cache vs 框架層 cache — 唔好撈亂

| | 隱式 cache（方舟計費） | Framework/Token cache（Responses API） |
|---|---|---|
| 邊度 | Volcengine 計費引擎 | VeADK / 框架 + provider 側 |
| 你控制 | ❌ 自動、不可關 | ✅ 默認開、可關（§5.3） |
| Rate | ~20%（估算） | 命中率 50–95%、平價/半價計 |
| 用法 | 唔使諗 | 靠 `usage_metadata` + prompt 排位（§6） |

### 5.3 output_schema 自動關緩存 — 準 vs 慳嘅取捨

設咗 `output_schema`（指定輸出 JSON schema）就同緩存機制**衝突**，VeADK **自動關閉上下文緩存**。

- **VS**：framework 緩存（§2）同 provider prefix cache（§3）都可能受影響——所以要結構化抽取就**預咗冇咗緩存慳錢**。
- **幾時用邊個**：

| 場景 | 開 / 關 |
|---|---|
| 多輪客服、長 prompt、工具多 | ✅ 開緩存（默認） |
| 要 `output_schema` 強制結構 | ⚠️ 自動關——衡量「準 vs 慳」 |
| 每輪 context 都唔同（一次性） | 開咗都冇命中，無損失 |
| 一定要合 JSON schema | 犧牲 cache（`output_schema`） |

> 💡 替代：如果要結構化又想慳 cache，可考慮 **engine 級 constrained decoding**（SGLang 強項，見 serving/inference tab）、`JSON mode` 或 `function calling`——睇返 AI concepts §2 兩條路線嘅取捨。

---

## 6. Cache 命中實務（點睇 + 點優化）

### 6.1 點睇命中

每輪用 `usage_metadata` 度：

```python
u = response.usage_metadata
print(f"prefix cache: {u.cached_content_token_count}/{u.prompt_token_count} (目標 50–95%)")
```

`cached_content_token_count` = 命中緩存 token；`prompt_token_count` = 實際送 model；命中率 = cached / prompt。

**低命中排查**：
- 低過 50% → 係咪每輪塞咗大 object（成個 file 入 tool return / 每次 run 重放成串歷史）？
- 檢查前綴係咪有 session id / timestamp / 每輪都改嘅 tool schema → 成個 prefix miss。

### 6.2 點優化（prompt 排位規則）

| 規則 | 點解 |
|---|---|
| **system 前綴穩定** | system 部分 = 緩存區，穩定先命中 |
| **動態嘢放 prompt 後面** | 前面變 = 成個 prefix miss |
| **唔加 session id / timestamp 落 prefix** | 每輪唔同 → KV-cache 唔會 hit |
| **tool schema 唔好每輪改** | 改咗 = prefix 失效 |
| 唔好每輪塞大 object / 成串歷史 | 塞咗就強制重送 |
| 結構化需求少用 `output_schema` | `output_schema` 會關緩存（§5.3） |

> ✅ 正例：`system（永遠不變） → few-shot（少變） → RAG top_k（每次 ok，放中後） → 歷史（cache） → 今日輸入（最尾、動態）`。

---

## 7. 蝴蝶鏈（prompt 排位 → prefix hit → KV 需求降 → VRAM 降 → 成本降）

三層 cache 事實係**一條龍**，慳錢係蝴蝶效應：

```
prompt 排位靚（§6）
  → prefix/input cache 命中（§3，引擎唔重算、慳 prefill）
  → KV cache 需求降低（§4，VRAM 壓力細）
  → 平台可以更多並行 / 慳卡
  → 成本降（回應 128k+ 加倍率，見 pricing doc）
```

- **由 framework 層開始**：你 prompt 排得靚，先令下面成條 infra 鏈慳。
- **❌ 反面**：system prompt 每輪加 timestamp / session id → prefix 唔同 → KV-cache 唔會 hit → 每次都重新計算、全程冇慳。

> **決策橋**：context 管理（framework 層）→ KV cache（memory 層）→ GPU VRAM（硬件層）係條因果鏈。你 review 一個 agent「context 唔應該咁長」時，背後係幫緊成條 infra 鏈慳——**呢個先係 sales 可以講嘅 infra story**。

---

## 8. Cache 詞彙速查

| 詞 | 一句 |
|---|---|
| Token / Response cache | 唔使重計嘅 prompt token（計費層慳錢，命中 50–95%） |
| Prefix cache / Input cache | 相同 prompt 前綴嘅 KV 複用（引擎層，慳 prefill） |
| **cached input** | 計費層話「見過呢舊 input」→ 平價收費嗰啲 token（方舟 ~20%）；睇 `usage_metadata` |
| Memory / KV cache | Decode 期間 Keep 嘅 Key/Value（VRAM 層） |
| 隱式 cache | 方舟 cached input ≈ 標準價 ~20%、自動不可關（計費特性） |
| output_schema 自動關緩存 | 設 JSON schema → 自動關 context cache（準 vs 慳取捨） |
| GQA / MQA | 共享 KV 頭，慳 KV 記憶（4–8×） |
| KV quantization | KV 用 FP8/INT8 存，慳約 2× |
| PagedAttention | vLLM 分頁式 KV，慳碎片 |
| Copy-on-Write（CoW） | vLLM 平行 sampling 共享前段 block，岔開先抄 |
| RadixAttention | SGLang 前綴樹，自動複用共享 prefix |
| Streaming（H2O/SnapKV） | 唔留全部 token，長 context 大減（精度 trade-off） |
| llama.cpp | 純 C/C++ 本地推理庫（ggml），GGUF 量化 + 混合 CPU/GPU |
| GGUF / K-quants | llama.cpp 權重量化格式（Q4_K_M 等），RAM/VRAM 大減 |
| `cache_prompt` / `--cache-reuse` | llama-server prefix 複用 + 中段 chunk KV shifting |
| `--slot-save-path` | 將 slot KV 存 disk，重啟 server 都慳 prefill |
| KV 量化（q8_0） | llama.cpp `--cache-type-k/v`，KV 慳約一半 |
| Compressed grammar FSM | SGLang regex→GPU FSM，mask invalid token，結構化輸出零折返 |
| xLLM | BytePlus / ModelArk 自研企業級引擎，PD/EPD 分離 + MoE 優化 |
| xTensor | xLLM「邏輯連續 / 物理離散」KV 分配，前瞻 mapping + 即時重用 |
| PD / EPD 分離 | Prefill(_Encode)-Decode 拆 instance 池，動態調度，慳碎片 + 低 TTFT |
| Global KV cache | xLLM 分佈式 KV 管理，跨 instance 重用 accelerator 記憶體 |
| Cache-aware prompting | prompt 排位令命中率升（system 穩定、動態放後） |
| 命中率 | cached/prompt，目標 50–95% |
| 128k+ 加倍率 | 長 context 分段係數（≥128k 按 2×），見 pricing doc |
| usage_metadata | 每輪 cached/prompt token 計數，度命中用 |

---

## 9. 資料來源

| 來源 | URL | 日期 |
|---|---|---|
| Token / Input / Memory 三層 cache + 詞彙 | `references/veadk-agentkit-hardware.md` §5–§7（已合併） | 2026-08-15 |
| 上下文緩存 + compaction + usage_metadata + output_schema 衝突 | `references/veadk-agentkit-vector-cache.md` §4/§5 | 2026-08-13 |
| Cache 管理三層深入 + cache-aware prompting | `references/veadk-agentkit-ai-concepts.md` §4 | 2026-08-16 |
| KV-Cache（§0 底層 + §4）+ Prefix Caching / Batch 命中（§3） | `references/veadk-agentkit-hardware.md` §5（已合併） | 2026-08-13 |
| 方舟隱式 cache（cached input ≈ 標準價 ~20%） | `references/veadk-vendor-cost-comparison.md` §3.1 | 2026 |
| AFP 折算 / 128k+ 分段係數 | `references/veadk-agentkit-pricing.md` §3 | 2026-08-09 |
| Producer/Context caching + `usage_metadata` | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/agent/prompt-management | 頁面日 |
| VeADK 默認上下文緩存（Responses API） | `references/veadk-agentkit-uniqueness.md` §2.4 | 2026 |
| vLLM 官方（PagedAttention / prefix caching / KV quant） | https://docs.vllm.ai | 頁面日 |
| SGLang 官方（RadixAttention / prefix cache） | https://docs.sglang.ai | 頁面日 |
| vLLM vs SGLang blog（deepinfra） | https://deepinfra.com/blog/vllm-vs-sglang | 2026 |
| vLLM vs SGLang 2026（spheron，碎片 / PagedAttention） | https://www.spheron.network/blog/vllm-vs-sglang-2026 | 2026 |
| SGLang vs vLLM（atomic.chat，continuous batching） | https://atomic.chat/blog/llm-updates/sglang-vs-vllm | 2026 |
| SGLang vs vLLM comparison（localaimaster） | https://localaimaster.com/blog/sglang-vs-vllm-comparison | 2026 |
| vLLM vs SGLang（llm-academy） | https://llm-academy.dev/inference/vllm-vs-sglang/ | 2026 |
| vLLM vs SGLang（techsy，structured output） | https://techsy.io/en/blog/vllm-vs-sglang | 2026 |
| vLLM vs SGLang H100 benchmark（rawlinson） | https://rawlinson.ca/articles/vllm-vs-sglang-performance-benchmark-h100 | 2026 |
| llama.cpp 入門（learn.arm，GGUF / -ngl） | https://learn.arm.com/learning-paths/servers-and-cloud-computing/llama_cpp_streamline/2_llama.cpp_intro/ | 頁面日 |
| llama.cpp KV slot / ring-buffer（discussion 8860） | https://github.com/ggml-org/llama.cpp/discussions/8860 | 頁面日 |
| llama-server cache 機制（cache_prompt / --cache-reuse / slot-save） | https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md | 頁面日 |
| llama.cpp KV reuse（--cache-reuse 原理，PR 9866） | https://github.com/ggml-org/llama.cpp/pull/9866 | 2025 |
| **vLLM // 論文：Efficient Memory Management for LLM Serving with PagedAttention（SOSP 2023）** | https://arxiv.org/abs/2309.06180 | 2023 |
| KV Cache 原理 / 記憶體公式（cs.toronto CMADDIS） | https://cs.toronto.edu/~cmaddis/posts/self-attention-and-kv-cache | 頁面日 |
| KV Cache + 碎片 / PagedAttention 圖解（hamzaelshafie） | https://hamzaelshafie.bearblog.dev/the-caching-problem-of-llm-inference/ | 頁面日 |
| SGLang v0.4 RadixAttention 解析（siyingfeng） | https://siyingfeng.github.io/blog/RadixAttention | 2025 |
| SGLang Internals / RadixAttention（swyx system design） | https://llmsystem.github.io/2025_papers/sglang_internals.pdf | 頁面日 |
| **xLLM Technical Report（arXiv 2510.14686）** | https://arxiv.org/abs/2510.14686 | 2025-10 |
| **xLLM GitHub（OpenAtom / xLLM-AI）** | https://github.com/xLLM-AI/xllm | 頁面日 |
| **ServingKit 官方方案頁（xLLM 自研引擎）** | https://www.byteplus.com/en/solutions/ai-cloud-native-servingkit | 頁面日 |
| **vke ServingKit overview（xLLM PD 分離深部署）** | https://docs.byteplus.com/zh-CN/docs/vke/Servingkit_overview | 2026-07 |
| **veMLP xLLM PD 分離（vs vLLM / SGLang 對照）** | https://docs.byteplus.com/en/docs/mlp/veMLP_xLLM_Inference_Engine_PD_Separation_Deployment_for_Qwen_Model | 2026 |
| **xLLM PD 分離 DeepSeek-R1（吞吐 +5×）** | https://docs.byteplus.com/en/docs/mlp/MLPxLLM | 2026 |
| KV-Cache 量化（KV quant） | https://huggingface.co/docs/transformers/quantization | 頁面日 |
| GQA：Multi-Query Attention 變體 | https://arxiv.org/abs/2305.13245 | 2023 |

> **免責**：隱式 cache 折扣（~20% cached input）、命中率（50–95%）、KV 記憶估算、AFP 折算屬第三方/參考估算，**以方舟計費頁 + 控制台「用量明細」同 `usage_metadata` 實測為準**。官方明確定價同隱式 cache 規則以方舟官方文檔為準。

---

*Last audit date: 2026-08-17 · cache 機制 / 折扣 / 命中率會走，引用前 refetch 方舟計費頁同引擎 docs（vLLM / SGLang / llama.cpp / xLLM）。新增 §0 KV Cache 底層（SOSP 2023 PagedAttention / RadixAttention / xLLM 深潛）+ 前綴快取來源（arXiv 2309.06180 等），已 2026-09-06 更新。*
