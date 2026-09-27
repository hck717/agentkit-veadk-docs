# Seedance — 視頻生成家族深潛（Video Generation）

Seedance 係 **ByteDance / BytePlus 自家嘅多模態視頻生成模型家族**：由 1.0 去到而家嘅 **2.5**，支援「文字→片」「圖→片」「參考融合」「編輯＋延伸」同 **原生音畫同步**。呢份係**成個家族深潛**：歷代演進、而家拎到嘅型號、規格、定價（LAS per-second）、平台／解決方案（**Dreamina / CapCut / ModelArk / 火山方舟 / BytePlus VideoOne**），同埋用 **VeADK / AgentKit** 點喺 agent 入面撳佢。

> **Sale 一句**：「唔使同十間公司駁十個 API——Seedream 生圖打底、Seedance 一條過生 30 秒片仲有音、VideoOne 幫你上線短劇同直播。」

---

## 1. 快睇：Seedance 家族全家

| 型號 | Model ID（BytePlus LAS） | 主打 | 長度 | 解像度 |
|---|---|---|---|---|
| **Seedance 2.5** | `dreamina-seedance-2-5-260628` | **30 秒一條過**、50 參考、timestamp 級編輯 | 4–30s | 480p / 720p |
| **Seedance 2.0** | `dreamina-seedance-2-0-260128` | **4K（10-bit）+ 原生音**、編輯＋延伸 | 4–15s | 480p→**4K** |
| **Seedance 2.0 Fast** | `dreamina-seedance-2-0-fast-260128` | 快、啱迭代初稿 | 4–15s | 480p / 720p |
| **Seedance 2.0 Mini** | `dreamina-seedance-2-0-mini-260615` | ~2× 快過 Fast、~50% 價、**量產** | 4–15s | 480p / 720p |
| Seedance 1.5-pro | （方舟 `doubao-seedance-1.5-pro`） | 音畫同步、對話 | — | **方舟標「即將下線」** |
| Seedance 1.0-pro | `seedance-1-0-pro-250528` | 早期座標 | — | $2.5 / M tokens |

> 🎯 **揀型號唔係睇 version number，係睇出片規格**：要 1080p/4K → **2.0**（2.5 而家得 480p/720p 做人）；要長故事 → **2.5**；要量產慳錢 → **2.0 Mini**。

---

## 2. 家族歷代演進

| 版本 | 時間 | 做主啲咩 |
|---|---|---|
| **1.0 / 1.0-pro** | 2025 | 文字/圖→片、1080p、多鏡頭故事 |
| **1.5-pro** | 2025-12-18 | **音畫同步**主角：多語對話、鏡頭級導演控制（方舟而家標「即將下線」） |
| **2.0** | 2026-02-12 | 文字/圖/片/音**混合參考**、編輯＋延伸、15 秒；2026-06 喺 Volcano FORCE 確認 **4K** |
| **2.0 Fast** | 2026（同 2.0 一系） | 快鏡頭迭代 |
| **2.0 Mini** | 2026-06 中 | **最快最平**：量產型 |
| **2.5** | 2026-06-23 公佈（FORCE）· **2026-07-16 API 上線** · 2026-08 BytePlus blog | **30 秒 one-take**、**50 多模態參考**、timestamp 級精準編輯、3D blockout 輸入 |

> 📌 2.0 → 2.5 係「**製片思維**」跳升：2.0 做「一段 clip」，2.5 做「一個完整故事單元」——銀幕情節、品牌片、長旁白一次過。

---

## 3. 而家拎到嘅型號（Model ID 表）

| 平台 | Model ID | 規格 |
|---|---|---|
| **BytePlus LAS / ModelArk（國際）** | `dreamina-seedance-2-5-260628` / `-2-0-260128` / `-2-0-fast-260128` / `-2-0-mini-260615` | 全部文本/圖/片/音輸入 + 編輯 + 延伸 + 原生音 |
| **火山方舟（中國）** | `doubao-seedance-2.0` / `2.0-fast` / `2.0-mini` / `1.5-pro`（即將下線） | AgentKit 嘅 AFP 就係呢度燒 |
| **ModelArk classic** | `seedance-1-0-pro-250528` | 舊續；按 tokens 計（$2.5/M） |

> ⚠️ **Video generation 係異步接口**：`create task` → 用 task ID 查結果，唔係同步返片（ModelArk docs 講明）。

---

## 4. 核心能力逐個拆

| 能力 | 2.5 | 2.0 | Fast | Mini |
|---|---|---|---|---|
| **Text-to-video** | ✅ | ✅ | ✅ | ✅ |
| **Image-to-video（首幀）** | ✅ | ✅ | ✅ | ✅ |
| **Image-to-video（首＋尾幀）** | ✅ | ✅ | ✅ | ✅ |
| **多模態參考**（圖/片/音組合） | ✅（**最多 50**） | ✅（9 圖+3 片+3 音） | ✅ | ✅ |
| **純音頻參考**（齋歌） | ✅ | ❌（要搭圖/片） | ❌ | — |
| **編輯影片 Edit** | ✅ | ✅ | ✅ | ✅ |
| **延伸影片 Extend** | ✅ | ✅ | ✅ | ✅ |
| **原生生成音**（`generate_audio: true`） | ✅ | ✅ | ✅ | ✅ |
| **3D blockout 輸入** | ✅ | — | — | — |

### 規格速記

- 全 2.x 系列：**24 fps**、輸出 mp4、`resolution` 可揀 480p/720p（預設）/1080p/4k。
- **4K 只有 Seedance 2.0**；**1080p 喺「參考圖」場景唔 support**（2.5/fast/mini 沙面）。
- **Aspect ratio**：width/height 限 [0.4, 2.5]；總像素限 [640×640, 8295044]，即 2K/4K 以上要返 2.0。
- 音頻參考：mp3、每段 2–30s（2.5 最多 10 段），request body ≤64 MB。

---

## 5. 定價（計錢）

### 5.1 BytePlus LAS（國際，per-second）

**Enhanced（2.0 / 2.5）= $0.303 / 秒 × 分辨率 factor**

| 型號 | 480p | 720p | 1080p | 4K |
|---|---|---|---|---|
| **2.0**（無輸入片） | ×0.4651 | ×1 | ×2.5 | ×5.0761 |
| **2.5**（無輸入片） | ×0.6785 | **×1.525** | — | — |
| 有輸入片 | 2.0 ×0.2830 / 2.5 ×0.406 | 2.0 ×0.6098 / 2.5 ×0.9125 | — | — |

計法範例：**720p × 10s 無輸入片** → 2.0 = `0.303×10×1 = $3.03`；2.5 = `0.303×10×1.525 ≈ $4.62`。

**Basic（Fast / Mini）= $0.242 / 秒**

| 型號 | 480p | 720p |
|---|---|---|
| **2.0 Fast**（無輸入片） | ×0.465 | ×1 |
| **2.0 Mini**（無輸入片） | ×0.2907 | ×0.625 |

### 5.2 方舟 / AgentKit AFP 層面（docset 沿用）

| 嘢 | 單價 | 備註 |
|---|---|---|
| `doubao-seedance-2.0-fast` | **~2,000 AFP/clip** | 常用 |
| `doubao-seedance-2.0` 標準版 | ~6,000 AFP/clip | 4K 級 |
| **Tier 限制** | **只有 Large/Max Plan 先用得** | Medium 得 1.5-pro（即將下線） |

> ⚠️ **報價最易錯**：Seedance 2.0 全系列（2.0/fast/mini）**只有 Large/Max**——想幫 client 做片，起碼計 Large ¥500/月（pricing doc §4.1 原話）。

---

## 6. 平台全覽（喺邊度用到）

| 平台 | 類型 | 有咩 |
|---|---|---|
| **Dreamina** | 消費者 App | Seedance 官方嘅消費面；免費每日額度 + 訂閱（Light / Production Plan，2.5 有 per-token 計價偏移 ~1:1.8） |
| **CapCut** | 消費者 App | 剪片期間順手生片 |
| **BytePlus ModelArk / LAS** | **企業 API** | 異步 task 接口；正式支援 · **公司主力呢個** |
| **火山方舟** | 中國 API | `doubao-seedance-*`；AgentKit AFP 喺呢度燒 |
| **fal.ai** | 第三方 | 2.0 per-second 計費 |
| **seedance2.so**（Seedance Web） | 消費者 Web | 每日 free credits + 訂閱 |
| **BytePlus VideoOne** | **視頻解決方案平台** | 見下 §7 |

---

## 7. BytePlus VideoOne ——「平台」代表（deep-dive）

> 你問「平台／解決方案」——**VideoOne 就係 BytePlus 嘅視頻業務解決方案**，Seedance/Seedream 係佢下面嘅引擎層。佢唔係另一個模型，係「**教你點樣用班仔做嘢**」嘅平台。

### 7.1 VideoOne 係咩

BytePlus Video One Solution = **一鑊過嘅短視頻 / 直播 / 媒體業務平台**，四個支柱：

| 支柱 | 講咩 |
|---|---|
| **Days 上線** | 預建 solutions：**短劇 short drama、對話式 AI、互動直播**——開發週期由月變日 |
| **Production-ready code** | 開源 **BytePlus VideoOne Demo**：多媒體 SDK pre-integrated、解決 dependency 衝突 |
| **一站式端到端** | **Content creation（上傳/直播）→ Cloud processing（VOD/RTC）→ 消費（播放/互動）** 一個平台搞掂 |
| **Solution vs 產品能力** | 全套 solution 行到最快，或者自由撿拾基本產品能力（VOD / RTC / 媒體 SDK）砌自己嘢 |

### 7.2 同 Seedance/Seedream 嘅關係

- **Seedance 2.5/2.0** 喺下面幫你**自動生成內容**（廣告片、短劇場次、商品片）。
- **Seedream** 做**縮圖 / 素材圖 / 分鏡幀**，Feed 入 VideoOne 嘅 media pipeline。
- VideoOne 負責**雲端處理（轉碼/存儲/直播 RTC）+ 出街**——即「識得生」＋「識得送」，一條龍。

### 7.3 幾時用 VideoOne（決策）

| 情況 | 用咩 |
|---|---|
| 淨係要「生一段片返嚟旁住」 | 直接 Seedance API（ModelArk/LAS） |
| 要「上線一個短劇 / 帶自家 App 播放 + 直播」 | **VideoOne**（VOD/RTC/SDK + solutions） |
| 要「生片 + 出街 + 統計」一條龍 | VideoOne + Seedance 組合 |

> 🎯 **對客一句**：Seedance/Seedream 係「引擎」，VideoOne 係「車架」——引擎馬力勁，都要車架先上到路。

---

## 8. Agent 點用（VeADK / AgentKit）

### 8.1 內建工具：`video_generation`

AgentKit 內建 `video_generation` 工具（背後撳 Seedance）：

- 每個 scene 一條 clip（~2,000 AFP/clip）
- **mood board（Seedream 生圖）→ 首幀 → Seedance 生片**——圖→片流水線
- 語音旁白 / 歌曲同步（`generate_audio`）

### 8.2 VeADK 實例（電影 generator 思路）

```python
# veadk-python：研究 → 劇本 → 分鏡 → 生成（鳴謝 projects/movie-generator.md）
from veadk import Agent

## 前期：Seedream 負責分鏡圖
storyboard = Agent(model_name="doubao-seed-2.1-pro-260628", tools=[
    {"type": "image_generation", "instruction": "生分鏡電影分鏡圖（每幕一張）"},
])

## 生成：Seedance 負責每一幕
render = Agent(model_name="doubao-seed-2.1-pro-260628", tools=[
    {"type": "video_generation", "instruction": "用 Seedance 按配合 picture 生每幕 5–10 秒片"},
])

## render agent call；攞返 task id → 異步查結果
resp = render.invoke("幕 3：主角喺天台，黃昏，氛圍感，生成 8 秒 720p")
# → {"task_id": "...", "status": "queued"} ；再 poll status → 攞 mp4 url
```

> 💡 **異步係關鍵**：Seedance 唔係同步返片。agent 要設計成「批完 job → poll / callback」，唔好卡住個 loop。想慳：**唔好 12 幕全部 4K**——初稿用 Fast/Mini，Tail 先上 2.0。

### 8.3 決策：揀邊部

| 交付要求 | 揀 |
|---|---|
| **要 1080p / 4K 交付** | **2.0**（2.5 而家得 480p/720p） |
| **長故事 / 品牌片 / 旁白 30 秒** | **2.5** |
| 初稿 / 快 iteration | 2.0 Fast |
| 大量量產（幾百條） | **2.0 Mini**（~50% 價、~2× 快） |
| 有配音/對白 | 2.5 / 2.0（原生音同步） |
| 純歌劇目（冇圖/片） | 2.5（2.0 唔收齋音） |

---

## 9. Eval 點量（點知生得好唔好）

BytePlus 對 video gen 嘅評測維度（砌 rubric 用）：

| 維度 | 測咩 |
|---|---|
| **Instruction adherence** | 有冇跟 prompt（動作/風格/分鏡） |
| **Motion realism / 物理真實** | 重力、撞擊、流體運動係咪合理 |
| **Temporal coherence / 時間一致性** | 前後幀場景穩定，唔閃變 |
| **Character / scene stability** | 角色外觀、環境一路維持 |
| **Audio-visual alignment** | 音畫同步（毫秒級），對白/環境聲同畫面啱 |
| **Multi-shot consistency** | 多鏡頭同一故事一致 |

落地做法（詳見 eval tab §10）：

- **抽樣人工 HITL** 為主（影片質素 LLM-as-judge 只做初篩）
- 用 `video_generation` 前，先衡量「可用率」：一條 5s 片出嚟有幾高機率直接收貨
- 對應 movie-generator：研究/劇本 agent 用文字 eval，**生成 agent 用人工抽片**

---

## 10. 使用技巧 / Prompt Skills & Tricks

> 呢節係「點樣先用到佢靚」——Seedance 唔係「寫劇本」，係「**寫分鏡 + 導演指令 + 供料**」：主體、動作、鏡頭運動、場景、音。揀啱輸入（首幀 / 首＋尾幀 / 多模態參考 / 音軌）先係控制力所在。

### 10.1 Prompt 五件式（一貼即用）

| 件 | 問自己 | 例子 |
|---|---|---|
| **Subject 主體** | 邊個 / 咩嘢喺畫面？ | 一個穿紅色風褸嘅男人 |
| **Action 動作** | 佢做緊乜（動詞要明確）？ | 行向鏡頭，回頭 |
| **Camera 鏡頭運動** | 鏡頭點郁？ | 慢推近（dolly in），輕搖 |
| **Environment 環境** | 場景 / 氛圍 / 光影？ | 雨夜霓虹街，暖窗光 |
| **Audio 聲音（可選）** | 要唔要原生音？ | 落雨聲 + 腳步聲（`generate_audio`） |

```text
主體：一個穿紅色風褸嘅男人
動作：一路回頭一路行向鏡頭
鏡頭：慢推近（dolly in），手持微微晃
環境：雨夜霓虹街頭，暖黃窗光
音：雨聲 + 皮鞋踏地聲
```

> 🎯 **動作動詞要「能驗證」**：寫「行街」唔及「由左至右行過鏡頭、望住個招牌」——後者模型知你有 direction + 視線 + 鏡頭關係，output 先受控。

### 10.2 首＋尾幀（keyframe）做精準過場

**最有控制力嘅技巧**：提供**開始圖（首幀）＋ 結束圖（尾幀）**，Seedance 自動補中間嘅 motion——S 型過場、before/after、產品變形、換衫換景都靠呢招：

```text
首幀：一張產品未開箱圖
尾幀：同一產品已展開嘅圖
→ 用首＋尾幀模式，生 6 秒「開箱瞬間」過場片
```

> 💡 **用途**：品牌 reveal（Logo 由暗到光）、產品 morph、場景/季節切換、角色換衫——**尾幀一錘定音，唔使估。**

### 10.3 多模態參考（2.5 最多 50）

2.5 收**圖 / 片 / 音**混合參考：角色圖、環境圖、動作片段、純音樂軌一次過塞。技巧：

- 每張/每段參考**命名 + 講用途**（似 Seedream 多圖融合）：`Ref A＝演員樣貌 / Ref B＝場景 / Ref C＝動作範本`。
- 純音頻參考（齋歌）**淨係 2.5 收到**——2.0 要搭張圖/段片先得。
- 音頻每段 2–30s、2.5 最多 10 段、request ≤64 MB。

> ⚠️ 參考多唔代表好——**唔講用途嘅參考等如噪音**，反而令主體漂移。5–10 個「各自無名有命」嘅最佳。

### 10.4 Camera 語言：想控制鏡頭就講 cam 唔係劇情

要鏡頭受控，直接寫 cam 分鏡術語（跟住 Scene 生成時餵）：

```text
「先 wide shot 交代場景 → dolly in 到主角 → 主角起身 OTS（過肩）同佢講嘢 → 最後 zoom 到招牌、出 3D blockout 空間」
```

| 要咩效果 | 寫 |
|---|---|
| 由遠到近 | dolly in / 句號前移 |
| 拍跟住主角 | tracking shot |
| 先交代再聚焦 | wide shot → cut in |
| 對話感 | over-the-shoulder（OTS） |
| 運動感 / 手持 | handheld，輕微晃 |

### 10.5 編輯 / 延伸：一條片改到位（2.5 timestamp 級）

- **Edit**：撳住「改呢一段」→ 只改目標片段，其他唔郁（timestamp 級，2.5 主打）。
- **Extend**：已出嘅片**向後延伸 4–15 秒**——長片分幾段延伸砌，唔係一次過生好耐。
- 技巧：**先用 Fast/Mini 出 draft → 鏡頭啱先上 2.5/2.0 出 final**（慳錢見 §5；Mini ~50% 價）。

```python
# image_generation 出 draft → video_generation（異步 task）：
resp = render.invoke("幕 3 先用 Fast 出 4 秒 draft（720p）；鏡頭確認後先用 2.5 出 30 秒 final")
```

> 💡 **30 秒連環**想長過 4–15 秒單段？**2.5 可以直接 4–30s**；又或者「首＋尾幀 + Extend」夾段，維持連貫性。

### 10.6 人物片（portrait）特別提示

- 用**首幀近照**做起點（表情/角度有保證），再搭 2.5 補 motion。
- 對白 / 口形同步 → 開 `generate_audio` + 淨係 2.5/2.0（原生音畫同步）。
- 表情變化幅度唔好太大（2.5 對大變形仍會微漂移）——**分鏡逐格鎖，唔好靠一步到位**。

### 10.7 常見反模式

| 反模式 | 執法 |
|---|---|
| 得「寫劇本」冇鏡頭/動作指令 | 每幕帶 camera + action 動詞（§10.1） |
| 生 4K 先試都試 | 初稿 Fast/Mini 720p，final 先 4K（§5 價差 ~10 倍） |
| 參考圖唔命名唔講用途 | 全部 Ref A/B/C + 用途 |
| 齋歌參考餵 2.0 | 只適用 2.5 |
| 12 幕一次過生 4K | 分幕 + 異步批 + draft/final 分流 |
| 尾幀都用唔上 | 過場先係首＋尾幀主場（§10.2） |

---

## 11. 風險 / 免責

- **Proprietary**：冇權重、冇 technical report。
- **規格郁得快**：2.5 API 2026-07 先上黎，價錢/region 未齊；`1.5-pro` 方舟標「即將下線」。
- **BytePlus 唔喺美國**；中國 international 名 `dola-*` / `doubao-*` 分流。
- **Tier 鎖死**：2.0 系得 Large/Max——報價唔好報 Medium。
- 冇公開標準 benchmark → 憑樣本 + 內部可用率衡量。

---

## 12. 資料來源

| 來源 | URL | 日期 |
|---|---|---|
| BytePlus Seedance 產品頁（2.5 發佈） | https://www.byteplus.com/en/product/seedance | 2026 |
| BytePlus blog：Dreamina Seedance 2.5 上線 | https://www.byteplus.com/en/blog/dreamina-seedance2-5 | 2026-08-06 |
| BytePlus LAS 文檔（模型表/規格/計費） | https://docs.byteplus.com/en/docs/byteplus_las/video_gen_enhanced | 2026 |
| BytePlus ModelArk Seedance 2.5 tutorial | https://docs.byteplus.com/en/docs/ModelArk/2607688 | 2026-08-31 |
| BytePlus ModelArk Seedance 2.5 prompt guide（五件式 + 參考） | https://docs.byteplus.com/en/docs/ModelArk/2607689 | 2026-08-31 |
| BytePlus ModelArk Seedance 2.0 series prompt guide | https://docs.byteplus.com/en/docs/ModelArk/2222480 | 2026-08-31 |
| BytePlus ModelArk：portrait 人物片指南 | https://docs.byteplus.com/en/docs/ModelArk/2608626 | 2026-08-31 |
| BytePlus ModelArk Seedance tutorial | https://docs.byteplus.com/en/docs/ModelArk/2291680 | 2026-08-31 |
| seedance.tv：首＋尾幀 keyframe 指南 | https://seedance.tv/blog | 2026 |
| BytePlus blog：Seedance 2.0 上線 | https://www.byteplus.com/en/blog/dreamina-seedance2-0 | 2026-04-14 |
| BytePlus blog：Seedance 1.5 pro | https://www.byteplus.com/en/blog/seedance-1-5-pro | 2025-12-18 |
| BytePlus VideoOne 解決方案 | https://docs.byteplus.com/api/docs/byteplus-vos/docs-why-byteplus-video-one-solution | 2026 |
| corenexis：Seedance 2.0→2.5 完整指南 | https://blog.corenexis.com/seedance-2 | 2026-07-22 |
| aifreeapi：Seedance 2026 揀型號 | https://www.aifreeapi.com/en/posts/seedance-video-models-2026 | 2026-08-26 |
| 方舟/AgentKit AFP（`~2,000 AFP/clip`、tier 鎖位） | `references/veadk-agentkit-pricing.md` §4.1 | 2026 |
| 電影 generator project（Seedance 用法） | `projects/movie-generator.md` | 2026 |

> **免責**：LAS $0.303/$0.242 per-second + factor 以當刻文檔；AFP 數字係 docset 內部估算；model ID 同 tier 限制以 Console（`agentkit model list`）為準。Seedance 2.5 價錢同某些 region 未公開，落地前 refetch。

---

*Last audit date: 2026-09-06 · Seedance 2.5 上線後初建 + 用技巧節（五件式 prompt / 首＋尾幀 keyframe / 多模態參考 / camera 語言 / edit-extend / 人物片）。規格/價錢/region 仍在郁，落地前 refetch。*