# VeADK + AgentKit 推理交付解構（ServingKit — 大規模 GPU 集群推理）

呢份文件講**BytePlus AI Cloud Native ServingKit**：點解、點樣、喺邊度。ServingKit 係 ByteDance 大規模 AI 推理經驗 + 火山方舟業務沉澱嘅產品，用嚟喺大規模 GPU 集群上高穩定、高性價比咁跑主流推理模型。

內容分兩層（舊有嘅 engine-internal 文件已合併落嚟）：
- **引擎內部**（§3）：xLLM / vLLM / SGLang / Dynamo 點運作——PagedAttention / RadixAttention / PD 分離 / speculative decoding。
- **交付層**（§4 起）：ServingKit 點將呢啲引擎喺大 scale 上面落地（AI 網關、用量、監控），同 AgentKit / TrainingKit / 方舟嘅關係。

> **核心心法**：
> 1. **喺 AgentKit / VeADK 框架層，你用 `model_name` call 推理就得**——方舟幫你 serve。
> 2. 但**公司要自建 / 大規模私有推理**嗰陣，就落到 ServingKit——呢度係「底層落地嘅最後一里路」。
> 3. Sales 要識嘅係：ServingKit 解決咗乜問題、有幾快、幾慳錢，唔使識排 GPU。

---

## 0. ServingKit 係咩 — 一句 + 位置

| 產品 | 一句 | 同 ServingKit 關係 |
|---|---|---|
| **AI Cloud Native ServingKit** | 大規模 GPU 集群推理交付 | **呢份 doc 嘅主角** |
| **AI Cloud Native AgentKit** | Agent runtime 一層（可被 ServingKit 部署） | ServingKit 可以 serve AgentKit 嘅 agent |
| **AI Cloud Native TrainingKit** | 訓練（另一份 doc） | 訓練完嘅 model → ServingKit serve |
| **火山方舟 / ModelArk** | 托管 model API（`doubao-*`） | 一般客戶用方舟就夠；要自建先落 ServingKit |

> **Sale 一句**：「AgentKit 係你寫 agent 嘅地方，方舟係你 call API 嘅地方，ServingKit 係你要自己揸 GPU 嗰陣嘅答案。」

喺 docset 嘅位置：框架層（VeADK / AgentKit）用 `model_name` 指令調用推理；公司要自建 / 大規模私有推理嗰陣，先落到 ServingKit。ServingKit 係**自建大規模推理嘅「底層落地層」**。

---

## 1. 三條大數（講畀 client 聽）

| 指標 | 數字 | 說明 |
|---|---|---|
| **TPS ↑** | 1–3× | DeepSeek-R1 operator-level optimization |
| **TTFT ↓** | 60% | 首 token 延遲大幅縮短 |
| **Service startup** | 分鐘級 | DeepSeek-R1-671B 跨 100+ GPU 分鐘級部署 |

> **Sale 一句**：「三條數講完：出 token 快 1–3 倍、首 token 快 60%、100 張 GPU 幾分鐘起晒。」呢個係同 client 講嘅 selling point。

---

## 2. 架構五寶（Core Competencies）

### 2.1 模型極速啟動 Rapid Model Startup

- 權重加速引擎（weight-based acceleration engine）：LLM 載入速度提升 **8×**。
- GDKV warmup + RDMA 高速互聯，P2P + model loading utilities。
- 結果：100+ 張 GPU **分鐘級部署** DeepSeek-R1-671B。

### 2.2 算子優化 Operator Optimization

- 自研 SGLang operator：提升**單 GPU throughput**。
- 針對 vLLM / SGLang / Dynamo 嘅 operator-level optimizations → TPS **1–3×**。
- 唔止用開源，加埋自家調校。

### 2.3 AI Gateway

| 功能 | 一句 |
|---|---|
| 多 model 統一接入 | 一個 gateway serve 多個 model |
| 身份認證 + token 限額 | 控制邊個用幾多 |
| Add-ons | web search / content security / canary release |
| Load-aware routing | 根據 GPU 負載分 request |
| **KVCache-aware routing** | 識得將 request 路由去 KV-cache 命中率高嘅節點 |

### 2.4 PD 分離編排 Orchestration for PD Disaggregation

- **Dynamic Disaggregation**：動態將 prefill 同 decode 分開到唔同 GPU 節點。
- Metric-guided scaling：根據指標自動擴縮。
- 統一排 P / D nodes 喺 heterogeneous GPU cluster 上。
- HPA with KEDA custom scaling metrics：獨立 P / D scaling，用 composite metrics 控制。

### 2.5 端到端推理可觀測性

- Non-intrusive instrumentation：唔改 model code 就監控。
- 原生 metric monitoring for vLLM / Dynamo / SGLang。
- Lightweight dynamic activation：快速搵 bottleneck。

> **Sale 一句**：「五寶 = 快起 + 快出 + 智能路由 + PD 分離 + 睇得清。同普通自建 vLLM 嘅分別，就係呢五樣全部打包咗。」

---

## 3. 推理引擎相容（xLLM / vLLM / SGLang / Dynamo）

ServingKit 支援多個主流推理引擎，底層常識同速度來源詳見 `references/veadk-agentkit-hardware.md` §5（引擎運作），呢度做個速覽：

| 引擎 | 核心技術 | 適合場景 |
|---|---|---|
| **xLLM（自研）** | BytePlus 自研：PD 分離、xTensor 記憶（邏輯連續/物理離散）、EPLB MoE 優化、異步 pipeline 疊算 | DeepSeek / MoE 大規模、PD 分離開箱即用（內建） |
| **vLLM** | PagedAttention（分頁式 KV-Cache）、Continuous Batching、Prefix Caching | 大量獨立 request、成熟生態 |
| **SGLang** | RadixAttention（前綴樹複用）、Structured Output、Multi-LoRA | 高共享 prefix、多租戶、多 LoRA |
| **Dynamo** | NVIDIA 出品，operator-level 優化 | NVIDIA 生態深度整合 |

關鍵底層概念速覽：

| 概念 | 一句 |
|---|---|
| Prefill | 讀 prompt、計首 token（compute-bound） |
| Decode | 逐 token 出（memory-bound） |
| KV-Cache | 留住之前 token 嘅 attention 中間值 |
| Continuous Batching | 唔落 idle、即插下個 request → GPU 利用率飆升 |
| Speculative Decoding | 細 model 估 + 大 model verify → throughput 2–3× |
| Quantization（FP8 / AWQ / GPTQ） | 低位 bit 存權重：VRAM 慳、token/s 升 |
| SGLang Multi-LoRA | 單一引擎動態切換多個 LoRA adapter |
| PD 分離 | Prefill / Decode 拆 instance 池（xLLM 內建），慳碎片 + 低 TTFT |

> ⚠️ 托管方舟 / ModelArk 收埋引擎（**xLLM 係自家主打**，vLLM / SGLang 同場兼容）——你唔使揀。ServingKit 係**自建嗰陣嘅選項**，先需要理解呢啲。四引擎邊個啱邊種場景 → cache tab §2.6–2.7。

---

## 4. GPU 集群 + 硬件（大 Scale）

| 硬件 / 服務 | 一句 |
|---|---|
| **H100 / H200 / B200 大規模集群** | ServingKit 嘅底座，支援最新 NVIDIA GPU |
| **NVLink / RDMA** | GPU 高速互聯，模型切分跨卡無痛 |
| **PFS（Parallel File Storage）** | 做 checkpoint / weight 載入，唔使等 |
| **Weight-based acceleration** | 權重級加速，100+ images 分鐘級服務啟動 |
| **Image acceleration** | 容器鏡像加速，加快冷啟動 |

關聯 BytePlus products：

| Product | 用途 |
|---|---|
| GPU Compute Service | GPU 算力 |
| Vital Kubernetes Engine（VKE） | 容器編排 |
| Container Registry | 鏡像管理 |
| Parallel File Storage | 高速文件存儲 |
| Vital Managed Service for Prometheus | Metric 監控 |
| APMPlus | 應用性能監控 |

> **Sale 一句**：「唔止係 GPU——連 storage、container、monitoring 都係 BytePlus 自家 product，一個生態圈搞掂。」

---

## 5. 自建 vs 托管決策（幾時揀 ServingKit / 方舟 / AgentKit）

| | **自建大規模（ServingKit）** | **托管（方舟 / ModelArk）** | **AgentKit + 方舟** |
|---|---|---|---|
| 適合 | 數據不出域、極端 SLA、自家 model、大規模 GPU 集群 | 快速上線、中小規模、托管推理 | 快速交付 agent、要 eval / audit 全家桶 |
| 你管嘅 | GPU / 部署 / PD 分離 / 觀測 | model_name、context、runtime | context、model、runtime |
| 開運成本 | GPU + 部署 + 維運（高） | 方舟 API 費（中） | Agent Plan + Runtime（中） |
| 靈活度 | 高（量化 / AWQ / multi-LoRA / engine 揀） | 低（平台決定） | 低（平台決定） |
| 交付速度 | 慢（要排 GPU、部署、調參） | 快 | 最快 |

> **Sales 判斷**：「要控 100% 唔出我域 + 大 scale → ServingKit；要快上線、唔想管 infra → 方舟 / AgentKit。」兩條生意都有人做。具體計價見 `references/veadk-agentkit-pricing.md`。

> ⚠️ ServingKit 嘅定價同 Agent Plan 唔同——ServingKit 係 infra 級計費（GPU + storage + bandwidth），唔係 per-token 計。

---

## 6. 應用場景

### 6.1 AI Search（DeepSeek 部署 + RAG 內網知識）

- 用 ServingKit 部署 DeepSeek 系列模型，配合 RAG 搭建內網知識搜索引擎。
- 大規模 GPU 集群確保低延遲、高吞吐，支援高並發搜索請求。
- 適合企業內部知識管理、客服知識庫。

### 6.2 AI-Assisted Coding（Open-Source LLM 部署、成本控制）

- 部署開源 LLM（DeepSeek 等）做 code assistant。
- 透過 ServingKit 嘅算子優化 + continuous batching 控制成本。
- 支援 vibe coding 場景：長 context、多輪對話、結構化輸出。

### 6.3 AI Customer Service（客服 Assistant）

- 客服 assistant 需要低延遲、高並發、穩定 serving。
- ServingKit 嘅 AI Gateway + load-aware routing 確保請求分發均勻。
- 配合 content security add-on 做合規。

> **Sale 一句**：「三個場景都係用 ServingKit 部署 open-source models（DeepSeek 等），配合 RAG，解決企業內部 / 對外嘅 AI 需求。」

---

## 7. 資料來源

| 來源 | URL | 日期 |
|---|---|---|
| BytePlus ServingKit solution page | https://www.byteplus.com/solutions/ai-cloud-native-servingkit | 頁面日 |
| BytePlus AgentKit AI Cloud Native | https://www.byteplus.com/solutions/ai-cloud-native-agentkit | 頁面日 |
| BytePlus TrainingKit | https://www.byteplus.com/solutions/ai-cloud-native-trainingkit | 頁面日 |
| xLLM Technical Report | https://arxiv.org/abs/2510.14686 | 2025-10 |
| xLLM 官方 GitHub | https://github.com/xLLM-AI/xllm | 頁面日 |
| veMLP xLLM PD 分離（vs vLLM/SGLang） | https://docs.byteplus.com/en/docs/mlp/veMLP_xLLM_Inference_Engine_PD_Separation_Deployment_for_Qwen_Model | 2026 |
| vLLM 官方（PagedAttention / continuous batching） | https://docs.vllm.ai | 頁面日 |
| SGLang 官方（RadixAttention / multi-LoRA） | https://docs.sglang.ai | 頁面日 |
| 推理引擎底層常識（已合併） | `references/veadk-agentkit-hardware.md` §5 | 2026-08-15 |
| 自建 vs 托管決策 | `references/veadk-agentkit-hardware.md` §8 | 2026-08-13 |
| 定價 | `references/veadk-agentkit-pricing.md` | 2026-08 |

> **免責**：TPS 倍數、TTFT 個百分比、部署時間屬 BytePlus 官方參考估算；ServingKit 細節同定價會隨產品迭代而變，引用前 check 一遍最新資料。底層引擎版本同 GPU 硬件亦會走。

---

*Last audit date: 2026-08-17 · ServingKit 功能同定價會隨 BytePlus 產品迭代而變，引用前 check 一遍。*
