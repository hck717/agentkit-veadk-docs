"""
Validation Agent evaluation — bug-finding rate, false-positive rate,
correction accuracy. Errors are injected programmatically into the ground
truth before running the Validation agent.
Usage: python eval/validation_eval.py --test-data eval/test_data/error_injected/
"""
from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.eval_core import (
    add_common_args, build_validated_like, finish, gt_fields, image_key_of,
    load_ground_truth, numeric_close, run_validation, sum_line_items,
)


def _flagged(validated: dict) -> bool:
    v = validated.get("validation", {})
    if v.get("issues") or v.get("corrections"):
        return True
    return bool(_implicit_corrections(validated))


def _implicit_corrections(validated: dict) -> list[dict]:
    """Detect corrections the agent applied inline (field value != original),
    which real-mode agents often return instead of a structured corrections[]."""
    out: list[dict] = []
    for key in ("invoice_number", "date", "vendor", "amount", "tax", "currency"):
        f = validated.get(key)
        if not isinstance(f, dict):
            continue
        val, orig = f.get("value"), f.get("original")
        if not str(orig or "").strip():
            continue
        if key in ("amount", "tax"):
            changed = numeric_close(val, orig) is False
        else:
            changed = str(val).strip().lower() != str(orig).strip().lower()
        if changed:
            out.append({"field": key, "corrected_value": val, "original_value": orig})
    for li in validated.get("line_items", []):
        if not isinstance(li, dict):
            continue
        for key in ("quantity", "unit_price", "amount"):
            f = li.get(key)
            if not isinstance(f, dict):
                continue
            val, orig = f.get("value"), f.get("original")
            if not str(orig or "").strip():
                continue
            if numeric_close(val, orig) is False:
                out.append({"field": f"line_item.{key}",
                            "corrected_value": val, "original_value": orig})
    return out


def _injected_variants(fields: dict) -> list[tuple[str, dict]]:
    """Return [(variant_name, modified_fields)] with injected errors."""
    variants: list[tuple[str, dict]] = []

    a = copy.deepcopy(fields)
    try:
        a["amount"] = float(fields.get("amount", 0)) + 500.0
    except (TypeError, ValueError):
        pass
    variants.append(("amount_tampered", a))

    if fields.get("line_items"):
        b = copy.deepcopy(fields)
        li = b["line_items"][0]
        try:
            li["amount"] = float(li.get("amount", 0)) + 100.0
        except (TypeError, ValueError):
            pass
        variants.append(("line_item_tampered", b))

    c = copy.deepcopy(fields)
    c["date"] = "2026-13-40"
    variants.append(("invalid_date", c))

    return variants


def evaluate(ground_truth_dir: str, mock: bool = False, out: str | None = None,
             ci: bool = False, threshold: float = 0.90,
             session_id: str | None = None, user_id: str = "eval_user",
             cache: dict | None = None) -> dict:
    entries = load_ground_truth(ground_truth_dir)
    if not entries:
        raise SystemExit(f"[Eval] no ground truth found in {ground_truth_dir}")

    clean_flagged = 0
    clean_total = 0
    bugs_found = 0
    bugs_total = 0
    corrections_correct = 0
    corrections_checked = 0
    cases: list[dict] = []

    for entry in entries:
        fields = gt_fields(entry)
        image_key = image_key_of(entry)
        stem = Path(image_key).stem or Path(entry["_source"]).stem
        lang = entry.get("lang", "unknown")
        base = build_validated_like(fields, image_key, lang)
        sid_base = session_id or f"eval-val-{stem}"

        clean = run_validation(base, mock, sid_base, user_id, cache)
        clean_flagged += int(_flagged(clean))
        clean_total += 1

        for vname, vfields in _injected_variants(fields):
            variant = build_validated_like(vfields, image_key, lang)
            sid = f"{sid_base}-{vname}"
            validated = run_validation(variant, mock, sid, user_id, cache,
                                       tag=vname)
            flagged = _flagged(validated)
            bugs_total += 1
            bugs_found += int(flagged)

            if vname == "amount_tampered" and flagged:
                expected = sum_line_items(vfields)
                correct = False
                for corr in validated.get("validation", {}).get("corrections", []):
                    if corr.get("field") == "amount" and numeric_close(
                            corr.get("corrected_value"), expected):
                        correct = True
                        break
                if not correct:
                    for corr in _implicit_corrections(validated):
                        if corr.get("field") == "amount" and numeric_close(
                                corr.get("corrected_value"), expected):
                            correct = True
                            break
                corrections_checked += 1
                corrections_correct += int(correct)

            cases.append({
                "image": image_key,
                "variant": vname,
                "flagged": bool(flagged),
                "issues": validated.get("validation", {}).get("issues", []),
                "corrections": validated.get("validation", {}).get("corrections", []),
                "implicit_corrections": _implicit_corrections(validated),
            })

    result = {
        "bug_finding_rate": round(bugs_found / bugs_total, 4) if bugs_total else None,
        "false_positive_rate": round(clean_flagged / clean_total, 4) if clean_total else None,
        "correction_accuracy": (
            round(corrections_correct / corrections_checked, 4)
            if corrections_checked else None),
        "clean_flagged": clean_flagged,
        "clean_total": clean_total,
        "bugs_found": bugs_found,
        "bugs_total": bugs_total,
        "corrections_correct": corrections_correct,
        "corrections_checked": corrections_checked,
        "cases": cases,
        "num_invoices": len(entries),
        "status": "ok",
    }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validation evaluation")
    add_common_args(parser, default_threshold=0.90)
    parser.set_defaults(test_data="eval/test_data/error_injected/")
    args = parser.parse_args()
    res = evaluate(args.test_data, mock=args.mock, out=args.out, ci=args.ci,
                   threshold=args.threshold, session_id=args.session,
                   user_id=args.user)
    sys.exit(finish("validation_eval", res, args, "bug_finding_rate"))
