import os
import asyncio
import logging
from agents.base_agent import BaseAgent
from agents.models import RawInvoice, LineItem

logger = logging.getLogger(__name__)

MOCK_INVOICES = {
    "default": RawInvoice(
        invoice_number="INV-2026-0728-001",
        date="2026-07-28",
        vendor="ABC Logistics 物流有限公司",
        amount=12345.67,
        tax=1234.57,
        currency="CNY",
        line_items=[
            LineItem(description="國際快遞費 (DDP)", quantity=1, unit_price=8500.00, amount=8500.00),
            LineItem(description="倉儲費 7月", quantity=1, unit_price=2345.67, amount=2345.67),
            LineItem(description="報關服務費", quantity=1, unit_price=1500.00, amount=1500.00),
        ],
        detected_language="zh",
    ),
    "invoice2": RawInvoice(
        invoice_number="INV-2026-0728-002",
        date="2026-07-28",
        vendor="TechVision 科技有限公司",
        amount=56789.00,
        tax=5678.90,
        currency="CNY",
        line_items=[
            LineItem(description="Server R420 租賃", quantity=3, unit_price=12000.00, amount=36000.00),
            LineItem(description="雲端儲存 1TB", quantity=1, unit_price=7890.00, amount=7890.00),
            LineItem(description="技術支援年費", quantity=1, unit_price=12899.00, amount=12899.00),
        ],
        detected_language="zh",
    ),
    "invoice3": RawInvoice(
        invoice_number="INV-2026-0729-003",
        date="2026-07-29",
        vendor="GlobalTrade GmbH",
        amount=8750.00,
        tax=0.00,
        currency="EUR",
        line_items=[
            LineItem(description="Consulting Hours Q3", quantity=25, unit_price=250.00, amount=6250.00),
            LineItem(description="Software License Renewal", quantity=1, unit_price=2500.00, amount=2500.00),
        ],
        detected_language="de",
    ),
}


class OcrAgent(BaseAgent):
    def __init__(self, mock: bool = True):
        super().__init__(name="ocr_agent", mock=mock)

    def run(self, input_data: dict) -> dict:
        if self.mock:
            return self._run_mock(input_data).to_dict()
        return asyncio.run(self._run_veadk(input_data))

    def _run_mock(self, input_data: dict) -> RawInvoice:
        invoice_key = input_data.get("invoice_key", "default")
        invoice = MOCK_INVOICES.get(invoice_key, MOCK_INVOICES["default"])
        return RawInvoice(
            invoice_number=invoice.invoice_number,
            date=invoice.date,
            vendor=invoice.vendor,
            amount=invoice.amount,
            tax=invoice.tax,
            currency=invoice.currency,
            line_items=[LineItem(**li.to_dict()) for li in invoice.line_items],
            detected_language=invoice.detected_language,
            image_key=input_data.get("image_key", f"invoices/{invoice_key}.jpg"),
        )

    def build_veadk_agent(self):
        from veadk import Agent

        return Agent(**self._build_agent_kwargs(
            instruction=(
                "You are an OCR specialist. Extract all invoice fields from the image. "
                "Return valid JSON with keys: invoice_number, date, vendor, amount, "
                "tax, currency, line_items (array of {description, quantity, "
                "unit_price, amount}), detected_language. Numbers must be numeric."
            ),
        ))

    async def _run_veadk(self, input_data: dict) -> dict:
        from veadk.types import MediaMessage

        agent = self.build_veadk_agent()
        runner = self._build_runner(agent)

        image_path = input_data.get("image_key", "")
        if image_path and os.path.exists(image_path):
            message = MediaMessage(
                text="Extract all invoice fields from the attached image. Return JSON.",
                media=image_path,
            )
        else:
            message = "Extract invoice fields from the provided data."

        sid = input_data.get("session_id", f"{self.name}_session")
        uid = input_data.get("user_id", "system")

        if self.ltm is not None:
            vendor_hint = input_data.get("vendor_hint",
                                          input_data.get("image_key", "").split("/")[-1].split(".")[0])
            try:
                patterns = await self.ltm.search_memory(
                    app_name=self.name,
                    user_id=uid,
                    query=vendor_hint,
                )
                if patterns and patterns.memories:
                    logger.info("LTM correction patterns found for OCR: %s", patterns.memories)
            except Exception as e:
                logger.debug("LTM search unavailable for OCR: %s", e)

        result = await runner.run(messages=message, user_id=uid, session_id=sid)

        parsed = self._extract_json(result)
        parsed["image_key"] = image_path
        return RawInvoice.from_dict(parsed).to_dict()
