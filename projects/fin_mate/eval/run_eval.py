"""FIN-MATE D6 評估 runner：逐 golden record 出 prediction → 評分 → reports。

Prediction 路徑（全部用 fin-mate 現役模型 seed-1-6-flash-250715 / Ark responses）：
  qa        → `strategies.run('hybrid', …)` 過真 OpenViking KB（production pipeline，唔係新 RAG pipe）
  tool_call → model 出 `{tool,args}` JSON → harness 執行真 tool（calc / read_news_file）→ 對 golden
  sentiment → completion + parse（sent_score 係 strict JSON）

評分用 eval/evaluators.py 嘅 EVALUATORS；`llm_judge` 用本地 qwen3（Ollama），有 cache，
`--no-judge` 就 skip judge records（只評 rule-based）。`--lock-baseline` 唔喺度（見 gate.py）。

用法（root = projects/fin_mate）：
  ./.venv/bin/python -m eval.run_eval                         # 全部 6 sets
  ./.venv/bin/python -m eval.run_eval --suite qa --no-judge   # 快速 lane
輸出：eval/reports/<tag>.{json,md} + 更新 eval/reports/latest.{json,md}
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

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments import _lib  # noqa: E402
from experiments.rag_bench.eval_set import all_doc_uris  # noqa: E402

from eval.evaluators import EVALUATORS  # noqa: E402

SET_FILES = {
    "qa": ["qa/fact_single.jsonl", "qa/fact_multi.jsonl"],
    "tool_call": ["tool_call/calc_expr.jsonl", "tool_call/news_extract.jsonl"],
    "sentiment": ["sentiment/sent_3way.jsonl", "sentiment/sent_score.jsonl"],
}
GOLDEN_ROOT = ROOT / "eval" / "golden_datasets"
REPORTS = ROOT / "eval" / "reports"

TOOL_SYSTEM = (
    "你係 fin-mate 金融研究 agent。要計數時必須輸出嚴格 JSON（唔加任何其他字）："
    '{"tool": "calc", "args": {"expr": "<算式>"}}。要讀新聞 CSV 時：'
    '{"tool": "read_news_file", "args": {"path": "<csv path>"}}。'
)
SENT_SYSTEM = "你係金融新聞情緒分類器。嚴格跟 prompt 內嘅輸出格式。"
TRAP_SYSTEM = "根據已知資料回答，唔好老作。如果問題嘅答案唔喺資料入面，直接答『無資料』。"


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_records(suite: str) -> list[dict]:
    recs = []
    rels = [r for k, v in SET_FILES.items() for r in v] if suite == "all" else SET_FILES[suite]
    for rel in rels:
        for line in (GOLDEN_ROOT / rel).read_text(encoding="utf-8").splitlines():
            if line.strip():
                recs.append(json.loads(line))
    return recs


async def _pred_qa(rec: dict, doc_uris: dict) -> dict:
    from experiments.rag_bench import strategies

    cat = (rec.get("meta") or {}).get("src_cat") or "fact"
    t0 = time.perf_counter()
    trace: list = []
    res = await strategies.run("hybrid", rec["prompt"], rec["id"], cat, doc_uris, trace=trace)
    ms = (time.perf_counter() - t0) * 1000
    usage = {"prompt": sum(e.get("tokens", {}).get("prompt", 0) for e in res["events"]),
             "completion": sum(e.get("tokens", {}).get("completion", 0) for e in res["events"]),
             "cached": sum(e.get("tokens", {}).get("cached", 0) for e in res["events"])}
    uris = res.get("uris") or []
    return {"pred": res.get("answer") or "", "usage": usage, "ms": ms,
            "extra": {"uris_top": uris[:3], "n_events": len(res["events"])}}


async def _pred_chat(rec: dict, system: str) -> dict:
    t0 = time.perf_counter()
    c = await _lib.ark_complete(
        [{"role": "system", "content": system}, {"role": "user", "content": rec["prompt"]}],
        max_tokens=512,
    )
    ms = (time.perf_counter() - t0) * 1000
    usage = {"prompt": c.prompt_tokens, "completion": c.completion_tokens, "cached": c.cached_tokens}
    return {"pred": c.text, "usage": usage, "ms": c.ms or ms, "extra": {}}


async def _predict(rec: dict, doc_uris: dict | None) -> dict:
    if rec["type"] == "qa" and rec["evaluator"] != "trap":
        assert doc_uris is not None
        return await _pred_qa(rec, doc_uris)
    if rec["type"] == "qa":  # trap：模擬「KB 檢索空」嘅 path——直接問，唔行 KB
        ctx = "（背景：KB 檢索結果：無相關資料。）"
        return await _pred_chat({**rec, "prompt": rec["prompt"] + "\n\n" + ctx}, TRAP_SYSTEM)
    if rec["type"] == "tool_call":
        return await _pred_chat(rec, TOOL_SYSTEM)
    return await _pred_chat(rec, SENT_SYSTEM)


async def _score(rec: dict, pred: dict, judge_cache: list, no_judge: bool) -> dict:
    evaluator = rec["evaluator"]
    ctx = {"judge_cache": judge_cache}
    if evaluator == "llm_judge" and no_judge:
        return {"skipped": True, "score": None, "passed": None, "note": "skipped (--no-judge)"}
    fn = EVALUATORS[evaluator]
    if evaluator == "llm_judge":
        score, passed, note = await fn(rec, pred["pred"], ctx=ctx)
    else:
        score, passed, note = fn(rec, pred["pred"], ctx=ctx)
    return {"skipped": False, "score": score, "passed": bool(passed), "note": note}


def _mu(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def _fmt(v, nd=3):
    return f"{v:.{nd}f}" if isinstance(v, (int, float)) else "n/a"


def _agg(rows: list[dict]) -> dict:
    scored = [r for r in rows if not r.get("skipped")]
    n = len(scored)
    judge = [r for r in scored if r.get("evaluator") == "llm_judge"]
    exact = [r for r in scored if r.get("evaluator") != "llm_judge"]
    return {
        "n": n,
        "passed": sum(1 for r in scored if r.get("passed")),
        "score": _mu([r.get("score") for r in scored]),
        "exact_mean": _mu([r.get("score") for r in exact]),
        "judge_rate": (_mu([1.0 if r.get("passed") else 0.0 for r in judge]) if judge else None),
        "tokens": sum((r.get("usage") or {}).get("prompt", 0) + (r.get("usage") or {}).get("completion", 0) for r in rows),
        "usd": sum(_lib.usd((r.get("usage") or {}).get("prompt", 0),
                            (r.get("usage") or {}).get("completion", 0),
                            (r.get("usage") or {}).get("cached", 0)) for r in rows),
        "ms": sum(r.get("ms", 0) for r in rows),
    }


def _write_md(path: Path, tag: str, sets: dict, rows: list[dict]) -> None:
    lines = [f"# FIN-MATE Eval Report · {tag}", "", f"- generated: {_now()}",
             f"- records: {len(rows)}   judged: {sum(1 for r in rows if r.get('evaluator')=='llm_judge' and not r.get('skipped'))}",
             "", "## per-set", "", "| set | n | score | pass | exact_mean | judge_rate | tokens | usd | ms |",
             "|---|---|---|---|---|---|---|---|---|"]
    for k, a in sets.items():
        jr = _fmt(a["judge_rate"]) if a["judge_rate"] is not None else "n/a"
        lines.append(f"| {k} | {a['n']} | {_fmt(a['score'])} | {a['passed']}/{a['n']} | {_fmt(a['exact_mean'])} "
                     f"| {jr} | {a['tokens']} | ${_fmt(a['usd'], 4)} | {_fmt(a['ms'], 0)} |")
    vo = _agg(rows)
    lines.append(f"| **overall** | {vo['n']} | {_fmt(vo['score'])} | {vo['passed']}/{vo['n']} | "
                 f"{_fmt(vo['exact_mean'])} | {_fmt(vo['judge_rate']) if vo['judge_rate'] is not None else 'n/a'} "
                 f"| {vo['tokens']} | ${_fmt(vo['usd'], 4)} | {_fmt(vo['ms'], 0)} |")
    lines += ["", "## per-record", "", "| id | set | evaluator | score | pass | ms | note |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        sc = _fmt(r["score"]) if r["score"] is not None else "skip"
        p = "PASS" if r.get("passed") else ("-" if r.get("skipped") else "FAIL")
        note = (r.get("note") or "")[:70].replace("|", "/")
        lines.append(f"| {r['id']} | {r['set']} | {r['evaluator']} | {sc} | {p} | {_fmt(r['ms'],0)} | {note} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def _run(args) -> int:
    _lib.load_env()
    if not os.environ.get("MODEL_AGENT_API_KEY"):
        print("[error] MODEL_AGENT_API_KEY 空——eval 要行真 Ark model。")
        return 2

    records = load_records(args.suite)
    doc_uris = all_doc_uris() if args.suite in ("qa", "all") else None
    use_qa = args.suite in ("qa", "all")

    tag = args.tag or time.strftime("%y%m%d_%H%M")
    out_dir = REPORTS / tag
    out_dir.mkdir(parents=True, exist_ok=True)

    judge_cache: list = []
    if args.no_judge:
        judge_cache = []

    rows: list[dict] = []
    budget = args.max_tokens
    used = 0
    for rec in records:
        if used + 1200 > budget and rec["type"] == "qa":
            continue  # QA 較貴，budget 到先 skip（tool/sent 慳）
        if rec["type"] == "qa" and not use_qa:
            continue
        t0 = time.perf_counter()
        pred = await _predict(rec, doc_uris)
        score = await _score(rec, pred, judge_cache, args.no_judge)
        row = {"id": rec["id"], "set": rec["set"], "type": rec["type"], "evaluator": rec["evaluator"],
               "prompt": rec["prompt"], "pred": pred["pred"], **pred["extra"],
               "usage": pred["usage"], "ms": pred["ms"], **score,
               "skipped": score.get("skipped", False), "golden": rec.get("golden")}
        rows.append(row)
        used += (pred["usage"].get("prompt", 0) or 0) + (pred["usage"].get("completion", 0) or 0)
        flag = "PASS" if row.get("passed") else ("SKIP" if row.get("skipped") else "FAIL")
        note = (row.get("note") or "")[:60]
        print(f"[{row['id']}] {flag}  {row['set']:<16} {row['evaluator']:<10} ms={row['ms']:.0f} {note}")
        if (time.perf_counter() - t0) > 1:  # noisy marker
            pass

    sets = {sname: _agg([r for r in rows if r["set"] == sname]) for sname in dict.fromkeys(r["set"] for r in rows)}

    report = {"tag": tag, "ts": _now(),
              "models": {"primary": os.environ.get("MODEL_PRIMARY", "seed-1-6-flash-250715")},
              "suite": args.suite, "no_judge": args.no_judge, "max_tokens_budget": budget,
              "used_tokens": used, "sets": sets, "rows": rows}
    (out_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    _write_md(out_dir / "report.md", tag, sets, rows)
    (REPORTS / "latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    _write_md(REPORTS / "latest.md", tag, sets, rows)
    if judge_cache:
        cache_f = out_dir / "judge_cache.jsonl"
        cache_f.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in judge_cache), encoding="utf-8")
    print(f"\nused_tokens: {used}/{budget}  ${_lib.usd(used,0):.4f}")
    print(f"done → {REPORTS / tag}")
    return 0


def main():
    p = argparse.ArgumentParser(description="FIN-MATE D6 eval runner")
    p.add_argument("--suite", choices=["qa", "tool_call", "sentiment", "all"], default="all")
    p.add_argument("--no-judge", action="store_true", help="skip llm_judge records（只 rule-based）")
    p.add_argument("--tag", default="", help="run tag（default timestamp）")
    p.add_argument("--max-tokens", type=int, default=250_000)
    args = p.parse_args()
    sys.exit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()