import json
import asyncio
import logging
from agents.base_agent import BaseAgent
from agents.models import TranslatedInvoice, TranslatedField

logger = logging.getLogger(__name__)

VENDOR_TRANSLATIONS = {
    "ABC Logistics 物流有限公司": "ABC Logistics Co., Ltd.",
    "TechVision 科技有限公司": "TechVision Technology Co., Ltd.",
    "GlobalTrade GmbH": "GlobalTrade GmbH",
}


class TranslationAgent(BaseAgent):
    def __init__(self, mock: bool = True):
        super().__init__(name="translation_agent", mock=mock)

    def run(self, input_data: dict) -> dict:
        if self.mock:
            return self._run_mock(input_data).to_dict()
        return asyncio.run(self._run_veadk(input_data))

    def _run_mock(self, input_data: dict) -> TranslatedInvoice:
        lang = input_data.get("detected_language", "zh")

        def tv(field_value: str) -> TranslatedField:
            return TranslatedField(value=field_value, original=field_value)

        vendor_value = VENDOR_TRANSLATIONS.get(
            input_data.get("vendor", ""), input_data.get("vendor", "")
        )
        return TranslatedInvoice(
            invoice_number=tv(str(input_data.get("invoice_number", ""))),
            date=tv(str(input_data.get("date", ""))),
            vendor=TranslatedField(value=vendor_value, original=input_data.get("vendor", "")),
            amount=tv(str(input_data.get("amount", "0"))),
            tax=tv(str(input_data.get("tax", "0"))),
            currency=tv(str(input_data.get("currency", ""))),
            line_items=[
                {
                    "description": TranslatedField(
                        value=li["description"] if lang == "en" else f"[EN] {li['description']}",
                        original=li["description"],
                    ).to_dict(),
                    "quantity": tv(str(li["quantity"])).to_dict(),
                    "unit_price": tv(str(li["unit_price"])).to_dict(),
                    "amount": tv(str(li["amount"])).to_dict(),
                }
                for li in input_data.get("line_items", [])
            ],
            detected_language="en",
            original_language=lang,
            image_key=input_data.get("image_key", ""),
        )

    def build_veadk_agent(self):
        from veadk import Agent

        return Agent(**self._build_agent_kwargs(
            instruction=(
                "Translate all text fields of this invoice to English. "
                "Keep numeric fields (amount, tax, invoice_number) exactly as-is. "
                "Return JSON where each field has 'value' (translated) and 'original' "
                "(original text). Fields: invoice_number, date, vendor, amount, tax, "
                "currency, line_items (each with description, quantity, unit_price, "
                "amount). Also include detected_language='en' and original_language."
            ),
        ))

    async def _run_veadk(self, input_data: dict) -> dict:
        agent = self.build_veadk_agent()
        runner = self._build_runner(agent)

        prompt = json.dumps(input_data, ensure_ascii=False)
        sid = input_data.get("session_id", f"{self.name}_session")
        uid = input_data.get("user_id", "system")

        result = await runner.run(messages=prompt, user_id=uid, session_id=sid)

        parsed = self._extract_json(result)
        if isinstance(parsed, dict):
            located = self._locate_fields(parsed)
            if located is not None:
                parsed = located
        parsed["image_key"] = input_data.get("image_key", "")
        return parsed

    @staticmethod
    def _locate_fields(parsed: dict) -> dict | None:
        """Model output sometimes wraps the invoice fields under nested keys
        (e.g. {"translation_agent": {"fields": {...}}}). Recursively find a
        container that has the expected top-level field keys and return it."""
        if isinstance(parsed, dict):
            if all(k in parsed for k in ("invoice_number", "amount", "vendor")):
                return parsed
            for value in parsed.values():
                if isinstance(value, dict):
                    located = TranslationAgent._locate_fields(value)
                    if located is not None:
                        return located
        return None
