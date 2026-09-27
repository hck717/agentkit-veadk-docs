"""
Translation Agent evaluation — numeric preservation (primary) & BLEU (optional).
Usage: python eval/translation_eval.py --test-data eval/test_data/ground_truth/
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.eval_core import (
    add_common_args, bleu, finish, gt_fields, image_key_of,
    load_ground_truth, numeric_preservation, run_chain,
)


def evaluate(ground_truth_dir: str, mock: bool = False, out: str | None = None,
             ci: bool = False, threshold: float = 1.0,
             session_id: str | None = None, user_id: str = "eval_user",
             cache: dict | None = None) -> dict:
    entries = load_ground_truth(ground_truth_dir)
    if not entries:
        raise SystemExit(f"[Eval] no ground truth found in {ground_truth_dir}")

    cases = []
    preserved: list[float] = []
    bleu_scores: list[float] = []

    for entry in entries:
        fields = gt_fields(entry)
        image_key = image_key_of(entry)
        stem = Path(image_key).stem or Path(entry["_source"]).stem
        sid = session_id or f"eval-trans-{stem}"
        _, translated, _ = run_chain(image_key, stem, mock, sid, user_id, cache)

        ref_text = json.dumps(fields, ensure_ascii=False)
        hyp_text = json.dumps(translated, ensure_ascii=False)
        np = numeric_preservation(ref_text, hyp_text)
        preserved.append(np)

        b = None
        ref_translation = entry.get("expected_translation")
        if ref_translation:
            b = round(bleu(ref_translation, hyp_text), 4)
            bleu_scores.append(b)

        missing = sorted(
            (set(_numbers_of(ref_text)) - set(_numbers_of(hyp_text))))

        cases.append({
            "image": image_key,
            "numeric_preservation": round(np, 4),
            "bleu": b,
            "missing_numbers": missing,
        })

    bleu_available = [b for b in bleu_scores if b is not None]

    result = {
        "numeric_preservation_rate": round(sum(preserved) / len(preserved), 4),
        "translation_bleu": (
            round(sum(bleu_available) / len(bleu_available), 4)
            if bleu_available else None),
        "has_expected_translation": bool(bleu_available),
        "cases": cases,
        "num_invoices": len(entries),
        "status": "ok",
    }
    return result


def _numbers_of(text: str) -> list[str]:
    import re
    return re.findall(r"\d+(?:[.,]\d+)?", text or "")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Translation evaluation")
    add_common_args(parser, default_threshold=1.0)
    parser.set_defaults(test_data="eval/test_data/ground_truth/")
    args = parser.parse_args()
    res = evaluate(args.test_data, mock=args.mock, out=args.out, ci=args.ci,
                   threshold=args.threshold, session_id=args.session,
                   user_id=args.user)
    sys.exit(finish("translation_eval", res, args, "numeric_preservation_rate"))
