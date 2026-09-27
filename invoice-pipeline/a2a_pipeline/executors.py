"""A2A executors wrapping the 5 invoice pipeline agents.

Each executor is an `a2a.server.agent_execution.AgentExecutor` that reads a
JSON payload from the incoming user message, calls the wrapped agent's
`run_async()`, and publishes the JSON result back as a completed Task.
"""

from __future__ import annotations

import json
import uuid
import logging
from datetime import datetime, timezone

from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.types import (
    Message,
    Role,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)

from agents.ocr_agent import OcrAgent
from agents.translation_agent import TranslationAgent
from agents.validation_agent import ValidationAgent
from agents.aggregation_agent import AggregationAgent
from agents.formatting_agent import FormattingAgent
from agents.approval_agent import ApprovalAgent

logger = logging.getLogger(__name__)


class InvoiceExecutor(AgentExecutor):
    """Shared A2A executor base: JSON text in, JSON text out."""

    def __init__(self, agent, name: str):
        self.agent = agent
        self.name = name

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        try:
            input_text = context.get_user_input()
            payload = json.loads(input_text) if input_text else {}
            result = await self.agent.run_async(payload)
            await event_queue.enqueue_event(
                self._status_event(
                    context.task_id,
                    context.context_id,
                    TaskState.completed,
                    json.dumps(result, ensure_ascii=False),
                )
            )
        except Exception as e:
            logger.exception("%s executor failed", self.name)
            await event_queue.enqueue_event(
                self._status_event(
                    context.task_id,
                    context.context_id,
                    TaskState.failed,
                    str(e),
                )
            )

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        await event_queue.enqueue_event(
            self._status_event(
                context.task_id,
                context.context_id,
                TaskState.canceled,
                "canceled",
            )
        )

    @staticmethod
    def _status_event(
        task_id: str, context_id: str, state: TaskState, text: str
    ) -> TaskStatusUpdateEvent:
        return TaskStatusUpdateEvent(
            task_id=task_id,
            context_id=context_id,
            status=TaskStatus(
                state=state,
                timestamp=datetime.now(timezone.utc).isoformat(),
                message=Message(
                    message_id=str(uuid.uuid4()),
                    role=Role.agent,
                    parts=[TextPart(text=text)],
                ),
            ),
            final=True,
        )


class OcrExecutor(InvoiceExecutor):
    def __init__(self, mock: bool = True):
        super().__init__(OcrAgent(mock=mock), "ocr")


class TranslationExecutor(InvoiceExecutor):
    def __init__(self, mock: bool = True):
        super().__init__(TranslationAgent(mock=mock), "translation")


class ValidationExecutor(InvoiceExecutor):
    def __init__(self, mock: bool = True):
        super().__init__(ValidationAgent(mock=mock), "validation")


class AggregationExecutor(InvoiceExecutor):
    def __init__(self, mock: bool = True):
        super().__init__(AggregationAgent(mock=mock), "aggregation")


class FormattingExecutor(InvoiceExecutor):
    def __init__(self, mock: bool = True):
        super().__init__(FormattingAgent(mock=mock), "formatting")


class ApprovalExecutor(InvoiceExecutor):
    def __init__(self, mock: bool = True):
        super().__init__(ApprovalAgent(mock=mock), "approval")


EXECUTORS = {
    "ocr": OcrExecutor,
    "translation": TranslationExecutor,
    "validation": ValidationExecutor,
    "aggregation": AggregationExecutor,
    "formatting": FormattingExecutor,
    "approval": ApprovalExecutor,
}
