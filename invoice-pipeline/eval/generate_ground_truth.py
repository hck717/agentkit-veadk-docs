"""
Generate draft ground-truth candidates by running the OCR agent on invoice
images. Output is written to eval/test_data/ground_truth/ and tagged
"status": "draft_candidate" so a human can verify/correct the fields against
the physical invoice before the numbers are trusted.

Usage:
  python eval/generate_ground_truth.py --images invoice_upload/IMG_0403.jpg \
      invoice_upload/IMG_0404.jpg invoice_upload/IMG_0405.jpg
  python eval/generate_ground_truth.py --images-dir invoice_upload --suffix .jpg
  python eval/generate_ground_truth.py --images ... --mock --force
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

GT_DIR = Path("eval/test_data/ground_truth")
FIELD_KEYS = ("invoice_number", "date", "vendor", "amount", "tax", "currency")


def _collect_images(args) -> list[Path]:
    images: list[Path] = []
    if args.images:
        images += [Path(p) for p in args.images]
    if args.images_dir:
        suffix = args.suffix or ".jpg"
        images += sorted(Path(args.images_dir).glob(f"*{suffix}"))
    # de-duplicate while preserving order
    seen = set()
    unique = []
    for p in images:
        rp = str(p.resolve())
        if rp not in seen:
            seen.add(rp)
            unique.append(p)
    return unique


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate draft ground truth")
    parser.add_argument("--images", nargs="*", default=None)
    parser.add_argument("--images-dir", default=None)
    parser.add_argument("--suffix", default=".jpg")
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--out-dir", default=str(GT_DIR))
    args = parser.parse_args()

    from eval.eval_core import run_ocr

    images = _collect_images(args)
    if not images:
        print("[Eval] no images given. Use --images or --images-dir.")
        return 1

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []

    for img in images:
        # store a stable key relative to the project root when possible
        try:
            rel = img.resolve().relative_to(Path.cwd().resolve())
            image_key = str(rel)
        except ValueError:
            image_key = str(img)

        stem = img.stem
        out_path = out_dir / f"{stem}.json"
        if out_path.exists() and not args.force:
            print(f"[Eval] skip (exists, use --force): {out_path}")
            continue

        print(f"[Eval] OCR (mock={args.mock}) -> {img}")
        raw = run_ocr(image_key, stem, mock=args.mock,
                      session_id=f"gt-gen-{stem}", user_id="eval_user")

        fields = {k: raw.get(k) for k in FIELD_KEYS}
        fields["line_items"] = raw.get("line_items", [])

        gt = {
            "image_key": image_key,
            "status": "draft_candidate",
            "lang": raw.get("detected_language", "unknown"),
            "notes": "AUTO-GENERATED candidate from OCR. Verify/correct the "
                     "fields against the physical invoice, then set "
                     "status to 'verified'.",
            "fields": fields,
        }
        out_path.write_text(
            json.dumps(gt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(str(out_path))
        print(f"[Eval] wrote {out_path}")

    print(f"[Eval] {len(written)} ground-truth candidates written to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
