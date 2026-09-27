"""FIN-MATE D6 gate：對比 baseline（regression），決定 exit 0/1。

`--lock-baseline`：將目前 eval report 嘅 per-set score / exact_mean / judge_rate
寫落 `eval/baseline.json`（用呢個做往後門檻）。之後任何 run 低過 baseline − margin
就 fail ——「改壞 prompt → fail」嘅機制本體。

用法：
  ./.venv/bin/python -m eval.gate --lock-baseline          # 第一次：錄底 baseline
  ./.venv/bin/python -m eval.gate                          # 之後：對比（exit 0 pass / 1 fail）
  ./.venv/bin/python -m eval.gate --report eval/reports/latest.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "eval" / "reports"
BASELINE = ROOT / "eval" / "baseline.json"
CONFIG = ROOT / "eval" / "gate_config.json"

DEFAULT_CONFIG = {"margin": 0.03, "judge_margin": 0.10}


def _fmt(v, nd=3):
    return f"{v:.{nd}f}" if isinstance(v, (int, float)) else "n/a"


def _load_config() -> dict:
    if CONFIG.exists():
        return {**DEFAULT_CONFIG, **json.loads(CONFIG.read_text(encoding="utf-8"))}
    return dict(DEFAULT_CONFIG)


def _overall(rows: list[dict]) -> dict:
    scored = [r for r in rows if not r.get("skipped")]
    judge = [r for r in scored if r.get("evaluator") == "llm_judge"]
    exact = [r for r in scored if r.get("evaluator") != "llm_judge"]
    exact_mean = (sum(r["score"] for r in exact) / len(exact)) if exact else None
    judge_rate = (sum(1 for r in judge if r.get("passed")) / len(judge)) if judge else None
    score = (sum(r["score"] for r in scored) / len(scored)) if scored else None
    return {"n": len(scored), "passed": sum(1 for r in scored if r.get("passed")),
            "score": score, "exact_mean": exact_mean, "judge_rate": judge_rate}


def _check(report: dict, baseline: dict, cfg: dict) -> tuple[list, list]:
    margin = cfg["margin"]
    jmargin = cfg["judge_margin"]
    checks, fails = [], []
    # overall
    o = _overall(report["rows"])
    bo = baseline.get("overall") or {}
    for name, now, base in (("score", o.get("score"), bo.get("score")),
                            ("exact_mean", o.get("exact_mean"), bo.get("exact_mean")),
                            ("judge_rate", o.get("judge_rate"), bo.get("judge_rate"))):
        if now is None or base is None:
            continue
        th = base - (jmargin if name == "judge_rate" else margin)
        row = ("overall", name, now, base, now < th - 1e-9)
        checks.append(row)
        if row[4]:
            fails.append(row)
    # per-set
    for sname, agg in (report.get("sets") or {}).items():
        b = (baseline.get("sets") or {}).get(sname)
        if not b:
            checks.append((sname, "baseline", None, None, True))
            fails.append((sname, "baseline", None, None, True))
            continue
        for name, now, base in (("score", agg.get("score"), b.get("score")),
                                ("exact_mean", agg.get("exact_mean"), b.get("exact_mean")),
                                ("judge_rate", agg.get("judge_rate"), b.get("judge_rate"))):
            if now is None or base is None:
                continue
            th = base - (jmargin if name == "judge_rate" else margin)
            row = (sname, name, now, base, now < th - 1e-9)
            checks.append(row)
            if row[4]:
                fails.append(row)
    return checks, fails


def _print_table(checks, baseline_ts: str) -> None:
    lines = ["# Gate", f"- baseline: {baseline_ts}", "",
             "| scope | metric | now | baseline | thresh | verdict |", "|---|---|---|---|---|---|"]
    for sname, name, now, base, fail in checks:
        if base is None:
            lines.append(f"| {sname} | {name} | — | 冇 baseline | — | NO BASE |")
            continue
        lines.append(f"| {sname} | {name} | {_fmt(now)} | {_fmt(base)} | {_fmt(base - 0.03)} | {'FAIL' if fail else 'ok'} |")
    print("\n".join(lines) + "\n")


def main():
    p = argparse.ArgumentParser(description="FIN-MATE D6 gate")
    p.add_argument("--report", default=str(REPORTS / "latest.json"))
    p.add_argument("--lock-baseline", action="store_true")
    p.add_argument("--margin", type=float, default=None)
    p.add_argument("--judge-margin", type=float, default=None)
    p.add_argument("--config", default=str(CONFIG))
    args = p.parse_args()

    cfg = _load_config()
    if args.margin is not None:
        cfg["margin"] = args.margin
    if args.judge_margin is not None:
        cfg["judge_margin"] = args.judge_margin

    rp = Path(args.report)
    if not rp.exists():
        print(f"[error] report 唔存在: {rp}")
        return 2
    report = json.loads(rp.read_text(encoding="utf-8"))

    if args.lock_baseline:
        baseline = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tag": report.get("tag"),
            "suite": report.get("suite"),
            "model": (report.get("models") or {}).get("primary"),
            "margin": cfg["margin"],
            "judge_margin": cfg["judge_margin"],
            "overall": _overall(report["rows"]),
            "sets": {s: dict(agg) for s, agg in (report.get("sets") or {}).items()},
        }
        BASELINE.write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"baseline locked → {BASELINE}")
        print(f"  overall score={_fmt(baseline['overall'].get('score'))} "
              f"exact={_fmt(baseline['overall'].get('exact_mean'))} "
              f"judge={_fmt(baseline['overall'].get('judge_rate'))}")
        return 0

    if not BASELINE.exists():
        print(f"[error] 未有 baseline（{BASELINE}）。第一次請用 --lock-baseline。")
        return 2
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))

    checks, fails = _check(report, baseline, cfg)
    _print_table(checks, baseline.get("ts", "?"))
    if fails:
        print(f"GATE FAIL — {len(fails)} concern(s)")
        return 1
    print("GATE PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())