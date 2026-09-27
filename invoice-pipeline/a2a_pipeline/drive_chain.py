"""Drive-chain A2A orchestrator.

Calls each of the 5 invoice agents over the A2A protocol using `A2AClient`,
in strict sequence: OCR -> translation -> validation -> aggregation -> approval.
Agent outputs flow between steps as JSON text in the message parts.
"""

from __future__ import annotations

import json
import uuid
import asyncio
import logging
from datetime import datetime, timezone

import httpx
from a2a.client import A2AClient
from a2a.types import (
    Message,
    MessageSendConfiguration,
    MessageSendParams,
    Part,
    Role,
    SendMessageRequest,
    TaskState,
    TextPart,
)

logger = logging.getLogger(__name__)


class A2aDriveChain:

    AGENT_ORDER = ["ocr", "translation", "validation", "aggregation", "formatting", "approval"]

    def __init__(self, base_url: str = "http://127.0.0.1:9901", timeout: float = 180.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @staticmethod
    def _gen_batch_id() -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        suffix = uuid.uuid4().hex[:6]
        return f"batch-{ts}-{suffix}"

    @staticmethod
    def _agent_url(base_url: str, agent: str) -> str:
        return f"{base_url}/{agent}/"

    async def _call(self, agent: str, payload: dict) -> dict:
        request = SendMessageRequest(
            id=str(uuid.uuid4()),
            params=MessageSendParams(
                message=Message(
                    message_id=str(uuid.uuid4()),
                    role=Role.user,
                    parts=[Part(TextPart(text=json.dumps(payload, ensure_ascii=False)))],
                ),
                configuration=MessageSendConfiguration(blocking=True),
            ),
        )
        async with httpx.AsyncClient(timeout=self.timeout) as http:
            client = A2AClient(httpx_client=http, url=self._agent_url(self.base_url, agent))
            response = await client.send_message(request)

        task = response.root.result
        if task.status.state != TaskState.completed or not task.status.message:
            raise RuntimeError(
                f"A2A call to {agent} failed: state={task.status.state}, "
                f"message={task.status.message}"
            )
        text = task.status.message.parts[0].root.text
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError) as e:
            raise RuntimeError(f"A2A call to {agent} returned non-JSON: {e}") from e

    async def run_single_async(
        self,
        invoice_key: str = "default",
        image_key: str | None = None,
        session_id: str | None = None,
        user_id: str = "system",
    ) -> dict:
        batch_id = session_id or self._gen_batch_id()

        raw = await self._call("ocr", {
            "invoice_key": invoice_key,
            "image_key": image_key or f"invoices/{invoice_key}.jpg",
            "session_id": batch_id,
            "user_id": user_id,
        })

        translated = await self._call("translation", {
            **raw, "session_id": batch_id, "user_id": user_id,
        })

        validated = await self._call("validation", {
            **translated, "session_id": batch_id, "user_id": user_id,
        })

        aggregated = await self._call("aggregation", {
            "invoices": [validated], "session_id": batch_id, "user_id": user_id,
        })

        formatted = await self._call("formatting", {
            **validated, "session_id": batch_id, "user_id": user_id,
        })

        approved = await self._call("approval", {
            **validated, "session_id": batch_id, "user_id": user_id,
        })

        return {
            "pipeline": "single_invoice",
            "batch_id": batch_id,
            "invoice_key": invoice_key,
            "steps": {
                "1_ocr": raw,
                "2_translation": translated,
                "3_validation": validated,
                "4_aggregation": aggregated,
                "5_formatting": formatted,
                "6_approval": approved,
            },
        }

    def run_single(
        self,
        invoice_key: str = "default",
        image_key: str | None = None,
        session_id: str | None = None,
        user_id: str = "system",
    ) -> dict:
        return asyncio.run(
            self.run_single_async(invoice_key, image_key, session_id, user_id)
        )

    async def run_batch_async(
        self,
        invoice_keys: list[str] | None = None,
        session_id: str | None = None,
        user_id: str = "system",
    ) -> dict:
        if invoice_keys is None:
            invoice_keys = ["default", "invoice2", "invoice3"]
        batch_id = session_id or self._gen_batch_id()

        raw_steps: list[dict] = []
        translation_steps: list[dict] = []
        validated_invoices: list[dict] = []

        for key in invoice_keys:
            raw = await self._call("ocr", {
                "invoice_key": key,
                "image_key": f"invoices/{key}.jpg",
                "session_id": batch_id,
                "user_id": user_id,
            })
            raw_steps.append(raw)

            translated = await self._call("translation", {
                **raw, "session_id": batch_id, "user_id": user_id,
            })
            translation_steps.append(translated)

            validated = await self._call("validation", {
                **translated, "session_id": batch_id, "user_id": user_id,
            })
            validated_invoices.append(validated)

        aggregated = await self._call("aggregation", {
            "invoices": validated_invoices,
            "session_id": batch_id,
            "user_id": user_id,
        })

        formatted_steps: list[dict] = []
        approvals: list[dict] = []
        for inv in validated_invoices:
            formatted = await self._call("formatting", {
                **inv, "session_id": batch_id, "user_id": user_id,
            })
            formatted_steps.append(formatted)

            appr = await self._call("approval", {
                **inv, "session_id": batch_id, "user_id": user_id,
            })
            approvals.append(appr)

        aggregated["approvals"] = approvals

        return {
            "pipeline": "batch",
            "batch_id": batch_id,
            "invoice_count": len(invoice_keys),
            "steps": {
                "1_ocr": raw_steps,
                "2_translation": translation_steps,
                "3_validation": validated_invoices,
                "4_aggregation": aggregated,
                "5_formatting": formatted_steps,
                "6_approval": approvals,
            },
        }

    def run_batch(
        self,
        invoice_keys: list[str] | None = None,
        session_id: str | None = None,
        user_id: str = "system",
    ) -> dict:
        return asyncio.run(
            self.run_batch_async(invoice_keys, session_id, user_id)
        )
