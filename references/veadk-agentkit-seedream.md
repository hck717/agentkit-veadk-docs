# Seedream — 圖片生成家族深潛（Image Generation）

Seedream 係 **ByteDance / BytePlus 自家嘅圖像生成模型家族**：由「生得快」嘅 Lite 到「專業級」嘅 Pro，仲有 reasoning + 即時搜尋能力。呢份係**成個家族深潛**：歷代演進、而家拎到嘅型號、定價、平台／解決方案（Dreamina / CapCut / ModelArk / 火山方舟 / VideoOne），同埋用 **VeADK / AgentKit** 點喺 agent 入面撳佢。

> **Sale 一句**：「生圖唔使自己砌 TeaHerDiffusion——Seedream 一個 API 搞掂生圖、執圖、多參考融合，仲有 Pro 嘅 Layer Separation 可以直接拆層做設計。」

---

## 1. 快睇：Seedream 家族全家

| 型號 | 定位 | 主打 | 參考圖上限 | 定價（參考） |
|---|---|---|---|---|
| **Seedream 5.0 Pro** | 專業級（flagship） | Layer Separation、Precision Editing、14 語言原生文字、高密度排版 | 10 張 | **$0.045/張** 起（BytePlus 官方） |
| **Seedream 5.0 Lite** | 快速 + 平 | **Reasoning（chain-of-thought）+ 即時網上搜尋**、多參考融合、sequence batch | 14 張 | ~$0.035/張（第三方）· **~100 AFP/張**（方舟） |
| Seedream 4.5 / 4.0 | 上代 | 統一圖像創作 + 常識推理 | — | 已被 5.0 系列取代 |

> 🎯 **兩條腿分別**：**Lite = 平、快、識諗嘢（reasoning + search）**；**Pro = 靚、可拆層、識寫 14 種語言**。一般 agent 場景（mood board / 角色參考）Lite 就夠；要出街設計、要改完唔重生、要排版 → 上 Pro。

---

## 2. 家族歷代演進

| 版本 | 時間線 | 做主啲咩 |
|---|---|---|
| **Seedream 4.0** | 2025-09 研發公開 | 統一圖像創作模型，首次加入**常識 + 推理**能力 |
| **Seedream 4.5** | 2025 Q4 | 中間代 |
| **Seedream 5.0 Lite** | 2026-02（ModelArk 上線） | **統一多模態**：deep thinking + **即時網上搜尋**；唔係鬥解像度，係鬥「讀、睇、畫、寫」嘅諗法；Elo 全面提升，尤其知識推理、編輯一致性、辦公/學習場景 |
| **Seedream 5.0 Pro** | 2026-07-08 | 專業級：**Layer Separation（拆層）**、**Precision Editing（局部執）**、**原生 14 語言文字**、高密度設計支援 |

> ⚠️ **模型係 proprietary**：冇公開權重、冇官方 technical report、標準 benchmark（GenEval / T2I-CompBench 等）未見公開。有第三方提過「完整版 5.0」但**官方未確認**。落地面對客戶以官方能力頁為準。

---

## 3. 而家拎到嘅型號（Model ID）

| 平台 | Model ID | 記住 |
|---|---|---|
| 火山方舟（中國） | `doubao-seedream-5.0-lite` / `doubao-seedream-5-0-pro-260628` | 現有 docset 用緊嘅名 |
| **BytePlus ModelArk（國際）** | `doubao-seedream-5-0-pro-260628`？→ **係 `dola-seedream-5-0-pro-260628`**（Pro）；Lite 用 `dola-seedream-5.0-lite` 一類 | **以 Console 為準**，模型名好快郁 |
| 第三方轉售（fal / Replicate / EmpirioLabs / Higgsfield / APIXO / Atlas Cloud） | `seedream-5-0-pro` / `bytedance/seedream-5-lite` 等 | 各自命名 |

> ⚠️ **模型 ID 常常郁**（學埋 `doubao-seed-2.0-pro 即將下線`）。落地前查 Console / `agentkit model list` 一類，唔好 hardcode 長命。

---

## 4. 核心能力逐個拆

| 能力 | Lite 有冇 | Pro 有冇 | 講咩 |
|---|---|---|---|
| **Text-to-image** | ✅ | ✅ | 文案 → 圖 |
| **單圖編輯** | ✅ | ✅ | 執特定元素 |
| **多參考融合 Multi-reference** | ✅（最多 14 張） | ✅（最多 10 張） | 角色/產品/風格合埋 |
| **Sequential batch generation** | ✅ | ✅ | 連環出（storyboard / character sheet） |
| **Reasoning（chain-of-thought）** | ✅ | — | 理解你「點解」想生呢張 |
| **即時網上搜尋** | ✅ | — | 時效性創作（最新產品、新聞） |
| **Layer Separation 拆層** | — | ✅ | 前景/背景/文字分層俾你入設計工具 |
| **Precision Editing** | — | ✅ | 改一樣嘢唔使成張重生 |
| **原生多語言文字** | 英中 | **14 種語言** | 舖面文字正常 |
| **解像度** | 2K / 3K | 1K / 2K（1:1 至 21:9 多比例） | |

> 🎯 **同舊體系最大分別**：Seedream 5.0 Lite 已經由「執行指令」變「理解意圖」——**唔使再教 prompt 技巧**，講意圖就得。即係 agent 傳單行prompt 都出到貨。

---

## 5. 子產品 / 產品線細分

- **Seedream**（一條線）：4.0 → 4.5 → **5.0 Lite → 5.0 Pro**，唔係「好多個產品」，係**同一條 Model family 兩個 tier + 歷代版本**。
- **做圖責架**：畀 agent 用嘅係 `image_generation` 工具（AgentKit 內建），背後撳 Seedream（見 §7 / tools tab）。
- **同 Seedance 嘅關係**：Seedream 生圖 → 餵做 Seedance 嘅**首幀 / 參考幀**，係「圖→片」流水線第一環（見 seedance tab）。

---

## 6. 定價（計錢）

### 6.1 方舟 / AgentKit AFP 層面

| 東西 | 單價 | 備註 |
|---|---|---|
| `doubao-seedream-5.0-lite` | **~100 AFP/張** | 貴過文字好多；全部 Plan 都用到（Small 都得） |
| 多參考圖 | 每張加量 | 數張起跳 |

### 6.2 BytePlus ModelArk 國際 USD 層面

| 項目 | 價 |
|---|---|
| **5.0 Pro** | **$0.045/張 起**（官方推介）；第三方實際 **$0.075/張 ≤2.36MP、$0.150/張 >2.36MP** |
| **5.0 Lite** | ~**$0.035/張**（第三方） |
| 額外參考圖 | 第一張免費，之後 ~$0.003–0.005/張 |

> ⚠️ **報價口訣**：Seedream = **計張數**唔係計 token。AFP 封頂但**好使就浮動** → 報「上限 + buffer」（uniqueness doc 都咁講）。

---

## 7. Platform / Solutions 全覽（喺邊度用到）

| 平台 | 類型 | 有咩 |
|---|---|---|
| **Dreamina AI** | 消費者 App | 每日免費額度；Pro + Lite 都上線；CapCut 亦嵌 |
| **CapCut** | 消費者 App | 剪片嗰陣順手生圖 |
| **BytePlus ModelArk** | **企業 API** | `POST /api/v3/images/generations`；region ap-southeast-1 同 eu-west-1；正式支援 · **公司先主力用呢個** |
| **火山方舟 Volcengine** | 中國 API | `doubao-seedream-*` 一系；AgentKit 嘅 AFP 就係呢度燒 |
| **第三方**（fal / Replicate / Higgsfield / EmpirioLabs / APIXO / Atlas Cloud） | 轉售 | day-0 上架、各自計費 |
| **BytePlus VideoOne** | 視頻解決方案 | 主要以 Seedance 為主戰場；Seedream 做**縮圖 / 素材圖 / 分鏡圖**來源（詳見 seedance tab §7） |

> 📌 **BytePlus 唔喺美國提供**；Seedream 國際名係 `dola-*`（BytePlus），中國名係 `doubao-*`（方舟），唔好講錯。

---

## 8. Agent 點用（VeADK / AgentKit）

### 8.1 內建工具：`image_generation`

AgentKit 有內建 `image_generation` 工具（背後即 Seedream），常見角色：

- 角色參考圖、mood board（~100 AFP/張）
- 分鏡圖（storyboard）→ 餵畀 Seedance 生片
- 產品圖 / 營銷變體 A/B
- 去背 / 執圖（編輯模式）

### 8.2 VeADK 實例（A2A：研究 agent → 生圖 agent）

```python
# veadk-python：喺 agent loop 入面 call 生圖工具（A2A 俾「美術 agent」做）
from veadk import Agent

## 美術 agent：負責所有圖像生成
art = Agent(
    model_name="doubao-seed-2.1-pro-260628",      # 文字 agent；生圖照用內建 tool
    tools=[
        {
            "type": "image_generation",           # 背後撳 Seedream 5.0 Lite
            "instruction": (
                "用 Seedream 生圖。多參考融合：
                 1) 角色參考圖 2) mood/lighting 參考圖"
            ),
        },
    ],
)

## 主 agent 喺研究完之後叫美術 agent
result = art.invoke(
    "為『智能香薰機』生 3 張分鏡參考圖：未來風、暖色、室內環境"
)
```

> 💡 想慳？**先問 client 有冇真係要多模態**——一張圖 ~100 AFP 相當於 100 句文字。生圖之前喺主 agent prompt 加一句「除非明確要求，唔好自作主張生圖」。

### 8.3 決策：揀邊部

| 情況 | 揀 |
|---|---|
| Mood board / 角色參考 / 快速迭代 | **5.0 Lite**（平、有 reasoning） |
| 出街設計 / 系統排版 / 拆層落設計工具 | **5.0 Pro** |
| 時效性題目（最新產品外觀） | **5.0 Lite**（即時搜尋） |
| 多語言舖面（法文/德文...） | **5.0 Pro** |
| 大量批量（數百張商品圖） | **Lite + sequence batch**（連環出）餵落 pipeline |

---

## 9. Eval 點量（點知生得好唔好）

Seedream 官方用 **MagicBench 多維度評測**，核心維度（你可以照住砌 rubric）：

| 維度 | 測咩 |
|---|---|
| **Instruction following** | 有冇跟足 prompt |
| **Text-image consistency** | 圖同文字係咪講緊同一件事 |
| **Editing consistency** | 執完仲係咪維持原角色/原環境 |
| **Knowledge reasoning** | 知識型題目（辦公/教學場景） |
| **Business marketing / creativity / design** | 應用場景 |

Agent 落地做法（詳見 eval tab §10）：

- 每批生圖**抽樣人工評**（品質嘢，Judge 分數做輔助）
- 上線後 shadow 抽 10% 用 **LLM-as-judge + 人 HITL** 測 prompt-following
- 用 `image_generation` 工具前後，比較「一次過生」vs「A2A 分鏡」嘅可用率

---

## 10. 使用技巧 / Prompt Skills & Tricks

> 呢節係「點樣先用到佢靚」——**Prompt 唔係文法題，Seedream 係理解意圖**（尤其 Lite 有 reasoning）；但**幾種輸入模式（T2I / 區域執 / 草圖 / 錨點 / 多圖融合）嘅 prompt 寫法唔一樣**，揀錯模式、寫漏步驟先係最常見失敗。

### 10.1 先揀啱輸入模式（Seedream 5.0 Pro 五種）

| 模式 | 輸入 | 幾時用 | Prompt 心法 |
|---|---|---|---|
| **Text-to-image（T2I）** | 純文字 | 由零生圖 | 主體 + 風格 + 光影 + 構圖（見 §10.2） |
| **Region editing（區域執）** | 圖 + 文字 | 「改圖入面嘅一忽」 | **淨係講要執嘅區域 + 改成點**；唔好重新形容成張圖 |
| **Sketch editing（草圖執）** | 草圖 + 文字 | 用線稿定結構再上色 | 草圖 = 空間結構；文字加持色 / 材質 / 風格 |
| **Anchor editing（錨點執）** | 圖 + 錨點座標 | 精確到點嘅編輯 | 指明「錨點位置 + 改成乜」 |
| **Multi-image fusion（多圖融合）** | 多張圖 | 角色 / 風格合併 | 講清「邊張圖嘅邊樣嘢」做主（見 §10.5） |

> ⚠️ **最常見錯**：攞住「生成式 prompt」去撳 **Region editing**——即係成段拿臨繪影描述，模型唔知你淨係想執邊忽，結果成張變。**編輯任務 = 指住 + 講改點，唔係重新生。**

### 10.2 T2I 五元素框架（一貼即用）

實用嘅 T2I prompt 不外乎五舊（唔使長篇大論，Seedream 識執重點）：

| 元素 | 問自己 | 例子 |
|---|---|---|
| **Subject 主體** | 圖裏面有咩？「乜嘢在 / 喺度做緊咩」 | 一隻橙色機械貓 |
| **Style 風格** | 媒材 / 藝術流派？ | 賽博朋克貼紙風、水彩 |
| **Lighting & Color 光影色調** | 色板 / 打在幾點？ | 冷藍色調、一盞暖檯燈打側 |
| **Composition 構圖** | 鏡頭位 / 留白？ | 特寫、居中、三分法、大留白 |
| **Details 細節** | 紋理 / 環境物 / 前景背景？ | 金屬反光、桌面有乾花、淺景深虛化 |

```text
主體：一隻橙色機械貓，金屬部件反射金色
風格：玩具產品圖風格，乾淨
光影：冷藍環境光 + 一盞暖色主光打左側
構圖：正面特寫，居中，淺景深
細節：金屬鉚釘，背景純白漸變
```

> 💡 **Lite 識「唔使教」**：Seedream 5.0 Lite 有 reasoning，意圖講得清就出到貨；**越長越囉嗦反而容易跑偏**——三行講清主體 + 風格 + 一兩個限定就夠。

### 10.3 精準色控：直接寫 HEX

要顏色精準，喺 prompt 直接落 **HEX code**（`#FF5733`），比「橙紅色」準好多——尤其品牌色 / 產品圖：

```text
「背景用 #1A1A2E，橙色部分用 #FF6B35，提亮位用 #FFD166」
```

### 10.4 Layer Separation 提示技巧（Pro）

要拆層（前景 / 背景 / 文字）落設計工具，**喺 prompt 講明「要分層產出」+ 每層內容**：

```text
「生一張 3 層設計稿：L1 前景＝產品本體；
 L2 背景＝漸變底色；L3 文字＝Slogan」
```

> 🎯 Layer Separation 之後可以**執其中一層而其他唔郁**（配合 Precision Editing）——設計師接手唔使由頭嚟，呢個先係 Pro 平嘅位。

### 10.5 多圖融合：角色一致性

角色 / 產品跨場景要保持一致 → 用 **multi-reference fusion**：

- **參考圖上限**：Pro 10 張、Lite 14 張（AgentKit `image_generation` 內建工具跟同一上限）。
- **技巧**：每張參考圖喺 prompt **俾佢一個角色名**，跟住先描述「用邊張嘅邊樣嘢」：

```text
「Reference A＝主角，Reference B＝風格板。
 用 A 嘅樣貎 + B 嘅色調，生主角喺雨夜嘅街頭。」
```

> ⚠️ 一次過塞 14 張但唔講各自用途 = 模型自由發揮，一致性反而差。**少量高質參考 + 講清用途，好過多張亂塞。**

### 10.6 Sequence batch（量產連環出）

要 storyboard / 角色表 / 商品變體 → 用 sequential batch（連環出），每張維持同一角色：

```python
# image_generation 工具（AgentKit 內建）落 sequence batch：
resp = art.invoke(
    "用同一主角，連住生 6 張：① 企 ② 行 ③ 坐 ④ 跑 ⑤ 跳 ⑥ 瞓（只准改動作，其他一致）"
)
```

> 💡 成本唔變（張張照計），但**一次性攞到連貫系列**，慳返來回 prompt 量——商品圖幾百張走呢條路（再 pipe 落 Seedance 生片）。

### 10.7 負向提示 / 常見 CSS 反模式

| 反模式 | 點執 |
|---|---|
| 描述天文數字（幾十樣嘢） | 濃縮做主體 + 風格 + 2–3 個限定 |
| 英文 + 中文 / 符號混埋一齊 | 一條語言講清（14 語言原生，但混講易亂） |
| 冇講邊張參考圖用嚟做咩 | 全部命名 Reference A/B/C + 用途 |
| 編輯任務用生成式 prompt | 轉 region/sketch/anchor 模式，淨講執邊忽 |
| 想要「冇」嘅嘢（唔要紅色） | 直接用負向指令句：「不要紅色 / 無人 / 無背景文字」 |

---

## 11. 風險 / 免責

- **Proprietary**：冇權重、冇 technical report。
- **模型名同價格郁得好快**：`dola-*` / `doubao-*` 命名、新增 tier 都係短期嘢。
- **美國市場**：BytePlus 國際唔喺 US service。
- **貴**：~$0.035–0.15/張（國際）、~100 AFP/張（方舟），唔好當文字咁用。
- 標準 benchmark 未公開 → **憑樣本判斷，唔好吹紙面分數**。

---

## 12. 資料來源

| 來源 | URL | 日期 |
|---|---|---|
| Seedream 5.0 Pro 官方頁 | https://seed.bytedance.com/en/seedream5_0_Pro | 2026 |
| Seedream 5.0 Lite 官方頁 | https://seed.bytedance.com/en/seedream5_0_lite | 2026 |
| Seedream 5.0 Lite 發佈 blog（Seed Team） | https://seed.bytedance.com/en/blog/deeper-thinking-more-accurate-generation-introducing-seedream-5-0-lite | 2026 |
| BytePlus Seedream 產品頁（$0.045/張 起） | https://www.byteplus.com/en/product/Seedream | 2026 |
| BytePlus blog：Seedream 5.0 Lite on ModelArk | https://www.byteplus.com/en/blog/seedream5-0-lite | 2026-02-24 |
| kie.ai Seedream 5 總覽（Pro/Lite 對比 + 價） | https://kie.ai/blog/what-is-seedream-5 | 2026-07-13 |
| AIReiter 5.0 Pro preview（model ID 表） | https://aireiter.com/blog/seedream-5-0-pro-preview | 2026-07-08 |
| ModelArk Seedream 5.0 Pro tutorial（T2I 五元素） | https://docs.byteplus.com/en/docs/ModelArk/2582774 | 2026-08-31 |
| ModelArk Seedream 5.0 Pro interactive editing guide（region/sketch/anchor） | https://docs.byteplus.com/en/docs/ModelArk/2582775 | 2026-08-31 |
| ModelArk Image generation tutorial（模式 + 負向提示） | https://docs.byteplus.com/en/docs/ModelArk/1824121 | 頁面日 |
| Seedream 5.0 Pro Prompt Guide（imagine.art，五元素 + HEX + 錯誤表） | https://www.imagine.art/academy/seedream-5-0-pro-prompt-guide | 2026 |
| 方舟定價 / AgentKit AFP（`~100 AFP/張`） | `references/veadk-agentkit-pricing.md` §4.1 / §3 | 2026 |
| 工具 / 能力 tab（`image_generation` 內建工具） | `references/veadk-agentkit-tools-capabilities.md` | 2026 |

> **免責**：價錢（$0.045/$0.075/$0.035）同 model ID 以官方 Console / 當刻文件為準；AFP 數字係 docset 內部估算（約數），內部環境另行設。第三方轉售價同官方價唔一定一樣。

---

*Last audit date: 2026-09-06 · Seedream 5.0 Pro 上線後初建 + 用技巧節（五輸入模式 / 五元素 T2I / HEX 色控 / 拆層 / 多圖融合 / sequence batch）。模型/價錢郁得快，落地前 refetch。*