"""
Approval Agent evaluation — anomaly precision / recall vs ground truth labels.
Usage: python eval/approval_eval.py --test-data eval/test_data/ground_truth/
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.eval_core import (
    add_common_args, finish, gt_fields, image_key_of, load_ground_truth,
    run_chain,
)

ANOMALY_STATUSES = {"pending_review", "rejected"}


def evaluate(ground_truth_dir: str, mock: bool = False, out: str | None = None,
             ci: bool = False, threshold: float = 1.0,
             session_id: str | None = None, user_id: str = "eval_user",
             cache: dict | None = None) -> dict:
    entries = load_ground_truth(ground_truth_dir)
    if not entries:
        raise SystemExit(f"[Eval] no ground truth found in {ground_truth_dir}")

    from agents.approval_agent import ApprovalAgent

    tp = fp = fn = tn = 0
    cases = []
    for entry in entries:
        image_key = image_key_of(entry)
        stem = Path(image_key).stem or Path(entry["_source"]).stem
        sid = session_id or f"eval-approval-{stem}"
        _, _, validated = run_chain(image_key, stem, mock, sid, user_id, cache)

        result = ApprovalAgent(mock=mock).run({
            **validated, "session_id": sid, "user_id": user_id,
        })
        status = result.get("status", "unknown")
        predicted_anomaly = status in ANOMALY_STATUSES
        actual_anomaly = bool(entry.get("anomaly", False))

        tp += int(predicted_anomaly and actual_anomaly)
        fp += int(predicted_anomaly and not actual_anomaly)
        fn += int((not predicted_anomaly) and actual_anomaly)
        tn += int((not predicted_anomaly) and not actual_anomaly)

        cases.append({
            "image": image_key,
            "status": status,
            "predicted_anomaly": bool(predicted_anomaly),
            "actual_anomaly": bool(actual_anomaly),
            "reviewer_notes": result.get("reviewer_notes", ""),
        })

    precision = round(tp / (tp + fp), 4) if (tp + fp) else None
    recall = round(tp / (tp + fn), 4) if (tp + fn) else None

    result = {
        "anomaly_precision": precision,
        "anomaly_recall": recall,
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "cases": cases,
        "num_invoices": len(entries),
        "num_anomalies": tp + fn,
        "status": "ok",
    }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Approval evaluation")
    add_common_args(parser, default_threshold=1.0)
    parser.set_defaults(test_data="eval/test_data/ground_truth/")
    args = parser.parse_args()
    res = evaluate(args.test_data, mock=args.mock, out=args.out, ci=args.ci,
                   threshold=args.threshold, session_id=args.session,
                   user_id=args.user)
    sys.exit(finish("approval_eval", res, args, "anomaly_precision"))
