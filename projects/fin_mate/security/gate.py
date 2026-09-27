"""FIN-MATE D7 安全層：role allowlist × tool 權限矩陣。

三層 role（viewer < analyst < admin），`authorize_tool(role, tool_name)`
決定用戶用某 tool 是否合規。未列入任何矩陣嘅 tool 視作 admin-only
（防禦性 default-deny）。純 function、deterministic，可直接測。

matrix（邊界）：
  viewer   只讀：web_search / web_fetch / link_reader / calc / KB-search
  analyst  + news（fetch_news / read_news_file）
  admin    全部（含 run_code / coding / read_news_file 寫向操作）
hierarchy：admin 可做一切；analyst 做 viewer+news；viewer 淨係讀。
"""
from __future__ import annotations

from typing import Callable

ROLES = ("viewer", "analyst", "admin")

_READ = {"web_search", "web_fetch", "link_reader", "calc"}
_NEWS = {"fetch_news", "read_news_file"}
_WRITE = {"run_code", "coding"}
# KB / memory / load_knowledgebase 等 builtin 讀取工具一律許可（read-only 語意）
_READ_PREFIX_OK = ("knowledgebase_", "load_", "search", "query", "kb_")

_ALL = _READ | _NEWS | _WRITE


def _role_index(role: str) -> int:
    return ROLES.index(role) if role in ROLES else -1


def authorize_tool(role: str, tool_name: str, *, tool_fn: Callable | None = None) -> tuple[bool, str | None]:
    """執法：role 可以唔可以用 `tool_name`？回傳 (allowed, reason)。

    reason = None → 放行；否則係唔准用嘅原因（供 block 回應）。
    default-deny：任何唔喺矩陣嘅 tool 只俾 admin。
    """
    idx = _role_index(role)
    if idx < 0:
        return False, f"unknown role: {role}"
    if tool_name in _READ and idx >= 0:
        return True, None
    if tool_name in _NEWS and idx >= ROLES.index("analyst"):
        return True, None
    if tool_name in _WRITE:
        if idx >= ROLES.index("admin"):
            return True, None
        return False, f"tool '{tool_name}' is admin-only"
    # builtin 讀取類（名字開頭近似 read/search/load/kb）——viewer 都准
    name = (tool_name or "").lower()
    if any(name.startswith(p) for p in _READ_PREFIX_OK):
        return True, None
    # 其他一律 admin-only（default-deny）
    if idx >= ROLES.index("admin"):
        return True, None
    return False, f"tool '{tool_name}' is admin-only (unknown tool)"


def role_tools(role: str, all_tools: list[str] | None = None) -> list[str]:
    """顯示某 role 可用工具（debug / 報告用）。"""
    pool = sorted(all_tools) if all_tools else sorted(_ALL)
    return [t for t in pool if authorize_tool(role, t)[0]]


def allowed_tool_names(role: str) -> set[str]:
    if role == "admin":
        return set(_ALL)
    if role == "analyst":
        return set(_READ) | set(_NEWS)
    return set(_READ)