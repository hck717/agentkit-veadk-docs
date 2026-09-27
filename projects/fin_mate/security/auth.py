"""FIN-MATE D7 安全層：simple token auth + role 對應。

Token→role 由 `.env` 嘅 `FINMATE_TOKENS` 提供，格式：
  FINMATE_TOKENS="viewer=<token>,analyst=<token>,admin=<token>"
純 function、deterministic。`authenticate(token)` 回傳 role 或 None。
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ROLES = ("viewer", "analyst", "admin")


def _load_env() -> None:
    p = ROOT / ".env"
    if not p.exists():
        return
    env = os.environ
    for line in p.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def token_table() -> dict[str, str]:
    """{role: token}；冇設就回傳空表（即 auth 全拒）。"""
    _load_env()
    raw = os.getenv("FINMATE_TOKENS", "").strip()
    table: dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part or "=" not in part:
            continue
        role, _, tok = part.partition("=")
        role = role.strip()
        if role in ROLES and tok.strip():
            table[role] = tok.strip()
    return table


def authenticate(token: str | None) -> str | None:
    """回傳 token 對應嘅 role；token 空／唔識 → None。"""
    if not token:
        return None
    for role, tok in token_table().items():
        if _safe_eq(tok, token):
            return role
    return None


def token_for_role(role: str) -> str | None:
    return token_table().get(role)


def _safe_eq(a: str, b: str) -> bool:
    return len(a) == len(b) and a == b