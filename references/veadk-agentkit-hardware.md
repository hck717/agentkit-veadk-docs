# VeADK + AgentKit 硬體選型指南（VM / GPU / CPU）

呢份文件解答自建或規劃 Agent 基建時最實際嘅問題：**揀咩 VM / GPU / CPU，自建要點諗**。

> **核心心法**：
> 1. **AgentKit + 火山方舟托管**：GPU 打包喺 Agent Plan 度，你揀 `model_name` 就得，唔使碰硬件。
> 2. **自建 / 私有化部署**：先要識 VRAM、頻寬、算力、VM 規格——呢份就係你嘅揀機聖經。
> 3. 底層硬件知識用途 = **理解性能點嚟、預估成本、同 client 講 infrastructure story**。

---

## 0. 一句定位 + 快睇表

| 硬件類型 | 主要用喺邊 | 邊個場景 |
|---|---|---|
| **VM（通用雲服務器）** | Agent runtime、web server、API gateway、workflow orchestration、無需 GPU 嘅推理（細 model / CPU 推理） | 所有 Agent 項目嘅基礎；托管方案底下火山方舟已經幫你搞掂 |
| **GPU（加速卡）** | LLM 推理（model inference）、embedding 大模型、vision model、訓練 / 精調（finetune） | 大語言模型 serve；AgentKit 方舟已經打包，自建先要自己搞 |
| **CPU** | 細 model 推理（embedding、reranker、細 classifier）、邊緣部署（edge）、llama.cpp 級 demo | 輕量 workload、成本敏感、唔想碰 GPU |

> **Sale 一句**：「用 AgentKit 托管 = GPU 俾火山包咗，你管 context 同 model；自建 = 你連 GPU 都要自己排——硬件知識就係你多出嚟嘅操心。」

---

## 1. 框架層 vs 底層：邊個負責硬件

| 層 | 誰話事 | 你控制？ |
|---|---|---|
| **框架層**（AgentKit / VeADK） | Agent runtime、context、model、A2A | ✅ 你控制 |
| **API 層**（火山方舟 model API） | `model_name`（`doubao-*`） | ⚠️ 只控制名 |
| **推理引擎**（vLLM / SGLang） | batch、prefill、KV-cache 管理 | ❌ 托管；自建先輪到你 |
| **硬件**（GPU / VM / CPU） | 計算、記憶體、網路 | ❌ 托管；自建先輪到你 |

**決策點**：
- 托管方案（AgentKit + 方舟）：硬件全部收埋，你唔需要諗 GPU 型號、唔需要排 VM。
- 自建方案：你必須自己處理——VM 開幾大、GPU 揀邊張、CPU 用幾多 core、點 scale。
- 識呢個分層先唔會搞亂：**框架層可操作嘅 infra 槓桿**係模型選擇、context 管理、Runtime 資源（`--cpu-milli / --memory-mb / --max-concurrency`），見 `veadk-agentkit-performance.md`。

---

## 2. GPU 揀機三大數字

| 數字 | 代表咩 | 對 inference 嘅影響 |
|---|---|---|
| **VRAM（顯存）** | 裝得落幾大模型 + KV-Cache | 唔夠 = 放唔落 / 要量化 / 要拆卡 |
| **Memory bandwidth（HBM 頻寬）** | 每秒讀寫速度（GB/s） | **decode 快慢**（memory-bound） |
| **FP16/BF16 TFLOPS** | 每秒捭幾多算力（稠密） | **prefill / 訓練快慢**（compute-bound） |

**白話排序**：
- **推理（inference）** → 首重 **memory bandwidth + VRAM**，其次算力。（原因：decode 逐 token 出，每次要讀晒成個 KV-cache → memory-bound，見 `veadk-agentkit-serving-kit.md` §3）
- **訓練 / 精調（finetune）** → 首重 **TFLOPS + VRAM**（同埋 NVLink 互連）。

> ⚠️ 淨睇 TFLOPS 就買卡做推理係常見錯——decode 係 memory-bound，卡「算得快但讀得慢」一樣唔快。

---

## 3. 2026 主流 AI GPU 速查表

| GPU | VRAM | HBM 頻寬 (參考) | FP16/BF16 (參考) | 一句 |
|---|---|---|---|---|
| **H100 SXM** | 80GB HBM3 | ~3.3 TB/s | ~990 TFLOPs (sparse) | server 抓牙，訓練/推理通吃 |
| **H200** | 141GB HBM3e | ~4.8 TB/s | 同 H100 代 | 大 VRAM 係佢特價，長 context 友好 |
| **B200 / GB200** | 192GB HBM3e | ~8 TB/s | 大幅領先 | Blackwell 新代，貴 |
| **A100 (80GB)** | 80GB HBM2e | ~2.0 TB/s | ~312 TFLOPs | 上代，平、成熟 |
| **L40S / L40** | 48GB | ~0.86 TB/s | 推力為主 | **推理抵玩**，VRAM/價好 |
| **RTX 4090 / 5090** | 24GB / 32GB | ~1 TB/s (GDDR) | 強 | 自建 playground / dev |
| **L4** | 24GB | 細 | 細 | 純推理、入門、慳電 |

> ⚠️ 數字係第三方參考（2026，見來源），**唔係 Agent Plan 報價**。托管方案 GPU 錢已入 plan；呢張表只係「如果自建，預算幾多卡、幾多錢」。引用時標「參考 2026，見來源」以免過期。

---

## 4. 揀 GPU 決策樹（自建場景）

```
模型權重 + KV-Cache <= 一張卡 VRAM？
├── 可以 → 單卡（最簡單）
└── 唔可以 → 量化（FP8/AWQ）再睇
        ├── 仲係大 → 多卡（model/tensor parallel）
        └── 想慳卡數 → 4-bit 量化 or 揀更細 model

按 workload：
├── 純推理（serve API）→ memory bandwidth 優先：H100/H200/L40S
├── 多租戶長 context → VRAM 優先：H200 (141GB) 或 量化
├── 訓練/精調 → TFLOPS+互連優先：H100/B200 + NVLink
└── dev / demo → RTX 4090/5090 或雲 spot
```

**常見錯**
- 淨睇 TFLOPS 買卡做推理 → 但 decode 係 memory-bound，卡「算得快但讀得慢」一樣唔快。
- 淨睇「模型幾多 B」就買卡 → 冇計 **KV-Cache**（context 越長 / 並行越多，VRAM 需求越大）。
- 托管場景仲喺度諗 GPU → 直接講「打包咗喺 Agent Plan」就得。
- 唔理 memory bandwidth → 買張算力爆燈但 HBM 細嘅卡，decode 一樣慢。

---

## 5. VRAM 計數（唔使背，識晒）

```
VRAM ≈ 權重(weights) + KV-Cache + 額外 overhead（activation/framework）
```

- **權重**：參數數 × 每參數 byte。BF16 = 2B/參數 → 7B model ≈ **14GB**；70B ≈ **140GB**。
- **KV-Cache**：≈ 2 × layers × KV頭 × head_dim × 2B × tokens × 並行數（見 `veadk-agentkit-serving-kit.md` §3）。
- **4-bit 量化（AWQ/GPTQ）** ≈ 0.5–0.6B/參數 → 70B ≈ **40–45GB** → 一張 48GB/80GB 卡都掂。

> 自建先要計數；托管由方舟計。你只需要識「7B 唔使拆卡、70B 要量化或多卡」呢個量級 sense。

---

## 6. 量化（Quantization）— 記憶體嘅減肥

模型權重用 float16/bf16 存佔晒 VRAM。量化 = 用更低位元去存：

| 方法 | 位元 | 主要目的 |
|---|---|---|
| **FP8** | 8-bit 浮點 | 高吞吐加速、幾乎唔失真 |
| **AWQ** | 4-bit（權重感知） | 佔 VRAM 大減，慳 GPU 數 |
| **GPTQ** | 4-bit 逐層 | 舊啲、做得好都係 4-bit 路 |

- 量化嘅 AI 唔會你撞，平台收埋咗 → **唔使問**。
- 但**知**佢先唔會喺 client 面前鬧「點解咁食 VRAM」——係平台唔等你管。

> 對 client：「你買嘅 Agent Plan 已經幫你『買咗個會量化的 server』，唔使你喺 GPU 上左唸右唸。」

---

## 7. VM / CPU 揀機

### BytePlus / 火山雲 VM 產品對照

| 產品 | 用途 | 一句 |
|---|---|---|
| **Elastic Compute Service（ECS）** | 通用雲服務器，跑 Agent runtime、web、API、workflow | 火山雲 ECS / BytePlus 同源，彈性 vCPU + memory |
| **GPU Compute Service** | GPU 加速服務器，跑推理 / 訓練 / embedding | 有 H100/A100/L40S 等選項，按時或按量計 |
| **Vital Kubernetes Engine（VKE）** | 托管 Kubernetes，容器化 Agent 部署 | 適合大規模、多副本、自動 scale |

### CPU 揀機場景

| vCPU | Memory | 適合 |
|---|---|---|
| **8 vCPU** | 16–32 GB | 輕量 Agent runtime、API gateway、小型 workflow |
| **16 vCPU** | 32–64 GB | 多模型 orchestrator、中等並發、embedding + reranker |
| **32 vCPU** | 64–128 GB | 高並發 agent、大 context 處理、多租戶 |

> **Sale 一句**：「AgentKit 托管嘅 Runtime 資源（`--cpu-milli / --memory-mb / --max-instance`）其實就係火山方舟幫你排 VM——自建先要自己開 ECS / VKE。」

### Scaling 要點
- **ECS**：手動或 auto scaling group；適合穩定 workload。
- **VKE**：HPA（Horizontal Pod Autoscaler）+ node auto provisioning；適合波動大、多 model。
- **CPU 推理可行場景**：embedding model（如 `doubao-embedding-vision` 細 model）、reranker、classifier；但大 LLM 推理（7B+）一定要 GPU。

---

## 8. 自建 vs 托管決策表

| | 自建 vLLM/SGLang + VM/GPU（底層） | VeADK/AgentKit + 方舟（托管框架） |
|---|---|---|
| 開運成本 | GPU + VM + 部署 + 維運 | Agent Plan + Runtime |
| 靈活度 | 高（量化 / AWQ / SGLang multi-LoRA） | 低（平台決定） |
| 你管嘅 | 排 request、GPU、VM、networking | context、model、runtime |
| 硬件揀機 | ✅ 自己搞（ECS / GPU Compute / VKE） | ❌ 打包喺 Agent Plan |
| 量化 / KV 優化 | ✅ 自己搞 | 方舟自動 |
| 適合 | 自家 model / 極端 SLA / 數據不出域 | 快速交付、多模態、要 eval/audit 全家桶 |
| ServingKit（推理托管） | 可以做嘅選項（見 `veadk-agentkit-serving-kit.md`） | 方舟已收埋 |

**Sales 判斷**：「要控 100% 唔出我域 → 自建；要『快 + 準 + 已經 package』→ AgentKit。」兩條生意都有人做。

> ⚠️ 自建唔淨係買 GPU——仲要排 VM（ECS/VKE）、管 networking（RDMA/NVLink）、做 monitoring。成本同複雜度係幾何級上升。

---

## 9. 硬件詞彙速查

| 詞 | 一句 |
|---|---|
| VRAM | 顯存，裝模型 + KV + parallel |
| Memory bandwidth | 每秒讀寫，決定 decode 快慢 |
| TFLOPS | 算力，決定 prefill / 訓練快慢 |
| NVLink | GPU 之間高速互連（多卡訓練 / tensor parallel） |
| RDMA | 遠端直接記憶體存取，多節點 GPU cluster 互連 |
| FP8 / AWQ / GPTQ | 低位 bit 存權重：VRAM 慳、token/s 升 |
| ECS | BytePlus / 火山雲 Elastic Compute Service（通用 VM） |
| VKE | Vital Kubernetes Engine（托管 K8s） |
| GPU Compute Service | BytePlus GPU 加速服務器 |
| PD（Prefill-Decode） | 推理兩階段分離部署（見 `veadk-agentkit-serving-kit.md` §3） |
| GQA / MQA | 共享 KV 頭，慳 KV 記憶 |
| KV-Cache | 記住之前 token 嘅 attention 中間值 |
| PagedAttention | vLLM 嘅 KV 分頁，慳碎片 |
| RadixAttention | SGLang 嘅 prefix 樹複用 |
| Continuous batching | 唔落 idle、即插 next request → RPS 20× |
| Speculative decoding | 細 model 估 + 大 model verify → 2–3× |

---

## 10. 資料來源

| 來源 | URL | 日期 |
|---|---|---|
| GPU 規格 / 價參考（H100/H200/L40S/A100/4090） | https://www.vast.ai / https://cloud.gpux.ai | 2026 |
| BytePlus GPU Compute Service | https://byteplus.com/product/gpu | 頁面日 |
| BytePlus Vital Kubernetes Engine（VKE） | https://byteplus.com/product/vke | 頁面日 |
| vLLM 官方（PagedAttention / continuous batching） | https://docs.vllm.ai | 頁面日 |
| SGLang 官方（RadixAttention / prefix cache） | https://docs.sglang.ai | 頁面日 |
| 量化 AWQ / GPTQ / FP8 簡介 | https://huggingface.co/docs/transformers/quantization | 頁面日 |
| 引擎內部（prefill / decode / KV / spec，已合併） | `references/veadk-agentkit-serving-kit.md` §3 | 2026-08-15 |
| 框架 vs 底層宏觀地圖 | `references/veadk-agentkit-serving-kit.md` 同 `veadk-agentkit-hardware.md` | 2026-08-13 |
| Cache 管理（tokens / inputs / memory） | `references/veadk-agentkit-cache-management.md` | 2026 |
| Agent Plan / AFP 計價（GPU 已入 plan） | `references/veadk-agentkit-pricing.md` | 2026-08-09 |
| Performance 同 Runtime 資源 | `references/veadk-agentkit-performance.md` | 2026-08-13 |
| AI 基礎概念 | `references/veadk-agentkit-ai-concepts.md` | 2026 |

> **免責**：GPU 價、規格、bandwidth/TFLOPS 數字屬第三方 2026 參考估算；唔係 Agent Plan 報價。托管方案 GPU 已打包於 Agent Plan，唔好將 GPU 價直接加落方案報價——真錢用 `veadk-agentkit-pricing.md` 三條線。引用前 check 一遍，GPU 型號同價會走。

---

*Last audit date: 2026-08-17 · GPU 型號、BytePlus 產品同價會走，引用前 check 一遍。*
