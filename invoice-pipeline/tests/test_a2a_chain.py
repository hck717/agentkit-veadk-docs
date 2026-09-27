"""A2A drive-chain tests (mock mode, in-process uvicorn, no API calls)."""

import sys
import asyncio
import threading
import warnings
from pathlib import Path

import pytest

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn
import httpx

from a2a_pipeline.server import build_server
from a2a_pipeline.drive_chain import A2aDriveChain

PORT = 9910


@pytest.fixture(scope="module")
def server_url():
    app = build_server(mock=True, host="127.0.0.1", port=PORT)
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    async def _wait_ready():
        async with httpx.AsyncClient() as client:
            for _ in range(50):
                try:
                    r = await client.get(f"http://127.0.0.1:{PORT}/ping")
                    if r.status_code == 200:
                        return
                except Exception:
                    pass
                await asyncio.sleep(0.2)

    asyncio.run(_wait_ready())
    yield f"http://127.0.0.1:{PORT}"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.mark.anyio
async def test_agent_cards_served(server_url):
    async with httpx.AsyncClient() as client:
        for agent in ["ocr", "translation", "validation", "aggregation", "approval"]:
            r = await client.get(
                f"{server_url}/{agent}/.well-known/agent-card.json"
            )
            assert r.status_code == 200
            assert r.json()["version"] == "1.0.0"


@pytest.mark.anyio
async def test_single_chain(server_url):
    chain = A2aDriveChain(base_url=server_url)
    result = await chain.run_single_async("default")
    assert result["pipeline"] == "single_invoice"
    assert set(result["steps"].keys()) == {
        "1_ocr", "2_translation", "3_validation", "4_aggregation",
        "5_formatting", "6_approval",
    }
    assert result["steps"]["1_ocr"]["invoice_number"]
    assert result["steps"]["5_formatting"]["status"] == "mock_placeholder"
    assert result["steps"]["6_approval"]["status"] in ("approved", "pending_review")


@pytest.mark.anyio
async def test_batch_chain(server_url):
    chain = A2aDriveChain(base_url=server_url)
    result = await chain.run_batch_async(["default", "invoice2"])
    assert result["pipeline"] == "batch"
    assert result["invoice_count"] == 2
    assert len(result["steps"]["1_ocr"]) == 2
    assert len(result["steps"]["5_formatting"]) == 2
    assert len(result["steps"]["6_approval"]) == 2
