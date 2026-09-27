import json
import os
import random
import asyncio
import logging
from agents.base_agent import BaseAgent
from agents.models import (
    TranslatedInvoice, ValidatedInvoice, ValidationReport,
    Correction, TranslatedField,
)

logger = logging.getLogger(__name__)


class ValidationAgent(BaseAgent):
    def __init__(self, mock: bool = True):
        super().__init__(name="validation_agent", mock=mock)

    def run(self, input_data: dict) -> dict:
        if self.mock:
            return self._run_mock(input_data).to_dict()
        return asyncio.run(self._run_veadk(input_data))

    def _run_mock(self, input_data: dict) -> ValidatedInvoice:
        issues: list[str] = []
        corrections: list[Correction] = []

        line_items = input_data.get("line_items", [])
        total = sum(float(li["amount"]["value"]) for li in line_items) if line_items else 0
        declared_amount = float(input_data.get("amount", {}).get("value", "0"))

        if abs(total - declared_amount) > 0.01:
            issues.append(
                f"Amount mismatch: line items sum to {total:.2f}, declared is {declared_amount:.2f}"
            )
            corrections.append(Correction(
                field="amount",
                original_value=f"{declared_amount:.2f}",
                corrected_value=f"{total:.2f}",
                reason=f"Line items sum to {total:.2f}, correcting declared amount",
            ))

        corrected_amount = total if corrections else declared_amount

        report = ValidationReport(
            confidence_score=round(random.uniform(0.85, 0.99), 2),
            corrections=corrections,
            issues=issues,
        )

        def tf(key: str) -> TranslatedField:
            d = input_data.get(key, {"value": "", "original": ""})
            if isinstance(d, TranslatedField):
                return d
            return TranslatedField.from_dict(d)

        validated = ValidatedInvoice(
            invoice_number=tf("invoice_number"),
            date=tf("date"),
            vendor=tf("vendor"),
            amount=TranslatedField(
                value=f"{corrected_amount:.2f}",
                original=input_data.get("amount", {}).get("original", ""),
            ),
            tax=tf("tax"),
            currency=tf("currency"),
            line_items=input_data.get("line_items", []),
            validation=report,
            detected_language=input_data.get("detected_language", "en"),
            original_language=input_data.get("original_language", ""),
            image_key=input_data.get("image_key", ""),
        )

        return validated

    def build_veadk_agent(self):
        from veadk import Agent

        return Agent(**self._build_agent_kwargs(
            instruction=(
                "Compare extracted invoice data against the original image. "
                "Check: amount matches line_items sum, date is valid, "
                "vendor name matches image, currency is reasonable. "
                "If discrepancy found, correct the field and log the reason. "
                "Return corrected invoice data plus a validation report with "
                "confidence_score, corrections[], and issues[]."
            ),
        ))

    async def _run_veadk(self, input_data: dict) -> dict:
        from veadk.types import MediaMessage

        agent = self.build_veadk_agent()
        runner = self._build_runner(agent)

        sid = input_data.get("session_id", f"{self.name}_session")
        uid = input_data.get("user_id", "system")

        image_path = input_data.get("image_key", "")
        if image_path and os.path.exists(image_path):
            message = MediaMessage(
                text=f"Validate this invoice data against the attached image:\n{json.dumps(input_data, indent=2)}",
                media=image_path,
            )
        else:
            message = f"Validate this invoice data:\n{json.dumps(input_data, indent=2)}"

        result = await runner.run(messages=message, user_id=uid, session_id=sid)

        parsed = self._extract_json(result)
        if not isinstance(parsed, dict):
            parsed = {}
        report = parsed.get("validation")
        if not isinstance(report, dict):
            report = {"confidence_score": 0.9, "corrections": [], "issues": []}

        merged = {**input_data, **parsed, "validation": report}
        merged.pop("session_id", None)
        merged.pop("user_id", None)

        return merged
