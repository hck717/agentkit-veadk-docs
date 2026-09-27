"""FIN-MATE D7 安全層：接駁到 veadk Agent 嘅 callbacks（hooks）。

三個 hook，全部配 ADK callback 簽名，可直接放喺 `Agent(...)`：
  input_injection_filter   before_model_callback：偵測 injection/PII → 直接拒絕
  output_pii_filter        after_model_callback：輸出 mask PII + secret
  role_tool_gate           before_tool_callback：role 唔准用該 tool → block

`current_role` 用 contextvars 提供：預設 admin（唔影響現有 agent）；
demo / eval 用 `set_role()` 切換。because callback 係 framework thread，
load 時會讀返 context，所以用 contextvar 而非 module global。
"""
from __future__ import annotations

import contextvars
import re
from typing import Any, Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from security import filters, gate

current_role: contextvars.ContextVar[str] = contextvars.ContextVar("finmate_role", default="admin")


class role:
    """context 切換：`with role("analyst"): ...` 或 `role.set("viewer")`。"""

    @staticmethod
    def set(r: str) -> contextvars.Token:
        return current_role.set(r)

    @staticmethod
    def reset(token: contextvars.Token) -> None:
        current_role.reset(token)

    def __init__(self, r: str):
        self.r = r
        self._tok = None

    def __enter__(self):
        self._tok = current_role.set(self.r)
        return self

    def __exit__(self, *exc):
        current_role.reset(self._tok)


REFUSE_MSG = ("⛔ 輸入被安全層攔截：{why}。呢個要求唔會交由模型處理。"
              "如有疑問請聯絡管理員。")


def _last_user_text(llm_request: LlmRequest) -> str:
    texts: list[str] = []
    for c in llm_request.contents:
        if getattr(c, "role", "") == "user":
            texts = []
        for p in (getattr(c, "parts", None) or []):
            t = getattr(p, "text", None)
            if t:
                texts.append(t)
    return "".join(texts)


async def input_injection_filter(callback_context: CallbackContext,
                                 llm_request: LlmRequest) -> Optional[LlmResponse]:
    """before_model_callback：injection / PII 命中就唔行 model，直接拒。

    回傳 LlmResponse = short-circuit（ADK 唔會再 call model）；None = 放行。
    filter 係 rules-only → 百分百 reproducible。
    """
    text = _last_user_text(llm_request)
    if not text:
        return None
    inj = filters.detect_injection(text)
    pii = filters.detect_pii(text)
    reasons = [h["family"] for h in inj + pii]
    if not reasons:
        return None
    why = ", ".join(reasons)
    parts = [types.Part(text=REFUSE_MSG.format(why=why))]
    return LlmResponse(content=types.Content(role="model", parts=parts), turn_complete=True)


async def output_pii_filter(callback_context: CallbackContext,
                            llm_response: LlmResponse) -> Optional[LlmResponse]:
    """after_model_callback：輸出 mask PII / secret 先交俾用戶。"""
    if llm_response is None or llm_response.content is None:
        return llm_response
    new_parts = []
    for p in (llm_response.content.parts or []):
        t = getattr(p, "text", None)
        if t:
            clean, _ = filters.redact(t)
            p = types.Part(text=clean)  # noqa: PLW2901
        new_parts.append(p)
    llm_response.content.parts = new_parts
    return llm_response


def role_tool_gate(tool: BaseTool, tool_args: dict[str, Any],
                   tool_context: ToolContext) -> Optional[dict]:
    """before_tool_callback：role allowlist 執法。「越權 call 全 block」。

    返回 dict 就係「取代 tool 執行嘅結果」（ADK 唔會跑真 tool）；
    返回 None = 放行。default-deny：唔識嘅 tool 亦拒。
    """
    role_name = current_role.get()
    allowed, reason = gate.authorize_tool(role_name, tool.name)
    if allowed:
        return None
    return {"result": "ROLE_BLOCKED", "reason": reason or "權限不足",
            "tool": tool.name, "role": role_name}