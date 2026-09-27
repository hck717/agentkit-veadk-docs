"""
Shared evaluation harness for the invoice pipeline.

Provides ground-truth loading, string/numeric metrics (similarity, CER, edit
distance, field F1, numeric preservation, BLEU) and thin helpers to run the
OCR / Translation / Validation agents (mock or real) with optional in-memory
caching so ``run_all.py`` can reuse one chain run across all eval scripts.

Metrics follow projects/invoice-pipeline.md (Evaluation 策略):

  OCR        -> Field F1 (primary), CER, per-field precision/recall
  Translation-> numeric preservation (must be 100%), BLEU (optional)
  Validation -> bug-finding rate (primary), false-positive rate, correction accuracy
  Aggregation-> total error rate, duplicate detection accuracy
  Approval   -> anomaly precision / recall
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

SCALAR_FIELDS = ["invoice_number", "date", "vendor", "amount", "tax", "currency"]
SIMILARITY_THRESHOLD = 0.8
NUMERIC_RE = re.compile(r"\d+(?:[.,]\d+)?")
TOKEN_RE = re.compile(r"[\u4e00-\u9fff]|[A-Za-z0-9]+")


# --------------------------------------------------------------------------- #
# Ground truth
# --------------------------------------------------------------------------- #
def load_ground_truth(test_data_dir: str) -> list[dict]:
    """Load ground-truth JSON files from a directory.

    Schema (see projects/invoice-pipeline.md)::

        {
          "image_key": "invoice_upload/IMG_0403.jpg",
          "fields": {"invoice_number": "...", "date": "...", "vendor": "...",
                     "amount": 1234.56, "tax": 123.45, "currency": "CNY",
                     "line_items": [{"description": "...", "quantity": 1,
                                     "unit_price": 100, "amount": 100}]},
          "lang": "zh",
          "notes": "...",
          "anomaly": false,                 # optional, for approval eval
          "expected_translation": "..."     # optional, for BLEU
        }

    Files with either an explicit ``fields`` key or flat field dicts are
    accepted.
    """
    entries: list[dict] = []
    gt_dir = Path(test_data_dir)
    if not gt_dir.is_dir():
        raise FileNotFoundError(f"ground truth dir not found: {gt_dir}")
    for f in sorted(gt_dir.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"[Eval] skip unparseable {f.name}: {e}")
            continue
        if not isinstance(d, dict):
            continue
        d.setdefault("image_key", f.stem)
        d["_source"] = f.name
        entries.append(d)
    return entries


def gt_fields(entry: dict) -> dict:
    return entry.get("fields", entry)


def image_key_of(entry: dict) -> str:
    return str(entry.get("image_key") or entry.get("_source", ""))


# --------------------------------------------------------------------------- #
# Matching primitives
# --------------------------------------------------------------------------- #
def _norm(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def _num(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def string_similarity(a: Any, b: Any) -> float:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def numeric_close(a: Any, b: Any, tol_abs: float = 0.01, tol_rel: float = 0.01) -> bool:
    na, nb = _num(a), _num(b)
    if na is None or nb is None:
        return False
    return abs(na - nb) <= max(tol_abs, tol_rel * abs(nb))


def field_match(pred: Any, truth: Any, field: str) -> bool:
    if field in ("amount", "tax", "unit_price", "quantity"):
        return numeric_close(pred, truth)
    if not str(truth or "").strip():
        return True  # no ground truth for this field -> do not penalize
    t = _norm(truth)
    # short strings (invoice numbers, currency codes) are error-prone at 0.8
    min_sim = 0.95 if len(t) < 6 else SIMILARITY_THRESHOLD
    return string_similarity(pred, truth) >= min_sim


def edit_distance(a: str, b: str) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def cer(ref: Any, hyp: Any) -> float:
    r, h = _norm(ref), _norm(hyp)
    if not r:
        return 0.0 if not h else 1.0
    return edit_distance(r, h) / len(r)


def field_f1(matched: int, total: int) -> float:
    if total == 0:
        return 0.0
    precision = recall = matched / total
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def line_items_match(pred_items: list, truth_items: list) -> dict:
    """Greedily match predicted line items against ground truth.

    A pair matches when the amounts are numerically close and (if a ground
    truth description exists) the descriptions are >= 0.6 similar.
    """
    used: set[int] = set()
    matched = 0
    for p in pred_items:
        pa = (p.get("amount") if isinstance(p, dict) else None)
        pd = (p.get("description") if isinstance(p, dict) else None)
        if isinstance(pa, dict):
            pa = pa.get("value")
        if isinstance(pd, dict):
            pd = pd.get("value")
        for idx, t in enumerate(truth_items):
            if idx in used:
                continue
            ta = (t.get("amount") if isinstance(t, dict) else None)
            td = (t.get("description") if isinstance(t, dict) else None)
            if isinstance(ta, dict):
                ta = ta.get("value")
            if isinstance(td, dict):
                td = td.get("value")
            desc_ok = (not str(td or "").strip()
                       or string_similarity(pd, td) >= 0.6)
            if numeric_close(pa, ta) and desc_ok:
                used.add(idx)
                matched += 1
                break
    precision = matched / len(pred_items) if pred_items else 0.0
    recall = matched / len(truth_items) if truth_items else (1.0 if not pred_items else 0.0)
    return {
        "line_items_precision": round(precision, 4),
        "line_items_recall": round(recall, 4),
        "matched": matched,
        "predicted": len(pred_items),
        "truth": len(truth_items),
    }


# --------------------------------------------------------------------------- #
# Numeric preservation & BLEU
# --------------------------------------------------------------------------- #
def _numbers(text: Any) -> set[float]:
    out: set[float] = set()
    for n in NUMERIC_RE.findall(str(text or "")):
        try:
            out.add(round(float(n.replace(",", "")), 2))
        except ValueError:
            continue
    return out


def numeric_preservation(reference: Any, hypothesis: Any) -> float:
    src = _numbers(reference)
    if not src:
        return 1.0
    tgt = _numbers(hypothesis)
    return len(src & tgt) / len(src)


def _tokenize(text: Any) -> list[str]:
    return [t for t in TOKEN_RE.findall(str(text or "").lower()) if t]


def _ngrams(tokens: list[str], n: int) -> list[tuple]:
    if len(tokens) < n:
        return []
    return list(zip(*[tokens[i:] for i in range(n)]))


def bleu(reference: Any, hypothesis: Any, max_n: int = 2) -> float:
    ref_tok = _tokenize(reference)
    hyp_tok = _tokenize(hypothesis)
    if not hyp_tok:
        return 0.0
    matches = 0
    total = 0
    for n in range(1, max_n + 1):
        ref_ng = Counter(_ngrams(ref_tok, n))
        hyp_ng = _ngrams(hyp_tok, n)
        if not hyp_ng:
            continue
        m = 0
        for ng in hyp_ng:
            if ref_ng.get(ng, 0) > 0:
                ref_ng[ng] -= 1
                m += 1
        matches += m
        total += len(hyp_ng)
    precision = matches / total if total else 0.0
    brevity = 1.0
    if len(hyp_tok) < len(ref_tok):
        brevity = math.exp(1.0 - len(ref_tok) / max(1, len(hyp_tok)))
    return brevity * precision


# --------------------------------------------------------------------------- #
# Agent runners (mock or real) with optional shared cache
# --------------------------------------------------------------------------- #
def run_ocr(image_key: str, invoice_key: str, mock: bool, session_id: str,
            user_id: str, cache: dict | None = None, tag: str = "") -> dict:
    key = ("ocr", image_key, mock, tag)
    if cache is not None and key in cache:
        return cache[key]
    from agents.ocr_agent import OcrAgent
    raw = OcrAgent(mock=mock).run({
        "invoice_key": invoice_key,
        "image_key": image_key,
        "session_id": session_id,
        "user_id": user_id,
    })
    if cache is not None:
        cache[key] = raw
    return raw


def run_translation(raw: dict, mock: bool, session_id: str, user_id: str,
                    cache: dict | None = None, tag: str = "") -> dict:
    image_key = raw.get("image_key", "")
    key = ("translation", image_key, mock, tag)
    if cache is not None and key in cache:
        return cache[key]
    from agents.translation_agent import TranslationAgent
    translated = TranslationAgent(mock=mock).run({
        **raw, "session_id": session_id, "user_id": user_id,
    })
    if cache is not None:
        cache[key] = translated
    return translated


def run_validation(translated: dict, mock: bool, session_id: str, user_id: str,
                   cache: dict | None = None, tag: str = "") -> dict:
    image_key = translated.get("image_key", "")
    key = ("validation", image_key, mock, tag)
    if cache is not None and key in cache:
        return cache[key]
    from agents.validation_agent import ValidationAgent
    validated = ValidationAgent(mock=mock).run({
        **translated, "session_id": session_id, "user_id": user_id,
    })
    if cache is not None:
        cache[key] = validated
    return validated


def run_chain(image_key: str, invoice_key: str, mock: bool, session_id: str,
              user_id: str, cache: dict | None = None):
    raw = run_ocr(image_key, invoice_key, mock, session_id, user_id, cache)
    translated = run_translation(raw, mock, session_id, user_id, cache)
    validated = run_validation(translated, mock, session_id, user_id, cache)
    return raw, translated, validated


# --------------------------------------------------------------------------- #
# Building validation-shaped input from ground-truth fields
# --------------------------------------------------------------------------- #
def tf(value: Any) -> dict:
    return {"value": str(value), "original": str(value)}


def build_validated_like(fields: dict, image_key: str = "",
                         lang: str = "unknown") -> dict:
    """Convert ground-truth fields into the TranslatedInvoice-shaped dict the
    Validation / Approval agents consume (fields wrapped as {value, original})."""
    line_items = []
    for li in fields.get("line_items", []):
        line_items.append({
            "description": tf(li.get("description", "")),
            "quantity": tf(li.get("quantity", 0)),
            "unit_price": tf(li.get("unit_price", 0)),
            "amount": tf(li.get("amount", 0)),
        })
    return {
        "invoice_number": tf(fields.get("invoice_number", "")),
        "date": tf(fields.get("date", "")),
        "vendor": tf(fields.get("vendor", "")),
        "amount": tf(fields.get("amount", 0)),
        "tax": tf(fields.get("tax", 0)),
        "currency": tf(fields.get("currency", "")),
        "line_items": line_items,
        "detected_language": "en",
        "original_language": lang,
        "image_key": image_key,
    }


def sum_line_items(fields: dict) -> float:
    total = 0.0
    for li in fields.get("line_items", []):
        v = li.get("amount", 0)
        if isinstance(v, dict):
            v = v.get("value", 0)
        try:
            total += float(v)
        except (TypeError, ValueError):
            continue
    return round(total, 2)


# --------------------------------------------------------------------------- #
# CLI helpers
# --------------------------------------------------------------------------- #
def add_common_args(parser: argparse.ArgumentParser, default_threshold: float) -> None:
    parser.add_argument("--test-data", default=None,
                        help="directory with ground-truth JSON files")
    parser.add_argument("--mock", action="store_true",
                        help="run agents in mock mode (no API calls)")
    parser.add_argument("--ci", action="store_true",
                        help="exit non-zero if the primary metric < threshold")
    parser.add_argument("--threshold", type=float, default=default_threshold)
    parser.add_argument("--out", default=None,
                        help="directory to write <name>.json report")
    parser.add_argument("--session", default=None, help="session id prefix")
    parser.add_argument("--user", default="eval_user")


def finish(name: str, result: dict, args: argparse.Namespace, primary_key: str) -> int:
    primary = result.get(primary_key)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if args.out:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{name}.json"
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False),
                        encoding="utf-8")
        print(f"[Eval] {name} report written: {path}")
    if args.ci:
        if primary is None:
            print(f"[Eval] {name}: primary metric {primary_key} unavailable -> FAIL")
            return 1
        passed = float(primary) >= args.threshold
        print(f"[Eval] {name}: {primary_key}={primary} "
              f"threshold={args.threshold} -> {'PASS' if passed else 'FAIL'}")
        return 0 if passed else 1
    return 0
