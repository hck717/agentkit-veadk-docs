from __future__ import annotations

import os
import json
import logging

from agents.config_loader import resolve_feishu_config

logger = logging.getLogger(__name__)


def _build_approval_card(approval: dict, task_id: str) -> dict:
    inv_num = approval.get("invoice_number", "N/A")
    vendor = approval.get("vendor", "N/A")
    amount = approval.get("amount", 0)
    notes = approval.get("reviewer_notes", "")

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "Invoice Approval Required"},
            "template": "orange",
        },
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**Invoice:** {inv_num}\n**Vendor:** {vendor}\n**Amount:** {amount}\n**Notes:** {notes}"}},
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "Approve"},
                        "type": "primary",
                        "value": {"action": "approve", "task_id": task_id},
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "Reject"},
                        "type": "danger",
                        "value": {"action": "reject", "task_id": task_id},
                    },
                ],
            },
        ],
    }


def _build_result_card(approval: dict) -> dict:
    status = approval.get("status", "unknown")
    icon = "Approved" if status == "approved" else "Rejected"
    template = "green" if status == "approved" else "red"

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"{icon}: Invoice {status.title()}"},
            "template": template,
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"**Invoice:** {approval.get('invoice_number', 'N/A')}\n"
                        f"**Vendor:** {approval.get('vendor', 'N/A')}\n"
                        f"**Amount:** {approval.get('amount', 0)}\n"
                        f"**Status:** {status}\n"
                        f"**Reviewed by:** {approval.get('approved_by', 'N/A')}\n"
                        f"**Notes:** {approval.get('reviewer_notes', 'N/A')}"
                    ),
                },
            },
        ],
    }


class FeishuNotifier:
    def __init__(self):
        self.config = resolve_feishu_config()
        self._channel = None

    def _init_channel(self):
        if self._channel is not None:
            return
        if self.config["app_id"] and self.config["app_secret"]:
            try:
                from veadk import Agent, Runner
                from veadk.extensions import FeishuChannelExtension
                agent = Agent(name="feishu_bot")
                runner = Runner(agent=agent, app_name="feishu_bot")
                self._channel = FeishuChannelExtension(runner=runner)
                logger.info("FeishuChannelExtension initialized from config.yaml")
            except Exception as e:
                logger.warning("FeishuChannelExtension init failed: %s", e)
                self._channel = None
        else:
            logger.info("Feishu credentials not configured — falling back to webhook/log")

    async def send_approval_request(self, approval: dict, task_id: str):
        self._init_channel()
        card = _build_approval_card(approval, task_id)

        if self._channel:
            try:
                await self._channel.send_message(
                    message_type="interactive",
                    content=json.dumps(card),
                )
                logger.info("Approval request sent via FeishuChannel for task %s", task_id)
                return
            except Exception as e:
                logger.warning("FeishuChannel send failed: %s", e)

        if self.config["webhook_url"]:
            await self._send_webhook(self.config["webhook_url"], card)
            logger.info("Approval request sent via webhook for task %s", task_id)
            return

        logger.info("[MOCK] Feishu approval request for task %s: %s",
                     task_id, approval.get("invoice_number"))

    async def send_result_notification(self, approval: dict):
        self._init_channel()
        card = _build_result_card(approval)

        if self._channel:
            try:
                await self._channel.send_message(
                    message_type="interactive",
                    content=json.dumps(card),
                )
                return
            except Exception as e:
                logger.warning("FeishuChannel send failed: %s", e)

        if self.config["webhook_url"]:
            await self._send_webhook(self.config["webhook_url"], card)
            return

        status = approval.get("status", "unknown")
        logger.info("[MOCK] Feishu result notification: %s -> %s",
                     approval.get("invoice_number"), status)

    async def _send_webhook(self, url: str, card: dict):
        try:
            import httpx
            payload = {"msg_type": "interactive", "card": card}
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
        except ImportError:
            logger.warning("httpx not installed — skipping webhook send")
        except Exception as e:
            logger.warning("Feishu webhook failed: %s", e)
