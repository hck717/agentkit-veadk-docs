"""RAG Optimization trace analysis: 由 events.jsonl 抽 speed/time/processes，
覆蓋 D7（8 runs：default/chunk/mm/gen × naive/hybrid）同 D4 原版 RAG（5 pipes × 16 題）。

用法：
  python trace_analysis.py        # 讀 results/ 落 call，輸出結構化 trace 去 stdout
  python trace_analysis.py --all  # 連 D4 advanced/corrective/adaptive/agentic 都計
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
D7 = RESULTS / "d7_final"
D4 = RESULTS / "d4_original"

# USD / 1M tokens（同 _lib.PRICES）
USD = {"i": 0.021, "o": 0.211, "c": 0.004}

# D7 index 建立時間（run 時 stdout 捕獲）
INDEX_BUILD = {"default (512/50, text)": "13.2s", "chunk (256/50, text)": "9.4s", "mm (512/50, text+vis)": "8.8s"}

D4_PIPES = ("naive", "hybrid", "advanced", "corrective", "adaptive")
D7_RUNS = ("d7_default_naive", "d7_default_hybrid", "d7_chunk_naive", "d7_chunk_hybrid",
           "d7_mm_naive", "d7_mm_hybrid", "d7_gen_naive", "d7_gen_hybrid")


def _cost(prompt, completion, cached=0):
    return ((prompt - cached) * USD["i"] + cached * USD["c"] + completion * USD["o"]) / 1e6


def analyze_d7(run: str) -> dict:
    ev = [json.loads(l) for l in (D7 / run / "events.jsonl").read_text().splitlines() if l.strip()]
    info = json.loads((D7 / run / "info.json").read_text())
    return _analyze(ev, info, run)


def analyze_d4(pipe: str) -> dict:
    ev = [json.loads(l) for l in (D4 / pipe / "events.jsonl").read_text().splitlines() if l.strip()]
    info = {"axis": "original", "strategy": pipe}
    return _analyze(ev, info, f"D4·{pipe}")


def _analyze(ev, info, label):
    per_item = {}
    for e in ev:
        per_item.setdefault(e["eid"], {"retrieve_ms": 0.0, "answer_ms": 0.0, "total_ms": 0.0,
                                       "prompt": 0, "completion": 0, "cached": 0, "stages": []})
        p = per_item[e["eid"]]
        p["stages"].append(e["stage"])
        ms = e.get("ms") or 0
        if e["stage"] == "retrieve":
            p["retrieve_ms"] += ms
        elif e["stage"] == "answer":
            p["answer_ms"] += ms
        p["total_ms"] += ms
        p["prompt"] += e.get("tokens", {}).get("prompt", 0) or 0
        p["completion"] += e.get("tokens", {}).get("completion", 0) or 0
        p["cached"] += e.get("tokens", {}).get("cached", 0) or 0
    n = len(per_item)
    agg = {
        "run": label, "axis": info["axis"], "strategy": info["strategy"],
        "n_items": n,
        "retrieve_ms_avg": sum(v["retrieve_ms"] for v in per_item.values()) / n,
        "answer_ms_avg": sum(v["answer_ms"] for v in per_item.values()) / n,
        "total_ms_avg": sum(v["total_ms"] for v in per_item.values()) / n,
        "total_s": sum(v["total_ms"] for v in per_item.values()) / 1000,
        "prompt": sum(v["prompt"] for v in per_item.values()),
        "completion": sum(v["completion"] for v in per_item.values()),
        "cached": sum(v["cached"] for v in per_item.values()),
        "usd": sum(_cost(v["prompt"], v["completion"], v["cached"]) for v in per_item.values()),
        "stage_counts": {},
    }
    for p in per_item.values():
        joined = " → ".join(p["stages"])
        agg["stage_counts"][joined] = agg["stage_counts"].get(joined, 0) + 1
    return agg


def fmt(v, d=1):
    return f"{v:.{d}f}"


def main():
    only_d7 = "--all" not in sys.argv
    fair_dir = None
    if "--fair" in sys.argv:
        raw = sys.argv[sys.argv.index("--fair") + 1]
        p = Path(raw)
        fair_dir = p if p.exists() else RESULTS / "fair" / f"runs_{raw}"
        fair_dir = fair_dir if fair_dir.exists() else None
    print("=== D7 runs ===\n")
    print(f"{'run':24s} {'n':>3s} {'retr/題(ms)':>13s} {'answer/題(ms)':>15s} {'total/題(ms)':>13s} {'total(s)':>8s} {'prompt':>8s} {'comp':>6s} {'USD':>8s}")
    for r in D7_RUNS:
        a = analyze_d7(r)
        print(f"{r:24s} {a['n_items']:>3d} {fmt(a['retrieve_ms_avg']):>13s} {fmt(a['answer_ms_avg']):>15s} "
              f"{fmt(a['total_ms_avg']):>13s} {fmt(a['total_s']):>8s} {a['prompt']:>8d} {a['completion']:>6d} ${a['usd']:.4f}")
    print("\n### D7 stage 流程（每題 events 次序）")
    for r in D7_RUNS:
        a = analyze_d7(r)
        sc = a["stage_counts"]
        joined = list(sc.keys())
        print(f"  {r:24s} {joined}  (分佈: {sc})")

    print("\n=== D4 original RAG ===\n")
    pipes = D4_PIPES if only_d7 else D4_PIPES
    for p in pipes:
        a = analyze_d4(p)
        print(f"{a['run']:24s} {a['n_items']:>3d} {fmt(a['retrieve_ms_avg']):>13s} {fmt(a['answer_ms_avg']):>15s} "
              f"{fmt(a['total_ms_avg']):>13s} {fmt(a['total_s']):>8s} {a['prompt']:>8d} {a['completion']:>6d} ${a['usd']:.4f}")

    print("\n=== D8 fair runs（BytePlus AI + OpenViking） ===")
    a8 = []
    if fair_dir and fair_dir.exists():
        for dr in sorted(fair_dir.glob("fair_*")):
            if not dr.is_dir():
                continue
            ev = [json.loads(l) for l in (dr / "events.jsonl").read_text().splitlines() if l.strip()]
            info = json.loads((dr / "info.json").read_text())
            a8.append(_analyze(ev, info, f"D8·{info['axis']}·{info['strategy']}"))
    if not a8:
        print("  （未有 fair runs；用 --fair <runs 目錄名或路徑> 指定）")
    for a in a8:
        print(f"{a['run']:24s} {a['n_items']:>3d} {fmt(a['retrieve_ms_avg']):>13s} {fmt(a['answer_ms_avg']):>15s} "
              f"{fmt(a['total_ms_avg']):>13s} {fmt(a['total_s']):>8s} {a['prompt']:>8d} {a['completion']:>6d} ${a['usd']:.4f}")

    print("\n=== D7 index build 時間（一次，run 前） ===")
    for k, v in INDEX_BUILD.items():
        print(f"  {k:28s} {v}")


if __name__ == "__main__":
    main()