# VeADK + AgentKit 方案計價指南

呢份文件教你點樣幫 client 計掂一套 VeADK / AgentKit 方案嘅月度成本。
唔止係報一個幾多錢——要拆到 **邊個層食你邊度嘅錢**、點解某個 plan 夠唔夠用、
邊啲位會 silent 超支，先報得到一張 client 信得過嘅報價單。

> ✅ **前提**：VeADK 框架、AgentKit SDK、AgentKit CLI **全部開源免費**。
> 你要幫 client 計嘅，係下面三條收費骨幹，唔係 framework 本身。

---

## 0. 核心心法 — 三條收費骨幹

所有成本都由呢三條線組成，任何方案都係「三選二或三選三」：

| 收費骨幹 | 邊層食錢 | 計費方式 | 可控性 |
|---|---|---|---|
| ① Agent Plan 訂閱 (AFP) | 模型推論 + 內置工具（搜索/記憶/知識庫） | 月費包乾（¥40–1000） | ⭐⭐⭐ 封頂、可預測 |
| ② 按量計費 (Pay-as-you-go) | 訂閱外模型、部分 API、向量模型、圖片/視頻超配額 | 逐 token / 逐張 / 逐時長 | ⭐⭐ 有上限但貴 |
| ③ 雲資源 (Cloud infra) | Runtime、Sandbox、TOS、VikingDB、PostgreSQL、Redis、流量 | 按時長 / 容量 / 流量 | ⭐ 最難估，最易爆 |

**一句總括**：Agent Plan 幫你 **封頂** 模型推流費，但 **唔包** 所有雲資源同部分 API。下面逐層拆。

---

## 1. 全部 Plan 一覽（VeADK / AgentKit / BytePlus）

成個 solution 嘅「Plan」唔止一套——由 framework 到雲平台分四層，各有唔同計量。報價前先睇呢張總表，認清**邊層免費、邊層要畀錢、計量係 AFP / 請求次數 / 按量 token**：

| 層 | 產品 | Plan | 價錢 | 計量 | 買嚟做咩 |
|---|---|---|---|---|---|
| 框架 | **VeADK** | Open source（Apache 2.0） | 免費 | — | Agent / A2A / A2UI / 記憶+KB abstraction（§1.4） |
| 框架 | **AgentKit SDK + CLI** | Open source | 免費 | — | A2aApp / init-build-deploy-launch-eval / harness / sandbox（§1.4） |
| 平台（國際） | **BytePlus AgentKit** | Free Tier（Beta） | Beta 免費（官方未公開詳價） | 官方未公開 | Runtime / 工具 / MCP / 記憶 / 觀察（§1.3） |
| 平台（國際） | **ModelArk** | 免費 Tokens | 每 LLM 50 萬免費 token · 每視覺模型 200 萬 · 企業合作 500 萬 | 逐模型 | 起步試玩，用完轉按量（§1.3） |
| 平台（大陸） | **火山方舟 Agent Plan** | Small / Medium / Large / Max | ¥40 / ¥200 / ¥500 / ¥1,000·月 | **AFP（封頂）** | 多模態 + Harness 一站式（§1.1） |
| 平台（大陸） | **火山方舟 Coding Plan** | Lite / Pro | ¥40 / ¥200·月 | **請求次數**（5h/週/月） | 純編程（Claude Code / Cursor / OpenCode…）（§1.2） |
| 平台 | 按量（Pay-as-you-go） | — | 逐 token / 張 / 時長 | 浮動 | 訂閱冇 / 超額嘅部分（§4.2、§7–§9） |

> **三樣嘢直接免費**：VeADK、AgentKit SDK/CLI、以及 BytePlus / 火山 ModelArk 嘅免費 Tokens。真正要報嘅係**平台 Plan（§1.1–§1.3）+ 雲資源三條線（§0）**——框架免費，但框架幫你行嘅每一步都可能化為錢（見 §6）。

### 1.1 BytePlus Agent Plan（訂閱制）— 四檔額度

官方來源：[火山方舟 Agent Plan 套餐概覽](https://www.volcengine.com/docs/82379/2366394)（更新 2026-07-24）；產品頁：<https://www.volcengine.com/activity/agentplan>。

| 套餐 | 月費 | 月額度 | 週額度 | 5 小時額度 | 視覺模型日額度 |
|---|---|---|---|---|---|
| **Small** | ¥40 | 20,000 | 7,000 | 2,000 | 10,000（只計圖片） |
| **Medium** | ¥200 | 100,000 | 35,000 | 10,000 | 50,000（只計圖片） |
| **Large** | ¥500 | 250,000 | 87,500 | 25,000 | 125,000 |
| **Max** | ¥1,000 | 500,000 | 175,000 | 50,000 | 250,000 |

重點：

- 圖片生成、視頻生成模型 **冇 5 小時、週額度限制**，只受 **日額度 + 月額度**。
- 語音模型、Harness（搜索等）冇 5 小時、週額度，只受 **月額度** 限制。
- 套餐有效期以自然月計算，自購買當日開始。
- 支援非七天無理由退訂（費用中心 → 退訂管理）。
- 有 2.5 折首兩月普惠活動（Small ¥9.9 / Medium ¥49.9，第三個月起原價）同邀請活動——報價前查活動頁即時價。
- **Sales 好使嘅一句**：「買 Agent Plan = 買封頂控制權。」用量唔似 token 咁逐次計，下下個月改大改細都得。

### 1.2 BytePlus Coding Plan（純編程）— Lite / Pro

官方來源：[火山方舟 Coding Plan 套餐概覽](https://www.volcengine.com/docs/82379/1925114)（更新 2026-08-14）；產品頁：<https://www.volcengine.com/activity/codingplan>。

| 套餐 | 月費 | 計量 | 5 小時 | 週 | 訂閱月 |
|---|---|---|---|---|---|
| **Lite** | ¥40（¥120/季） | 按「模型調用次數」 | ~1,200 次 | ~9,000 次 | ~18,000 次 |
| **Pro** | ¥200（¥600/季） | 同上（Lite 5 倍） | ~6,000 次 | ~45,000 次 | ~90,000 次 |

重點：

- **定位唔同**：Coding Plan 純編程（文本 + 向量化模型），講「請求次數」；Agent Plan 先有視覺/語音模型 + Harness（豆包搜索、Agent 記憶、Supabase）並改用 **AFP** 抵扣。要生圖/片/搜索 → Agent Plan；只寫 code → Coding Plan 成本結構更簡單。
- **額度獨立 + 專屬 Base URL**：Agent Plan 用 `/api/plan`（Anthropic）或 `/api/plan/v3`（OpenAI Compatible）；Coding Plan 用 Coding Plan 控制台拎嘅專屬 URL + 方舟 API Key。**混用 Key / Base URL 可能扣唔到套餐、走後付費。**
- **模型**：`ark-code-latest` 自動路由 + Doubao-Seed-2.0-Code / GLM-4.7 / DeepSeek-V3.2 / Kimi-K2.5，後續上 DeepSeek V4 系列 / MiniMax M3 / GLM-5.1 等。TPM 保障、高峰唔降速（Pro 更高）。
- 也有 Lite/Pro 2.5 折首兩月活動（¥9.9 / ¥49.9，第三個月起原價）。Coding Plan Pro 曾有贈送 ArkClaw 活動，官方已公告下線。
- **Sales 一句**：純 code 場景 Coding Plan 性價比最高（約 API 1 折）；要先玩多模態/Harness 先升 Agent Plan。

### 1.3 BytePlus 國際版（ModelArk / AgentKit）— 免費額度 + Beta Free Tier

國際 BytePlus（新加坡實體，非大陸火山方舟）另有自己嘅雲 + 計費：

| 產品 | Plan / 模式 | 內容 | 備註 |
|---|---|---|---|
| **ModelArk** | 免費 Tokens | 每款 LLM 送 **50 萬 tokens** 免費額度；每款視覺模型送 **200 萬 tokens**；企業參與合作計劃送 **500 萬 tokens** | 即「Free Tokens Only」模式，用完可喺 Activation Management 開通按量；RPM/TPM 有限 |
| **ModelArk** | Agent Plan / Coding Plan | 國際版同樣有 Agent + Coding Plan 訂閱（以 USD 計） | 面世中，價格以國際控制台為準（見來源） |
| **AgentKit** | Free Tier（Beta） | Agent 平台（runtime / 工具 / MCP / 記憶 / 知識庫 / 可觀測）公開預覽期間提供 Free Tier；有「Billing instructions in Beta」 | 官方未公開詳價，報價前向代理商拎 Beta 報價 |
| AgentKit / ModelArk | IAM 等平台能力 | Identity & Access Management 免費 | 同大陸側一致 |

要注意「Agent Plan / Coding Plan」（國際版）同大陸「火山方舟 Agent Plan / Coding Plan」**係兩嚿嘢**：Region、幣值、free tier 都唔同。報國際客戶時以 docs.byteplus.com 及國際控制台為準，唔好直接用大陸價。

### 1.4 VeADK + AgentKit（framework / SDK / CLI）— Plan 就係免費

- **VeADK**（`veadk-python`）開源 **Apache 2.0**，可自由用於商業項目；CLI 提供 `veadk deploy`（落 VeFaaS）、`veadk prompt`（PromptPilot 優化）、`veadk frontend`（A2UI 一齊起）。
- **AgentKit SDK**（A2aApp / MCP / 記憶 / 知識庫 abstraction）同 **AgentKit CLI**（`ak init/build/deploy/launch/eval/harness/sandbox`）**全部開源免費**。
- 冇「升級 Pro / 付費授權」呢回事——**真銀只嚟自佢哋幫你連去嘅平台 Plan + 雲資源**，三條線見 §0。
- 唯一要睇嘅係：部署越複雜（多 Agent、A2A、harness、sandbox），framework 幫你行嘅 model call 越多 → AFP / token 越快燒（詳見 §5–§9 同跨廠商對照 Tab）。

---

## 2. 咩係 額度 (Quota) — 消耗週期要識睇

「額度」= 你個 plan 每個期間可以燒幾多 AFP。記住分幾層：

| 額度層 | 用途 | 補充 |
|---|---|---|
| 5 小時額度 | 突發用量上限 | 用盡等 5 小時週期重置；**唔會**自動扣其他資源包 |
| 日額度（視覺模型） | 圖片/視頻生成每日上限 | 每日 00:00 釋放；圖片/視頻唔計週/5 小時 |
| 週額度 | 中長期平均用量 | 圖片/視頻唔受影響 |
| 月額度 | 終極封頂 | 用盡等下一自然月；圖片/視頻受呢個 + 日額度制 |

- **唔同額度層獨立計**：呃到圖片唔會偷到文字，反之亦然。
- Sandbox 雲資源存續期間都計費，要 `sandbox delete --tool-id <id> --force` 先停。
- **部署排雷**：`harness deploy` 同 `sandbox build/create` 會**建立雲資源 → 可能產生費用**；`sandbox build` 用 TOS / Container Registry / Code Pipeline。見 `agentkit-cli.md`。

---

## 3. 咩係 AFP（Agent Fuel Points）— 點計

AFP 係統一「燃料值」，將唔同模型×工具嘅消耗折算做一分積分。參考計算：

```
AFP 消耗 = 基礎係數（模型等級） × 分段係數（輸入長度） × (token 量 / 一萬)
```

根據第三方剖析作「參考」近似：

| 模型等級 | 基礎係數 | 分段係數（按輸入長度） |
|---|---|---|
| 極速（mini 類） | 0.5 | 0–32k: 0.67 · 32k–128k: 1 · 128k–256k: 2 |
| 標準（lite 類） | 1 | 同上 |
| 進階（code / pro / v3.2 / m2.7 等） | 5 | 同上 |

⚠️ **呢啲唔係官方公開公式**，官方只講「按模型、上下文、輸入輸出折算」。計價時**以你實戰量出嚟嘅 AFP/動作 + 控制台「用量明細」為準**。官方文件：[套餐內 AFP 抵扣規則](https://www.volcengine.com/docs/82379/2516283)。

**參考實際金額**（參考，見資料來源）：

- 極速文字生成 ≈ **0.5 AFP / 萬 tokens**
- 圖片生成 ≈ **~99–100 AFP / 張**
- 視頻生成 ≈ 按時長：Seedance 2.0 **Fast ~2,000/clip**，標準版 ~6,000/clip
- 向量（embedding）按向量維度計
- 搜索：Medium 起每月贈送免費額度（見下），超出後按量

> ⚠️ 視覺（圖片）token 數遠高於純文字——所以「OCR 睇一張圖」嘅 AFP 會遠貴過「讀 1,000 字」。

---

## 4. 模型（LLM / Vision）計費 — 主力消費

模型推流係任何方案最大出血點，分兩類：**包月（Agent Plan 內）** 同 **按量（訂閱外）**。

### 4.1 各 Plan 官方模型可用性矩陣（最重要一節）

直接回答「係咪得 Medium 以上先用到 Pro / 進階模型」：

> **答案：唔係。** 官方矩陣顯示——**文字進階模型（含 `doubao-seed-2.0-pro`、`doubao-seed-evolving`、`glm-5.2`、`kimi-k2.6`、`minimax-m2.7`、`deepseek-v4-pro`）四個 Plan 全部支持**（即連 Small ¥40 都用得）。真正嘅 tier 限制喺 **視頻生成**、**個別模型** 同 **Harness**。

來源：[火山方舟-Agent Plan 個人版套餐概覽（不同套餐支持的模型及 Harness）](https://www.volcengine.com/docs/82379/2366394)

| 分類 | 模型 | 上下文/輸出 | Small | Medium | Large | Max |
|---|---|---|---|---|---|---|
| 文本-極速 | `doubao-seed-2.0-mini` | 256k / 128k | ✓ | ✓ | ✓ | ✓ |
| 文本-標準 | `doubao-seed-2.0-lite` | 256k / 128k | ✓ | ✓ | ✓ | ✓ |
| 文本-標準 | `deepseek-v4-flash`（嘗鮮） | 1024k / 384k | ✓ | ✓ | ✓ | ✓ |
| 文本-進階 | `doubao-seed-2.1-turbo` | 256k / 256k | ✓ | ✓ | ✓ | ✓ |
| 文本-進階 | `doubao-seed-evolving` | 1024k / 256k | ✓ | ✓ | ✓ | ✓ |
| 文本-進階 | `doubao-seed-2.0-code`（即將下線） | 256k / 128k | ✓ | ✓ | ✓ | ✓ |
| 文本-進階 | `doubao-seed-2.0-pro`（即將下線） | 256k / 128k | ✓ | ✓ | ✓ | ✓ |
| 文本-進階 | `minimax-m2.7` / `minimax-m3` | 200k–512k / 128k | ✓ | ✓ | ✓ | ✓ |
| 文本-進階 | `glm-5.2 (glm-latest)` | 1024k / 128k | ✓ | ✓ | ✓ | ✓ |
| 文本-進階 | `kimi-k2.6` / `kimi-k2.7-code` | 256k / 32k | ✓ | ✓ | ✓ | ✓ |
| 文本-進階 | `deepseek-v4-pro`（嘗鮮） | 1024k / 384k | ✓ | ✓ | ✓ | ✓ |
| 文本-進階 | **`kimi-k3`** | 1024k / 128k | ❌ | ✓ | ✓ | ✓ |
| 向量化 | `doubao-embedding-vision` | 128k | ✓ | ✓ | ✓ | ✓ |
| 圖片生成 | `doubao-seedream-5.0-lite` | — | ✓ | ✓ | ✓ | ✓ |
| 視頻生成 | `doubao-seedance-1.5-pro`（即將下線） | — | ❌ | ✓ | ✓ | ✓ |
| 視頻生成 | **`doubao-seedance-2.0`** | — | ❌ | ❌ | ✓ | ✓ |
| 視頻生成 | **`doubao-seedance-2.0-fast`** | — | ❌ | ❌ | ✓ | ✓ |
| 視頻生成 | **`doubao-seedance-2.0-mini`** | — | ❌ | ❌ | ✓ | ✓ |
| 語音模型 | `doubao-seed-tts-2.0` / `doubao-seed-asr-2.0` | — | ✓ | ✓ | ✓ | ✓ |
| Harness | 專業數據集 | — | ✓ | ✓ | ✓ | ✓ |

> ⚠️ **呢個係報價嘅關鍵**：`Seedance 2.0` 全系列（2.0 / fast / mini）**只有 Large 同 Max 先用得**。Medium 只支援 `seedance-1.5-pro`（仲要「即將下線」）。即係話——**想用新嘅 Seedance 2.0 做視頻 → 起碼升 Large（¥500/月）**，唔係 Medium。

> ⚠️ **模型上線但唔一定支援**：`deepseek-v4-flash/pro` 同 `kimi-k3` 等係「嘗鮮/體驗版」，如遇訪問擁擠或頻繁限流，官方建議切換其他模型。`doubao-seed-2.0-pro` / `2.0-code` / `seedance-1.5-pro` 標示「即將下線」，新項目唔好用。

> 📌 **模型 deep-dive 另開 tab**：Seedream 全家族（Lite/Pro 能力 + 國際 `dola-*` 定價）→ **seedream tab**；Seedance 全家族（2.0/2.5/Fast/Mini + LAS 按秒計費 + VideoOne）→ **seedance tab**。呢度淨係 Plan-配額矩陣。

### 4.2 按量計費（訂閱外）

Agent Plan 冇嘅模型或超配額嘅部分：火山方舟產品頁參考價（2026）：`doubao-seed-evolving` 約 **¥6/百萬輸入、¥30/百萬輸出**（見來源）。

---

## 5. 工具 / MCP / Harness 計費

| 工具 | 計費 | 備註 |
|---|---|---|
| **內置 Harness：豆包搜索** | Medium 起每月送免費額度（約 **500 次/月**）；超出扣 AFP | 包喺 Agent Plan 入面，誇量至爆 |
| **web_search**（VeADK built-in） | 計 AFP 或隨餐配額 | 視套餐同搜索類型 |
| **記憶 / 知識庫** | 向量化（embedding）+ 儲存 | 屬第三條線，詳§8 |
| **MCP tools** | **本身免費**；外部 API 支出 + 每次 round-trip 嘅 model call | 唔直接扣，但會推高 token |
| **自訂 Python tool** | 代碼免費；執行時 model call 先計 | 一個 tool call ≈ 一次 model round trip |

> **MCP 計費重點**：MCP server 免費掛進去，但你每次 tool call 都係一次 model round trip。工具越多、context 越長，越食 token（尤其 128k+ 段 ×2 倍率）。想慳：工具 return 要短、唔好將成個文件丟入 context。

---

## 6. Framework（VeADK / AgentKit SDK / CLI）計費

| 組件 | 成本 |
|---|---|
| `veadk-python`（Agent、Runner、A2A、A2UI、記憶、知識庫 abstraction） | **免費**（open source） |
| `agentkit-sdk-python`（SimpleApp / MCPApp / A2aApp） | **免費** |
| `agentkit` / `ak` CLI（init/build/deploy/launch/eval/harness/sandbox） | **免費** |
| `agentkit harness`（zero-code） | **免費**產生 Runtime 用雲資源先有錢 |

> 結論：framework 本身免費。但 ① 多 Agent loop（交談）→ 多次 model call；② summary/retry/compaction 都係額外 model call。「框架免費，但框架幫你做嘅每一步都可能化為 AFP。」

---

## 7. Sandbox / 代碼執行計費

參考 `ak sandbox`：

- `sandbox build` 用 TOS + Container Registry + Code Pipeline → 建立產生費用；失敗會留 buffer `.agentkit/sandbox/build/`。
- `sandbox create` 分配**雲端計算資源**（規格、網絡、鏡像、TOS 掛載），資源存續期間持續計費。唔用就 `sandbox delete --tool-id <id> --force`。
- 估算基準：火山引擎「計算資源約 **0.45 元 / CU / 小時**」，Sandbox 規格倍數看控制台（見來源）。

> ⚠️ 唔好俾 client 開住 Sandbox 掛 —— 每小時燒錢，係橫軸最易爆嗰條。

---

## 8. 記憶 (Memory) / 知識庫 (Knowledge Base) / 儲存計費

| 資源 | 計費 |
|---|---|
| TOS（物件儲存） | 官方產品頁 **0.0015 元/GB/小時** 儲存；流量另計 |
| VikingDB / OpenViking（向量） | 儲存 0.0015 元/GB/小時 起 + 向量模型按量；查詢/容量看控制台 |
| PostgreSQL / MySQL / Redis（自架） | 雲資源小時費（RDS/CVM），或用火山托管 |
| 向量化（embedding） | Agent Plan 內用 `Doubao-embedding-vision` 計 AFP；訂閱外按量 |
| 記憶首次寫入（ContextBucket/Set 建立） | 可能觸發 TOS 資源設定 → 有計費 |

> LTM / KB 用咗 embedding + 儲存 —— **「長期記憶 + 知識庫」係第三條線嘅主力**，尤其 retention 365–730 日（見 invoice / movie 計劃）。

---

## 9. 部署 / Runtime 計費

- `ak deploy` / `harness deploy`：build 鏡像 + create/update Runtime → **產生雲資源**（網關、API Gateway、IAM、VeIdentity 都可能計費）。
- Frontend：跑 serverless 網關，預設**復用現有網關**（唔會新開，避免佔用網關配額）；要固定先 `frontend.gateway`。
- A2A 服務之間走 internal，冇出 public 流量費。
- **估價概念**：Runtime 數 × 時長 × 小時費率 + 網關流量。開幾多個 Agent 就幾多份。

> 多 Agent 平行（例如 movie 12 scenes 同時 seedance）會同時食最多 model + 多份 runtime。

---

## 10. 安全 / 訪問控制 / 部署嘅「隱性成本」

安全本身**幾乎唔直接收費**（AuthRequestProcessor、IAM、內容過濾 pre/post、A2A mTLS 都係 overlay），但會**間接加大模型消耗**：

| 項目 | 間接成本 |
|---|---|
| Content-safety（pre / post filter） | 每張 flow 多一次模型/接口 call，如 |
| A2A + AuthRequestProcessor | 每次 `run()` 前驗證——唔貴但次數多會累積 |
| Audit log（chain-hash，invoice 保留 7 年） | 寫入 PostgreSQL + TOS archive → 儲存計費 |
| PII scan（mask / flag） | 每次多一次 API call / token 處理 |
| RBAC / rate-limit / secrets(Vault) | 純軟件，冇直接雲費（如果自架 Vault 按小時） |
| Shadow eval（10% 流量） | **+10% 模型消耗**，等於額外 AFP |

> 報價時可以講「安全集中做，唔單獨開一條」，但 audit + shadow eval 一定要計入「隱性 +%」。

---

## 11. 對比：「封頂」vs 其他平台

參考：OpenAI SDK 免費但 **按 token 無上限**（GPT-5.4 ≈ \$2.5/\$15 每百萬）；LangSmith Plus \$39/座/月 + 超量；LangGraph Cloud ~$35/月。

| | VeADK + AgentKit（Agent Plan） | OpenAI Agents SDK | LangGraph / LangSmith |
|---|---|---|---|
| Framework 本身 | 免費 | 免費 | 免費 |
| **計費** | **AFP 訂閱（¥40–¥1000 封頂）** | 每 token / 無上限 | LangSmith \$39/座 + Cloud |
| 可預測性 | 高（封頂） | 低（multi-agent 長 context 易爆） | 中（trace 講超量） |
| 多模態 | SEED + Seedream/Seedance 一條包 | 需另外買工具（web search $10/1k） | 唔直接包 |
| 部署 + 監控 | 一體（`ak deploy` + OTel） | 自行搭 | LangGraph Cloud |

> Sales 說話術：「Agent Plan = 買斷推量 INF 天花板。OpenAI 你個 multi-agent 每次 handoff 都多一筆 token 錢；呢邊一包乾做，用勁先要你 upgrade。」

---

## 12. 六個 Scenario 實例計數

---

### S1. 企業發票 Pipeline（5-Agent A2A，每日 20 批 × 5 張）

沿用 `projects/invoice-pipeline.md` 估算：

| 步驟 | 模型 | AFP/批次 |
|---|---|---|
| A1 OCR（視覺 Lite） | Seed 2.0 Lite | ~25 / 5 張 |
| A2 翻譯 | Seed 2.0 Mini | ~8 |
| A3 驗證（視覺） | Seed 2.0 Lite | ~25 |
| A4 匯總 | Seed 2.0 Mini | ~5 |
| A5 審批（A2UI HITL） | Seed 2.0 Lite | ~3 |
| **小計** | | **~66 / 批** |

每月估算：

```
20 批/日 × 66 = 1,320 AFP/日
1,320 × 22 工作日 ≈ 29,040 AFP/月 ≈ ~29% of Medium (100,000)
剩餘精力：~71,000 AFP ← eval / 其他 / 升級
```

**報價**：Agent Plan **Medium ¥200/月** 綽綽有餘，留 ~71%。日後想提升 OCR 準確度，獨立換 A1 做 Pro（~3×）都唔會爆。

---

### S2. AI 電影生成（12-scene，movie-generator）

沿用 `projects/movie-generator.md` 估算，但要**以 §4.1 官方矩陣修正**：Seedance 2.0 Fast 只係 **Large/Max** 先用得（Medium 只支援 1.5-pro 且即將下線）。

| 步驟 | AFP/项目 |
|---|---|
| A1 Research（web_search、Lite） | ~50 |
| A2 Script（Lite） | ~80 |
| A3 Storyboard（Mini + 12×Seedream ~100） | ~1,220 |
| A4 Video 12 scenes（Seedance 2.0 Fast ~2,000/clip） | ~24,000 |
| A5 Merge | 微 |
| **小計** | **~25,371 / 项目（10%）** |

每月產能（Large）：1 部 ≈ 25,371（約 10% of Large 250k）；建議上限 6–8 部 → 75–80%。

**報價**：要做 Seedance 2.0 片 → **Large ¥500**（Start 有，Medium 用唔到）。若只係做圖像 + 文字 → Medium 即可。Omnihuman / DreamActor 都要另外睇支援（獨立計費）。

---

### S3. 企業知識庫 RAG Chatbot（500 Q / 日）

- 模型：`Seed 2.0 Mini`（純文字）+ `Doubao-embedding`（向量）
- 每 Q 約 input 2,000 + output 500 tokens → 用~0.005 AFP/萬近似：
  `2,500 × 0.005 ≈ 0.125 AFP/Q`
- 每月：11,500 Q/月 ≈ **~1,400 AFP** — 只食 1.4% of Medium

但 **真成本在「知識庫儲存 + 向量化」**（第三條線）：10,000 docs → GB×小時 + 向量計量。

**報價**：純文字 RAG → **Small ¥40** 頂住；要加搜索免費額 → Medium。

---

### S4. Zero-code Harness：內部 FAQ 支援 Agent

- `harness.yaml`：一個 model + 搜索 + KB 綁定，唔使 custom code
- 用量極低（200 Q/日，每 Q ~200 tokens）

每 Q ≈ 0.1–0.2 AFP → 每日 ~40 → 每月 ~1,200 AFP

**報價**：**Small ¥40** 起步已經行——中小企業「唔使寫 code」嘅 killer pitch。

---

### S5. 企業級客服：5-Agent + MCP + Sandbox（中量）

場景：客服諮詢 + 退換貨，Agent 之間交到 → MCP 掛 internal CRM → 偶爾 Sandbox 分析。

| 項目 | 每月 |
|---|---|
| 聊天/查閱（A1–A4） | ~25,000 AFP |
| MCP@CRM（每次 round-trip 成大 context） | ~8,000 AFP |
| Sandbox 分析（每 2-hr 會話，10 次/月） | 雲端 ≈ 0.45元/CU·hr × 40h ≈ ¥18（第二條線） |
| 記憶/知識庫 長期 retention | 儲存 ≈ ¥10–30/月 |
| Eval / CI eval | ~3,000 AFP |
| **總計** | **~36,000–50,000 AFP + ¥30–60 雲** |

**報價**：接近 Medium 上限→直接 **Large ¥500** 穩陣；雲資源部分按「時長」報價（開 buffer）。

---

### S6. 多模態 UGC 內容平台（圖/視頻：Medium vs Large）

先睇 §4.1：**Seedance 2.0 全系列只係 Large/Max 先用得** —— 呢個場景只要有影片，就**唔可能用 Medium**，直接鎖 Large。

- 每日 200 張圖（Seedream）+ 20 條 5s video
- `200 img × 100 = 20,000 日`；video `20 × ~400 = 8,000 日` → **~28,000 AFP/日**

**Large（25 萬/月）：** 日 28k ≈ 11% 月額度，圖片日額度 125k > 28k → 穩行。**但留意日額度**：圖片日額度 125k，爆日就 Max 或停 burst。**Max（50 萬/月）：** 更高 buffer，但貴一倍，除非日度極高先需要。

**報價心法**：**多模態 = 日額度為王 + 先查官方矩陣（§4.1）鎖死 tier**。做 video → 起手就報 Large，唔好報 Medium 之後先俾人打返轉頭。

---

### 速查：邊個 Scenario → 邊個 Tier

| Scenario | 月爆發 | 建議 Plan |
|---|---|---|
| S1 發票 20批/日 | ~29k | Medium ¥200 |
| S2 電影 12-scene / 部 | ~25k/部 | **Large ¥500**（Seedance 2.0 先有） |
| S3 RAG 文字 chatbot | ~1.4k | Small ¥40 |
| S4 Harness FAQ | ~1.2k | Small ¥40 |
| S5 客服 5-Agent + MCP + Sandbox | ~36–50k | Large ¥500 |
| S6 UGC 多模態（圖+video） | ~28k/日 | **Large ¥500**（有 video 即鎖 Large） |
| S6' UGC 純圖（無 video） | ~20k/日 | Medium ¥200 |

---

## 13. 幫 client 報價 6 步流程

1. **畫 Agent 圖**：每個 agent 幾多步、幾多 model call、有冇 loop 回頭。
2. **估 token**：每 turn 的 input / output + 上下文長度（影響分段係數）+ 有冇圖片。
3. **計 AFP**：用「每動作 AFP 估算」（上表）乘日常量；再用控制台實測校正。
4. **拆雲資源**：runtime 小時、sandbox、儲存/向量、流量自己計，唔混入 AFP。
5. **加 buffer + 封頂機制**：例如估到 60％ 計劃 7 成，97% 才升 tier；內部保留 ~20% buffer。
6. **報「兩個數」**：正常預期（e.g. Medium ¥200/月）+ 爆量方案（e.g. Large ¥500/月），同 client 講「超額知會」。

> ⚠️ 每張報價都要標「**估算**，以控制台用量明細/計價器為準」。Agent Plan 數字會跟官方變，唔好當永恆。

---

## 14. 資料來源（含日期，方便日後核對）

| 來源 | URL | 日期 |
|---|---|---|
| 火山方舟 Agent Plan 套餐概覽（四檔/額度/各 Plan 模型可用性矩陣） | https://www.volcengine.com/docs/82379/2366394 | 更新 2026-07 後 |
| 火山方舟 Agent Plan 產品/活動頁 | https://www.volcengine.com/activity/agentplan | 2026-05 上場 |
| 火山方舟 Coding Plan 套餐概覽（Lite/Pro 額度） | https://www.volcengine.com/docs/82379/1925114 | 更新 2026-08 |
| 火山方舟 Coding Plan 產品/活動頁 | https://www.volcengine.com/activity/codingplan | 2026-04 上場 |
| 火山方舟「訂閱 \[Agent/Coding Plan\]」總索引 | https://www.volcengine.com/docs/82379/1925114 | 頁面日 |
| BytePlus ModelArk（免費 Tokens：500K/LLM、2M/視覺、企業 5M） | https://www.byteplus.com/zh-CN/product/modelark · docs.byteplus.com/en/docs/ModelArk/1159200 | 頁面日 |
| BytePlus ModelArk Activation Management / Free Tokens Only 模式 | https://docs.byteplus.com/en/docs/modelark/1159200 | 2026-06 更新 |
| BytePlus AgentKit（Beta Free Tier / Billing instructions in Beta） | https://docs.byteplus.com/en/docs/agentkit/Billing_instructions_during_public_preview | 2026-04 更新 |
| Coding Plan 收費/額度規則解析 | https://www.volcengine.com/article/37969 · /37388 · /37937 | 2026-04 |
| Coding Plan vs Agent Plan 選擇指南 | https://codepick.dev/zh/guides/ark-coding-plan-guide/ · watermelonwater.tech | 2026-05 |
| 火山方舟產品頁（定價 / 免費額度 / 儲存） | https://www.volcengine.com/product/ark | 頁面日 |
| 方舟套餐內 AFP 抵扣規則 | https://www.volcengine.com/docs/82379/2516283 | 跟套餐概覽 |
| CSDN 深度測評（模型矩陣 + Harness 歸納） | https://adg.csdn.net/6a6160b8662f9a54cb935ac9.html | 2026-07-22 |
| weste.net Coding vs Agent Plan 對比（AFP 系數參考） | https://www.weste.net/2026/05-10/CodingPlan-AgentPlan.html | 2026-05-10 |
| codepick.dev Agent Plan 解讀 | https://codepick.dev/zh/guides/ark-agent-plan/ | 2026-05-13/28 |
| aiproducthub 方舟 Agent Plan 導覽 | https://aiproducthub.cn/sites/方舟-agent-plan.html | 2026-05-18 |
| mindwave-ai 火山引擎 Agent Plan 報導 | https://www.mindwave-ai.xyz/news/2026/05/agent-plan-ai-1974/ | 2026-05-11 |
| OpenAI Agents SDK 定價分析 | https://comparedge.com/tools/openai-agents-sdk/pricing | 2026-07-08 |
| LangSmith / LangChain 定價 | https://aitrendtool.com/tools/langchain · https://www.langchain.com/pricing | 2026-07-12 |
| OpenAI API 定價 | https://developers.openai.com/api/docs/pricing | 頁面日 |
| GPT-5.4 官方費率/對照 | https://runapi.ai/zh-HK/openai-api-pricing | 2026-06-18 |

> **使用方法**：AF-FP 真實值 = 用 billing API / 控制台「用量明細」校正。本文數字（尤其單一動作比例）屬**參考/估算**，報價需加免責。

---

*Last audit date: 2026-08-09 · 一定對正官方套餐頁變動（次 2026-07 先後更新）再賣。*