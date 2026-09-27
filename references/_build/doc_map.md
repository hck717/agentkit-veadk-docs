<!-- GENERATED FILE — do not edit by hand.
     Regenerate with:  python3 references/_build/doc_map.py --md > references/_build/doc_map.md
     Verify with:      python3 references/_build/doc_map.py --check
     Sources of truth: _build/build.py (TABS / GUIDE_TABS / GUIDE_MERGES / SECTIONS)
                       _build/guide_parts.py (PARTS / SECTIONS)
-->

# Doc map — BytePlus × Volcengine Agent 文檔導覽地圖

Two superset documents cover the same corpus from two angles:

| File | Shape | Structure | Generator |
|---|---|---|---|
| `references/veadk-agentkit-all.html` | Tab view (interactive) | **33 tabs / 8 sections** | `_build/build.py` |
| `references/veadk-agentkit-comprehensive-guide.html` | Part view (linear) | **26 Parts / 8 sections** | `_build/guide_parts.py` |
| `references/veadk-agentkit-comprehensive-guide.md` | Markdown twin of the Part view | same 26 Parts | `_build/append_part.py` |

Deep links: `…all.html#<tab>` or `…all.html#<tab>:<subdoc>` (the page JS reads `location.hash`);
`…guide.html#<part-id>`.

## Tab map — `veadk-agentkit-all.html`

| Section | Tab | Label | Source doc(s) | Guide Part(s) | Deep link |
|---|---|---|---|---|---|
| 定向 Orient | `overview` | 總覽 Overview | `readme.md` | P10 | `#overview` |
| 定向 Orient | `concepts` | AI 概念百科 AI Concepts | `veadk-agentkit-ai-concepts.md` | P11 | `#concepts` |
| 定向 Orient | `uniq` | 獨特賣點 Unique Value | `veadk-agentkit-uniqueness.md` | P21 | `#uniq` |
| 定向 Orient | `arch` | LLM 架構 · 端到端 LLM Architecture | `arch.html` | P23 | `#arch` |
| 定向 Orient | `links` | 實用連結 Useful Links | `links.html` | P24 | `#links` |
| 起手 Build | `cli` | CLI / 部署 Deployment | `agentkit-cli.md` | P5 | `#cli:cli\|cfull` |
| 起手 Build | `api` | 開發 API Developer API | `veadk-api.md`, `agentkit-sdk.md` | P3, P4 | `#api:api\|sdk\|vfull\|sfull` |
| 能力 Capabilities | `tools` | 工具 / 能力 Tools & Capabilities | `veadk-agentkit-tools-capabilities.md` | P12 | `#tools` |
| 能力 Capabilities | `vc` | 記憶 / 知識庫 Memory & Vector DB | `veadk-agentkit-vector-cache.md` | P13 | `#vc` |
| 能力 Capabilities | `rag` | RAG 全攻略 RAG Playbook | `veadk-agentkit-rag-guide.md` | P14 | `#rag` |
| 能力 Capabilities | `db` | 資料庫管理 Database Management | `veadk-agentkit-database-management.md` | P13 | `#db` |
| 能力 Capabilities | `mem` | 記憶 + 上下文 Memory & Context | `veadk-agentkit-memory-context.md` | P13 | `#mem` |
| 能力 Capabilities | `cache` | Cache 管理 Cache Management | `veadk-agentkit-cache-management.md` | P15 | `#cache` |
| 變強 Make Better | `ft` | 精調 / 優化 + 訓練 Fine-tune & Train | `veadk-agentkit-finetune-optimize.md`, `veadk-agentkit-training-kit.md` | P17 | `#ft:ft\|train` |
| 變強 Make Better | `val` | 評估 / 評測 Eval & Testing | `veadk-agentkit-evaluation.md`, `veadk-agentkit-optimization-evaluation-guide.md` | P17 | `#val:eval\|oe` |
| 變強 Make Better | `perf` | 性能 Playbook Performance | `veadk-agentkit-performance.md` | P17 | `#perf` |
| 錢 Cost | `price` | 計價 Pricing | `veadk-agentkit-pricing.md` | P16 | `#price` |
| 錢 Cost | `cmp` | 跨廠商對照 Vendor Comparison | `veadk-vendor-cost-comparison.md` | P16 | `#cmp` |
| 底層 + 安全 Infra & Safety | `hard` | 硬體 Hardware | `veadk-agentkit-hardware.md` | P18 | `#hard` |
| 底層 + 安全 Infra & Safety | `serv` | ServingKit（推理交付 Inference Delivery） | `veadk-agentkit-serving-kit.md` | P18 | `#serv` |
| 底層 + 安全 Infra & Safety | `gw` | 閘道 / 網關 Gateway | `veadk-agentkit-gateway.md` | P19 | `#gw` |
| 底層 + 安全 Infra & Safety | `sec` | 安全 / 可觀測 Security & Observability | `veadk-agentkit-rbac-observability.md` | P20 | `#sec` |
| 自家模型 Seed Models | `seedream` | Seedream 圖片生 Image Gen | `veadk-agentkit-seedream.md` | P22 | `#seedream` |
| 自家模型 Seed Models | `seedance` | Seedance 視頻生 Video Gen | `veadk-agentkit-seedance.md` | P22 | `#seedance` |
| 攻略完全參考 Guide Parts | `prereq` | 前置知識 Prerequisites | *(guide)* | P0 | `#prereq` |
| 攻略完全參考 Guide Parts | `modelark` | ModelArk 模型層 ModelArk | *(guide)* | P1 | `#modelark` |
| 攻略完全參考 Guide Parts | `akplat` | AgentKit 平台 AgentKit Platform | *(guide)* | P2 | `#akplat` |
| 攻略完全參考 Guide Parts | `gov` | Agent 治理與安全 Governance ★ | *(guide)* | P2 | `#gov` |
| 攻略完全參考 Guide Parts | `ctrl` | Agent 管控 Agent Control ★ | *(guide)* | P25 | `#ctrl` |
| 攻略完全參考 Guide Parts | `tut` | 端到端實戰 Tutorial | *(guide)* | P6 | `#tut` |
| 攻略完全參考 Guide Parts | `viking` | Viking AI Search | *(guide)* | P7 | `#viking` |
| 攻略完全參考 Guide Parts | `arkclaw` | ArkClaw 企業級平台 ArkClaw | *(guide)* | P8 | `#arkclaw` |
| 攻略完全參考 Guide Parts | `apx` | 附錄 速查總表 Appendix | *(guide)* | P9 | `#apx` |

## Part map — `veadk-agentkit-comprehensive-guide.html` / `.md`

| Section | Part | Title | Part id | Source doc(s) | Tab(s) |
|---|---|---|---|---|---|
| 定向 Orient | P0 | Part 0 | `part0` | *(handcrafted)* | `#prereq` |
| 定向 Orient | P10 | Part 10 — 總覽 Overview | `part10-overview` | `readme.md` | `#overview` |
| 定向 Orient | P11 | Part 11 — AI 概念百科 AI Concepts | `part11-concepts` | `veadk-agentkit-ai-concepts.md` | `#concepts` |
| 定向 Orient | P21 | Part 21 — 獨特賣點 Unique Value | `part21-uniq` | `veadk-agentkit-uniqueness.md` | `#uniq` |
| 定向 Orient | P23 | Part 23 — LLM 架構 · 端到端 LLM Architecture | `part23-arch` | `arch.html` | `#arch` |
| 定向 Orient | P24 | Part 24 — 實用連結 Useful Links | `part24-links` | `links.html` | `#links` |
| 起手 Build | P1 | Part 1 | `part1-modelark` | *(handcrafted)* | `#modelark` |
| 起手 Build | P2 | Part 2 | `part2-agentkit` | *(handcrafted)* | `#akplat`, `#gov` |
| 起手 Build | P3 | Part 3 | `part3-veadk` | *(handcrafted)* | `#api` |
| 起手 Build | P4 | Part 4 | `part4-sdk` | *(handcrafted)* | `#api` |
| 起手 Build | P5 | Part 5 | `part5-cli` | *(handcrafted)* | `#cli` |
| 起手 Build | P6 | Part 6 | `part6-tutorial` | *(handcrafted)* | `#tut` |
| 能力 Capabilities | P7 | Part 7 | `part7-viking` | *(handcrafted)* | `#viking` |
| 能力 Capabilities | P12 | Part 12 — 工具 / 能力 Tools & Capabilities | `part12-tools` | `veadk-agentkit-tools-capabilities.md` | `#tools` |
| 能力 Capabilities | P13 | Part 13 — 記憶 · 知識庫 · 資料庫 · 上下文 Memory, Vector DB & Context | `part13-memory` | `veadk-agentkit-vector-cache.md`, `veadk-agentkit-database-management.md`, `veadk-agentkit-memory-context.md` | `#vc`, `#db`, `#mem` |
| 能力 Capabilities | P14 | Part 14 — RAG 全攻略 RAG Playbook | `part14-rag` | `veadk-agentkit-rag-guide.md` | `#rag` |
| 能力 Capabilities | P15 | Part 15 — Cache 管理 Cache Management | `part15-cache` | `veadk-agentkit-cache-management.md` | `#cache` |
| 變強 Make Better | P17 | Part 17 — 優化 + 評估 完全指南 Optimization & Evaluation | `part17-optimize-eval` | `veadk-agentkit-optimization-evaluation-guide.md`, `veadk-agentkit-finetune-optimize.md`, `veadk-agentkit-training-kit.md`, `veadk-agentkit-evaluation.md`, `veadk-agentkit-performance.md` | `#ft`, `#val`, `#perf` |
| 錢 Cost | P16 | Part 16 — 計價 + 跨廠商成本對照 Pricing & Vendor Cost | `part16-cost` | `veadk-agentkit-pricing.md`, `veadk-vendor-cost-comparison.md` | `#price`, `#cmp` |
| 底層 + 安全 Infra & Safety | P8 | Part 8 | `part8-arkclaw` | *(handcrafted)* | `#arkclaw` |
| 底層 + 安全 Infra & Safety | P18 | Part 18 — 推理基建：硬體 + ServingKit Hardware & Inference Serving | `part18-infra` | `veadk-agentkit-hardware.md`, `veadk-agentkit-serving-kit.md` | `#hard`, `#serv` |
| 底層 + 安全 Infra & Safety | P19 | Part 19 — 閘道 / 網關 Gateway | `part19-gateway` | `veadk-agentkit-gateway.md` | `#gw` |
| 底層 + 安全 Infra & Safety | P20 | Part 20 — 安全 / 可觀測 Security & Observability | `part20-security` | `veadk-agentkit-rbac-observability.md` | `#sec` |
| 底層 + 安全 Infra & Safety | P25 | Part 25 — Agent 管控：規則 · 護欄 · 白名單 / 黑名單 · 分層限制 Agent Control & Restrictions | `part25-control` | `veadk-agentkit-agent-control-rules.md` | `#ctrl` |
| 自家模型 Seed Models | P22 | Part 22 — 生成模型家族：Seedream + Seedance Generative Model Families | `part22-genmedia` | `veadk-agentkit-seedream.md`, `veadk-agentkit-seedance.md` | `#seedream`, `#seedance` |
| 附錄 Appendix | P9 | Part 9 | `part9-appendix` | *(handcrafted)* | `#apx` |

## Coverage

- tabs                        : 33 in 8 sections
- guide Parts                 : 26 in 8 sections
- source docs on the tab side : 27
- source docs on the Part side: 25
- source only in all.html     : 3 ['agentkit-cli.md', 'agentkit-sdk.md', 'veadk-api.md']
- source only in the guide    : 1 ['veadk-agentkit-agent-control-rules.md']
- tabs with no guide Part     : 0 []
- Parts with no tab           : 0 []

