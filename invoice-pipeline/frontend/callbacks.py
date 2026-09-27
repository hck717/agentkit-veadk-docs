from __future__ import annotations

import time
import threading
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_lock = threading.Lock()


class ApprovalState:
    """In-memory approval task store with TTL expiry."""

    def __init__(self):
        self._store: dict[str, dict] = {}
        self._ttl: int = 3600

    def set(self, task_id: str, state: dict):
        with _lock:
            state["_updated_at"] = time.time()
            self._store[task_id] = state
            self._evict_expired()

    def get(self, task_id: str) -> Optional[dict]:
        with _lock:
            state = self._store.get(task_id)
            if state is None:
                return None
            if time.time() - state.get("_updated_at", 0) > self._ttl:
                del self._store[task_id]
                return None
            return state

    def list_pending(self) -> list[dict]:
        with _lock:
            self._evict_expired()
            return [s for s in self._store.values() if s.get("status") in ("pending_review",)]

    def _evict_expired(self):
        now = time.time()
        expired = [k for k, v in self._store.items() if now - v.get("_updated_at", 0) > self._ttl]
        for k in expired:
            del self._store[k]

    def clear(self):
        with _lock:
            self._store.clear()
