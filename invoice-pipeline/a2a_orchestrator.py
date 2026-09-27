from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone

from agents.ocr_agent import OcrAgent
from agents.translation_agent import TranslationAgent
from agents.validation_agent import ValidationAgent
from agents.aggregation_agent import AggregationAgent
from agents.formatting_agent import FormattingAgent
from agents.approval_agent import ApprovalAgent
from agents.models import (
    RawInvoice, TranslatedInvoice, ValidatedInvoice,
    AggregatedReport, FormattedInvoice, ApprovalResult,
)

logger = logging.getLogger(__name__)


class InvoicePipeline:
    def __init__(self, mock: bool = True, approval_callback: callable = None):
        self.ocr = OcrAgent(mock=mock)
        self.translator = TranslationAgent(mock=mock)
        self.validator = ValidationAgent(mock=mock)
        self.aggregator = AggregationAgent(mock=mock)
        self.formatter = FormattingAgent(mock=mock)
        self.approver = ApprovalAgent(mock=mock, notify_callback=approval_callback)

    @staticmethod
    def _gen_batch_id() -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        suffix = uuid.uuid4().hex[:6]
        return f"batch-{ts}-{suffix}"

    def run_single(self, invoice_key: str = "default",
                   image_key: str | None = None,
                   session_id: str | None = None,
                   user_id: str = "system") -> dict:
        batch_id = session_id or self._gen_batch_id()

        raw_dict = self.ocr.run({
            "invoice_key": invoice_key,
            "image_key": image_key or f"invoices/{invoice_key}.jpg",
            "session_id": batch_id,
            "user_id": user_id,
        })
        raw = RawInvoice.from_dict(raw_dict)

        translated_dict = self.translator.run({
            **raw.to_dict(),
            "session_id": batch_id,
            "user_id": user_id,
        })
        translated = TranslatedInvoice.from_dict(translated_dict)

        validated_dict = self.validator.run({
            **translated.to_dict(),
            "session_id": batch_id,
            "user_id": user_id,
        })
        validated = ValidatedInvoice.from_dict(validated_dict)

        aggregated_dict = self.aggregator.run({
            "invoices": [validated.to_dict()],
            "session_id": batch_id,
            "user_id": user_id,
        })
        aggregated = AggregatedReport.from_dict(aggregated_dict)

        formatted_dict = self.formatter.run({
            **validated.to_dict(),
            "session_id": batch_id,
            "user_id": user_id,
        })
        formatted = FormattedInvoice.from_dict(formatted_dict)

        approved_dict = self.approver.run({
            **validated.to_dict(),
            "session_id": batch_id,
            "user_id": user_id,
        })
        approved = ApprovalResult.from_dict(approved_dict)

        return {
            "pipeline": "single_invoice",
            "batch_id": batch_id,
            "invoice_key": invoice_key,
            "steps": {
                "1_ocr": raw.to_dict(),
                "2_translation": translated.to_dict(),
                "3_validation": validated.to_dict(),
                "4_aggregation": aggregated.to_dict(),
                "5_formatting": formatted.to_dict(),
                "6_approval": approved.to_dict(),
            },
        }

    def run_batch(self, invoice_keys: list[str] | None = None,
                  session_id: str | None = None,
                  user_id: str = "system") -> dict:
        if invoice_keys is None:
            invoice_keys = ["default", "invoice2", "invoice3"]
        batch_id = session_id or self._gen_batch_id()

        raw_steps: list[dict] = []
        translation_steps: list[dict] = []
        validated_invoices: list[dict] = []

        for key in invoice_keys:
            raw_dict = self.ocr.run({
                "invoice_key": key,
                "image_key": f"invoices/{key}.jpg",
                "session_id": batch_id,
                "user_id": user_id,
            })
            raw = RawInvoice.from_dict(raw_dict)
            raw_steps.append(raw.to_dict())

            translated_dict = self.translator.run({
                **raw.to_dict(),
                "session_id": batch_id,
                "user_id": user_id,
            })
            translated = TranslatedInvoice.from_dict(translated_dict)
            translation_steps.append(translated.to_dict())

            validated_dict = self.validator.run({
                **translated.to_dict(),
                "session_id": batch_id,
                "user_id": user_id,
            })
            validated = ValidatedInvoice.from_dict(validated_dict)
            validated_invoices.append(validated.to_dict())

        aggregated_dict = self.aggregator.run({
            "invoices": validated_invoices,
            "session_id": batch_id,
            "user_id": user_id,
        })
        aggregated = AggregatedReport.from_dict(aggregated_dict)

        formatted_steps: list[dict] = []
        for inv in validated_invoices:
            formatted_dict = self.formatter.run({
                **inv,
                "session_id": batch_id,
                "user_id": user_id,
            })
            formatted_steps.append(FormattedInvoice.from_dict(formatted_dict).to_dict())

        approvals: list[dict] = []
        for inv in validated_invoices:
            app_dict = self.approver.run({
                **inv,
                "session_id": batch_id,
                "user_id": user_id,
            })
            approvals.append(ApprovalResult.from_dict(app_dict).to_dict())

        aggregated_dict["approvals"] = approvals

        return {
            "pipeline": "batch",
            "batch_id": batch_id,
            "invoice_count": len(invoice_keys),
            "steps": {
                "1_ocr": raw_steps,
                "2_translation": translation_steps,
                "3_validation": validated_invoices,
                "4_aggregation": aggregated.to_dict(),
                "5_formatting": formatted_steps,
                "6_approval": approvals,
            },
        }

    async def run_single_async(self, invoice_key: str = "default",
                               image_key: str | None = None,
                               session_id: str | None = None,
                               user_id: str = "system") -> dict:
        batch_id = session_id or self._gen_batch_id()

        raw_dict = await self.ocr.run_async({
            "invoice_key": invoice_key,
            "image_key": image_key or f"invoices/{invoice_key}.jpg",
            "session_id": batch_id,
            "user_id": user_id,
        })

        translated_dict = await self.translator.run_async({
            **raw_dict,
            "session_id": batch_id,
            "user_id": user_id,
        })

        validated_dict = await self.validator.run_async({
            **translated_dict,
            "session_id": batch_id,
            "user_id": user_id,
        })

        aggregated_dict = await self.aggregator.run_async({
            "invoices": [validated_dict],
            "session_id": batch_id,
            "user_id": user_id,
        })

        formatted_dict = await self.formatter.run_async({
            **validated_dict,
            "session_id": batch_id,
            "user_id": user_id,
        })

        approved_dict = await self.approver.run_async({
            **validated_dict,
            "session_id": batch_id,
            "user_id": user_id,
        })

        return {
            "pipeline": "single_invoice",
            "batch_id": batch_id,
            "invoice_key": invoice_key,
            "steps": {
                "1_ocr": raw_dict,
                "2_translation": translated_dict,
                "3_validation": validated_dict,
                "4_aggregation": aggregated_dict,
                "5_formatting": formatted_dict,
                "6_approval": approved_dict,
            },
        }
