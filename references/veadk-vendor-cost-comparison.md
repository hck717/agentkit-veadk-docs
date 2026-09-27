# VeADK + AgentKit 跨廠商全棧成本對照（BytePlus vs Azure / AWS / Google / DeepSeek / Qwen / 混元 + 其他）

呢份文件係「**同一個 agent，十個平台，五層錢**」嘅逐項對照。唔淨係比模型 token 價——仲比你落咗 RAG、MCP 工具、guardrails、PII 脫敏、RBAC、GPU、微調、優化之後，個個月條數點計法。

> **先讀 4 條心法**：
> 1. **平台收錢係分層數**：model token / embedding / RAG-KB / hosting+tools / safety+observability+fine-tune——五張單，唔好淨睇第一張。
> 2. **同一個開源 model，host 唔同價差可達 10×**（Llama 3.3 70B：OpenRouter ~$0.10/$0.32 到 Cerebras $0.85/$1.20）——真錢與其話「揀好 model」，不如話「揀好房東」。
> 3. **BytePlus 嘅打法唔係「最平 token」**，係「**封頂月費 + 多模態 + GPU/sandbox 已包 + 隱式 cache**」——sell cost-per-outcome 同可預測性，唔係玩標價競賽。
> 4. **所有 Hosted agent 平台其實都係「token + infra + safety」三線收貴**：Azure / Bedrock / Gemini Enterprise / ADP 全部一樣，分別只係「封頂定浮動」。

---
**計價時點與名義對照**
- 本文件價格以 **2026-08-16** 為時點；**DeepSeek 峰谷價 2026-08-17 00:00（北京）生效**。
- 名義 FX：**¥1 ≈ $0.14**（報價時請用即日匯率）。RMB 平台標 ¥、國際平台標 $。
- 所有數字係公開資訊整理，**官方 $-blank 位（Azure / Google 主頁）用第三方 mailout 補**，大額報價前一定去官網 rate 再 check。定性描述（合規/定位）標「要確認」。

---

## 0. 快睇：邊個平台，邊個身份

| 平台 | 收費形態 | 一句定位 | 邊個啱 |
|---|---|---|---|
| **BytePlus 火山方舟** | Plan 封頂（¥40–1000）+ 超額按量 | 封頂、多模態、GPU 已包 | 要可預測月費、要 MVP 快、中文/粵語 |
| **Azure OpenAI / Foundry** | 純 token + runtime + tools | GPT-5 家族 + 整套 Azure 治理 | 全球盤、已有 Azure、要 Batch −50% |
| **AWS Bedrock** | token + KB floor + guardrails | 62+ model、深 AWS 整合 | 已有 AWS、多 model 唔想綁死 |
| **Google Gemini / Agent Platform** | token + Agent Compute/Memory | 平價 Flash + 最平 Agent runtime | 已用 GCP、長文 context、低價 cache |
| **DeepSeek 官方** | 純 API（無 hosting） | 標價最平 + 峰谷再 ×0.5 | 壓量、cache 密集、唔介意自組排程 |
| **Alibaba 百煉** | token + 部署 MU + 免費額度 | Qwen 生態 + 90日1M free | 淘系/大陸、要 Qwen 全系 |
| **Tencent 混元 / ADP / 元器** | 訂閱 (¥88–4880) + PU 浮動 | 工具佢收得貴 | 已用騰訊雲、域內 (元器免費) |
| **Zhipu GLM** | token | GLM 5/5.1 | 智譜系、中文推理 |
| **Mistral La Plateforme** | token, batch −50% | 歐系、細行 | 歐洲主權、細中模型 |
| **Groq / Cerebras / DeepInfra / 聚合** | token | 開源 model 快 / 平 / 自動路由 | 開源系、latency 敏感、想自組最平 |

---

## 1. 五層成本框架（同一個 agent，五張單）

| 層 | 收咩錢 | 幾時有 | 邊個平台最突出 |
|---|---|---|---|
| ① **Model tokens** | in / out / cache-read | 一定有 | DeepSeek、nano/Micro 級最平 |
| ② **Embedding** | 每 1M token 向量化 | RAG 先有 | Gemini ($0.15–0.20) 平過 OpenAI t3-large ($0.13) 代理人用 t3-small $0.02 |
| ③ **RAG / 知識庫** | KB 儲存 + 每 query 額外 input token | RAG 先有 | Bedrock KB 有 $345/月底（OpenSearch）；Azure File Search $0.10/GB·日 |
| ④ **Agent hosting / runtime / tools** | vCPU·h / session / 工具次數 | 要做 agent | Google Agent Compute $0.085/vCPU·h（50h free）最平；Azure Code Interpreter $0.03/session |
| ⑤ **Safety + Observability + Fine-tune** | guardrail 每 request / PII / 監控 / 微調 | 生產先有 | BytePlus LLM-FW 內置；Azure Defender $0.80/1M·月；各自加 0.5–10% |

> **報價第一句**：問 client「你嘅 agent 係咪 RAG？多模態？要唔要 guardrail？」——三個問題決定五層入面三層有冇錢收。

---

## 2. 同一個 Model，唔同 Host：價差 10× 嘅真相

### 2.1 Llama 3.3 70B（Meta 開源，12 個 host）

| Host | in $/1M | out $/1M | 快（tok/s 約） | 備註 |
|---|---|---|---|---|
| OpenRouter（路由） | $0.10–0.32 | 低至 $0.32 | — | 淨係 routing，另收 5.5% fee |
| DeepInfra | $0.35 | $0.35 | 27 | 最平意志價 |
| Nebius（Fast） | $0.42 | $0.42 | 80 | EU 數據主權 |
| Hyperbolic | $0.40 | $0.40 | 35 | — |
| **Groq** | **$0.59** | **$0.79** | **315** | LPU，RT 對話 |
| SambaNova | $0.60 | $1.20 | 294 | — |
| **AWS Bedrock** | $0.72 | $0.72 | 190 | AWS 整合 |
| **Cerebras** | **$0.85** | **$1.20** | **~2000** | 岩 size 模型最快 |
| Fireworks | $0.90 | $0.90 | 50 | 最低 TTFT |
| Together | $1.04 | $1.04 | 45 | 微調基建最好 |
| Cloudflare Workers AI | 免費（每日配額） | 免費 | 30 | 原型 |

> **結論**：同一個 model，OpenRouter ↔ Cerebras 價差 ~4–10×。**買嘅係 hosting/速度主權**，唔係 model。

### 2.2 DeepSeek V4-flash（同一個 model，4 個中國 host）

| Host | in ¥/1M | out ¥/1M | cache ¥/1M | 備註 |
|---|---|---|---|---|
| **DeepSeek 官方**（現行，8/17 前） | ¥1 | ¥2 | ¥0.02 | 最快出新模型，卻 503/429 傳聞 |
| **官方**（新峰谷 off-peak，8/17 起） | ¥1.5 | ¥4.5 | ¥0.05 | 離峰先平 |
| **官方**（高峰 北京9-12,14-18） | ¥3 | ¥9 | ¥0.10 | 高峰 ×2 |
| **火山方舟** | ¥1 | ¥2 | ¥0.2 | 同官方現行價，企業級並發/穩定，TTFT 低 |
| **阿里百煉** | 同官方 | 同官方 | 同官方 | 跟價 |
| 硅基流動 SiliconFlow | ~¥1 | ~¥2 | ~¥0.1 | 價格屠夫，穩定度一般 |
| 七月/七牛等聚合 | 折 4 折（年包） | — | — | 多 model 統一 key |

> **賣點**：火山方舟用接近官方價托管 DeepSeek（v4-flash ¥1/¥2），但嗰樣嘢官方買唔到嘅係「企業並發 + 穩定 → sell」。

### 2.3 其他開源/同系跨 host（快照）

| Model | 最平 host | 中間 | 最貴/最靚 host |
|---|---|---|---|
| **gpt-oss-120b**（OpenAI 開源） | DeepInfra $0.17 | **Cerebras $0.35/$0.75** · **Groq** $0.60 (out) | — |
| **Qwen3 235B A22B** | Hyperbolic $0.40 | **Cerebras** $1.20 (out) | 百煉 MU ¥216/hr 自托管 |
| **Qwen3 32B** | 百煉 open ¥2/¥8 → 單機 | **Cerebras $0.40/$0.80** · Groq 有 | 百煉 MU ¥400/hr |
| **DeepSeek-R1**（滿血） | 方舟 ¥4/¥16（同官方） | Bedrock $? · Azure $3.5/14 級 | chain-of-thought 實耗 3–5× |
| **Mistral Large 2** | La Plateforme ~$0.9/$2.2 | **Bedrock $3/$9** | — |

> ⚠️ 呢啲 price 每幾個月郁一次（2026 開源市場好「卷」）；引用前 refetch。**同 model 歸同 model，hosting 先係性格。**

---

## 3. 逐廠檔案（每個：模型 5–7 隻 cheap→top + 完整 line items）

### 3.1 BytePlus 火山方舟（豆包 Doubao + seed）

**Model tokens（¥/1M，2026 ai.volcengine.com 定價）**

| 模型 | in ¥/1M | out ¥/1M | 一句 |
|---|---|---|---|
| doubao-seed-2-0-mini | ¥0.2–0.8 | ¥2–8 | 極速文字，0.5× 係數 |
| doubao-seed-2-0-lite | ¥0.6–1.8 | ¥3.6–10.8 | 混合層 |
| doubao-seed-2-1-turbo | ¥3 | ¥15 | 主推/編碼小子 |
| doubao-seed-2-1-pro | ¥6 | ¥30 | 推理 |
| doubao-seed-evolving | ¥6 | ¥30 | Coding/Agent 旗艦，256K ctx |
| Seedream（圖） | ≈100 AFP/張 | — | 圖很貴，問多模態先 |
| Seedance 2.0（video） | ≈2,000 AFP/段 | — | 只有 Large/Max 可用 |

**Agent 打包：Agent Plan（AFP）**：Small ¥40/20k · Medium ¥200/100k · Large ¥500/250k · Max ¥1,000/500k AFP（月度window）。Harness ≈500 次/月 free → 超出扣 AFP；Sandbox 計 CU·hr（雲線）；記憶/KB 儲存按 GB·hr；向量化用 doubao-embedding-vision 計 AFP；LoRA 微調收返 AFP/按量。

**其餘層**：隱式 cache（cached input ≈ 標準價 ~20%，自動、不可關）；GPU/sandbox **已入 plan**（唔好另加）；LLM-FW（Prompt 過濾）內置近免費；PII/RBAC（IAM/AK-SK/JWT/審計）見 sec tab；APMPlus observability 另購。
**定位**：封頂、多模態獨家（Seedance/Seedream 你唔使離開佢）、GPU 已包。弱點：大陸數據主權、超額浮動、國際 SLA/文檔較弱。

### 3.2 Azure OpenAI / AI Foundry / Agent Service

**Model tokens（$ /1M，Global PAYG，2026）**

| 模型 | in | 平價 cache-in | out | Batch −50% |
|---|---|---|---|---|
| **GPT-5-nano** | $0.05 | — | $0.40 | ✓ |
| **GPT-5-mini** | $0.25 | $0.025 | $2.00 | ✓ |
| **GPT-5** | $1.25 | $0.125 | $10.00 | ✓ |
| GPT-5.4 | $2.50 | $0.25 | $15.00 | ✓ |
| **GPT-5 Pro** | $15.00 | $1.50 | $120.00 | ✓ |

*(註：GPT-5.4 系列 $2.5/$15 參與，5.5 更新——用 dl-chat 最新 rate。Batch Global 50% off；Regional 貴 5–10%。)*

**其餘層**
- Embedding：t3-small $0.02 / t3-large $0.13（1M tokens）；File Search 預設 t3-large。
- RAG/KB：**File Search $0.10/GB-vector·day（1GB free）** + 每 query KB 內容當 input token。
- Tools/MCP：**Code Interpreter $0.03/session**（每人 1 小時窗口）；Web Search / Custom Search 按 1K transactions 收費；Toolbox 集中 creds/policy（工具照收）；Agentic 官方 model 唔另收 framing。
- Hosting：hosted agents = **container compute（vCPU·h + GiB·h）**，per-session sandbox、scale-to-zero（冇流量冇錢）；Code Interpreter 唔跟 agent subnet。
- Guardrails：**Content Safety $0.75/1K text records + $1.50/1K images**（免費 5K/月）；Prompt Shields 可跟 API。
- PII：可用 Azure AI Language PII（按 text record）或 DLP 類。
- Security/RBAC：Entra ID 角色免費（Foundry User/Owner…）；**Defender for AI Services $0.80/1M tok·month**（30 日/75B tok free）；agent 級 posture 自 2026-07 轉 Microsoft Agent 365 許可以外另收。
- GPU/Throughput：**PTU 約 $2,448/PTU·月**（~$3.35/hr），sustained 慳 70%。
- Fine-tune：SFT 按「training tokens × epoch」**GPT-4.1 $2.00/1M**、4o-mini $3.30/1M、4o $25/1M；**hosting $1.70/hr**（Standard/Global Standard）；o4-mini RFT $100/hr + grader tokens；Developer tier 免 hosting（冇 SLA，24h 自刪）。
- 優化：prompt cache 自動（$0.025–0.50 級），fine-tuned model 都享 cache −50% 級。
**弱點**：靜態 $ 標籤易漏（hosting/PTU/Defender），三套 portaling。

### 3.3 AWS Bedrock（含 AgentCore / Agent / Knowledge Bases）

**Model tokens（$ /1M，on-demand 2026）**

| 模型 | in | out | 一句 |
|---|---|---|---|
| **Amazon Nova Micro** | $0.035 | $0.14 | 全平台最平 |
| Nova Lite | $0.06 | $0.24 | 多模態 |
| **Llama 4 Scout** | $0.17 | $0.36 | 開源長文 |
| Llama 4 Maverick | $0.50 | $0.80 | — |
| **DeepSeek V3.2** | $0.62 | $1.85 | 平第三方 |
| **Nova Pro** | $0.80 | $3.20 | 自家主打 |
| Claude Haiku 4.5 | $1.00 | $5.00 | 平 Claude |
| **Claude Sonnet 4.6** | $3.00 | $15.00 | 最流行 |
| Claude Opus 4.8 | $5.00 | $25.00 | 高階 |
| Nova Premier | $2.50 | $12.50 | 旗艦 |

*(傳：Claude Fable 5 $10/$50 最貴。MARS 已整批 50%、cache write/read、路由 −30%。)*

**其餘層**
- RAG/KB：**OpenSearch Serverless 底價 2 OCU × $0.24/h ≈ $345/月（零 query 都照收）**；可轉 S3 Vectors（−90%）。每 query：embed + vector scan + generation **amplification 4–8×**。
- Tools/MCP：**Bedrock Flows $0.035/1K node-transitions**；AgentCore Policy（$/authorization）＋NL policy text → Cedar 轉換按 1M user-input tokens；AgentCore **Web Search $7/1K queries**；KB input tokens $0.13/1K。
- Guardrails：content/denied **$0.15/1K text-units**、PII(sensitive) **$0.10/1K**、接地 **$0.10/1K**、automated reasoning **$0.17/1K**、img $0.00075/張；InvokeGuardrailChecks API 減價版 content $0.07 / prompt-attack $0.08。**in+out 各計一次**。
- PII：**Comprehend Detect PII $0.0001/100-char unit（≈$1/1M chars，300-char min）**；Contains PII $0.000002/unit 用嚟做 triage。
- Hosting：AgentCore Runtime microVMs（consumption，idle 免費，active 俾 CPU+memory）；Instances = EC2 + 管理費 per-second。
- Security/RBAC：IAM free；Guardrails + CloudTrail；CloudWatch logs $0.50/GB ingest、$0.03/GB store。
- GPU：Provisioned Throughput **$0.12–24/h·MU**（model 而定），commit 1/6 月平 D；BREAK-EVEN ~5M req/月先值得。
- Fine-tune：per training token **Llama 13B $1.49/1M、70B $7.99/1M、Titan Lite $1/1M**；custom model **storage $1.95/月**；Nova on-demand LoRA 平（同 base 價）、其他要 PT；**RFT $80/h**（GPT-OSS 20B / Qwen3 32B）。
**弱點**：KB floor + guardrails + amplification 令實際單 1.5–2×；啲 $ 分散喺成個 AWS 橫面。

### 3.4 Google Gemini / Gemini Enterprise Agent Platform

**Model tokens（$ /1M，2026）**

| 模型 | in ≤200k | in >200k | out | 一句 |
|---|---|---|---|---|
| **Gemini 2.5 Flash-Lite** | $0.10 | — | $0.40 | 平+快 |
| Gemini 2.0 Flash | $0.15 | — | $0.60 | 2026-06 後退役 |
| **Gemini 2.5 Flash** | $0.30 | — | $2.50 | 主推平 |
| Gemini 3.1 Flash | $0.50 | — | $3.00 | — |
| **Gemini 2.5 Pro** | $1.25 | $2.50 | $10.00 / $15.00 | 推理/長文 |
| Gemini 3.1 Flash-Lite | $0.25 | — | $1.50 | 新一代 3.x 更平 |
| **Gemini 3.1 Pro** | $2.00 | $4.00 | $12.00 / $24.00 | 1M ctx |

**其餘層**
- Embedding：**text $0.15–0.20、image $0.45、audio $6.5、video $12 /1M**（Gemini Embedding 2）——大廠最平 text。
- Cache：context cache **$0.125/1M·h 讀入 + storage $4.50/1M·h**；batch 再半價。
- Hosting（Agent Platform，統一 SKU）：**Agent Compute $0.085/vCPU·h（免首 50h/月）+ Memory $0.009/GiB·h（免 100GiB·h）+ Storage $0.000411/GiB·h**；**Agent Gateway 計 15k API calls /（1 vCPU·h）**；tiers 按 30 日 spend 自動升吞吐。
- Tools/MCP：function calling 當普通 input tokens；Agent Engine/工具由 Agent Compute 計。
- GPU：**A100 $2.93/h、H100 $10–11/h（+mgmt）**、TPU v5e premium；~1-yr CUD −30%。
- Fine-tune：**tuning $1–3/1M training tokens**（2.0 Flash $3/1M、Flash-Lite $1/1M）；**tuned endpoint = base 價**（2.0；3.7 Flash 例外 ×1.5）；custom training 按 node·h 另計；eval 當 batch job。
- PII：Google DLP ~$1/GB。
- Standard PayGo tiers：Pro Tier1 $10–250 (500k TPM) → Tier3 >$2000 (2M TPM)。
**弱點**：3.x 退休快；Agent platform 收費位多（compute/memory/storage/gateway）；preview model 唔入 Standard PayGo。

### 3.5 DeepSeek 官方（純 API）

| 模型 | cache-hit in | miss in | out | 備註 |
|---|---|---|---|---|
| **deepseek-v4-flash**（現行，8/17 前） | $0.0028 (¥0.02) | $0.14 (¥1) | $0.28 (¥2) | 1M ctx / 384K out |
| **v4-flash off-peak**（8/17 起） | $0.007 | $0.22 | $0.66 | 離峰 ×0.5 |
| v4-flash peak（北京 9-12、14-18） | $0.014 | $0.44 | $1.32 | 高峰 ×2 |
| **v4-pro**（現行） | $0.003625 | $0.435 | $0.87 | — |
| **v4-pro off-peak** | $0.022 | $0.66 | $1.98 | — |
| v4-pro peak | $0.044 | $1.32 | $3.96 | — |

**其餘層**：**無 Embedding、無 agent hosting、無托管 fine-tune**——你食 API 或靠第三方（方舟/百煉/硅基都托管返）。峰谷：每日 ~14h 離峰（UTC 23:00–01:00 之外…實質：北京 9–12、14–18 峰），**排程壓到離峰 = 慳一半**。
**弱點**：冇 infra/tools/guardrail 一體，production 要自己砌；官方並發穩定度要驗。

### 3.6 Alibaba 百煉（Model Studio）

**Model tokens（¥/1M，2026 官方 help）**

| 模型 | in | out | 備註 |
|---|---|---|---|
| qwen3-0.6B / 1.7B open | ¥0.6 級 | ¥2–? 級 | 開放微調 |
| **qwen3-8B open** | ¥0.5 | ¥2（思考 ¥5） | 好平嘅 open 部署 |
| qwen3-14B open | ¥1 | ¥4（思考 ¥10） | — |
| **qwen-max** | ¥2.4 | ¥9.6 | — |
| **qwen3-max**（≤32k） | ¥2.5 | ¥10 | 32–128k ¥4/¥16；128–256k ¥7/¥28 |
| qwen3.7-max | ¥12 | ¥36 | 頂 |
| 隱式 cache | ≈20% in 價 | — | 不可關 |

**其餘層**
- 免費：每 model **1M tokens / 90 日**。
- KB：**標準 ¥0.03/庫·h（≤100GB、1QPS）**、旗艦 ¥0.2/RCU·h；RAG recall 另計 input tokens。
- Fine-tune：按「training tokens × epoch」**qwen3-8B ¥6/1M、32B ¥40/1M、72B ¥150/1M**；部署可「按時間（MU ¥21–1,096/h）」或「按調用（同 in/out 價）」。
- 工具/工作流：App Studio / 插件按 token + 節點另計。
- 第三方：**托管 DeepSeek（同官方價）**、Kimi 等。
**弱點**：免費額度過後即轉浮動；部署 MU 明顯貴（自托管大 model 唔抵）。

### 3.7 Tencent 混元 / 元器 / 智能體開發平台 (ADP)

**Model tokens（¥/1M）**
- Hunyuan-a13b ¥0.5/¥2（入門）· role ¥2.4/¥9.6 · 翻譯 ¥1.2/¥3.6 · Vision ¥3/¥9 · Tencent HY2.0 Think（2026-03 調整後）¥5.3/¥21.2 · embedding ¥0.7。

**Agent 打包（ADP 訂閱，2026-01 上線）**
| 套餐 | ¥/月 | PU/月 | 模型 QPM | KB 容量 |
|---|---|---|---|---|
| 免費版 | ¥0（1 月試用） | 15k | 300 | 1GB |
| **Skill Plan** | ¥88 | 89k | 300 | — |
| **專業版** | ¥188 | 150k | 300 | 100GB |
| 企業版 | ¥4,880 | 3M | 1,200 | 2TB |

**PU = ¥0.001**；模型 token、工具、KB 超量都食 PU。工具清單貴：網頁解析 ¥120/1M、DocParsing ¥480/1M、DeepSeek 搜索 ¥0.055/次、混元搜索 ¥0.03/次、智能工作台 ¥0.025/分、Claw ¥0.0125/分。內容安全 ¥0.001/次。KB 超量 ¥0.0015/GB·h + 向量化 ¥0.06/GB·h。**深度推理模型並發包 ¥9,600/月起**（hybrid）——要連續高 QPS 就貴。

**元器**：域內發布免費 + API 每月 1M tokens free；私有化/企業要「企業級解決方案」另議。
**弱點**：工具收費貴（¥120–480/1M 網頁/文件解析）、並發包貴、訂閱+浮動雙軌難估。

### 3.8 Zhipu GLM（智譜）

| 模型 | in ¥/1M | out ¥/1M | cache-read |
|---|---|---|---|
| **GLM-5** | ¥4 | ¥18 | ¥1 |
| **GLM-5.1** | ¥6 | ¥24 | ¥1.3 |
| GLM-5.2（約） | ~¥10 | ~¥31.7 | — |

**其餘層**：API-only 為主；微調要睇官方控制台；無一體 agent hosting/guardrails——自砌。中文推理強。**弱點**：生態比三巨頭細。

### 3.9 Mistral La Plateforme

| 模型 | in $/1M | cache | out $/1M | 備註 |
|---|---|---|---|---|
| **Ministral 3 3B** | $0.10 | — | $0.10 | 細、快 |
| Ministral 3 8B | $0.15 | — | $0.15 | — |
| **Small 4** | $0.15 | — | $0.60 | 主推 |
| Large 3 | $0.50 | $0.05 | $1.50 | — |
| **Medium 3.5** | $1.50 | $0.15 | $7.50 | 頂 |

**其餘層**：**batch −50%、cache −90%**；Embedding（Mistral Embed）有；agent hosting 部分靠第三方（SDK 一體唔同 BytePlus/Azure 級）。歐系主權/CCPA 友好。

### 3.10 開源快推理（Groq / Cerebras / DeepInfra）+ 聚合（OpenRouter）

| Model | Groq | Cerebras | DeepInfra | 聚合 OpenRouter |
|---|---|---|---|---|
| Llama 3.3 70B | $0.59/$0.79 | $0.85/$1.20 | $0.35/$0.35 | 低至 $0.10/$0.32 +5.5% |
| gpt-oss-120b | $0.60 (out) | $0.35/$0.75 | $0.17 | 路由 |
| Qwen3 32B | 有 | $0.40/$0.80 | — | 路由 |
| 速度 | ~315–500 tok/s | ~2,000 tok/s | 慢（27） | 自動 failover |

**其餘層**：無 RAG/hosting/guardrails 一體（純推理）。OpenRouter PAYG +5.5% fee、50 req/day free、BYOK $25k/月免費後 5%。**啱 latency 敏感或 batch 壓量，唔啱「一個 console 搞掂」。**

---

## 4. 全棧每月 P&L（約定場景，含假設）

> ⚠️ **假設塊（一定要 label）**：10k queries/日 ≈ 300k/月 · base 每 call 2k in + 400 out · **agent amplification 4×**（router→KB→main→verify）→ 每月 model tokens = **2,400M in + 480M out** · 有 prefix cache 嘅平台假設 **50% input cache-hit** · KB 100GB · guardrails in+out · PII 脫敏 · shadow eval +5% model tokens。**數值係 range，方法係公式。**

```
monthly model bill =
  in_M × ( (1−h) × P_in_miss + h × P_cached )  +  out_M × P_out
  └── 再 × 1.05（shadow eval）                └── cache hit率 h（有先計）
```

| Vendor（標準配置） | model 大數（$/月，range） | cache 影響 | 另計 infra（約） |
|---|---|---|---|
| **BytePlus AFP（封頂）** | **¥500–1,000+**（Large/Max；Mini 混合縮低） | 隱式 ~20% | sandbox CU·hr、KB 儲存 → 雲線 |
| **BytePlus 按量（mini）** | ~¥2.6k ≈ $363 | 隱式 | — |
| **Azure GPT-5-mini** | ~$1,355 | −45%（cache 50%） | hosting $50–150 · FileSearch $300 · ContentSafety $450（可減） |
| Azure GPT-5 | ~$6,773 | — | 同上 |
| **Bedrock DeepSeek V3.2** | ~$1,791 | silent cache | **KB $345 底** + guardrails $135–270 |
| Bedrock Claude Sonnet 4.6 | ~$11,718 | −60% | KB + guardrails 同上 |
| **Gemini 2.5 Flash** | ~$1,796 | cache + batch | Agent Compute ~$13–25（50h free） |
| Gemini 2.5 Flash-Lite | ~$454 | — | 同上 |
| **DeepSeek official flash**（離峰） | **$620–900**（高峰混入 ×1.45） | cache $0.007 極狠 | 無 hosting，自砌聚合 |
| DeepSeek official pro（離峰） | $1,857–2,700 | — | 同上 |
| **Alibaba qwen3-max** | ¥8.8k ≈ $1,235 | 20% | KB ¥0.03/庫·h 可忽略 |
| Alibaba qwen3-8B open | ¥2.3k ≈ $318 | — | 部署 MU 另計 |
| **Tencent ADP 訂閱＋模型** | ¥188 + ~¥10–12k model ≈ $1.5k | — | 工具 ¥120–480/1M 好易爆 |
| Zhipu GLM-5 | ¥15.4k ≈ $2,152 | ¥1 cache | API-only |
| **Mistral Small 4** | ~$510 | −90% | — |
| Groq Llama 3.3 70B | ~$1,885 | 無 | — |
| DeepInfra Llama 3.3 | ~$1,058 | 無 | 慢 |

**讀法**（同一個 agent）：
- **要封頂 + 唔想砌 infra**：BytePlus（¥500–1,000 封頂）vs Gemini Flash 級（$450–1,800 浮動+ runtime）——BytePlus 貴過 DeepInfra 填空模型，但嗰筆錢包住 hosting/tools/guardrail/GPU。
- **要全球主權 + Batch 離線**：Azure GPT-5-mini（~$1,355，batch −50%）/ Mistral。
- **要極平純推理**：DeepSeek 離峰 / DeepInfra——但要自己承接 infra 成本同風險。
- **放大真相**：Bedrock Claude 標準一夜 ~$11.7k（仲未計 KB floor）——「好用嘅貴」，換 open model 即刻 ~1.8k。

---

## 5. 優勢／弱點矩陣

| Vendor | ✅ 優勢 | ❌ 弱點 |
|---|---|---|
| **BytePlus** | 封頂月費、多模態獨家、GPU/sandbox 已包、隱式 cache、中文/粵語、方舟托管 DeepSeek 同價質量穩 | 大陸數據主權、超額浮動、國際 SLA/文檔弱、圖/影片好貴 |
| **Azure** | GPT-5 全系、Batch −50%、治理/合規齊（Entra/Defender）、PTU | 費用散落（PTU/hosting/Defender）易漏、幣別 USD 浮動 |
| **Bedrock** | 62+ model 唔綁死、AWS 整合、Provisioned/Guardrails 成熟 | KB floor $345/月、guardrails 逐次計、amplification 4–8× 令帳單 1.5–2× |
| **Gemini** | Flash 平 + cache 平 + Agent Compute 最平 runtime | 退休節奏快、收費位多、preview 唔入 Standard PayGo |
| **DeepSeek** | 標價最平; cache $0.0028 極狠、峰谷可壓 | 純 API、無 hosting/embedding/fine-tune 一體、並發要驗、峰谷波動 |
| **百煉** | 免費 1M×90日、Qwen 全系、微調平 | 部署 MU 貴、免費過後浮動 |
| **Tencent** | 訂閱模式、域內元器免費 | 工具驚人貴、並發包 ¥9.6k 起、雙軌難估 |
| **GLM** | 中文推理、GLM-5/5.1 價實 | 生態細、無一體 infra |
| **Mistral** | 歐系主權、batch −50%/cache −90% | 規模細、agent 一體弱 |
| **開源快推理** | latency 超快、同 model 最平 | 無 RAG/hosting/safety 一體、要自砌 |

---

## 6. BytePlus 喺香港（HK）嘅定位

### 6.1 香港 selling story（由實數支撐）

- **成本可預測 > 標價最平**：同一個 5-agent KB pipeline，BytePlus **AFP 封頂**（¥500–1,000/月）對比 Bedrock Claude ~$11.7k、Azure ~$1.4–6.8k 浮動——你 Sell「**兩個數都得講：封頂月費 + 超額知會**」。
- **多模態獨家**：Seedance 2.0 / Seedream 只有 BytePlus 有 API——client 要圖/影片，platform **唔使離開佢**就搞掂（其他家要駁第三方再計錢）。
- **GPU + sandbox 已包**：唔使再開一張 EC2/Vertex GPU 單（H100 $10–11/h）。
- **中文 + 粵語第一身**：doubao 中英+粵語表現、LLM-FW/APMPlus/RBAC(JWT/審計) 一體（見 sec tab）。
- **方舟托管第三方規格**：DeepSeek V4-flash ¥1/¥2 同官方價，但企業並發/TTFT 好過直連（中文生態朋友）。
- **地理/地域**：畀燒到近廣深 edge，HK 延遲低；¥ 結算，預算框 RMB。

### 6.2 要誠實講嘅 caveats（定位文件必寫）

- **數據主權**：火山方舟係大陸服務（數據落大陸）——**HK PDPO / 金融跨境合規**對口嘅主權要求要另外傾（國際 BytePlus edition / 或 Azure/AWS HK region 並列方案）。呢個係「by default 揀唔到 BytePlus」嘅少數硬理由。
- **超額浮動**：AFP 封頂但好使（Seedance 2.0、大量 OCR/多模態）超額按量浮動 → 報「上限 + buffer」。
- **國際 SLA / 多語言文檔 / 全球 region**：弱過 Azure/AWS——出海、24×7 全球 SLA 客戶要早知。
- **FX**：¥/$ 波動打入 1 年期方案。

### 6.3 一句市場定位

> **BytePlus = 「封頂月費 + 多模態 + GPUs 包晒」嘅**HK 本土化 MVP 廠商——**cost-per-outcome 可預測**；Azure/AWS/Gemini 攞嚟做「全球主權 / 最大規模 / 開放生態」嘅對照。唔喺佢嘅戰場（全球合規 + 標價最低）硬撼，喺佢嘅戰場（快、平地、一條龍、封頂）贏。

---

## 7. 資料來源

| 來源 | URL | 日期 |
|---|---|---|
| 火山方舟模型價（ai.volcengine.com） | https://www.llmrates.ai/zh-Hans/providers/volcano-ark 同控制台 | 2026 |
| DeepSeek 官方 API 價 + 峰谷公告 | https://api-docs.deepseek.com/quick_start/pricing | 2026-08-16 |
| Azure OpenAI 價（$-blank → 第三方 2026-06 mailout） | https://azure.microsoft.com/pricing/details/azure-openai/ | 3rd-party |
| Azure Foundry Agent Service（tools/hosting） | https://azure.microsoft.com/pricing/details/foundry-agent-service/ | 2026 |
| Azure 微調計費法 + SFT/RFT | https://learn.microsoft.com/azure/foundry/openai/how-to/fine-tuning-cost-management | 2026 |
| Azure Content Safety + Defender AI | https://azure.microsoft.com/pricing/details/content-safety/ · /defender-for-cloud/ | 2026 |
| AWS Bedrock 價 / Guardrails / AgentCore / Flows | https://aws.amazon.com/bedrock/pricing/ · /agentcore/pricing/ | 2026 |
| AWS Comprehend PII | https://aws.amazon.com/comprehend/pricing/ | 2026 |
| Google Gemini / Agent Platform 價 | https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing | 2026 |
| Google Vertex GPU/Tuning | https://www.cloudzero.com/blog/google-vertex-ai-pricing/ | 2026-05 |
| 阿里百煉模型訓練/部署/調用計費 | https://help.aliyun.com/zh/model-studio/model-training-and-deployment-billing | 2026-08 |
| 騰訊 ADP 計費（套餐/PU/工具/KB） | https://cloud.tencent.com/document/product/1759/127342 | 2026 |
| GLM-5/5.1 價 | priceai.cc + segmentfault 整理 | 2026 |
| Mistral / Groq / Cerebras / DeepInfra / Together（Llama 3.3 對照） | modelpricewatch.com · inferencehub.org · perkstack.co | 2026-06/07 |
| SegmentFault 七平台總結 | https://segmentfault.com/a/1190000048112421 同 1190000047914013 | 2026-08 |

> **免責**：價格係 2026-08-16 公開資訊快照，各平台可能已郁；**大額報價以各平台官網/控制台為準**。RMB vs USD 用 ¥1≈$0.14 名義折算。HK 合規/定位內容係定性，落 contract 前同法務確認。
> 數法假設（amplification 4×、cache 50%）係估算，將實際量用控制台「用量明細」calibrate（見 pricing doc §七）。

---

*Last audit date: 2026-08-16 · 峰谷價/新 model 常常郁，引用前 refetch。*