from __future__ import annotations

import json
import os
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

from agents.config_loader import load_agent_config
from agents.memory import build_stm, build_ltm, make_runner, LocalMockSTM, LocalMockLTM

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    def __init__(self, name: str, mock: bool = True):
        self.name = name
        self.mock = mock
        self.config = load_agent_config(name)
        if mock:
            self.stm = LocalMockSTM()
            self.ltm = LocalMockLTM(app_name=f"{name}_ltm")
        else:
            self.stm = build_stm(name)
            self.ltm = build_ltm(name)

    @abstractmethod
    def run(self, input_data: dict) -> dict:
        ...

    async def run_async(self, input_data: dict) -> dict:
        if self.mock:
            return self.run(input_data)
        return await self._run_veadk(input_data)

    def _build_runner(self, agent: Any, app_name: str | None = None) -> Any:
        return make_runner(agent, self.stm, app_name or self.name)

    def _build_agent_kwargs(self, **extra) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        kwargs["name"] = self.config.get("agent", {}).get("name", self.name)
        kwargs["model_name"] = self._resolve_model()
        kwargs["instruction"] = extra.pop("instruction", "")
        if extra:
            kwargs.update(extra)
        if self.ltm is not None:
            kwargs["long_term_memory"] = self.ltm
            kwargs["auto_save_session"] = True
        enable_a2ui = self.config.get("agent", {}).get("enable_a2ui", False)
        if enable_a2ui:
            kwargs["enable_a2ui"] = True
        reasoning_effort = self.config.get("agent", {}).get("reasoning_effort")
        if reasoning_effort:
            kwargs["model_extra_config"] = {
                "extra_body": {"reasoning_effort": reasoning_effort}
            }
        return kwargs

    def _resolve_model(self, default: str = "dola-seed-2-1-turbo-260628") -> str:
        model = self.config.get("agent", {}).get("model", default)
        return os.environ.get("MODEL_AGENT_NAME", model)

    @staticmethod
    def _get_model_name(default: str) -> str:
        return os.environ.get("MODEL_AGENT_NAME", default)

    @staticmethod
    def _extract_json(result: Any) -> Any:
        """Parse a model result into JSON, tolerating markdown/code fences."""
        if not isinstance(result, str):
            return result
        text = result.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lstrip().lower().startswith("json"):
                text = text.lstrip()[4:]
            text = text.strip()
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            pass
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except (json.JSONDecodeError, ValueError):
                pass
        logger.warning("Could not extract JSON from model result: %s", text[:300])
        return text
