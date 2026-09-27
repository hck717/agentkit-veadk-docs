import json
import os
import asyncio
import logging
from datetime import datetime, timezone
from agents.base_agent import BaseAgent
from agents.models import ApprovalResult

logger = logging.getLogger(__name__)


class ApprovalAgent(BaseAgent):
    def __init__(self, mock: bool = True, notify_callback: callable = None):
        super().__init__(name="approval_agent", mock=mock)
        self.notify_callback = notify_callback

    def run(self, input_data: dict) -> dict:
        if self.mock:
            result = self._run_mock(input_data).to_dict()
        else:
            result = asyncio.run(self._run_veadk(input_data))

        if result.get("status") == "pending_review" and self.notify_callback:
            self.notify_callback(result)

        return result

    def _run_mock(self, input_data: dict) -> ApprovalResult:
        approval_cfg = self.config.get("approval", {})
        auto_approve_threshold = float(approval_cfg.get("auto_approve_threshold", 10000))
        flag_review_list = approval_cfg.get("flag_for_review", [{}])
        flag_max_amount = float(flag_review_list[0].get("max_amount", 50000)) if flag_review_list else 50000
        flag_low_confidence = float(flag_review_list[1].get("low_confidence", 0.8)) if len(flag_review_list) > 1 else 0.8

        def g(d: dict | str | float, key: str = "") -> str | float:
            if isinstance(d, dict):
                return d.get("value", d.get(key, ""))
            return d

        inv_num = str(g(input_data.get("invoice_number", "")))
        vendor = str(g(input_data.get("vendor", "")))
        amount = float(g(input_data.get("amount", ""), "value"))
        confidence = float(input_data.get("validation", {}).get("confidence_score", 0.95))
        issues = list(input_data.get("validation", {}).get("issues", []))

        if confidence < flag_low_confidence or len(issues) > 0 or amount >= flag_max_amount:
            status = "pending_review"
            notes = f"Flagged for human review: confidence={confidence}, issues={len(issues)}, amount={amount}"
            approved_by = ""
        elif amount > auto_approve_threshold:
            status = "approved"
            notes = f"Auto-approved (amount={amount}, within threshold)"
            approved_by = "system (auto)"
        else:
            status = "approved"
            notes = "Auto-approved (low amount)"
            approved_by = "system (auto)"

        return ApprovalResult(
            status=status,
            reviewer_notes=notes,
            approved_by=approved_by,
            timestamp=datetime.now(timezone.utc).isoformat(),
            invoice_number=inv_num,
            amount=amount,
            vendor=vendor,
        )

    def build_veadk_agent(self):
        from veadk import Agent

        return Agent(**self._build_agent_kwargs(
            instruction=(
                "Review this invoice and its validation report. "
                "Decide: 'approved' (all good), 'pending_review' (needs human), "
                "or 'rejected' (fraudulent). "
                "Return JSON with: status, reviewer_notes, approved_by, "
                "timestamp, invoice_number, amount, vendor."
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
        parsed.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        return parsed
