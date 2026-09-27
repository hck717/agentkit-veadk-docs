"""
Run all invoice-pipeline evals over one ground-truth set, sharing a single
chain run per image (OCR -> Translation -> Validation) so agents are not
re-invoked across scripts.

Usage:
  python eval/run_all.py --test-data eval/test_data/ground_truth/
  python eval/run_all.py --test-data eval/test_data/ground_truth/ --mock --ci
  python eval/run_all.py --test-data eval/test_data/ground_truth/ --out eval/results
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval import (
    ocr_eval, translation_eval, validation_eval, aggregation_eval, approval_eval,
)

# name -> (evaluate_fn, {metric: min_threshold})
SCOPE = [
    ("ocr_eval", ocr_eval.evaluate, {"ocr_field_f1": 0.85}),
    ("translation_eval", translation_eval.evaluate, {"numeric_preservation_rate": 1.0}),
    ("validation_eval", validation_eval.evaluate, {"bug_finding_rate": 0.90}),
    ("aggregation_eval", aggregation_eval.evaluate, {"total_error_rate": 0.05}),
    ("approval_eval", approval_eval.evaluate, {"anomaly_precision": None}),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all invoice-pipeline evals")
    parser.add_argument("--test-data", default="eval/test_data/ground_truth/")
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--ci", action="store_true")
    parser.add_argument("--out", default=None)
    parser.add_argument("--session", default=None)
    parser.add_argument("--user", default="eval_user")
    args = parser.parse_args()

    cache: dict = {}
    reports: dict = {}
    code = 0

    for name, fn, thresholds in SCOPE:
        print(f"\n=== {name} ===")
        res = fn(args.test_data, mock=args.mock, out=None, ci=False,
                 threshold=0.0, session_id=args.session, user_id=args.user,
                 cache=cache)
        reports[name] = res
        if args.ci:
            for key, thr in thresholds.items():
                if thr is None:
                    continue
                val = res.get(key)
                if val is None:
                    print(f"[CI] {name}.{key} = N/A -> FAIL")
                    code = 1
                elif float(val) < thr:
                    print(f"[CI] {name}.{key} = {val} < {thr} -> FAIL")
                    code = 1
                else:
                    print(f"[CI] {name}.{key} = {val} >= {thr} -> PASS")

    combined = {"reports": reports}
    if args.out:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "latest.json"
        path.write_text(json.dumps(combined, indent=2, ensure_ascii=False),
                        encoding="utf-8")
        print(f"\n[Eval] combined report written: {path}")

    summary = {
        name: {k: v for k, v in rep.items() if k not in ("cases",)}
        for name, rep in reports.items()
    }
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
