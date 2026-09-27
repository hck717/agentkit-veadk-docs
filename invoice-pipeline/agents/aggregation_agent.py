import json
import asyncio
import logging
from collections import defaultdict
from agents.base_agent import BaseAgent
from agents.models import AggregatedReport

logger = logging.getLogger(__name__)


class AggregationAgent(BaseAgent):
    def __init__(self, mock: bool = True):
        super().__init__(name="aggregation_agent", mock=mock)

    def run(self, input_data: dict) -> dict:
        if self.mock:
            return self._run_mock(input_data).to_dict()
        return asyncio.run(self._run_veadk(input_data))

    def _run_mock(self, input_data: dict) -> AggregatedReport:
        invoices = input_data.get("invoices", [])
        total_amount = 0.0
        currency_totals: dict[str, float] = defaultdict(float)
        all_items: dict[str, float] = defaultdict(float)
        seen_numbers: set[str] = set()
        duplicates: list[dict] = []

        for inv in invoices:
            def g(d: dict | str | float, key: str = "") -> str | float:
                if isinstance(d, dict):
                    return d.get("value", d.get(key, ""))
                return d

            inv_num = str(g(inv.get("invoice_number", "")))
            currency = str(g(inv.get("currency", "")))
            amt = float(g(inv.get("amount", ""), "value"))

            currency_totals[currency] += amt
            total_amount += amt

            if inv_num in seen_numbers:
                duplicates.append({
                    "invoice_number": inv_num,
                    "reason": "Duplicate invoice number detected",
                })
            seen_numbers.add(inv_num)

            for li in inv.get("line_items", []):
                desc = li.get("description", "")
                if isinstance(desc, dict):
                    desc = desc.get("value", "")
                amt_li = li.get("amount", 0)
                if isinstance(amt_li, dict):
                    amt_li = float(amt_li.get("value", 0))
                else:
                    amt_li = float(amt_li)
                all_items[desc] += amt_li

        return AggregatedReport(
            total_amount=round(total_amount, 2),
            currencies=dict(currency_totals),
            itemized_summary=dict(all_items),
            discrepancies=[{"note": f"Multiple currencies found: {dict(currency_totals)}"}] if len(currency_totals) > 1 else [],
            duplicate_flags=duplicates,
            invoice_count=len(invoices),
            validated_invoices=invoices,
        )

    def build_veadk_agent(self):
        from veadk import Agent

        return Agent(**self._build_agent_kwargs(
            instruction=(
                "Standardize and aggregate these validated invoices. "
                "Calculate total_amount, detect duplicates (same invoice_number), "
                "flag currency discrepancies. "
                "Return JSON with: total_amount (number), "
                "currencies (object mapping currency code to total amount), "
                "itemized_summary (object mapping each line item description to "
                "its aggregated total amount), discrepancies (array of strings), "
                "duplicate_flags (array of objects), invoice_count (integer)."
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
        parsed["validated_invoices"] = input_data.get("invoices", [])
        return parsed
