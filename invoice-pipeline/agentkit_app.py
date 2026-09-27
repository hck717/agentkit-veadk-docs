from __future__ import annotations

import os
import logging

from veadk.integrations.agentkit import create_agentkit_app

from agents.ocr_agent import OcrAgent
from agents.translation_agent import TranslationAgent
from agents.validation_agent import ValidationAgent
from agents.aggregation_agent import AggregationAgent
from agents.formatting_agent import FormattingAgent
from agents.approval_agent import ApprovalAgent

logger = logging.getLogger(__name__)

AGENTS = {
    "ocr_agent": OcrAgent(mock=False),
    "translation_agent": TranslationAgent(mock=False),
    "validation_agent": ValidationAgent(mock=False),
    "aggregation_agent": AggregationAgent(mock=False),
    "formatting_agent": FormattingAgent(mock=False),
    "approval_agent": ApprovalAgent(mock=False),
}


def build_app(agent_name: str):
    """Wrap the selected agent as an AgentKit runtime app (conversation + A2A + Web UI)."""
    agent = AGENTS.get(agent_name)
    if agent is None:
        raise SystemExit(f"Unknown AGENT_NAME: {agent_name} (choose from {sorted(AGENTS)})")
    return create_agentkit_app(agent.build_veadk_agent())


if __name__ == "__main__":
    import uvicorn
    name = os.environ.get("AGENT_NAME", "ocr_agent")
    port = int(os.environ.get("PORT", "8080"))
    app = build_app(name)
    print(f"A2A service for {name} running on :{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
