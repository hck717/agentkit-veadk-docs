"""Tests for the eval harness and eval scripts (mock mode only, no API)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.eval_core import (
    bleu, build_validated_like, cer, field_f1, field_match, line_items_match,
    load_ground_truth, numeric_close, numeric_preservation, string_similarity,
    sum_line_items,
)
from eval import (
    ocr_eval, translation_eval, validation_eval, aggregation_eval, approval_eval,
)

GT_DIR = str(Path(__file__).resolve().parent / "fixtures" / "eval_gt")


# --------------------------------------------------------------------------- #
# Metric functions
# --------------------------------------------------------------------------- #
def test_string_similarity():
    assert string_similarity("abc", "abc") == 1.0
    assert string_similarity("ABC  ", "abc") == 1.0  # case + whitespace tolerant
    assert string_similarity("abc", "xyz") < 0.5


def test_numeric_close():
    assert numeric_close(10.0, 10.0)
    assert numeric_close(10.0, 10.01)
    assert numeric_close("1,234.50", 1234.50)
    assert not numeric_close(10.0, 11.0)


def test_cer():
    assert cer("abc", "abc") == 0.0
    assert abs(cer("abc", "abd") - 1 / 3) < 1e-9
    assert cer("", "") == 0.0


def test_field_f1():
    assert abs(field_f1(4, 6) - 2 * (4 / 6) ** 2 / (2 * 4 / 6)) < 1e-9
    assert field_f1(0, 5) == 0.0


def test_field_match():
    assert field_match(1234.56, 1234.5, "amount")
    assert field_match("INV-1", "INV-1", "invoice_number")
    assert field_match("INV-1", "INV-2", "invoice_number") is False


def test_line_items_match():
    pred = [{"description": "快遞", "amount": 100.0},
            {"description": "倉儲", "amount": 50.0}]
    truth = [{"description": "快遞", "amount": 100.0},
             {"description": "倉儲", "amount": 60.0}]
    res = line_items_match(pred, truth)
    assert res["matched"] == 1
    assert res["predicted"] == 2 and res["truth"] == 2


def test_numeric_preservation():
    assert numeric_preservation("amount 100.50 tax 10", "amount 100.50 tax 10") == 1.0
    assert numeric_preservation("amount 100.50", "amount 200.00") == 0.0


def test_bleu():
    assert bleu("hello world", "hello world") == 1.0
    assert bleu("hello world", "goodbye moon") == 0.0


def test_build_validated_like_and_sum():
    fields = {"amount": 150.0, "line_items": [
        {"description": "a", "quantity": 1, "unit_price": 50.0, "amount": 50.0},
        {"description": "b", "quantity": 2, "unit_price": 50.0, "amount": 100.0},
    ]}
    like = build_validated_like(fields, image_key="x.jpg", lang="zh")
    assert like["amount"]["value"] == "150.0"
    assert like["line_items"][1]["amount"]["value"] == "100.0"
    assert sum_line_items(fields) == 150.0


# --------------------------------------------------------------------------- #
# Ground truth loading
# --------------------------------------------------------------------------- #
def test_load_ground_truth():
    entries = load_ground_truth(GT_DIR)
    assert len(entries) == 3
    assert all("fields" in e for e in entries)


# --------------------------------------------------------------------------- #
# Eval scripts (mock mode)
# --------------------------------------------------------------------------- #
def test_ocr_eval_mock():
    res = ocr_eval.evaluate(GT_DIR, mock=True)
    assert res["status"] == "ok"
    assert res["ocr_field_f1"] == 1.0  # fixtures match mock OCR
    assert res["num_invoices"] == 3
    assert "per_field" in res and "line_items" in res["per_field"]


def test_translation_eval_mock():
    res = translation_eval.evaluate(GT_DIR, mock=True)
    assert res["status"] == "ok"
    assert res["numeric_preservation_rate"] == 1.0
    assert res["translation_bleu"] is None  # no expected_translation in fixtures


def test_validation_eval_mock():
    res = validation_eval.evaluate(GT_DIR, mock=True)
    assert res["status"] == "ok"
    assert res["bugs_total"] == 9  # 3 invoices x 3 variants
    # mock catches amount + line-item tampering, not invalid date
    assert res["bugs_found"] == 6
    assert abs(res["bug_finding_rate"] - 6 / 9) < 1e-3
    assert res["false_positive_rate"] == 0.0  # clean fixtures are consistent
    assert res["corrections_checked"] == 3
    assert res["corrections_correct"] == 3


def test_aggregation_eval_mock():
    res = aggregation_eval.evaluate(GT_DIR, mock=True)
    assert res["status"] == "ok"
    assert res["total_error_rate"] == 0.0  # mock totals match expected
    assert res["duplicate_detection_accuracy"] == 1.0


def test_approval_eval_mock():
    res = approval_eval.evaluate(GT_DIR, mock=True)
    assert res["status"] == "ok"
    # mock auto-approves amounts within threshold, so the labeled anomaly is missed
    assert res["confusion"] == {"tp": 0, "fp": 0, "fn": 1, "tn": 2}
    assert res["anomaly_recall"] == 0.0
