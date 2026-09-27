# FIN-MATE Observability — 完整 trace / logs / monitoring 指南

> 本文件每一項「點樣攞」都直接對應真 code（veadk 1.1.9 / agentkit SDK 0.8.5 / 本 repo）。
> 冇 tracer 設定 → 照行但冇 span；冇 log env → 冇 file log（全部有 default / graceful degrade）。

層級概念：**stage events**（個 run 做咗咩）、**full log / transcript**（每個 LLM call 講咗咩）、
**system trace**（veadk span / OpenViking / 容器 logs）。

| 層 | 內容 | 邊度 | 攞法 |
|---|---|---|---|
| L1 stage events | 每 stage 細到事件（ms/tokens/uris/score/detail） | `experiments/runs/<run>/<strategy>/events.jsonl` | 直接 cat / 過濾 |
| L2 full log（transcript） | 每題所有 LLM call ＋ function call/response 完整 replay | `experiments/runs/<run>/<strategy>/<eid>/transcript.jsonl` | 直接 cat / 計 cost |
| L3a OTLP span trace | veadk `OpentelemetryTracer` span → otel-collector → Jaeger | Jaeger UI `http://localhost:16686` | `docker compose up -d otel-collector jaeger` |
| L3b veadk built-in trace dump | `Runner.run(save_tracing_data=True)` / `tracer.dump()` → 本地 span JSON | `<name>_<user>_<session>_<traceid>.json` | §5 snippet |
| L3c veadk env exporters | `ENABLE_APMPLUS/COZELOOP/TLS` auto-attach 雲端 exporter | APMPlus / Cozeloop / Volcengine TLS | §4c |
| L3' OpenViking 內部 | embedding/retrieval/queue/filesystem 統計 | OpenViking `/api/v1/observer/*` | `scripts/trace_all.py` / curl |
| L3'' raw logs | web / openviking / otel-collector / jaeger 容器 log ＋ CLI log | `docker compose logs <svc>`、`AGENTKIT_LOG_FILE` | §7 |

---

## 0. 一鍵打包全部（最快路）

```bash
cd projects/fin_mate
./.venv/bin/python scripts/trace_all.py          # 全部收晒，輸出 observability/observability-<ts>/
```

收返嚟嘅 bundle（對應 `scripts/trace_all.py:30-37` 嘅 endpoint list）：

```bash
observability-20260907-172645/
├── SUMMARY.txt                        # 人類可讀 health（queue / vikingdb / models ...）
├── JAEGER.txt                         # Jaeger UI 提示
├── openviking_observer_system.json    # health + 全部組件狀態
├── openviking_observer_retrieval.json # 查詢統計（zero-result rate、avg latency...）
├── openviking_observer_filesystem.json
├── openviking_observer_models.json    # embedding model call/token 統計
├── openviking_tasks.json              # add_resource 任務狀態（確認 corpus 有冇 seed 到）
├── openviking_debug_vector_count.json # vector 數目（reseed 前後對比有用）
├── logs/{web,openviking,otel-collector,jaeger}.log
└── agentkit_logs/                     # CLI 自身 log（見 §7）
```

---

## 1. L1 · Stage events（run 發生咗咩）— `events.jsonl`

每條 strategy/variant 一個 `events.jsonl`。`_emit()`（`experiments/rag_bench/strategies.py:47`）寫入，每個 event 有
`strategy / eid / category / stage / ms / tokens{prompt,completion,cached} / score / uris / detail`。
Stage 因 pipe 而定：`hyde`、`retrieve`、`gate`、`judge`、`rewrite`、`router`、`answer`、`rerank`…

```python
# 攞某策略某題嘅 stage 事件 + token 用量
import json
evs = [json.loads(l) for l in open("experiments/runs/run_260909_hyde_rrf_full/hyde_rrf/events.jsonl")]
for e in evs:
    if e["eid"] != "f1": continue
    print(e["stage"], e.get("ms"), e.get("tokens"), (e.get("detail") or {}), (e.get("uris") or [])[:3])
```

```bash
# CLI 快速 grep（例：搵出所有 retrieve stage 嘅首位 uri）
rg '"stage": "retrieve"' experiments/runs/*/hyde_rrf/events.jsonl
```

## 2. L2 · Full log（每個 LLM call 講咗咩）— `transcript.jsonl`

呢個就係「**full log**」：每題 `<eid>/transcript.jsonl`，一行 = 一個 call。
- `llm: ark` / `llm: local` / `llm: qwen3` → 每個有 `msgs`（完整 prompt）、`text`（完整 output）、
  `prompt_tokens`、`completion_tokens`、`cached_tokens`、`ms`。（本地 reranker variant 用 `qwen3` 條目，係 `output` 同 `score` 而唔係 `text`。）
- llm stub（`--retrieve-only`）↔ `llm: stub`，text 空。
- agentic（已退役）用 ADK Runner event 格式：`kind=function_call/function_response/llm/final`，
  `calls[].name/args`、`responses[].name/response`、逐個 `usage`。

```python
# 重播某題全部 LLM call（邊個 prompt 餵咗啲乜、答咗啲乜、用咗幾多 token）
import json
for call in map(json.loads, open("experiments/runs/run_260909_hyde_full/hyde/f1/transcript.jsonl")):
    print(call["llm"], "tg={}/{} cached={} ms={:.0f}".format(
        call.get("prompt_tokens"), call.get("completion_tokens"),
        call.get("cached_tokens", 0), call.get("ms", 0)))
    print("  Q:", call["msgs"][0]["content"][:80].replace("\n", " "))
    print("  A:", (call.get("text") or "")[:120].strip())
```

```python
# 由 transcript 重算成條 pipe 嘅 cost（等於 runner 個 usage 打份）
import json, sys
sys.path.insert(0, ".")
from experiments import _lib
p = c = k = 0
for call in map(json.loads, open("experiments/runs/run_260909_hyde_full/hyde/f1/transcript.jsonl")):
    p += call.get("prompt_tokens", 0); c += call.get("completion_tokens", 0); k += call.get("cached_tokens", 0)
print("prompt", p, "completion", c, "cached", k, "≈ $%.4f" % _lib.usd(p, c, k))
```

```bash
# 睇成個 run 指定題嘅 answer
cat experiments/runs/run_260909_hyde_rrf_full/hyde_rrf/f1/answer.txt
```

## 3. 全部 run 會出嘅 meta + 計咗嘅 metrics

- `run_meta.json` — models／prices／gate／rrf_k／budget／items → **可重現**（budget 機制喺 `run.py:196` BUDGET_SKIP）。
- `<strategy>/info.json` — 該 pipe config（read_limit、k、desc）。
- `<strategy>/report.md` — per-item 表（recall@5/prec@5/MRR@5/nDCG@5/answer_F1/trap/usd）。
- `SUMMARY.md` — 全 pipe 對照表（Rerank Lab 版用 `RERANK_SUMMARY.md`）。

```python
import json
m = json.load(open("experiments/runs/run_260909_hyde_rrf_full/run_meta.json"))
print(m["models"], m["used_tokens"], m["items"])
```

---

## 4. L3a · veadk/agentkit span trace（OTLP → Jaeger）

### 4a) 本 repo 做法：自行掛 `LocalOtlpExporter`

`_build_local_otlp_tracer()`（`agent_build.py:140`）定義咗 `LocalOtlpExporter`——**呢個係我哋自己嘅
`veadk.tracing.telemetry.exporters.base_exporter.BaseExporter` subclass**（唔係 veadk 內建類），
佢 `model_post_init()` 起一個 OTLP HTTP exporter（`OpentelemetryTracer` API 層次如下）：

```python
from veadk.tracing.telemetry.opentelemetry_tracer import OpentelemetryTracer
from veadk.tracing.telemetry.exporters.base_exporter import BaseExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

class LocalOtlpExporter(BaseExporter):
    resource_attributes: dict = {"service.name": "fin_mate"}
    def model_post_init(self, context) -> None:
        self._exporter = OTLPSpanExporter(endpoint=endpoint, timeout=10)
        self.processor = BatchSpanProcessor(self._exporter)
    def export(self) -> None:
        if self._exporter:
            self._exporter.force_flush()

tracer = OpentelemetryTracer(exporters=[LocalOtlpExporter()])
```

`build_agent()`（`agent_build.py:202`）endpoint 唔通就 `except → return None`（`agent_build.py:170` 度）→ **graceful
degrade**：照行、淨係冇 span。`tracers=tracers or None` 喺 `:240`。

`docker-compose.yml:43` 傳 `OBSERVABILITY_OTLP_ENDPOINT=http://otel-collector:4318/v1/traces`，`.env:43` 有同一個 key。

```bash
# 起 collector + Jaeger（docker compose 有定義）
docker compose up -d otel-collector jaeger
open http://localhost:16686        # Jaeger UI → Search → service = fin_mate → Find Traces
```

trace 睇到 agent 逐個 turn（LLM call、tool call、KB retrieval）嘅 span 樹。
（agentic 已退役：佢每題跑喺獨立 subprocess，Runner events 淨係入 `<eid>/transcript.jsonl`，
唔會自動入 Jaeger；要入就要喺 subprocess 內都 set 同一個 OTLP env——依家冇必要。）

### 4b) veadk 原生方式一：`Runner.run(save_tracing_data=True)` → span JSON dump

`veadk` 個 `Runner.run()` 直接有 `save_tracing_data` 參數（`veadk/runner.py:474, 568, 689`）：
真行完一輪就 call 晒所有 tracer 嘅 `tracer.dump(user_id, session_id)`（default path = `get_agent_dir()`，
即 entry script 所在目錄），寫出 `<name>_<user>_<session>_<traceid>.json`。唔使自己企 exporter。

`fin-mate.py` 個 entrypoint 可以加一行就自動留低每輪嘅 span file：

```python
response = await runner.run(
    messages=prompt, user_id=user_id, session_id=session_id,
    save_tracing_data=True,
)
```

「邊個 session 邊啲 span」由 `gen_ai.session.id` attribute（`call_llm` span）決定，見 §5。

### 4c) veadk 原生方式二：env 開雲端 exporter（唔寫 code）

`Agent._prepare_tracers()`（`veadk/agent.py:708-751`）讀 env 自動加 exporter——唔使傳 `tracers=`：

| env | 加邊個 exporter | 相關設定（`veadk/configs/tracing_configs.py`） |
|---|---|---|
| `ENABLE_APMPLUS=true` | `APMPlusExporter` | `OBSERVABILITY_OPENTELEMETRY_APMPLUS_ENDPOINT` / `..._SERVICE_NAME` / `..._API_KEY` |
| `ENABLE_COZELOOP=true` | `CozeloopExporter` | `OBSERVABILITY_OPENTELEMETRY_COZELOOP_ENDPOINT` / `..._API_KEY` / `..._SERVICE_NAME` |
| `ENABLE_TLS=true` | `TLSExporter`（Volcengine TLS，OTLP HTTP） | `OBSERVABILITY_OPENTELEMETRY_TLS_ENDPOINT` / `..._TLS_REGION` / `..._SERVICE_NAME`；`VOLCENGINE_ACCESS_KEY` / `VOLCENGINE_SECRET_KEY` |

另：`OBSERVABILITY_OPENTELEMETRY_TRACE_CONTENT`（default `true`）控制 span 內容藏唔藏 token。

## 5. L3b · veadk built-in trace dump（offline span JSON）

三個 API 全部喺 `veadk.tracing.telemetry`：

1. **`tracer.dump(user_id, session_id, path="")`**（`opentelemetry_tracer.py:258`）——force export 當前 spans，
   篩該 session，寫一份 JSON：每行 `{name, span_id, trace_id, start_time, end_time, attributes, parent_span_id}`。
2. **`tracer.force_export()`**（`opentelemetry_tracer.py:248`）——即時 flush pending spans。
3. **`InMemoryExporter.get_finished_spans(session_id=...)`**（`inmemory_exporter.py:105`）——`OpentelemetryTracer`
   永遠內置一個 in-memory exporter 儲晒 span；`session_trace_dict` 記 `session_id → [trace_id]`
   （由 `call_llm` span 嘅 `gen_ai.session.id` 建立，`inmemory_exporter.py:70-88`）。

攞 span（唔使 Jaeger，純本地）：

```python
from veadk.tracing.telemetry.opentelemetry_tracer import OpentelemetryTracer
tracer = OpentelemetryTracer(exporters=[])          # 淨係要 in-memory 搜集
# ... 跑 agent（同一個 tracer instance）...
path = tracer.dump(user_id="me", session_id="sess-1", path="/tmp")  # 離線 span JSON
print(path)

# 或直接讀 in-memory spans
spans = tracer._inmemory_exporter._exporter.get_finished_spans(session_id="sess-1")
for s in spans:
    print(s.name, format(s.context.trace_id, "016x"), dict(s.attributes).get("gen_ai.session.id"))
```

`OpentelemetryTracer.exporters` 設咗非 in-memory exporter 時，`dump()` 一樣會 work——佢嘅 span 都係用
同一個 global tracer provider 記，所以 in-memory exporter 多數都收齊（`agent.py:709-727` 個 auto 模式亦如此）。

## 6. L3' · OpenViking 內部監控（REST observer）

OpenViking 自己都有全套統計，`scripts/trace_all.py` 用 `X-API-Key` header 逐個攞：

```bash
V=http://localhost:1933; K="$(grep DATABASE_OPENVIKING_API_KEY .env | cut -d= -f2 | tr -d '"')"
curl -s -H "X-API-Key: $K" "$V/api/v1/observer/retrieval"   # 查詢/延遲/zero-result/score
curl -s -H "X-API-Key: $K" "$V/api/v1/observer/system"      # queue/embedding/models/lock health
curl -s -H "X-API-Key: $K" "$V/api/v1/observer/queue"       # embedding 進度（reseed 監控）
curl -s -H "X-API-Key: $K" "$V/api/v1/debug/vector/count"   # vector 數目（reseed 前後對比）
curl -s -H "X-API-Key: $K" "$V/api/v1/tasks?limit=100"      # add_resource 完成未
```

```python
# 用 code 亦可（strategies.py 內 `_ov_snapshot()` 就係咁做）
import os, json, urllib.request
base = os.getenv("DATABASE_OPENVIKING_URL", "http://localhost:1933")
key  = os.getenv("DATABASE_OPENVIKING_API_KEY", "")
req = urllib.request.Request(base + "/api/v1/observer/retrieval", headers={"X-API-Key": key})
print(json.load(urllib.request.urlopen(req, timeout=10)))
```

常用指標（`observer/retrieval`）：`Total Queries / Zero-Result Rate / Avg Score / Avg Latency`；
`observer/queue`：`Embedding processed` —— RAG 實驗每次 rerun 前，用 `debug/vector/count` ＋ `tasks` 確認 corpus 已成功 reseed（見 REPORT caveat #8）。

## 7. L3'' · 容器同 CLI logs

```bash
docker compose logs --tail=200 web            # agent server logs
docker compose logs --tail=200 openviking     # KB 服務 logs
docker compose logs --tail=200 otel-collector # trace 傳送狀態
docker compose logs --tail=200 jaeger
```

CLI／server log 由 **agentkit** 控制（`agentkit/utils/logging_config.py:50-58`）：

| env | 作用 |
|---|---|
| `AGENTKIT_LOG_LEVEL` | 全局 level（console + file） |
| `AGENTKIT_FILE_ENABLED` | 開 file log |
| `AGENTKIT_LOG_FILE` | file 路徑（唔 set 就用 default，見下） |
| `AGENTKIT_CONSOLE_ENABLED` / `AGENTKIT_LOG_CONSOLE` | 開 console output |
| `AGENTKIT_CONSOLE_LOG_LEVEL` / `AGENTKIT_FILE_LOG_LEVEL` | 各自 level |
| `AGENTKIT_LOG_FORMAT` / `AGENTKIT_LOG_JSON_INDENT` | format / pretty-print |

`setup_cli_logging()` default（`logging_config.py:436-441`）：console off，file 開就寫去 **cwd 下 `.agentkit/logs/agentkit-YYYYMMDD.log`**：

```bash
ls .agentkit/logs/                          # 依 cwd 計
AGENTKIT_FILE_ENABLED=1 AGENTKIT_LOG_LEVEL=DEBUG python -m veadk.web ...
```

veadk 自己個 logger（`veadk/utils/logger.py`）永遠 output 去 stdout，level 用 `LOGGING_LEVEL`，而且當有 span
recording 時每行自動加 `trace_id=...` prefix——想 log 同 trace 對埋就靠呢個。

## 8. 例常操作（每次 run 之後）

```bash
# 1) 收成個 run 嘅 full log bundle
./.venv/bin/python scripts/trace_all.py
# 2) 對埋 OpenViking vector count（reseed 之後應該係 >0 嘅新數）
rg 'indexCount|vector' observability/*/openviking_debug_vector_count.json | head
# 3) Jaeger 睇最慢 span
open http://localhost:16686
# 4) 要每個 session 都留 span file：fin-mate entrypoint 加 save_tracing_data=True（§4b），
#    或者直接 tracer.dump(...)（§5）
```

> 想睇 React 出邊度慢 / 多 call：`transcript.jsonl` 行一個 jq 計每個 `llm` 嘅 `ms` sum，快過 Jaeger 粒度細唔到 call 級——兩者互補。想 trace 級（span 樹）就 §4/§5，想 call 級就 L1/L2。