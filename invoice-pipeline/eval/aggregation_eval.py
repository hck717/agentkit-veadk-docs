"""
Aggregation Agent evaluation — total error rate & duplicate detection accuracy.
Usage: python eval/aggregation_eval.py --test-data eval/test_data/ground_truth/
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.eval_core import (
    add_common_args, finish, gt_fields, image_key_of, load_ground_truth,
    _num, run_chain,
)


def evaluate(ground_truth_dir: str, mock: bool = False, out: str | None = None,
             ci: bool = False, threshold: float = 0.05,
             session_id: str | None = None, user_id: str = "eval_user",
             cache: dict | None = None) -> dict:
    entries = load_ground_truth(ground_truth_dir)
    if not entries:
        raise SystemExit(f"[Eval] no ground truth found in {ground_truth_dir}")

    from agents.aggregation_agent import AggregationAgent

    expected_total = sum(
        _num(gt_fields(e).get("amount", 0)) or 0.0 for e in entries)

    validated_invoices = []
    for entry in entries:
        image_key = image_key_of(entry)
        stem = Path(image_key).stem or Path(entry["_source"]).stem
        sid = session_id or f"eval-agg-{stem}"
        _, _, validated = run_chain(image_key, stem, mock, sid, user_id, cache)
        validated_invoices.append(validated)

    batch_sid = session_id or "eval-agg-batch"
    agg = AggregationAgent(mock=mock).run({
        "invoices": validated_invoices,
        "session_id": batch_sid,
        "user_id": user_id,
    })
    predicted_total = float(agg.get("total_amount", 0) or 0)

    if expected_total:
        total_error_rate = abs(predicted_total - expected_total) / expected_total
    else:
        total_error_rate = 1.0 if predicted_total else 0.0

    dup_batch = [dict(validated_invoices[0])] + validated_invoices
    agg_dup = AggregationAgent(mock=mock).run({
        "invoices": dup_batch,
        "session_id": f"{batch_sid}-dup",
        "user_id": user_id,
    })
    dup_flags = agg_dup.get("duplicate_flags", [])
    duplicate_detection_accuracy = 1.0 if len(dup_flags) >= 1 else 0.0

    result = {
        "total_error_rate": round(total_error_rate, 4),
        "predicted_total_amount": round(predicted_total, 2),
        "expected_total_amount": round(expected_total, 2),
        "duplicate_detection_accuracy": duplicate_detection_accuracy,
        "duplicate_flags": dup_flags,
        "invoice_count": len(validated_invoices),
        "num_invoices": len(entries),
        "status": "ok",
    }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aggregation evaluation")
    add_common_args(parser, default_threshold=0.05)
    parser.set_defaults(test_data="eval/test_data/ground_truth/")
    args = parser.parse_args()
    res = evaluate(args.test_data, mock=args.mock, out=args.out, ci=args.ci,
                   threshold=args.threshold, session_id=args.session,
                   user_id=args.user)
    sys.exit(finish("aggregation_eval", res, args, "total_error_rate"))
