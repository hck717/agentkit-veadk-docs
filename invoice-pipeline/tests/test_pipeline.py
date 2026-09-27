"""Smoke tests for the invoice pipeline (mock mode, no API calls)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from a2a_orchestrator import InvoicePipeline
from agents.ocr_agent import OcrAgent
from agents.translation_agent import TranslationAgent
from agents.validation_agent import ValidationAgent
from agents.aggregation_agent import AggregationAgent
from agents.formatting_agent import FormattingAgent
from agents.approval_agent import ApprovalAgent

EXPECTED_STEPS = [
    "1_ocr", "2_translation", "3_validation", "4_aggregation",
    "5_formatting", "6_approval",
]


def test_single_pipeline():
    result = InvoicePipeline(mock=True).run_single("default")
    assert result["pipeline"] == "single_invoice"
    assert set(EXPECTED_STEPS) <= set(result["steps"].keys())
    ocr = result["steps"]["1_ocr"]
    assert ocr["invoice_number"]
    assert float(ocr["amount"]) > 0
    formatting = result["steps"]["5_formatting"]
    assert formatting["status"] == "mock_placeholder"
    assert formatting["invoice_number"] == ocr["invoice_number"]
    assert result["steps"]["6_approval"]["status"] in ("approved", "pending_review")


def test_batch_pipeline():
    result = InvoicePipeline(mock=True).run_batch(["default", "invoice2", "invoice3"])
    assert result["pipeline"] == "batch"
    assert result["invoice_count"] == 3
    assert len(result["steps"]["1_ocr"]) == 3
    assert len(result["steps"]["5_formatting"]) == 3
    assert len(result["steps"]["6_approval"]) == 3


def test_agents_mock_outputs():
    ocr = OcrAgent(mock=True).run({"invoice_key": "invoice2"})
    assert ocr["invoice_number"] == "INV-2026-0728-002"

    translated = TranslationAgent(mock=True).run(ocr)
    assert translated["detected_language"] == "en"

    validated = ValidationAgent(mock=True).run(translated)
    assert validated["validation"]["confidence_score"] > 0

    aggregated = AggregationAgent(mock=True).run(
        {"invoices": [validated], "session_id": "s", "user_id": "u"}
    )
    assert aggregated["invoice_count"] == 1
    assert float(aggregated["total_amount"]) > 0

    formatted = FormattingAgent(mock=True).run(validated)
    assert formatted["status"] == "mock_placeholder"
    assert formatted["formatted_image_path"] == validated["image_key"]

    approved = ApprovalAgent(mock=True).run(validated)
    assert approved["status"] in ("approved", "pending_review", "rejected")
