"""Seedream invoice formatting agent (6th pipeline step).

Reformats an original invoice image into a clean, template-based invoice image
using Seedream 5.0 (`single_image_to_single`). The hot path is deterministic —
no LLM involved — so mock mode returns a placeholder pointing at the original
image, and real mode POSTs the base64 image + a template prompt to the
`images/generations` endpoint. The result is also exposed as an MCP tool via
`a2a_pipeline.mcp_server.FormattingMCPApp`.
"""

from __future__ import annotations

import os
import json
import base64
import asyncio
import logging
from pathlib import Path

import httpx

from agents.base_agent import BaseAgent
from agents.config_loader import resolve_api_key, resolve_image_gen_config
from agents.models import FormattedInvoice

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "seedream-5-0-260128"
DEFAULT_API_BASE = "https://ark.ap-southeast.bytepluses.com/api/v3/"


class FormattingAgent(BaseAgent):
    """Deterministic Seedream image formatting (no VeADK LLM agent needed)."""

    def __init__(self, mock: bool = True):
        super().__init__(name="formatting_agent", mock=mock)
        self.image_cfg = resolve_image_gen_config(self.name)

    def run(self, input_data: dict) -> dict:
        if self.mock:
            return self._run_mock(input_data).to_dict()
        return asyncio.run(self._run_real(input_data))

    async def run_async(self, input_data: dict) -> dict:
        if self.mock:
            return self._run_mock(input_data).to_dict()
        return await self._run_real(input_data)

    async def format_invoice_image(
        self, image_path: str, invoice_json: str | dict, template: str = "clean_business_invoice"
    ) -> dict:
        """MCP-facing entry point: reformat one invoice image to a template."""
        data: dict = {}
        if isinstance(invoice_json, str):
            try:
                data = json.loads(invoice_json)
            except (json.JSONDecodeError, TypeError):
                logger.warning("format_invoice_image: invoice_json not valid JSON: %s", invoice_json)
                data = {}
        else:
            data = dict(invoice_json or {})
        data["image_key"] = image_path
        data["template"] = template
        return await self.run_async(data)

    def _run_mock(self, input_data: dict) -> FormattedInvoice:
        invoice_key = input_data.get("image_key", "")
        template = input_data.get("template", self.image_cfg.get("template", "clean_business_invoice"))
        return FormattedInvoice(
            invoice_number=self._field_str(input_data.get("invoice_number")),
            status="mock_placeholder",
            template=template,
            prompt=self._build_template_prompt(input_data, template),
            formatted_image_path=invoice_key,
            invoice_key=invoice_key,
            vendor=self._field_str(input_data.get("vendor")),
            amount=self._field_float(input_data.get("amount")),
        )

    async def _run_real(self, input_data: dict) -> dict:
        invoice_key = input_data.get("image_key", "")
        template = input_data.get("template", self.image_cfg.get("template", "clean_business_invoice"))
        prompt = self._build_template_prompt(input_data, template)

        if not invoice_key or not os.path.exists(invoice_key):
            return FormattedInvoice(
                invoice_number=self._field_str(input_data.get("invoice_number")),
                status="failed",
                template=template,
                prompt=prompt,
                invoice_key=invoice_key,
                error=f"image_key not found: {invoice_key}",
            ).to_dict()

        model = os.environ.get("MODEL_IMAGE_NAME", self.image_cfg.get("model", DEFAULT_MODEL))
        api_base = os.environ.get(
            "MODEL_IMAGE_API_BASE", self.image_cfg.get("api_base", DEFAULT_API_BASE)
        ).rstrip("/")
        api_key = os.environ.get("MODEL_IMAGE_API_KEY") or os.environ.get("MODEL_AGENT_API_KEY") or resolve_api_key()

        try:
            body: dict = {
                "model": model,
                "prompt": prompt,
                "image": self._to_data_uri(invoice_key),
                "size": self.image_cfg.get("size", "2048x2048"),
            }
            if self.image_cfg.get("watermark") is not None:
                body["watermark"] = bool(self.image_cfg["watermark"])
            if self.image_cfg.get("output_format"):
                body["output_format"] = self.image_cfg["output_format"]

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }
            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(
                    f"{api_base}/images/generations", headers=headers, json=body
                )
                resp.raise_for_status()
                data = resp.json()

            url, b64 = self._extract_image(data)
            local_path = self._save_image(url, b64, invoice_key, input_data)

            return FormattedInvoice(
                invoice_number=self._field_str(input_data.get("invoice_number")),
                status="generated",
                template=template,
                prompt=prompt,
                formatted_image_url=url or "",
                formatted_image_path=local_path or "",
                invoice_key=invoice_key,
                vendor=self._field_str(input_data.get("vendor")),
                amount=self._field_float(input_data.get("amount")),
            ).to_dict()
        except Exception as e:
            logger.exception("Seedream formatting failed for %s", invoice_key)
            return FormattedInvoice(
                invoice_number=self._field_str(input_data.get("invoice_number")),
                status="failed",
                template=template,
                prompt=prompt,
                invoice_key=invoice_key,
                error=str(e),
            ).to_dict()

    def build_veadk_agent(self):
        """Conversational/A2A path (ak deploy / agentkit-run): LLM + image_generate tool."""
        from veadk import Agent
        from veadk.tools.builtin_tools.image_generate import image_generate

        return Agent(**self._build_agent_kwargs(
            instruction=(
                "You reformat invoice photos into clean, template-based invoice images. "
                "Use the image_generate tool with task_type='single_image_to_single', "
                "passing the original invoice image and a prompt that keeps all extracted "
                "fields and figures exactly as-is while applying a professional layout "
                "(header, line-item table, totals, footer, white background). "
                "Report the resulting image URL."
            ),
            tools=[image_generate],
        ))

    @staticmethod
    def _field_str(value) -> str:
        if isinstance(value, dict):
            return str(value.get("value", value.get("original", "")))
        return "" if value is None else str(value)

    @staticmethod
    def _field_float(value) -> float:
        if isinstance(value, dict):
            value = value.get("value", 0)
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _to_data_uri(path: str) -> str:
        mime = "image/jpeg"
        ext = Path(path).suffix.lower()
        if ext in (".png",):
            mime = "image/png"
        elif ext in (".webp",):
            mime = "image/webp"
        with open(path, "rb") as f:
            return f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"

    def _normalize_line_items(self, input_data: dict) -> str:
        items = input_data.get("line_items", [])
        if not items:
            return "N/A"
        lines = []
        for li in items:
            if not isinstance(li, dict):
                lines.append(f"- {li}")
                continue
            desc = self._field_str(li.get("description"))
            qty = self._field_str(li.get("quantity"))
            up = self._field_str(li.get("unit_price"))
            amt = self._field_str(li.get("amount"))
            lines.append(f"- {desc} | qty={qty} | unit_price={up} | amount={amt}")
        return "\n".join(lines)

    def _build_template_prompt(self, input_data: dict, template: str) -> str:
        return (
            "Reformat this invoice photo into a clean, professional "
            f"'{template}' invoice layout. Keep every value EXACTLY as listed below; "
            "do not invent, change, or add any figures or text.\n"
            f"Invoice number: {self._field_str(input_data.get('invoice_number'))}\n"
            f"Date: {self._field_str(input_data.get('date'))}\n"
            f"Vendor: {self._field_str(input_data.get('vendor'))}\n"
            f"Amount: {self._field_str(input_data.get('amount'))}\n"
            f"Tax: {self._field_str(input_data.get('tax'))}\n"
            f"Currency: {self._field_str(input_data.get('currency'))}\n"
            f"Line items:\n{self._normalize_line_items(input_data)}\n"
            "Layout: white background, clear black text, an 'INVOICE' header, "
            "a line-item table (Description | Quantity | Unit Price | Amount), "
            "subtotal, tax, total, and a footer. No watermarks, no decorative text."
        )

    @staticmethod
    def _extract_image(data: dict) -> tuple[str | None, str | None]:
        items = data.get("data") or []
        if not items:
            return None, None
        first = items[0] if isinstance(items[0], dict) else {}
        return first.get("url"), first.get("b64_json")

    def _save_image(self, url: str | None, b64: str | None, invoice_key: str, input_data: dict) -> str:
        output_dir = self.image_cfg.get("output_dir", "data/formatted")
        stem = Path(invoice_key).stem or self._field_str(input_data.get("invoice_number")) or "invoice"
        out_path = Path(output_dir) / f"{stem}.jpg"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if b64:
            out_path.write_bytes(base64.b64decode(b64))
        elif url:
            import httpx as _httpx
            with _httpx.Client(timeout=300) as client:
                resp = client.get(url)
                resp.raise_for_status()
                out_path.write_bytes(resp.content)
        else:
            return ""
        return str(out_path)
