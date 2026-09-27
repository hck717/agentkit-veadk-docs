"""FIN-MATE E1 lora_bench matrix runner（local-only）。

每一 row（串行起 server）：
  rag      = 3 條 RAG pipe（naive/hybrid/adaptive）用**本地 base 模型**代答（strategies.ark_complete 換做 local 版）
  base     = base 模型 closed-book（冇 RAG、冇 context 注入；純 prompt）
  lora     = LoRA fused closed-book
  qlora    = QLoRA fused closed-book
對全部 34 條 eval golden 出 prediction → 用 eval/evaluators.py 同一套 EVALUATORS 評分 → ms/tokens。
逐 row append 去 experiments/lora_bench/run.json；最後行 report 合成（--report）。

用法（全部 local；先起 server）：
  mlx_lm.server --model <base>      --port 8201 &
  PY -m experiments.lora_bench.run --row rag   --port 8201
  PY -m experiments.lora_bench.run --row base  --port 8201
  # kill
  mlx_lm.server --model <fused_lora>  --port 8202 &
  PY -m experiments.lora_bench.run --row lora  --port 8202
  # kill
  mlx_lm.server --model <fused_qlora> --port 8203 &
  PY -m experiments.lora_bench.run --row qlora --port 8203
  # kill
  PY -m experiments.lora_bench.run --report   # 合成 report.md
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments import _lib  # noqa: E402
from experiments import eval_metrics  # noqa: E402

from eval.evaluators import EVALUATORS, extract_json  # noqa: E402

THIS = Path(__file__).resolve().parent
RESULTS = THIS / "run.json"
PIPES = ["naive", "hybrid", "adaptive"]
# better-retrieval diagnostic panel（D6 升降板）：k=15 + sparse + RRF / gate，全部 fact_single 重跑
BETTER_PIPES = ["hybrid", "advanced"]

# Qwen3 預設 thinking on——4B 本地做 eval 唔想 thinking 拖慢同拖長 output。
# ✅ mlx_lm.server 讀 chat_template_kwargs；Ollama 讀 think。両方都傳係 union。
EXTRA_BODY = {"think": False, "chat_template_kwargs": {"enable_thinking": False}}

# _lib.local_complete 120s timeout 太短——4B + 2k token context 生成 up to 512 tok 可能 >120s。
# 呢個 helper 用 300s timeout，輸出格式同 _lib.Completion 兼容。
LOCAL_TIMEOUT = 300.0

TOOL_SYSTEM = (
    "你係 fin-mate 金融研究 agent。要計數時必須輸出嚴格 JSON（唔加任何其他字）："
    '{"tool": "calc", "args": {"expr": "<算式>"}}。要讀新聞 CSV 時：'
    '{"tool": "read_news_file", "args": {"path": "<csv path>"}}。'
)
SENT_SYSTEM = "你係金融新聞情緒分類器。嚴格跟 prompt 內嘅輸出格式。"
TRAP_SYSTEM = "根據已知資料回答，唔好老作。如果問題嘅答案唔喺資料入面，直接答『無資料』。"


def load_records() -> list[dict]:
    recs = []
    from eval.run_eval import SET_FILES, GOLDEN_ROOT

    for rels in SET_FILES.values():
        for rel in rels:
            fp = GOLDEN_ROOT / rel
            for line in fp.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    recs.append(json.loads(line))
    return sorted(recs, key=lambda r: (r["set"], r["id"]))


async def _local_chat(msgs: list, base_url: str, model: str,
                     max_tokens: int = 512, temperature: float = 0.0,
                     extra_body: dict | None = None):
    """兼容 _lib.Completion 嘅本地 OpenAI-compat call，timeout 300s。"""
    import httpx as _httpx
    body = {"model": model, "messages": msgs, "stream": False,
            "max_tokens": max_tokens, "temperature": temperature, **(extra_body or EXTRA_BODY)}
    t = time.perf_counter()
    async with _httpx.AsyncClient(timeout=LOCAL_TIMEOUT) as c:
        r = await c.post(base_url.rstrip("/") + "/v1/chat/completions", json=body)
        r.raise_for_status()
        j = r.json()
    ms = (time.perf_counter() - t) * 1000
    u = (j.get("usage") or {})
    cached = (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
    comp = _lib.Completion(text=j["choices"][0]["message"]["content"],
                           prompt_tokens=u.get("prompt_tokens", 0),
                           completion_tokens=u.get("completion_tokens", 0),
                           cached_tokens=cached, ms=ms)
    return comp


def _local_wrapper(base_url: str, model: str):
    """strategies.ark_complete 嘅 local 版（signature 兼容：msgs, max_tokens, trace）。
    strategies 唔畀 model 名時用外層 model（Ollama/MLX server 唔識 'local'）。"""
    async def _f(msgs, _model=None, *, max_tokens=512, caching=False, trace=None,
                 output_schema=None, text_format=None):
        return await _local_chat(msgs, base_url=base_url, model=_model or model,
                                 max_tokens=max_tokens, temperature=0.0)
    return _f


async def _rag_record(rec, doc_uris, pipe):
    import experiments.rag_bench.strategies as strategies

    cat = (rec.get("meta") or {}).get("src_cat") or "fact"
    res = await strategies.run(pipe, rec["prompt"], rec["id"], cat, doc_uris, trace=[])
    ms = sum(e.get("ms") or 0 for e in res["events"]) + (res.get("extra") or {}).get("retry_ms", 0)
    return {"pred": res.get("answer") or "", "ms": ms,
            "usage": {"uris": len(res.get("uris") or []), "events": len(res["events"])}}


async def _chat_record(rec, base_url, model):
    """closed-book prediction：唔注入任何 KB/context（「無 RAG」條件），純 prompt。"""
    t0 = time.perf_counter()
    if rec["type"] == "qa":
        system, prompt = TRAP_SYSTEM, rec["prompt"]
    elif rec["type"] == "tool_call":
        system, prompt = TOOL_SYSTEM, rec["prompt"]
    else:
        system, prompt = SENT_SYSTEM, rec["prompt"]
    c = await _local_chat([{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                          base_url=base_url, model=model, max_tokens=768, temperature=0.0)
    ms = (time.perf_counter() - t0) * 1000
    return {"pred": c.text, "ms": max(c.ms, ms), "usage": {"prompt": c.prompt_tokens, "completion": c.completion_tokens}}


async def _score(rec, pred, judge_cache, no_judge=False):
    """deterministic evaluators inline；llm_judge 喺 `--judge` pass（全部 MLX server kill
    晒、淨 Ollama）先行——以免 Ollama + MLX server 同時 resident 爆 16GB。"""
    evaluator = rec["evaluator"]
    fn = EVALUATORS[evaluator]
    ctx = {"judge_cache": judge_cache}
    if evaluator == "llm_judge":
        if no_judge:
            return None, None, "pending-llm-judge"
        return await fn(rec, pred, ctx=ctx)
    return fn(rec, pred, ctx=ctx)


async def run_row(row: str, base_url: str, model: str) -> dict:
    recs = load_records()
    judge_cache = []
    out = {"row": row, "pipe": None, "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "records": []}

    local_ark = _local_wrapper(base_url, model)

    if row in ("rag", "better"):
        import experiments.rag_bench.strategies as strategies

        strategies.ark_complete = local_ark
        doc_uris = {}
        try:
            from experiments.rag_bench.eval_set import all_doc_uris

            doc_uris = all_doc_uris()
        except Exception as exc:  # noqa: BLE001
            print("all_doc_uris failed:", exc)
        pipes = PIPES if row == "rag" else BETTER_PIPES
        for pipe in pipes:
            row_ms = 0.0
            for rec in recs:
                if rec["type"] != "qa":
                    continue
                pred = await _rag_record(rec, doc_uris, pipe)
                score, passed, note = await _score(rec, pred["pred"], judge_cache, no_judge=True)
                row_ms += pred["ms"]
                out["records"].append({"set": rec["set"], "id": rec["id"], "pipe": pipe, "pred": pred["pred"],
                                       "score": score, "passed": passed, "note": note,
                                       "evaluator_pending": rec["evaluator"] == "llm_judge",
                                       "ms": round(pred["ms"], 1)})
            out["records"].append({"set": "__row_total__", "pipe": pipe, "ms": round(row_ms, 1)})
        return out

    for rec in recs:
        pred = await _chat_record(rec, base_url, model)
        score, passed, note = await _score(rec, pred["pred"], judge_cache, no_judge=True)
        out["records"].append({"set": rec["set"], "id": rec["id"], "pred": pred["pred"], "score": score,
                               "passed": passed, "note": note,
                               "evaluator_pending": rec["evaluator"] == "llm_judge",
                               "ms": round(pred["ms"], 1), "tokens": pred["usage"]})
    return out


def _merge(results: list[dict]) -> dict:
    rows = {}
    per = {}
    for block in results:
        for rec in block.get("records", []):
            if rec.get("set") == "__row_total__":
                continue
            key = (block["row"], rec["set"], rec.get("pipe") or "-")
            per.setdefault(key, []).append(rec)
    return {"rows": rows, "per": per}


def print_summary(results: list[dict]) -> None:
    per = _merge(results)["per"]
    for key in sorted(per):
        row, set_, pipe = key
        recs = per[key]
        ok = sum(1 for r in recs if r["passed"])
        ms = sum(r["ms"] for r in recs)
        sc = sum(r["score"] for r in recs if r["score"] is not None) / len(recs)
        print(f"{row:>8} | {set_:<12} | {pipe:<8} | {ok}/{len(recs)} | score={sc:.3f} | {ms:.0f} ms")


async def judge_pass() -> int:
    """Ollama-only pass：所有 MLX server 已經 kill 晒先行。補返 evaluator_pending
    嘅 llm_judge records（2 條 fact_multi × 每 row/pipe）。"""
    recs = {f"{r['set']}::{r['id']}": r for r in load_records()}
    runs = _load_runs()
    if not runs:
        print("run.json 空——先跑 rows")
        return 0
    judge_cache: list = []
    n = 0
    for block in runs:
        for rec in block.get("records", []):
            if not rec.get("evaluator_pending"):
                continue
            src = recs.get(f"{rec['set']}::{rec['id']}")
            if src is None:
                continue
            score, passed, note = await _score(src, rec["pred"], judge_cache, no_judge=False)
            rec["score"], rec["passed"], rec["note"] = score, passed, note
            rec["evaluator_pending"] = False
            n += 1
    RESULTS.write_text(json.dumps(runs, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"judge_pass: scored {n} llm_judge records (Ollama-only)")
    return n


async def judge_fs_pass() -> int:
    """Ollama-only pass：用 llm_judge（語言中立）re-score 全部 fact_single preds。
    原本 f1（英文 golden × 粵語 pred 嘅 token overlap）會低估——呢個 pass 畀評語。
    f1 原分保留落 note；score/passed 換做 llm_judge 判定。"""
    recs = {f"{r['set']}::{r['id']}": r for r in load_records()}
    runs = _load_runs()
    if not runs:
        print("run.json 空——先跑 rows")
        return 0
    judge_cache: list = []
    n = 0
    judge_fn = EVALUATORS["llm_judge"]
    for block in runs:
        for rec in block.get("records", []):
            if rec["set"] != "fact_single":
                continue
            src = recs.get(f"fact_single::{rec['id']}")
            if src is None:
                continue
            f1 = rec.get("score")
            ctx = {"judge_cache": judge_cache}
            score, passed, note = await judge_fn(src, rec["pred"], ctx=ctx)
            rec["score_f1"] = f1
            rec["score"] = score
            rec["passed"] = passed
            rec["note"] = f"{note} | f1={f1:.3f}"
            n += 1
    RESULTS.write_text(json.dumps(runs, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"judge_fs_pass: llm_judge re-scored {n} fact_single preds (Ollama-only)")
    return n


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--row", choices=["rag", "base", "lora", "qlora", "better"])
    ap.add_argument("--port", type=int, default=8201)
    ap.add_argument("--model", default="local")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--judge", action="store_true")
    ap.add_argument("--judgefs", action="store_true")
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args()

    if args.judge:
        await judge_pass()
        results = _load_runs()
        print_summary(results)
        return

    if args.judgefs:
        await judge_fs_pass()
        results = _load_runs()
        print_summary(results)
        return

    if args.report:
        results = _load_runs()
        print_summary(results)
        _write_report(results)
        return

    base_url = f"http://127.0.0.1:{args.port}"
    block = await run_row(args.row, base_url, args.model)
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    runs = _load_runs()
    runs = [r for r in runs if r["row"] != args.row]
    runs.append(block)
    RESULTS.write_text(json.dumps(runs, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(block["records"][-20:], ensure_ascii=False, indent=1))


def _load_runs() -> list[dict]:
    if RESULTS.exists():
        try:
            return json.loads(RESULTS.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return []
    return []


def _write_report(results: list[dict]) -> None:
    per = _merge(results)["per"]

    def _agg_metrics(key):
        recs = per[key]
        ok = sum(1 for r in recs if r["passed"])
        ms = sum(r["ms"] for r in recs)
        pts = [r["score"] for r in recs if r["score"] is not None]
        sc = (sum(pts) / len(pts)) if pts else 0.0
        return len(recs), ok, sc, ms

    # 每 row（跨 set 聚合，rag 每 pipe 一條）
    keys = sorted(per)
    agg = {}
    for k in keys:
        row, set_, pipe = k
        if set_ == "__row_total__":
            continue
        agg.setdefault(row, []).append((pipe, set_, *_agg_metrics(k)))

    lines = [
        f"# FIN-MATE E1 · LoRA/QLoRA vs RAG（全 local）bench report",
        f"",
        f"- generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 設定：Qwen3-4B-Instruct-2507 base；LoRA（bf16 base, r=8, 16 layers, 500 iters）；QLoRA（4-bit base）；",
        f"  RAG = naive/hybrid/adaptive 用本地 4-bit base 代答；eval = 34 條 golden，同 D6 同一套 evaluators",
        f"- 全 local：無 Ark／無雲／無 API 費用。ranking 用同一批 golden，同枱對比閉卷 vs RAG。",
        f"- 記憶體友好：每 row 只 serve 1 個 model；llm_judge 拆開做 `--judge` pass（Ollama 單獨）。",
        f"",
        f"## 結論",
        f"",
        f"- **QA 子集（15 條，唯一 RAG 有跑嘅 subset，fact_single 用 llm_judge 語言中立重評）**：",
        f"  RAG hybrid/better 8/15 > naive/adaptive 6/15 > LoRA 閉卷 5/15 > base/QLoRA 4/15。",
        f"  - **fact_multi（4 條）**：RAG 全 pipe 4/4，閉卷只得 base/QLoRA 2/4、LoRA 1/4——",
        f"    多跳 synthesis 靠 retrieval 畀料先做到，閉卷結構性做唔到。",
        f"  - **fact_single（11 條）**：hybrid/better（hybrid+advanced）**4/11** > naive/adaptive 2/11 >",
        f"    LoRA 閉卷 1/11 > base/QLoRA 0/11。RAG 拎到嘅 4 條（fs_01 Azure 38% vs guidance、fs_08 agentic→安全、",
        f"    fs_09 Cloud $50B/+26%、fs_11 市值 $2,977B）全部屬實且含關鍵數字。",
        f"- **fact_single 低分 90% 係 metric artifact，唔係 RAG 失敗**（見下節）。英語 golden × 粵語 pred 嘅",
        f"  `answer_f1` token-overlap 結構性封頂（高質 pred 都只得 f1 0–0.24，低過 PASS 0.25）。",
        f"  用語言中立 llm_judge 重評：`$2,977B（啱）` 由 f1=0.000 → PASS；`50B/+26%（啱）` 由 0.244 → PASS；",
        f"  相反 LoRA 有 2 條 f1 高分（fs_09 0.250、fs_10 0.588）judge 判 FAIL（漏關鍵數字）——f1 高分唔等如啱。",
        f"- **更好 retrieval 有冇幫到手？** better panel（hybrid+advanced，k=15+sparse）對 fact_single 同普通 hybrid",
        f"  一樣 4/11——**樽頸唔喺 retrieval**：加多料（15k、sparse/grep 覆蓋 gold doc）都唔會再升，",
        f"  4B 生成本身先係樽頸（回絕「KB：檔案名」或答漏數字）。",
        f"  反而 **adaptive/naive 只有 2/11**（k=5 太窄，MISS 咗 fs_01 嘅 Deutsche doc、fs_11 嘅 DeMatteo doc）——",
        f"  k 太細先係真 retrieve 樽頸，k=15 或以上即到頂。",
        f"- **QLoRA 保留 base 能力（非-qa task）**：sent_score 5/5、sent_3way 6/6、calc/news 滿分，完全追返 base；",
        f"  LoRA 反而跌（sent_score 3/5、sent_3way 5/6）——FT 有 catastrophic forgetting，QLoRA 傷害細好多。",
        f"- **Latency／資源**：閉卷 0.7–4.8s/record 快過 RAG（naive ~14s、adaptive ~21s、hybrid ~66s/record）；",
        f"  QLoRA 訓練 peak 3.96GB vs LoRA 9.68GB，fused 模型 2.1GB vs 7.5GB，eval 亦更快。",
        f"- **總評**：本地 4B 做係可以，但 fact recall 上限低——公司數就要 RAG + 強 model（D6 hybrid 全 34 條 26/34）；",
        f"  事實類問題 RAG（k≥15）> FT 閉卷，但唔好信英文-f1；要保留原 task 能力 → QLoRA。",
        f"",
        f"## fact_single 深度調查（metric vs llm_judge，每 row 同一批 11 條）",
        f"",
        f"`answer_f1` 將英文 golden 同粵語 pred 用 `[a-z0-9]+` token 化，overlap 結構性封頂 → f1-pass 嚴重低估。",
        f"",
        f"| row / pipe | f1-pass | llm_judge-pass | 被 metric 隱藏嘅啱答案 |",
        f"|---|---|---|---|",
        f"| base（閉卷） | 0/11 | 0/11 | — |",
        f"| LoRA（閉卷） | 3/11 | 1/11 | （fs_09/fs_10 f1 高分但 judge FAIL：漏數字） |",
        f"| QLoRA（閉卷） | 0/11 | 0/11 | — |",
        f"| rag naive | 0/11 | 2/11 | fs_08、fs_09（兩條答啱，f1 只得 0.235/0.244） |",
        f"| rag hybrid | 1/11 | 4/11 | fs_01、fs_08、fs_09、fs_11（fs_11 啱晒但 f1=0.000） |",
        f"| rag adaptive | 0/11 | 2/11 | fs_08、fs_09 |",
        f"| better hybrid | 1/11 | 4/11 | 同上（=普通 hybrid） |",
        f"| better advanced | 1/11 | 4/11 | 同上（=普通 hybrid） |",
        f"",
        f"### 每條 fact_single 根因",
        f"",
        f"| id | 內容 | 根因 |",
        f"|---|---|---|",
        f"| fs_01 | Azure 38% vs guidance 37% | hybrid/better 啱（+38%>37%）但 f1 0.18→FAIL；naive k=5 MISS Deutsche doc |",
        f"| fs_02 | F2Q revenue vs 預期 beat | 答到「略高於市場預期」冇實數 → judge FAIL |",
        f"| fs_03 | 總收入 $81,189M | 數字錯（答 81,215 或 76,441 萬）→ 錯答案 |",
        f"| fs_04 | 股價目標 | KB 冇 → model 求其答 → FAIL |",
        f"| fs_05 | 中國再保 EPS 17.11/15.80 | dense@5/15 都 MISS（table chunk 沉底），sparse 冇 term → 冇料答 |",
        f"| fs_06 | F2Q26 座位數 15M | 答到無咗/漏 → FAIL |",
        f"| fs_07 | Wells Fargo E7 $99 | hybrid/better 答到 $99/用戶（f1 0.41→PASS）但 judge 判 FAIL（pred 加咗「Agent 365/Copilot」可能誇大/假陰性）；naive/adaptive MISS doc |",
        f"| fs_08 | agentic adoption 靠安全 | 全 pipe 啱（judge PASS ×6）但 f1 0.14–0.24→FAIL |",
        f"| fs_09 | Cloud 首破 $50B/+26% | 全 pipe 啱（judge PASS ×6）但 f1 0.244 差少少→FAIL |",
        f"| fs_10 | 辦公 tile+收入 | KB 冇 → FAIL |",
        f"| fs_11 | 市值 $2,977B | hybrid/better 啱（答啱 $2,977B）但 f1=0.000（2,977,b vs 2977）→ 最誇張 1 宗 |",
        f"",
        f"> 即：11 條入面 metric-pass 3/11（loRA 有 2 條係假高分），judge 判 hybrid/better 均有 4/11 真啱。",
        f"> 呢個同 D6 Ark（同 metric）3/11 比較唔公平——D6 都係用英文-f1 量度；judge 版先係真本事。",
        f"> 結論：唔加料都加 k=15 + sparse 就好；4B 生成上限先係事實 recall 樽頸。",
        f"",
        f"## 模型 / 訓練",
        f"",
        f"| item | LoRA | QLoRA |",
        f"|---|---|---|",
        f"| base | Qwen3-4B-Instruct-2507 (bf16) | ...-2507-4bit |",
        f"| train loss (500 iters) | 0.086 | 0.136 |",
        f"| val loss | 0.533 | 0.522 |",
        f"| peak mem | 9.68 GB | 3.96 GB |",
        f"| trained tokens | 47,767 | 55,767 |",
        f"| adapter size | 169 MB | 169 MB |",
        f"| fused model | bf16 (7.5G) | 4-bit (2.1G) |",
        f"| training data | finetune/datasets (576 train / 64 valid) | 同左 |",
        f"| leakage check | golden answers/context 由 training data 剔除 | 同左 |",
        f"",
        f"## 總覽",
        f"",
        f"| row | pipe | 範圍 | n | pass | score(mean) | total ms | ms/rec |",
        f"|---|---|---|---|---|---|---|---|",
    ]
    for row in sorted(agg):
        recs = agg[row]
        pipes = " / ".join(sorted({x[0] for x in recs}))
        n = sum(x[2] for x in recs)
        scope = "QA 15 條 ×pipe" if row == "rag" else "全部 34 條（閉卷）"
        ok = sum(x[3] for x in recs)
        scs = [x[4] for x in recs]
        sc = (sum(scs) / len(scs)) if scs else 0.0
        ms = sum(x[5] for x in recs)
        pipes = " / ".join(sorted({x[0] for x in recs}))
        lines.append(f"| **{row}** | {pipes} | {scope} | {n} | **{ok}/{n}** | {sc:.3f} | {ms:.0f} | {ms/n:.0f} |")
    lines += [
        "",
        f"> D6 baseline（Ark `seed-1-6-flash` + hybrid RAG，全 34 條）= 26/34、fact_single 3/11（英文-f1 量度）、~40.5s/record。",
        f"> 本場 rag/better rows 只跑 QA 15 條（fact_multi 4 + fact_single 11），其餘 19 條閉卷 task 冇 RAG 版本可比。",
        f"> 公平比法：QA 子集內「本地 RAG vs 閉卷」，閉卷總做唔到 multi-hop；RAG 得唔到 D6 級 fact_single（但 D6 分都用英文-f1 低估）。",
        "",
        "## per-set 明細",
        "",
    ]
    for key in keys:
        row, set_, pipe = key
        recs = per[key]
        n, ok, sc, ms = (len(recs), sum(1 for r in recs if r["passed"]),
                         (sum(r["score"] for r in recs if r["score"] is not None) / len(recs)) if recs else 0.0,
                         sum(r["ms"] for r in recs))
        lines.append(f"### {row} · {pipe} · {set_}（{ok}/{n}，score={sc:.3f}，{ms:.0f} ms）")
        for r in recs:
            flag = "OK" if r["passed"] else "--"
            lines.append(f"- `{r['id']}` score={r['score']} pass={flag} {r['ms']:.0f}ms "
                         f"{('| ' + r['note']) if r.get('note') else ''}")
            if r.get("pred"):
                lines.append(f"  pred: {r['pred'][:160]}")
    (THIS / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("report.md written")


if __name__ == "__main__":
    asyncio.run(main())