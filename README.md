# agentkit-veadk-docs

BytePlus/Volcengine Agent 開發文檔 — VeADK + AgentKit SDK + AgentKit CLI

## 結構

```
.
├── references/              # 技術參考文檔（read-only 性質）
│   ├── agentkit-cli.md     — AgentKit CLI 所有指令 (ak init/deploy/logs/...)
│   ├── veadk-api.md        — VeADK 框架 Python API (Agent/A2UI/A2A)
│   ├── agentkit-sdk.md     — AgentKit SDK Python API (A2aApp/A2aAgent/Tool)
│   ├── veadk-agentkit-pricing.md      — 方案計價指南（全部 Plan：VeADK/AgentKit/BytePlus · AFP/額度/模型矩陣/6 個 scenario）
│   ├── veadk-vendor-cost-comparison.md — 跨廠商全棧成本對照（BytePlus vs Azure/AWS/Google/DeepSeek/Qwen/混元）
│   ├── veadk-agentkit-uniqueness.md    — 獨特賣點全覽（VeADK/AgentKit/BytePlus + doubao/Seed 自家模型 vs 其他 provider）
│   ├── veadk-agentkit-finetune-optimize.md — 精調 / 優化（LoRA/SFT/DPO/RLHF/Distillation · 決策樹 + 方舟實例）
│   ├── veadk-agentkit-training-kit.md — TrainingKit 訓練套件（pre/post-training + RL，與 ServingKit 分工）
│   ├── veadk-agentkit-evaluation.md — 評估 / 評測（Offline/CI/Shadow/Studio 回流 · dataset→evaluator→experiment）
│   ├── veadk-agentkit-optimization-evaluation-guide.md — 優化 + 評估 完全指南（三層架構：AgentKit CLI eval loop / VeADK ADKEvaluator+Deepeval+PromptPilot+RL+自反思 / ModelArk 模型評測+精調+TrainingKit · 全部 CLI flag + 源碼實證）
│   ├── veadk-agentkit-vector-cache.md — VectorDB + Cache 管理（KB/LTM 後端矩陣、緩存、壓縮）
│   ├── veadk-agentkit-rag-guide.md   — RAG 全攻略（Naive→Agentic/Corrective/Hybrid · 檢索+Ranker · 速度/準確/平衡/成本）
│   ├── veadk-agentkit-tools-capabilities.md — 工具 / 能力（MCP · Tools · Skills · A2A · Guardrail/Filter）
│   ├── veadk-agentkit-performance.md  — 性能優化 Playbook（latency/throughput/cost/eval）
│   ├── veadk-agentkit-seedream.md  — Seedream 圖片生成家族深潛（Lite/Pro · 歷代 · 定價 · Dreamina/CapCut/ModelArk/VideoOne）
│   ├── veadk-agentkit-seedance.md  — Seedance 視頻生成家族深潛（2.0/2.5/Fast/Mini · LAS 計費 · VideoOne deep-dive）
│   ├── veadk-agentkit-hardware.md     — 硬體 Hardware（VM/GPU/CPU 揀機 + 量化 + 自建 vs 托管）
│   ├── veadk-agentkit-cache-management.md — Cache 管理（前綴/上下文/隱式 cache + output_schema）
│   ├── veadk-agentkit-database-management.md — 資料庫管理（本地 vs 雲端 · SQL/Vector/NoSQL · 記憶三層後端 + 檢索）
│   ├── veadk-agentkit-memory-context.md — 記憶 + 上下文管理（STM/LTM/KB 點流入 context · Compaction · Cache 協同）
│   ├── veadk-agentkit-serving-kit.md  — ServingKit 推理交付（vLLM/SGLang/Dynamo + PD 分離 + AI 網關）
│   ├── veadk-agentkit-gateway.md      — 閘道 / 網關 Gateway（AgentKit MCP Gateway + BytePlus AI Gateway + 方舟 AI 加速網閘）
│   ├── veadk-agentkit-rbac-observability.md — 安全/RBAC/PII/Audit/Observability/Guardrail/Filter
│   ├── veadk-agentkit-agent-control-rules.md — Agent 管控完全指南（六層管控 L0–L5 × 五種手段 · 分層限制總表 · IAM 三級權限 · Runtime 網絡/認證/配額 · Guardrail 四回調 + LLM-FW 五 category · MCP toolset 工具白名單 · 工具參數 allowlist · 出站 scope · Trusted MCP · Viking must/must_not · 白名單 vs 黑名單決策 · 三場景 + 15 個常見錯誤）
│   ├── veadk-agentkit-ai-concepts.md      — AI 概念百科（Dictionary/Index · 每個概念用 BytePlus/Volcengine 實例解釋 · 指返專屬 tab）
│   ├── veadk-agentkit-comprehensive-guide.md — 完全攻略（**26 Parts · 8 個分區**，同 HTML 版同源：Part 0–9 原攻略 + Part 10–25 共 25 個主題參考，已按同類主題合併成 16 個 Part）
│   ├── veadk-agentkit-comprehensive-guide.html — 同一份攻略，但**已併入全部 25 個主題文檔 → 共 26 Parts**（單一完整文檔 · Part 10–25 = 原本 Tab 內容）
│   └── veadk-agentkit-all.html        — 全部參考文檔合併（33 Tab 導覽 · 已併入《完全攻略》全部內容）
└── projects/               # 多 Agent Project Plans
    ├── invoice-pipeline.md — 5-Agent 發票處理 Pipeline (OCR→翻譯→驗證→匯總→審批)
    ├── movie-generator.md  — 5-Agent AI 電影生成器 (研究→劇本→分鏡→生成→合成)
    └── fin-mate/           — 金融研究 Agent（自建微型框架 · 兩週 · 24 Tab 概念全落地）
        └── IMPLEMENTATION_PLAN.md — 14 日排期 + 7 個核心實驗 + 完整 repo 佈局
```

每份 `.md` 都有對應 `.html`（dark-theme + TOC 側欄 + Hide/Show code），可直接用瀏覽器開。

**`references/veadk-agentkit-all.html`** — 全部參考文檔合併版（Tab 導覽 + 子頁切換 + 每 Tab 詳細解說睇頭），一個文件睇晒。共 **33 個 Tab**：原本 24 個獨立 `.md` 主題，加上《完全攻略》嘅 9 個新 Tab（前置知識 / ModelArk / AgentKit 平台 / Agent 治理與安全 ★ / **Agent 管控 ★** / 端到端實戰 / Viking AI Search / ArkClaw / 附錄速查）；攻略入面同現有 Tab 撞題嘅 Part（VeADK API、SDK、CLI）唔會另開 Tab，而係直接併入 `api`／`cli` 做多一個子頁，所以冇重複內容。

> 合併原理：`_build/build.py` 會讀 `veadk-agentkit-comprehensive-guide.html`，按 `<h1 id>` 切 Part，再把攻略自帶嘅 stylesheet 全部 scope 落 `.gx` wrapper 之下，避免污染原有 24 個 Tab 嘅 code-block 樣式。Part 2 會喺 `<h2 id="a21-gov">` 位置切開，§2.21 治理嗰段獨立成 `gov` Tab（核心版）。改完之後跑 `python3 references/_build/validate.py` 應該 PASS。

> **Part 結構嘅唯一來源：`_build/guide_parts.py`**（26 個 Part + 8 個分區 + 邊個 Part 由邊幾份來源合併）。`sync_guide_md.py`（出 `.md`）、`splice_tabs_into_guide.py`（出 HTML Part）、`group_guide_parts.py`／`group_guide_partnav.py`（分區卡 + 浮動導覽）全部 import 佢，所以 `.md` 同 `.html` 兩邊唔可能對唔上。想改 Part 標題／分區／合併關係，**只改呢一個檔**，然後跑：

> ```bash
> python3 references/_build/append_part.py          # 重建兩份文檔嘅 Part 區 + 分區表 + TOC
> python3 references/_build/build.py --combined     # 重建 all.html（新 tab）
> python3 references/_build/validate.py && python3 references/_build/doc_map.py --check
> ```

> `append_part.py` 係**冪等**嘅（跑兩次結果一樣），亦會**順手更新來源文件嘅改動** —— 唔需要再「由 pristine 重跑 pipeline」（原本四個 script 都係一次性，跑完會 abort）。

## 快速導航

| 你想做咩？ | 睇邊份文檔 |
|---|---|
| 創建新 Agent 項目 | `references/agentkit-cli.md` → `ak init` |
| 寫 Agent Code（VeADK） | `references/veadk-api.md` |
| 寫 A2A Agent（AgentKit） | `references/agentkit-sdk.md` |
| 部署 Agent | `references/agentkit-cli.md` → `ak deploy` |
| **幫 client 報價** | `references/veadk-agentkit-pricing.md`（三條收費骨幹 + 6 個 scenario） |
| **究竟有咩人哋冇** | `references/veadk-agentkit-uniqueness.md`（四層獨特位 + 行貨對照 + 一包乾 checklist） |
| **睇全部分窗 Tab（最推薦）** | `references/veadk-agentkit-all.html`（**三層導覽：8 個分區 → 33 個主題 Tab → 子頁**，唔再係 33 粒掣平鋪。<br>**分區**：定向 Orient（總覽 / AI 概念百科 / 獨特賣點 / LLM 架構 / 實用連結）· 起手 Build（CLI / API）· 能力 Capabilities（工具 / 記憶知識庫 / RAG / 資料庫 / 記憶+上下文 / Cache）· 變強 Make Better（精調+訓練 / 評估評測 / 性能）· 錢 Cost（計價 / 跨廠商對照）· 底層+安全 Infra & Safety（硬體 / ServingKit / 閘道 / 安全可觀測）· 自家模型 Seed Models（Seedream / Seedance）· **攻略完全參考 Guide Parts**（前置知識 / ModelArk / AgentKit 平台 / 治理與安全 ★ / **管控 ★** / 實戰 / Viking / ArkClaw / 附錄）） |
| **睇單一完整文檔（HTML）** | `references/veadk-agentkit-comprehensive-guide.html`（**26 Parts 已分 8 個分區** = 原攻略 10 Parts + 25 個主題合併成 16 個 Part。分區：定向 Orient · 起手 Build · 能力 Capabilities · 變強 Make Better · 錢 Cost · 底層+安全 Infra & Safety · 自家模型 Seed Models · 附錄 Appendix。左側 TOC + 分區式 Part 卡 + **分區式浮動導覽**（滾動超過 240px 先出現；8 個分區標籤 + 26 粒 Part 掣，同 Part 卡共用同一份 `NAV_SEC` 分區表）+ 全文搜尋） |
| **睇同類主題合併咗邊幾組** | ① 記憶 · 知識庫 · 資料庫 · 上下文（原 P13+P15+P16）② 計價 + 跨廠商成本對照（P18+P19）③ **優化 + 評估 完全指南**（P20+P21+P22+P23+P29）④ 推理基建：硬體 + ServingKit（P24+P25）⑤ 生成模型家族：Seedream + Seedance（P30+P31）。**內容全部保留**，每個來源變成 Part 內嘅 `##` 子章節 |
| **睇完全攻略原文（.md · 26 Parts）** | `references/veadk-agentkit-comprehensive-guide.md`（**同 HTML 版同源同深度**。目錄已分 8 個分區；順手修好舊目錄 88 條由 code fence 誤認出嚟嘅死連結） |
| **agent 管控 / 白名單黑名單 / 分層限制** | `references/veadk-agentkit-agent-control-rules.md`（**Part 25 · Tab `#ctrl`**：六層管控 L0–L5 × 五種手段 · 分層限制總表 · IAM 三級權限 · Runtime 網絡/認證/配額 · Guardrail 四回調 + LLM-FW · MCP toolset 工具白名單 · 工具參數 allowlist · 出站 scope · Viking must/must_not · 三場景 + 15 個常見錯誤） |
| **做 LoRA / 精調 / 訓練** | `references/veadk-agentkit-finetune-optimize.md`（框架層冇微調，方舟底層做）＋ `references/veadk-agentkit-training-kit.md`（TrainingKit，同 Tab） |
| **揀知識庫/記憶後端、慳 token** | `references/veadk-agentkit-vector-cache.md` |
| **搞記憶 + 上下文管理（點流入/點慳）** | `references/veadk-agentkit-memory-context.md`（STM/LTM/KB flow · Compaction · Cache 協同） |
| **揀 RAG 架構 / Ranker** | `references/veadk-agentkit-rag-guide.md`（Agentic/Corrective/Hybrid + 速度/準確/平衡/成本） |
| **查工具 / MCP / Skills** | `references/veadk-agentkit-tools-capabilities.md` |
| **優化延遲/吞吐/成本** | `references/veadk-agentkit-performance.md` |
| **做評估 / 評測** | `references/veadk-agentkit-evaluation.md`（Offline/CI/Shadow/Studio 回流） |
| **優化 + 評估 全部細節（最齊）** | `references/veadk-agentkit-optimization-evaluation-guide.md`（三層：AgentKit CLI eval loop · VeADK evaluator/prompt/RL/自反思 · ModelArk 模型評測/精調/TrainingKit · 全部 flag + 源碼實證 + 避雷 + 成本） |
| **Seedream 生圖（Deep-dive）** | `references/veadk-agentkit-seedream.md`（自家生圖家族 · Lite/Pro + 平台一覽） |
| **Seedance 生片（Deep-dive）** | `references/veadk-agentkit-seedance.md`（2.0/2.5/Fast/Mini + LAS 計費 + VideoOne） |
| **模型訓練（pre/post-training + RL）** | `references/veadk-agentkit-training-kit.md`（TrainingKit，喺「精調 / 優化」Tab） |
| **揀 GPU / VM 硬體** | `references/veadk-agentkit-hardware.md`（GPU 揀機 + 量化 + 自建 vs 托管） |
| **慳 cache 錢** | `references/veadk-agentkit-cache-management.md`（前綴/上下文/隱式 cache + output_schema） |
| **揀數據庫** | `references/veadk-agentkit-database-management.md`（本地 vs 雲端 · SQL/Vector/NoSQL · 記憶三層後端 + 檢索） |
| **推理交付 / 上線** | `references/veadk-agentkit-serving-kit.md`（ServingKit） |
| **統一模型 / 工具入口（閘）** | `references/veadk-agentkit-gateway.md`（AgentKit MCP Gateway + BytePlus AI Gateway + 方舟 AI 加速網閘） |
| **安全/合規/可觀測** | `references/veadk-agentkit-rbac-observability.md` |
| **AI 概念總覽（對比 + 幾時用）** | `references/veadk-agentkit-ai-concepts.md`（Dictionary/Index，指返專屬 tab） |
| 發票 Pipeline 設計 | `projects/invoice-pipeline.md` |
| 電影 Generator 設計 | `projects/movie-generator.md` |
| 金融研究 Agent（自建框架·兩週） | `projects/fin-mate/IMPLEMENTATION_PLAN.md` |

## Project Plans 重點

**invoice-pipeline / movie-generator** 兩個 project 都建基於 **Agent Plan Medium（¥200/月，100,000 AFP）**，包含：

- Seed 2.0 Lite/Mini (1× AFP)
- Seedream 5.0 Lite (~100 AFP/img)
- Seedance 2.0 Fast (~2,000 AFP/clip)
- 全套 Production Infra: OTel tracing, auditing, error handling, CI/CD, PII/copyright detection, cost management 等 17 項
- 獨立部署 + 獨立評估，A2A 跨 Agent 通訊
- 每個 Agent 都標明 upgrade path（將來升 Large Plan 可以直接轉 Pro model）
