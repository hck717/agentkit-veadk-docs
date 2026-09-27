from __future__ import annotations

import os
import threading
import logging
from typing import Any

from agents.config_loader import (
    resolve_stm_config,
    resolve_ltm_config,
    resolve_context_policy,
    resolve_api_key,
    resolve_api_base,
)

logger = logging.getLogger(__name__)


def _embedding_reachable(timeout: float = 6.0) -> bool:
    """Probe the configured embedding model through the same client veadk uses.

    The LTM backend embeds via an Ark embedding model; if that model is not
    activated the request can hang for a very long time (and the SDK's client
    does not time out). Probing once at build time in a daemon thread lets us
    disable LTM cleanly instead of stalling the pipeline. A daemon thread is
    used so an abandoned hung request is never joined at interpreter exit.
    """
    name = os.environ.get("MODEL_EMBEDDING_NAME", "skylark-embedding-vision-251215")
    key = os.environ.get("MODEL_EMBEDDING_API_KEY", "")
    base = os.environ.get("MODEL_EMBEDDING_API_BASE", resolve_api_base())
    if not key:
        return False
    try:
        from veadk.models.ark_embedding import create_embedding_model
        model = create_embedding_model(model_name=name, api_key=key, api_base=base)
    except Exception as e:
        logger.debug("embedding probe: could not build model: %s", e)
        return False

    outcome: dict[str, bool] = {}

    def _probe() -> None:
        try:
            model.get_text_embedding("probe")
            outcome["ok"] = True
        except Exception:
            outcome["ok"] = False

    thread = threading.Thread(target=_probe, daemon=True)
    thread.start()
    thread.join(timeout=timeout)
    if thread.is_alive():
        logger.warning("LTM disabled: embedding model %s unreachable (timed out)", name)
        return False
    if not outcome.get("ok"):
        logger.warning("LTM disabled: embedding model %s failed probe", name)
        return False
    return True


def build_stm(agent_name: str) -> Any:
    cfg = resolve_stm_config(agent_name)
    backend = cfg.get("backend", "local")
    try:
        from veadk.memory.short_term_memory import ShortTermMemory
        kwargs: dict[str, Any] = {"backend": backend}
        if backend == "sqlite":
            kwargs["local_database_path"] = cfg.get("local_database_path", "./stm_dev.db")
        elif backend in ("postgresql", "mysql"):
            kwargs["db_url"] = cfg.get("db_url", "")
            if "session_ttl_hours" in cfg:
                kwargs["session_ttl_hours"] = int(cfg["session_ttl_hours"])
            if "cleanup_interval_minutes" in cfg:
                kwargs["cleanup_interval_minutes"] = int(cfg["cleanup_interval_minutes"])
        logger.debug("STM built: backend=%s agent=%s", backend, agent_name)
        return ShortTermMemory(**kwargs)
    except ImportError:
        logger.debug("veadk not installed — using LocalMockSTM for %s", agent_name)
        return LocalMockSTM()


def build_ltm(agent_name: str) -> Any:
    cfg = resolve_ltm_config(agent_name)
    if not cfg:
        return None
    backend = cfg.get("backend", "local")
    app_name = cfg.get("app_name", f"{agent_name}_ltm")
    try:
        os.environ.setdefault("MODEL_EMBEDDING_API_KEY", resolve_api_key())
        os.environ.setdefault("MODEL_EMBEDDING_API_BASE", resolve_api_base())
        os.environ.setdefault(
            "MODEL_EMBEDDING_NAME",
            cfg.get("embedding_model", "skylark-embedding-vision-251215"),
        )
        if backend != "openviking" and not _embedding_reachable():
            return None
        from veadk.memory.long_term_memory import LongTermMemory
        kwargs: dict[str, Any] = {"backend": backend, "app_name": app_name}
        extra_keys = ["embedding_model", "index", "host", "port"]
        for k in extra_keys:
            if k in cfg:
                kwargs[k] = cfg[k]
        logger.debug("LTM built: backend=%s app=%s", backend, app_name)
        return LongTermMemory(**kwargs)
    except ImportError:
        logger.debug("veadk not installed — using LocalMockLTM for %s", agent_name)
        return LocalMockLTM(app_name=app_name)


def make_runner(agent: Any, stm: Any, name: str) -> Any:
    from veadk import Runner
    policy = resolve_context_policy(name)
    runner_kwargs: dict[str, Any] = {
        "agent": agent,
        "app_name": name,
    }
    if stm is not None:
        runner_kwargs["short_term_memory"] = stm
    runner = Runner(**runner_kwargs)
    if policy:
        try:
            from google.adk.apps.app import App, EventsCompactionConfig
            interval = policy.get("compaction_interval", 5)
            overlap = policy.get("overlap_size", 2)
            adk_app = App(
                name=name,
                root_agent=agent,
                events_compaction_config=EventsCompactionConfig(
                    compaction_interval=interval,
                    overlap_size=overlap,
                ),
            )
            runner._app = adk_app
            logger.debug("App+compaction attached to runner: interval=%d overlap=%d", interval, overlap)
        except ImportError:
            logger.debug("google.adk not available — skipping App wrapper for %s", name)
    return runner


class LocalMockSTM:
    def __init__(self):
        self._store: dict[str, dict] = {}
        self._events: list[dict] = []
        self._sessions: dict[str, dict] = {}

    async def create_session(self, app_name: str = "", user_id: str = "",
                             session_id: str = "", metadata: dict | None = None):
        self._sessions[session_id] = {
            "app_name": app_name,
            "user_id": user_id,
            "session_id": session_id,
            "metadata": metadata or {},
            "status": "active",
        }
        return self._sessions[session_id]

    async def get_session(self, app_name: str = "", user_id: str = "",
                          session_id: str = ""):
        return self._sessions.get(session_id)

    async def list_sessions(self, app_name: str = "", user_id: str = ""):
        return [s for s in self._sessions.values()
                if s.get("app_name") == app_name and s.get("user_id") == user_id]

    async def delete_session(self, app_name: str = "", user_id: str = "",
                             session_id: str = ""):
        self._sessions.pop(session_id, None)

    async def append_event(self, app_name: str = "", user_id: str = "",
                           session_id: str = "", event: Any = None):
        self._events.append({
            "app_name": app_name,
            "user_id": user_id,
            "session_id": session_id,
            "event": event,
        })


class LocalMockLTM:
    def __init__(self, app_name: str = "mock_ltm"):
        self.app_name = app_name
        self._store: list[dict] = []

    async def save_memory(self, user_id: str = "", memory_type: str = "",
                          content: dict | None = None):
        self._store.append({
            "user_id": user_id,
            "memory_type": memory_type,
            "content": content or {},
        })
        return {"status": "saved"}

    async def search_memory(self, query: str = "", memory_type: str = "",
                            user_id: str = "", top_k: int = 5,
                            app_name: str = "", **kwargs):
        results = [m for m in self._store
                   if (not memory_type or m["memory_type"] == memory_type)
                   and (not user_id or m["user_id"] == user_id)
                   and (not app_name or m.get("app_name", self.app_name) == app_name)]
        class MockResponse:
            def __init__(self, memories):
                self.memories = memories
        return MockResponse(memories=results[:top_k])

    async def add_session_to_memory(self, completed_session: Any = None):
        pass
