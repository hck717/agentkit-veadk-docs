from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_BASE = Path(__file__).resolve().parent.parent


def load_yaml(path: str | Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError:
        return {}
    path = _BASE / path if not Path(path).is_absolute() else Path(path)
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_shared_config() -> dict[str, Any]:
    return load_yaml("config.yaml")


def load_agent_config(agent_name: str) -> dict[str, Any]:
    candidates = [
        f"agents/configs/{agent_name}.yaml",
        f"agents/configs/{agent_name.replace('_agent', '')}.yaml",
    ]
    for path in candidates:
        result = load_yaml(path)
        if result:
            return result
    return {}


def resolve_model_name(agent_name: str, default: str = "dola-seed-2-1-turbo-260628") -> str:
    config = load_agent_config(agent_name)
    model = config.get("agent", {}).get("model", default)
    return os.environ.get("MODEL_AGENT_NAME", model)


def resolve_api_key() -> str:
    shared = load_shared_config()
    key = shared.get("model", {}).get("agent", {}).get("api_key", "")
    return os.environ.get("MODEL_AGENT_API_KEY", key)


def resolve_api_base() -> str:
    shared = load_shared_config()
    base = shared.get("model", {}).get("agent", {}).get("api_base",
        "https://ark.ap-southeast.bytepluses.com/api/v3/")
    return os.environ.get("MODEL_AGENT_API_BASE", base)


def resolve_stm_config(agent_name: str) -> dict[str, Any]:
    config = load_agent_config(agent_name)
    return config.get("short_term_memory", {"backend": "local"})


def resolve_ltm_config(agent_name: str) -> dict[str, Any]:
    config = load_agent_config(agent_name)
    return config.get("long_term_memory", {})


def resolve_context_policy(agent_name: str) -> dict[str, Any]:
    config = load_agent_config(agent_name)
    return config.get("context_policy", {})


def resolve_image_gen_config(agent_name: str) -> dict[str, Any]:
    config = load_agent_config(agent_name)
    return config.get("image_generation", {})


def resolve_reasoning_effort(agent_name: str) -> str | None:
    config = load_agent_config(agent_name)
    effort = config.get("agent", {}).get("reasoning_effort")
    return os.environ.get("REASONING_EFFORT", effort)


def _clean_feishu_value(value: Any) -> str:
    """Treat config placeholders like `<your-...>` / `https://your-...` as unset."""
    if value is None:
        return ""
    text = str(value).strip()
    if text.startswith("<") and text.endswith(">"):
        return ""
    if "your-" in text:
        return ""
    return text


def resolve_feishu_config() -> dict[str, Any]:
    shared = load_shared_config()
    feishu = shared.get("feishu", {})
    return {
        # FeishuChannelExtension 用 TOOL_FEISHU_CHANNEL_*（見 veadk/extensions/feishu_channel.py）
        # FEISHU_APP_ID/SECRET 保留做 backward-compatible alias
        "app_id": _clean_feishu_value(
            os.environ.get("TOOL_FEISHU_CHANNEL_APP_ID")
            or os.environ.get("FEISHU_APP_ID")
            or feishu.get("channel", {}).get("app_id", "")
        ),
        "app_secret": _clean_feishu_value(
            os.environ.get("TOOL_FEISHU_CHANNEL_APP_SECRET")
            or os.environ.get("FEISHU_APP_SECRET")
            or feishu.get("channel", {}).get("app_secret", "")
        ),
        "webhook_url": _clean_feishu_value(
            os.environ.get("FEISHU_WEBHOOK_URL") or feishu.get("webhook", {}).get("url", "")
        ),
        "callback_url": _clean_feishu_value(
            os.environ.get("FEISHU_CALLBACK_URL")
            or feishu.get("approval", {}).get("callback_url", "")
        ),
        "enabled": os.environ.get("FEISHU_ENABLED", str(feishu.get("approval", {}).get("enabled", False))).lower() == "true",
    }
