from __future__ import annotations

import os
import json
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone

from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from a2a_orchestrator import InvoicePipeline
from frontend.feishu import FeishuNotifier
from frontend.callbacks import ApprovalState
from agents.config_loader import load_shared_config

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
FORMATTED_DIR = BASE_DIR.parent / "data" / "formatted"

MOCK = os.environ.get("PIPELINE_MOCK", "true").lower() != "false"

pipeline = InvoicePipeline(mock=MOCK)
approval_state = ApprovalState()
feishu = FeishuNotifier()

app = FastAPI(title="Invoice Pipeline")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/formatted", StaticFiles(directory=str(FORMATTED_DIR)), name="formatted")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

_agentkit_routes = False


def _init_agentkit():
    global _agentkit_routes
    if _agentkit_routes:
        return
    try:
        config = load_shared_config()
        model_name = config.get("model", {}).get("agent", {}).get("name", "seed-2-0-mini-260428")

        from veadk import Agent
        from veadk.integrations.agentkit import create_agentkit_app

        approval_agent = Agent(
            name="approval_agent",
            model_name=model_name,
            enable_a2ui=True,
            instruction="Review invoices and flag suspicious ones for human approval.",
        )
        ak_app = create_agentkit_app(approval_agent)
        app.mount("/agentkit", ak_app)
        _agentkit_routes = True
        logger.info("AgentKit Runtime routes mounted at /agentkit")
    except ImportError:
        logger.info("veadk not installed — AgentKit routes skipped")
        _agentkit_routes = False
    except Exception as e:
        logger.warning("AgentKit init failed: %s", e)
        _agentkit_routes = False


@app.on_event("startup")
async def startup():
    _init_agentkit()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"request": request})


@app.post("/upload")
async def upload_invoice(file: UploadFile = File(...), invoice_key: str = Form("invoice2")):
    task_id = str(uuid.uuid4())[:8]
    batch_id = f"frontend-{task_id}"
    file_ext = Path(file.filename or "invoice.jpg").suffix
    file_path = UPLOAD_DIR / f"{task_id}{file_ext}"
    content = await file.read()
    file_path.write_bytes(content)

    result = pipeline.run_single(
        invoice_key=invoice_key,
        image_key=str(file_path),
        session_id=batch_id,
        user_id="frontend_user",
    )

    steps = result["steps"]
    approval = steps["6_approval"]
    formatting = steps.get("5_formatting", {})
    task = {
        "task_id": task_id,
        "batch_id": batch_id,
        "filename": file.filename or "unknown",
        "status": approval["status"],
        "approval": approval,
        "formatted_image": {
            "status": formatting.get("status", ""),
            "url": formatting.get("formatted_image_url", ""),
            "path": formatting.get("formatted_image_path", ""),
        },
        "pipeline": result,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if approval["status"] == "pending_review":
        approval_state.set(task_id, task)
        await feishu.send_approval_request(approval, task_id)

    return JSONResponse(task)


@app.get("/status/{task_id}")
async def get_status(task_id: str):
    state = approval_state.get(task_id)
    return JSONResponse(state or {"status": "not_found"})


@app.post("/approve")
async def approve(task_id: str = Form(...), reviewer_notes: str = Form("")):
    state = approval_state.get(task_id)
    if not state:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    state["approval"]["status"] = "approved"
    state["approval"]["approved_by"] = "frontend_user"
    state["approval"]["reviewer_notes"] = reviewer_notes or state["approval"].get("reviewer_notes", "")
    state["approval"]["timestamp"] = datetime.now(timezone.utc).isoformat()
    state["status"] = "approved"
    approval_state.set(task_id, state)
    await feishu.send_result_notification(state["approval"])
    return JSONResponse(state)


@app.post("/reject")
async def reject(task_id: str = Form(...), reviewer_notes: str = Form("")):
    state = approval_state.get(task_id)
    if not state:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    state["approval"]["status"] = "rejected"
    state["approval"]["approved_by"] = "frontend_user"
    state["approval"]["reviewer_notes"] = reviewer_notes or state["approval"].get("reviewer_notes", "")
    state["approval"]["timestamp"] = datetime.now(timezone.utc).isoformat()
    state["status"] = "rejected"
    approval_state.set(task_id, state)
    await feishu.send_result_notification(state["approval"])
    return JSONResponse(state)


@app.post("/feishu/callback")
async def feishu_callback(request: Request):
    data = await request.json()
    action_value = data.get("action", {}).get("value", {})
    task_id = action_value.get("task_id", data.get("task_id", ""))
    action = action_value.get("action", data.get("action", ""))
    state = approval_state.get(task_id)
    if not state:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    if action == "approve":
        state["approval"]["status"] = "approved"
        state["approval"]["approved_by"] = "feishu_user"
    elif action == "reject":
        state["approval"]["status"] = "rejected"
        state["approval"]["approved_by"] = "feishu_user"
    state["approval"]["timestamp"] = datetime.now(timezone.utc).isoformat()
    state["status"] = state["approval"]["status"]
    approval_state.set(task_id, state)
    await feishu.send_result_notification(state["approval"])
    return JSONResponse({"ok": True})


@app.get("/health")
async def health():
    ak_status = "mounted" if _agentkit_routes else ("skipped" if _agentkit_routes is False else "not_initialized")
    return {
        "status": "ok",
        "service": "invoice-pipeline-frontend",
        "agentkit": ak_status,
        "mock": MOCK,
        "pending_approvals": len(approval_state.list_pending()),
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    print(f"Invoice Pipeline Frontend: http://localhost:{port}")
    uvicorn.run("frontend.app:app", host="0.0.0.0", port=port)
