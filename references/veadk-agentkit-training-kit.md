# BytePlus TrainingKit 解構 — 企業級模型訓練套件（pre/post-training）

BytePlus 嘅成個 AI 方案除咗**跑 agent**，仲有一條線係**訓練模型**——如果你個 enterprise client 唔係淨係「用」現成模型，而係想**自己由零起個私有模型**（pre-training），或者**力谷一輪強化學習 / RL（post-training）嚟調出自家 reasoning 能力**，就要用遊嘅呢套 **AI Cloud Native TrainingKit**。

呢份文件係講俾 sales engineer 聽：**TrainingKit 到底管咩、點行、同 AgentKit / ServingKit 點分工、幾時先真正要用到佢**。定位為「**精調 / 優化 + 訓練 tab**」入面嘅 sub-page——喺方舟精調 / LoRA（`veadk-agentkit-finetune-optimize.md`）之上，再講到**大規模訓練基建**（pre-training + post-training / RL）。

> ✅ **核心心法**：
> 1. **TrainingKit 唔係畀你「精調一隻 LoRA」**——精調（LoRA / SFT / DPO）走火山方舟模型精調，幾張卡就搞掂；TrainingKit 係**萬卡級 GPU cluster + 訓練框架 + 穩定基建**嘅成套訓練方案。
> 2. 三條 Kit 分工：**AgentKit** 管「部署同運行 agent」，**ServingKit** 管「推理 serving」，**TrainingKit** 管「訓練」。訓練完嘅 checkpoint → 服務去 ServingKit / 方舟 → AgentKit 掛去用，一條龍。
> 3. 賣點係三句大數：**MFU > 60%**、**ETTR > 99%**、**20× RL throughput**——記住呢三粒數就可以開場。

---

## 0. TrainingKit 係咩 — 一句 + 同 AgentKit / ServingKit 關係

**一句講晒**：TrainingKit 係建基於 ByteDance 大規模 AI 基建同 LLM 訓練經驗嘅 **AI Cloud Native 訓練套件**——用嚟喺 BytePlus GPU 集群度高效開發模型，幫你**慳資源、快迭代**，由 pre-training 到 RL post-training 都有齊。

BytePlus 嘅三套「AI Cloud Native」kit 各管一段 lifecycle：

| Kit | 管咩 | 主要客群 | 對應呢個 repo 嘅參考 doc |
|---|---|---|---|
| **AgentKit** | Agent 平台（runtime / tools / MCP / 記憶 / 可觀測） | 整 agent 應用嘅 developer | `references/agentkit-cli.md`、`veadk-agentkit-sdk.md` |
| **ServingKit** | 推理 serving（模型上線、QPS、延遲） | 將模型行到生產嘅團隊 | `references/veadk-agentkit-serving-kit.md` |
| **TrainingKit** | 模型訓練（pre-training + post-training / RL） | ML infra / 大模型團隊 | **呢份** `veadk-agentkit-training-kit.md` |

> **Sale 一句**：「AgentKit 買返嚟嘅係『agent 行得順』，TrainingKit 買返嚟嘅係『個模型練得出』——兩個客戶名都係 LLM 團隊，但錢袋唔同。」

---

## 1. 三條大數（MFU / ETTR / 20× RL）

TrainingKit 嘅官方主打數據就係呢三粒，**開場先報呢三粒先啱數**：

| 指標 | 數字 | 即係咩 | 點解對客戶重要 |
|---|---|---|---|
| **MFU**（Model FLOPs Utilization） | **> 60%** | GPU 嘅理論計算力有幾多用咗喺真訓練度 | 高 MFU = 你張卡冇「嘅—半時間吹水」，同樣資源練得快啲、慳錢 |
| **ETTR**（Effective Training Time Ratio） | **> 99%** | 計劃訓練時間入面幾多有成效行緊（vs 等重啟 / 等診斷） | 99%+ = 幾乎唔使停工，萬卡級跑 30 日都唔會呃你時間 |
| **RL throughput（veRL HybridEngine）** | **20×** | 用 veRL HybridEngine 做 RL 訓練嘅吞吐，vs 其他開源框架 | RL（尤其 GRPO）最燒錢又最慢，快 20× = 同一預算可以試多好多輪 |

> 🎯 **Sales 角度**：呢三粒數堆埋，客戶聽落係「**快、穩、慳**」——MFU 講「慳卡」，ETTR 講「唔使 Band-Aid 人手救」，20× 講「RL 你哋以前做唔起嘅，而家做得起」。對比其他雲廠，訓練集群通常淨係賣「你有幾多張 H 卡」，冇人敢報 MFU / ETTR——呢啲先係差異位。

---

## 2. 兩大架構：Pre-Training vs Post-Training

TrainingKit 對應兩條完全唔同嘅架構題——**先搞清楚客戶係想「由零起機」定係「喺基模上力谷 RL」**：

| 維度 | **Pre-Training**（由零起私有模型） | **Post-Training / RL**（喺基模上調） |
|---|---|---|
| 做咩 | 由大規模語料由零訓練 / 大規模持續預訓練 | 用 RL 算法（PPO / GRPO 等）將模型調到識推理、跟指令 |
| 規模 | **10,000 節點**級 AI 集群 | 百萬核並發（CPU 都要多，因為 rollout 燒 CPU） |
| 主要硬件 | 大量 GPU + **PFS 並行文件存儲**（餵高吞吐數據） | GPU（訓練/推理）+ **彈性 Sandbox** 環境 + 推理加速 |
| 通信 | **veCCL** 通信加速 | veCCL + 彈性 sandbox（唔使自行開滿成批機器） |
| CLI 關鍵 | 穩定運行 + 故障自愈 | 冷啟動快 + rolling 並發高 |
| 對應落地速度 | 慢（月計）、燒錢最狠 | 快啲（週計）、機會成本係 reward 設計 |

**每種要咩硬件 / 存儲（重點）：**

| 架構 | GPU | 存儲 | 通信 | 其他關鍵件 |
|---|---|---|---|---|
| Pre-Training | 萬卡 GPU 集群（GPU Compute Service） | **PFS（Parallel File Storage）** 高吞吐並行文件系統 | veCCL（訓練專用集合通信） | 一鍵診斷 + 自主癒合；VKE 編排 |
| Post-Training（RL） | GPU for training + inference；**百萬核**多核並發 | 相對細（checkpoint 為主） | veCCL + **模型快取 / caching** | **彈性 Sandbox**：150ms 冷啟動，seek torn 唔使長佔 GPU |

> ⚠️ **分清兩條線嘅價值主張**：Pre-Training 賣「你買得起萬卡 + 唔會日日斷」，Post-Training 賣「RL rollout 快 + 冷啟動平」——唔好串錯。諗住「我淨係想試 RL」就硬推 10k node cluster，客戶會當你冇做功課。

---

## 3. veRL 框架深入（PPO / GRPO / HybridEngine / Sandbox）

TrainingKit 嘅 post-training 心臟係 **veRL**——ByteDance 自家開源 RL 框架（同 BytePlus 官方整合），支援大量 RL 算法同多套訓練 / 推理框架。

| veRL 元件 | 作用 | 客戶見到咩 |
|---|---|---|
| **PPO** | 經典 RL，用 critic 模型估 value | 通用 RL 對齊 |
| **GRPO** | 唔使 critic，用 group 「好/trace 壞」比對估算 reward | **推理（reasoning）主力**——目前 best practice |
| **HybridEngine** | 混合多個訓練/推理框架加速 RL 循環 | **吞吐 20×**（vs 其他開源框架） |
| **Sandbox（Code Sandbox）** | 彈性、加速嘅執行環境，畀 agent 喺 RL 中間跑碼 / rollout | 百萬核並發 + **150ms 冷啟動** |

**GRPO 用喺邊——同 SFT / DPO 嘅分別：**

| 方法 | 數據類型 | 優化緊咩 | TrainingKit 角色 |
|---|---|---|---|
| **SFT** | 標好嘅「問題→答案」 | 直接抄模型格式 / 風格 | 唔特別需要（方舟精調已夠，見精調 doc §2） |
| **DPO** | 好 / 壞回覆配對 | 揀優，方向對但冇「分數」 | 方舟精調已支援 LoRA/全量 |
| **GRPO / RL** | **Rule-based reward**（例：答案啱唔啱、格式啱唔啱） | 用「分數」夾硬去優化，將 chain-of-thought 拉長 | **TrainingKit 主場**——reasoning 模型就係咁練出嚟 |

> 🎯 **對客戶講**：而家啲 reasoning 模型（包括 doubao-seed 系列自家嘅推理能力）**唔係 SFT 調出嚟，係 RL（GRPO 行 rule-based reward）「練」出嚟**——畀一分就知錯，繼續嗌佢諗深啲。SFT 教「口脗」，RL 教「諗嘢」，兩者唔同層次。

> ✅ **同精調 doc 嘅分工**：想做 LoRA / DPO 細執 → `veadk-agentkit-finetune-optimize.md`；想做完整 RL post-training（成千萬次 rollout、要 running infra + sandbox）→ 先會掂到 TrainingKit。精調 doc 嘅精調方法矩陣（SFT / DPO / GRPO）就係「細都喺方舟做」同「大先上 TrainingKit」嘅分界線。

---

## 4. 訓練集群硬件 + 通信（GPU / veCCL / BCC / caching / PFS / 10k nodes）

訓練同推理係兩嚿嘢——推理重低延遲、單卡都得；**訓練重吞吐同「唔好斷」**，分別由呢幾樣構成：

| 層 | 元件 | 一句 |
|---|---|---|
| 算力 | **GPU Compute Service**（GPU 集群） | 專為訓練優化嘅 GPU 集群，Pre-Training 可到 **10,000 節點** |
| 編排 | **Vital Kubernetes Engine（VKE）** | 容器編排，配合 KEDA 做彈性伸縮 |
| 數據 | **PFS（Parallel File Storage）** | 並行文件存儲，餵得飽萬卡同時讀數據 |
| 通信 | **veCCL** | 自家集合通信庫，optimize 大規模 all-reduce（官方有 high-performance 通信 best practice） |
| 通信 | **BCC / 模型 caching** | BCC（ByteDance 自家通信相關加速）+ 模型快取，RL 運算中間慳重覆傳輸 |
| 調度 | **topology-aware + NUMA affinity** | 安排任務時考慮機櫃拓樸同 NUMA，減少跨節點通信 |
| 彈性 | KEDA | 按負載自動伸縮 workload |

> 💡 **Sales 必讀**：萬卡級訓練最大敵人係**通信**，唔係算力——GPU 數多到某個位，卡與卡之間嘅 all-reduce 慢過你「停住等佢」，MFU 即刻跌。BytePlus 嘅賣點係**自家 veCCL / BCC / caching 疊埋**，先做到 MFU > 60% 呢個級數（一般開源棧 30–50% 已經偷笑）。

---

## 5. 穩定性 / 可觀測性（ETTR 99%+ / auto-healing / code-free instrumentation / 全鏈路）

萬卡訓練晒幾十日，**最貴嘅嘢係「中斷」**——TrainingKit 嘅穩定性賣點全部為咗保住 ETTR 99%+：

| 能力 | 做咩 | 客戶價值 |
|---|---|---|
| 診斷 + 即時故障告警 | 開機 / 運行期間自動偵測硬件 / 網絡異常 | 未斷先知 |
| **Auto-healing / 自主癒合** | 壞咗自動替補、自動重啟任務 | ETTR 99%+ 嘅來源 |
| 自動任務重啟 | 訓練 task crashed 自動接返 | 唔使半夜起身手動救 |
| **子秒級可觀測性** | 指標秒級出，睇到 GPU / 通信 / 進度 | 快啲搵到瓶頸 |
| 全訓練生命週期監控 | 由數據、到訓練、到 rollout 全 cover | 一條管睇晒 |
| **Code-free instrumentation** | 一鍵啟動、唔使自己寫監控 code | 接入成本近零 |
| **跨棧問題偵測** | agent → 推理引擎 → service 全鏈路**秒級**定位 | RL 中間邊一環出事即刻知 |

> ⚠️ **對比講法**：一般雲廠會講「我哋有 monitoring」，但係冇講**故障之後自動癒合**。TrainingKit 嘅可觀測性係**一鍵零代碼**嘅——你唔使喺訓練框架度插埋一堆 OTel，先係真正幫到唔想理 infra 嘅 ML 團隊。

**附帶相關產品**（同一張單好可能一齊落）：

GPU Compute Service · VKE · **PFS** · Function Service（FaaS）· Container Registry · Vital Managed Service for Prometheus · **APMPlus**（應用性能監控，跨棧那條就係佢）。

---

## 6. 幾時用 TrainingKit（vs 方舟精調 / Agent Plan — 決策表）

Sales 最常問「到底幾時先要開 TrainingKit 呢張單」——答案係**睇規模**，精調同 Agent Plan 都唔包訓練：

| 你個 case | 用咩 | 點解 |
|---|---|---|
| 想改 agent 語氣 / 格式 / 少量領域知識 | **改 system prompt / LoRA** | 零成本或方舟精調搞掂 |
| 想做 DPO / 細 GRPO（LoRA） | **方舟模型精調**（見 `veadk-agentkit-finetune-optimize.md`） | 幾張卡、幾個鐘級別，唔需要萬卡基建 |
| 想喺 Agent Plan 度「買訓練」 | ❌ **冇得買** | Agent Plan（AFP）**只包推理 + 工具**，隻字唔提訓練 |
| 想由零起私有模型 / 大型持續預訓練 | ✅ **TrainingKit Pre-Training** | 10k node + PFS + veCCL 先食得起個規模 |
| 想做完整 RL（GRPO / PPO）post-training、幾百萬 rollout | ✅ **TrainingKit Post-Training** | veRL + HybridEngine + 彈性 Sandbox 先做得起成本 |
| 模型練完想上線 | **ServingKit / 方舟推理** | 訓練唔等於 deploy，serving 係另一張單（見 `veadk-agentkit-serving-kit.md`） |

```
客戶想「自己整模型」？
├─ 只改風格 / 語氣 / 格式
│   └─ ➜ system prompt → LoRA（方舟精調）—— 唔使 TrainingKit
├─ 想做 DPO / 細量 GRPO
│   └─ ➜ 方舟模型精調（LoRA/全量）—— 睇 `veadk-agentkit-finetune-optimize.md`
├─ 想由零起私有 model / 萬卡 pre-training
│   └─ ➜ TrainingKit（Pre-Training：PFS + veCCL + 10k nodes）
├─ 想 RL 調推理（doubao-seed 式 reasoning）
│   └─ ➜ TrainingKit（Post-Training：veRL + GRPO + HybridEngine + Sandbox）
└─ 只想「用」模型
    └─ ➜ Agent Plan / 按量 —— 詳見 `veadk-agentkit-pricing.md`
```

> **Sale 一句**：「Agent Plan 幫你慳推理錢，精調幫你細執，但**兩個都唔包含『自己練個模型』**——練模型呢啲先係 TrainingKit 張單，而且同推理 / agent 嗰兩條收費線完全分開。」

---

## 7. 資料來源

| 來源 | URL | 用途 |
|---|---|---|
| TrainingKit 官方頁（MFU / ETTR / 20× / 兩大架構） | https://www.byteplus.com/solutions/ai-cloud-native-trainingkit | 主打數據 + 架構 |
| ServingKit 官方頁（同 TrainingKit 分工） | https://www.byteplus.com/solutions/ai-cloud-native-servingkit | 三 Kit 對照 |
| AgentKit 官方頁 | https://www.byteplus.com/solutions/ai-cloud-native-agentkit | 三 Kit 對照 |
| veRL GRPO RL 訓練 best practice（MLP 範例） | https://docs.byteplus.com/en/docs/.../GRPO_reinforcement_learning_training_best_practices_with_verl | pre/post-training 教學 |
| PPO on GSM8K with veRL | https://docs.byteplus.com/.../PPO_training_on_the_GSM8K_dataset_with_veRL | PPO 流程參考 |
| veRL 做 RL code generation（Eurus-2-RL-Data + Code Sandbox） | https://docs.byteplus.com/.../Conducting_RL_for_code_generation_through_veRL_Code_Sandbox | Sandbox 場景 |
| veCCL 高效通信 practices | https://docs.byteplus.com/.../High-performance_communication_practices_of_veCCL | 通信加速論據 |
| 精調 / 優化 tab（SFT / DPO / GRPO 分工） | `references/veadk-agentkit-finetune-optimize.md` | 分界線 |
| 定價指南（Agent Plan 唔包訓練） | `references/veadk-agentkit-pricing.md` | 收費線 |
| 推理 / serving 參考 | `references/veadk-agentkit-serving-kit.md` | ServingKit 側 |

> **免責**：MFU > 60% / ETTR > 99% / 20× RL 等數字係 BytePlus 官方宣稱，實際數字隨 workload、模型、集群規模有差異——引用時標明「官方數據，實際以 POC 為準」。

---

*Last audit date: 2026-08-17 · TrainingKit / veRL 係快速演化嘅產品，賣之前對正官方頁同 best practice 教學再講。*