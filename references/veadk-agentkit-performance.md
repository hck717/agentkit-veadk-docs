# VeADK + AgentKit 性能優化 Playbook

呢份文件幫你 client 將一套 VeADK / AgentKit 方案由「行得」推到「慳錢 + 快」。
主角唔係 GPU——係 **四條槓**：延遲（Latency）、吞吐（Throughput）、成本（Cost）、呢三樣背後嘅 **Prompt chain / 上下文管理**。

> ✅ **核心心法**：
> 1. **性能問題 90% 係「context 太大 / model call 太多」**，9% 係 Runtime 資源，1% 先係 platform。
> 2. 慳錢 = 減行 token，唔係減 GPU；**上下文緩存（§3）+ 壓縮（§4）**係兩個最大槓桿。
> 3. 所有優化都要用 **agentkit eval** 守住質量——慳到飛起但 accuracy 跌晒等於白做。
> 4. Runtime 調資源係 **`agentkit runtime update`**，唔係改 Dockerfile。

---

## 0. 性能四象限 — 邊個場景食邊樣

| 場景 | 死因首選 | 對應章節 |
|---|---|---|
| 多輪客服長對話 | context 越滾越長 → 每輪 token 爆 | §3 緩存、§4 壓縮 |
| 多 Agent pipeline（invoice/movie） | 每個 agent 一句 prompt 過長 + 多 agent 之間 handoff | §5 prompt chain、§2 響應 |
| 高吞吐 request 湧入 | Runtime concurrency / 實例數唔夠 | §6 runtime scale |
| 追求低延遲（即時對話） | model call 太長（大模型）+ 唔盡用緩存 | §2、§3 |
| 成本爆炸 | 日日 full context 重跑 + summary 唔識用 | §3、§4、§7 |

---

## 1. 三大「數字」先拆清楚

| 指標 | 點樣量 | 點先叫好 |
|---|---|---|
| **TTFT（首 token 延遲）** | 由 request 到第一個 token | 細模型 <1s，中模型 1–3s |
| **Total latency（成個回合）** | request → 完整 answer | 多步 agent loop 會 xN turns |
| **Throughput（token/s）** | 平台吞吐 / 並行度 | 想睇 APMPlus + `usage_metadata` |
| **Cost per task** | 每次任務總 token × 費率 | 用 `eval run` + 計費定基線 |

**Sales 一句**：「延遲係明示，成本係暗線。你話『快』，但其實日日重跑幾萬 token 冇 cache——一個月先見真章。」

---

## 2. 模型選擇 = 第一道加速

- **細模型行高頻**：極速（`mini`）基礎係數 0.5×，仲要唔使行全 context；default 主走 mini，遇到難題先 fallback（`model_name=[mini, pro]` list 自動 fallback，見 `veadk-api.md`）。
- **快慢分行**：customer-facing 即時對話用 `mini` / `lite`；離線 deep reasoning 用 `pro`。唔好淨用一個 model 走天涯。
- **視覺要小心**：OCR 一張圖 token 遠高過讀 1,000 字（見定價 doc §3）——圖片還是小 model 好。

---

## 3. 上下文緩存（Responses API）— 命中率要識睇

Responses API **默認開** session 上下文緩存。每輪 response event 個 `usage_metadata` 有兩條 key：

```
cached_content_token_count   # 命中等於唔使入 prompt
prompt_token_count           # 今次實際送到 model 嘅輸入
命中率 = cached / prompt
```

**優化動作：**
- 多輪對話：命中率應該 50–95%；若低過 50%，好可能每輪幫 context 加咗唔應該加嘅大 object（例如成個 file 丟入 tool return）。
- **`output_schema` 會關緩存**（VeADK 自動關）——要結構化輸出嘅場景就要衡量「準確 vs 慳」。
- prompt 前面（system 部分）穩定就係緩存區；**printf 動態內容放後面**，命中率自然上去。

---

## 4. Context 壓縮（Compaction）— 最直接嘅 token 殺手

用 `EventsCompactionConfig` + `LlmEventSummarizer` 將長對話壓成 summary，減少 replay token。

```python
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.apps.llm_event_summarizer import LlmEventSummarizer

summarizer = LlmEventSummarizer(
    model="doubao-seed-2-0-mini",     # 用細模型做 summary，慳錢
    system_instruction="壓縮成精簡中文摘要，保留用戶事實、已承諾事項、key terms。",
)
app = App(
    agents=[my_agent],
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=10,        # 每 10 次新 call 壓一次（太密好貴）
        max_events=50,                 # 超過 50 events 觸發
        max_tokens=8000,               # summary 上限
        compactor=summarizer,
    ),
)
```

**經驗**：`compaction_interval` 太細（如 3）壓得太密反而貴；長 RA g 對話同埋要 detail 嘅 domain 對話唔好壓太勁，會冇咗細數字。

---

## 5. Prompt chain 優化 — 唔好「一次過堆滿」

| 反模式 | 點改 |
|---|---|
| 成個 KB 全文塞入 system | 用 `load_knowledgebase` RAG 只塞 top_k 片段 |
| tool 回傳大 JSON 唔諗就入 context | 喺 tool 內預先 summarize / 抽 key fields |
| 一個 agent 做十件事 | 拆 Hans：抽取 agent / 驗證 agent（A2A）平行 |
| 每次 run 都重放成串歷史 | 靠 session cache + 壓縮，或切 session 令佢重新計 |
| 所有輪都問埋大 model | 用 gateway / 前端規則先行 handle 簡單查詢（純 pipeline，唔落 LLM） |

> ⚠️ 每個 agent 嘅 `instruction` 都係 **system prompt 一部分**。寫得精簡 = 每輪慳幾百 token × 幾萬輪 = 實質銀兩。

---

## 6. Runtime 調資源 — `agentkit runtime update`

橫向即係 `runtime update`（CLI），唔使重 build：

```bash
# 提高單實例資源
agentkit runtime update my-agent \
  --cpu-milli 2000 \
  --memory-mb 4096 \
  --max-concurrency 40 \
  --auto-release

# 或者加實例數（多實例要配持久化 DB，見 vector-cache doc §2/§7）
agentkit runtime update my-agent --max-instance 5 --auto-release
```

**睇有冇需要調**：APMPlus 指標（模型調用次數 / 操作耗時 / 異常次數 / 工具耗時）見 §8；`--max-concurrency` 每 instance 預設 20。
開 `--apmplus` 監控正路：`agentkit runtime update my-agent --apmplus --auto-release`。

> ⚠️ concurrency 升得快 = 同時間多 request = **唔一定慳**；跑得順但 cost 爆就應該返去 §3/§4，唔係一味加機。

---

## 7. 並行 / 異步 — 多 Agent 出結果唔好排隊

- **多 Agent A2A**：做「parallel tool calls / 多個 downstream Agent 一齊跑」用 A2A registry；movie 12 scenes seedance 可以同時出。
- **`runner.run` 異步**：`asyncio.gather` 多 batch，唔好 for-loop 排住隊。
- **eval 並行**：`agentkit eval run --concurrency 10`（預設 5）縮短 CI turnaround。

---

## 8. 可觀測性 — 唔量測就唔好話快

| 平台 | 用嚟睇 | 接入 |
|---|---|---|
| **APMPlus** | 模型調用次數、token 用量、操作耗時、異常次數、工具耗時；推理內容用 `reasoning` 標注 | `OpentelemetryTracer([APMPlusExporter()])` 或 `ENABLE_APMPLUS=true` |
| **Cozeloop** | trace + 評測 | `CozeloopExporter()` |
| **TLS** | 集中日誌、長期留存 | `TLSExporter()` |
| **InMemory** | 本地 debug，span JSON 落盤 | 自動附帶，唔使手加 |
| **CLI logs** | 快速睇 runtime | `agentkit runtime logs my-agent --limit 200` |

**Performance checklist**：睇 APMPlus「操作耗時」分佈 → 俾你知邊個 agent / 邊個工具最慢 → 集中攻嗰嚿。

> ⚠️ `LOGGING_LEVEL=DEBUG` 會記錄模型輸出、思考內容、工具參數同結果——生產環境記住轉 INFO（見 security/observability doc）。

---

## 9. 優化順序 — 由零成本排到貴

1. **Context 工廠**：轉 RAG（唔好全文件）+ 睇緩存命中率（§3）——零 code。
2. **縮 prompt**：instruction 精簡、tool return 抽 key（§5）——少 code、冇 infra 影響。
3. **加壓縮**：`EventsCompactionConfig` + mini summarizer（§4）——少 code。
4. **調 Runtime**：`runtime update` CPU/mem/concurrency（§6）——有雲費銀兩，唔好隨便。
5. **拆 Agent + 並行**：A2A + `asyncio.gather`（§7）——工程量較大。
6. **評估守住**：任何改動過 `agentkit eval run` 先放心（§10）。

---

## 10. Eval — 優化嘅安全網

```bash
agentkit dataset create --name qa-set --schema "input,reference_output"
agentkit dataset add qa-set --file ./cases.json
agentkit eval run --dataset qa-set --evaluator 相关性 --target my-agent \
  --concurrency 10 --dry-run
agentkit eval run --dataset qa-set --evaluator 相关性 --target my-agent --json
```

- 一次可多個 `--evaluator`（相關性 / 完整性）加權。
- CI 用：`eval run` 回傳 `experimentId` → `eval experiment get / results`。
- **Studio 自動回流**：部署開「自動創建評測集」→ 每輪對話自動評分（0–1，≥0.6 入 Good Case）→ Good/Bad Case 落返 `{agent}_good_case`/`{agent}_bad_case`。

> Sales 一句：「性能優化唔使講『應該快少少』——我哋用 eval 每改一版都畀分，慳錢之餘有實績。」

---

## 11. 實例：客服 Agent「快同慳」前後對比

場景：S5 客服，20k turns/日，每 turn 平均 input 4k token、output 500。

| 優化前 | 優化後 | 慳 |
|---|---|---|
| 每輪全 context 重送 4k token | Responses cache 命中等 ~ 首輪 4k + 後續 ~600 | **~75%** |
| 每 turn 大 model | 主輪 `mini` + 難題 fallback `pro` | 大 model 用量 ~50%↓ |
| 每輪 full summary | `compaction_interval=10` | summary call ~10×↓ |
| context 塞成個 FAQ | RAG top_k=10 | token ~30%↓ |

**結果**：月成本大概 -50%，median latency 由 ~3s 落到 ~1.5s，`eval` 分不跌反升（因為 context 乾淨）。

---

## 12. 資料來源

| 來源 | URL | 日期 |
|---|---|---|
| runtime update（CPU/記憶/instance/concurrency/APMPlus） | https://agentkit-f14c9eb5.mintlify.app/productions/agentkit-cli/preview/zh/commands/runtime/update | 頁面日 |
| eval run / dataset / experiment（CI 編排） | https://agentkit-f14c9eb5.mintlify.app/productions/agentkit-cli/preview/zh/commands/eval | 頁面日 |
| 上下文緩存 + `usage_metadata`（cached/prompt count） | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/agent/prompt-management | 頁面日 |
| ADK EventsCompactionConfig / LlmEventSummarizer | https://google.github.io/adk-python/app/ | 頁面日 |
| APMPlus 指標（model calls/token/耗時/工具耗時） | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/observability/apmplus | 頁面日 |
| Studio 自動評測（Good/Bad Case 回流入 eval 集） | https://agentkit-f14c9eb5.mintlify.app/productions/veadk/preview/zh/components/frontend/studio | 頁面日 |
| model 頻率係數 / AFP 估算 | `references/veadk-agentkit-pricing.md` | 2026-08-09 |

> **免責**：慳 % 數字係參考估算，以實戰 `usage_metadata` + APMPlus 為準；每個 model 費率畀 pricing doc 覆蓋。

---

*Last audit date: 2026-08-13 · 優化順序優先做「零成本」嘅 context 層，再掂錢袋。*