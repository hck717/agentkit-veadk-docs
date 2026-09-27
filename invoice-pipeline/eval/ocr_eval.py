"""
OCR Agent evaluation — compare extracted fields against ground truth.
Usage: python eval/ocr_eval.py --test-data eval/test_data/ground_truth/
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.eval_core import (
    add_common_args, cer, field_f1, field_match, finish, gt_fields,
    image_key_of, line_items_match, load_ground_truth, run_ocr, SCALAR_FIELDS,
)


def evaluate(ground_truth_dir: str, mock: bool = False, out: str | None = None,
             ci: bool = False, threshold: float = 0.85,
             session_id: str | None = None, user_id: str = "eval_user",
             cache: dict | None = None) -> dict:
    entries = load_ground_truth(ground_truth_dir)
    if not entries:
        raise SystemExit(f"[Eval] no ground truth found in {ground_truth_dir}")

    cases = []
    per_field_tp: dict[str, int] = {}
    per_field_total: dict[str, int] = {}
    cer_nums: list[float] = []
    cer_vendors: list[float] = []

    for entry in entries:
        fields = gt_fields(entry)
        image_key = image_key_of(entry)
        stem = Path(image_key).stem or Path(entry["_source"]).stem
        sid = session_id or f"eval-ocr-{stem}"
        raw = run_ocr(image_key, stem, mock, sid, user_id, cache)

        case = {"image": image_key, "predicted": raw, "truth": fields}
        for fld in SCALAR_FIELDS:
            matched = field_match(raw.get(fld), fields.get(fld), fld)
            per_field_tp[fld] = per_field_tp.get(fld, 0) + int(matched)
            per_field_total[fld] = per_field_total.get(fld, 0) + 1
            case[f"{fld}_match"] = bool(matched)

        li = line_items_match(raw.get("line_items", []), fields.get("line_items", []))
        case["line_items"] = li
        case["cer_invoice_number"] = cer(
            fields.get("invoice_number", ""), raw.get("invoice_number", ""))
        case["cer_vendor"] = cer(fields.get("vendor", ""), raw.get("vendor", ""))
        cer_nums.append(case["cer_invoice_number"])
        cer_vendors.append(case["cer_vendor"])
        cases.append(case)

    per_field: dict[str, dict] = {}
    total_matched = 0
    total_fields = 0
    for fld in SCALAR_FIELDS:
        tot = per_field_total.get(fld, 0)
        tp = per_field_tp.get(fld, 0)
        p = tp / tot if tot else 0.0
        per_field[fld] = {"precision": round(p, 4), "recall": round(p, 4), "n": tot}
        total_matched += tp
        total_fields += tot

    n_cases = max(1, len(cases))
    li_prec = sum(c["line_items"]["line_items_precision"] for c in cases) / n_cases
    li_rec = sum(c["line_items"]["line_items_recall"] for c in cases) / n_cases
    per_field["line_items"] = {
        "precision": round(li_prec, 4), "recall": round(li_rec, 4), "n": len(cases),
    }

    result = {
        "ocr_field_f1": round(field_f1(total_matched, total_fields), 4),
        "cer_invoice_number": round(sum(cer_nums) / len(cer_nums), 4) if cer_nums else None,
        "cer_vendor": round(sum(cer_vendors) / len(cer_vendors), 4) if cer_vendors else None,
        "per_field": per_field,
        "cases": cases,
        "num_invoices": len(entries),
        "status": "ok",
    }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OCR evaluation")
    add_common_args(parser, default_threshold=0.85)
    parser.set_defaults(test_data="eval/test_data/ground_truth/")
    args = parser.parse_args()
    res = evaluate(args.test_data, mock=args.mock, out=args.out, ci=args.ci,
                   threshold=args.threshold, session_id=args.session,
                   user_id=args.user)
    sys.exit(finish("ocr_eval", res, args, "ocr_field_f1"))
