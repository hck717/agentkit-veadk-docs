"""brian_assistant — 共用 Agent 建構（veadk studio / web 同 agentkit deploy 共用）。

呢個係最細嘅「接線」版本，只負責令 Studio 見到同用到：
- Model：Ark（MODEL_AGENT_* 由 .env 提供）
- KnowledgeBase：本機 OpenViking（index = brian_kb，auto seed data/kb/）
- Memory：STM = sqlite；LTM = OpenViking

未加入任何自訂工具、自訂 instruction 或業務邏輯。
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from veadk import Agent
from veadk.knowledgebase import KnowledgeBase
from veadk.memory import LongTermMemory, ShortTermMemory
from veadk.prompts.agent_default_prompt import DEFAULT_DESCRIPTION, DEFAULT_INSTRUCTION
from veadk.tools.builtin_tools.coding import coding
from veadk.tools.builtin_tools.link_reader import link_reader
from veadk.tools.builtin_tools.run_code import run_code
from veadk.tools.builtin_tools.web_fetch import web_fetch
from veadk.tools.builtin_tools.web_search import web_search

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

AGENT_NAME = "brian_assistant"
DESCRIPTION = DEFAULT_DESCRIPTION
INSTRUCTION = DEFAULT_INSTRUCTION

# ---- Model（Ark，API base 由 MODEL_AGENT_API_BASE 提供）----
MODEL_PRIMARY = "seed-1-6-flash-250715"
MODEL_BACKUP = "seed-1-6-flash-250615"

KB_INDEX = "brian_kb"

_DATA_DIR = Path(__file__).resolve().parent / "data"


def _patch_openviking_hydrate() -> None:
    """Compat shim：veadk 1.1.9 嘅 openviking backend 淨係靠 `is_leaf` 決定用 read() 定 overview()。

    OpenViking `find` 回傳嘅 resource 全部 `is_leaf=None`，搞到永遠行 overview() →
    '[Directory overview is not ready]'，攞唔到正文。呢度 monkey-patch `_hydrate`，
    header 之後直接 read() 拉葉節內容。
    """
    try:
        from veadk.knowledgebase.backends.openviking_backend import (
            OpenVikingKnowledgeBackend,
        )
    except Exception:  # noqa: BLE001 - backend 未裝就 skip
        return

    if getattr(OpenVikingKnowledgeBackend, "_brian_assistant_hydrate_patched", False):
        return

    def _hydrate_patched(self, uri: str, item: dict):
        if not uri:
            return str(item.get("abstract") or "")
        try:
            client = self._ensure_client()
            if item.get("is_leaf"):
                return client.read(uri, offset=0, limit=self.read_limit)
            # 即使 find 唔標 is_leaf，讀到正文就用正文；read() 失敗先 fallback overview
            try:
                return client.read(uri, offset=0, limit=self.read_limit)
            except Exception:  # noqa: BLE001
                return client.overview(uri)
        except Exception as e:  # noqa: BLE001 - hydration 失敗 fallback 去 abstract
            logger.debug(f"Failed to hydrate OpenViking resource {uri}: {e}")
            return str(item.get("abstract") or "")

    OpenVikingKnowledgeBackend._hydrate = _hydrate_patched
    OpenVikingKnowledgeBackend._brian_assistant_hydrate_patched = True
    logger.info("Patched OpenViking KB hydration to prefer read() over overview().")


_patch_openviking_hydrate()


def _openviking_has_data(index: str = KB_INDEX) -> bool:
    """OpenViking 該 index 已經有 completed add_resource 就唔再 add（避免重複塞 data）。"""
    try:
        from openviking_sdk import SyncHTTPClient

        client = SyncHTTPClient(
            url=os.getenv("DATABASE_OPENVIKING_URL") or "http://localhost:1934",
            api_key=os.getenv("DATABASE_OPENVIKING_API_KEY"),
            timeout=15,
        )
        client.initialize()
        try:
            tasks = client.list_tasks(limit=100)
        finally:
            client.close()
        return any(
            t.get("task_type") == "add_resource"
            and index in (t.get("resource_id") or "")
            and t.get("status") == "completed"
            for t in tasks
        )
    except Exception:  # noqa: BLE001 - check 失敗時唔好 blocking，照 add
        return False


def build_knowledgebase() -> KnowledgeBase | None:
    """KnowledgeBase：本機 OpenViking（viking:// resource，server 端 parse + embed）。

    資料喺 data/kb（含子目錄）。已 seed 過就 skip，避免每次重啟重複 insert。
    服務未通時返回 None，令 agent 照起（無 knowledgebase）。
    """
    kb_root = _DATA_DIR / "kb"
    kb_root.mkdir(parents=True, exist_ok=True)
    source_paths = sorted({kb_root, *(p for p in kb_root.rglob("*") if p.is_dir())})

    try:
        kb = KnowledgeBase(backend="openviking", index=KB_INDEX, top_k=5)
        if not _openviking_has_data(index=KB_INDEX):
            for p in source_paths:
                kb.add_from_directory(str(p))
            logger.info("KnowledgeBase backend: openviking — seeded data/kb/")
        else:
            logger.info("KnowledgeBase backend: openviking — already seeded, skip add")
        return kb
    except Exception as exc:  # noqa: BLE001 - config 未齊/服務未通時降級
        logger.warning("No working KB backend (%s); agent will run without knowledgebase.", exc)
        return None


def build_agent() -> Agent:
    """建構 brian_assistant agent（veadk studio / web 同 agentkit deploy 共用）。"""
    kb = build_knowledgebase()

    stm = ShortTermMemory(
        backend="sqlite",
        local_database_path=str(_DATA_DIR / "stores" / "brian_assistant.db"),
    )
    ltm = LongTermMemory(backend="openviking", index=AGENT_NAME)

    tools = [
        web_search,
        web_fetch,
        link_reader,
        run_code,
        coding,
    ]

    return Agent(
        name=AGENT_NAME,
        description=DESCRIPTION,
        instruction=INSTRUCTION,
        tools=tools,
        knowledgebase=kb,
        short_term_memory=stm,
        long_term_memory=ltm,
        auto_save_session=True,
        model_name=[MODEL_PRIMARY, MODEL_BACKUP],
    )
