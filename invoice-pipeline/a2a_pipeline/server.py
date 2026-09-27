"""Single-process A2A server mounting the 5 invoice agents as sub-apps.

Each agent is served as its own `A2AStarletteApplication`, mounted under a
path prefix (e.g. `/ocr`). A drive-chain orchestrator calls them in sequence
over the A2A protocol via `A2AClient`.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from starlette.applications import Starlette
from starlette.responses import JSONResponse

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, AgentCapabilities, AgentSkill

from a2a_pipeline.executors import EXECUTORS, InvoiceExecutor

logger = logging.getLogger(__name__)

AGENT_META = {
    "ocr": {"title": "OCR Agent", "description": "Extracts raw invoice fields from an image."},
    "translation": {"title": "Translation Agent", "description": "Translates invoice fields to English."},
    "validation": {"title": "Validation Agent", "description": "Validates and corrects extracted invoice data."},
    "aggregation": {"title": "Aggregation Agent", "description": "Aggregates validated invoices into a report."},
    "formatting": {"title": "Formatting Agent", "description": "Reformats invoice images into a clean template via Seedream."},
    "approval": {"title": "Approval Agent", "description": "Approves invoices or flags them for review."},
}


def build_agent_card(name: str, host: str, port: int) -> AgentCard:
    meta = AGENT_META[name]
    return AgentCard(
        name=meta["title"],
        description=meta["description"],
        url=f"http://{host}:{port}/{name}/",
        version="1.0.0",
        protocol_version="0.3.0",
        capabilities=AgentCapabilities(),
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        skills=[
            AgentSkill(
                id=name,
                name=meta["title"],
                description=meta["description"],
                tags=["invoice", name],
            )
        ],
    )


def build_agent_subapp(
    name: str, mock: bool, host: str, port: int
) -> Starlette:
    executor: InvoiceExecutor = EXECUTORS[name](mock=mock)
    card = build_agent_card(name, host, port)
    handler = DefaultRequestHandler(
        agent_executor=executor, task_store=InMemoryTaskStore()
    )
    return A2AStarletteApplication(
        agent_card=card, http_handler=handler
    ).build()


def build_server(mock: bool = True, host: str = "0.0.0.0", port: int = 9901) -> FastAPI:
    """Build the single-process FastAPI server with all 5 A2A agents mounted."""
    app = FastAPI(title="Invoice Pipeline A2A Server")

    @app.get("/ping")
    async def ping() -> dict:
        return {"status": "ok"}

    @app.get("/env")
    async def env() -> JSONResponse:
        return JSONResponse({"env": "veadk"})

    for name in AGENT_META:
        app.mount(f"/{name}", build_agent_subapp(name, mock, host, port))

    return app


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(build_server(), host="0.0.0.0", port=9901)
