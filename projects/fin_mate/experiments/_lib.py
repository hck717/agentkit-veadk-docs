"""RAG 實驗室共用（D4/D5）：env、KB、Ark + 本地 LLM client、stage timing、chars→tokens、USD 計。"""
from __future__ import annotations

import os
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# USD / 1M tokens — Volcano Ark 官方 2026（seed-1-6-flash）：input ¥0.15 / output ¥1.5 / cache-hit ¥0.03（¥7.1≈1USD）
PRICES = {"input": 0.021, "output": 0.211, "cached": 0.004}
DEFAULT_MODEL = "seed-1-6-flash-250715"


def load_env() -> None:
    p = ROOT / ".env"
    if not p.exists():
        return
    env = os.environ
    for line in p.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def build_kb(read_limit: int = 2000):
    """KB builder：粗/細 = read_limit hydration depth。agent_build imports 喺 load_env 之後先做。"""
    load_env()
    os.environ["DATABASE_OPENVIKING_READ_LIMIT"] = str(read_limit)
    import agent_build

    agent_build._patch_openviking_hydrate()
    return agent_build.build_knowledgebase()


@dataclass
class Completion:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    ms: float = 0.0


def _extract_text(raw) -> str:
    """Ark Responses 答案 text 有兩個位：部分 response 用 `output_text`，seed-1-6 就放
    `output[].content[].text`（type=output_text）。 response 冇 output_text attr 時要行後者。
    注意：raw.text 可能係 server echo 返嚟嘅 ResponseTextConfig（有 schema時），唔係答案
    string——淨係 str 先當答案。返回答案 text（唔含 reasoning）。"""
    t = getattr(raw, "text", None)
    if isinstance(t, str) and t:
        return t
    out = getattr(raw, "output", None) or []
    for o in out:
        if getattr(o, "type", "") == "message":
            for p in (getattr(o, "content", None) or []):
                txt = getattr(p, "text", None)
                if txt:
                    return txt
    return getattr(raw, "output_text", "") or ""


async def ark_complete(msgs: list, model: str | None = None, *, max_tokens: int = 512, caching: bool = False,
                       trace: list | None = None, output_schema: dict | None = None,
                       text_format: str | None = None) -> Completion:
    load_env()
    from volcenginesdkarkruntime import AsyncArk

    kwargs = {
        "model": model or os.environ.get("MODEL_PRIMARY", DEFAULT_MODEL),
        "input": msgs,
        "stream": False,
        "max_output_tokens": max_tokens,
        "thinking": {"type": "disabled"},  # seed-1-6 預設 thinking：會燒成個 output 預算用嚟諗嘢
    }
    if caching:
        kwargs["extra_body"] = {"caching": {"type": "enabled"}}
    if output_schema is not None:
        # Ark Responses API 原生 structured output：text.format json_schema（request 面）
        kwargs["text"] = {
            "format": {
                "type": "json_schema",
                "name": output_schema.pop("title", "output") or "output",
                "schema": output_schema,
                "strict": True,
            }
        }
    elif text_format == "json_object":
        kwargs["text"] = {"format": {"type": "json_object"}}
    client = AsyncArk(base_url=os.environ["MODEL_AGENT_API_BASE"], api_key=os.environ["MODEL_AGENT_API_KEY"])
    t = time.perf_counter()
    raw = await client.responses.create(**kwargs)
    ms = (time.perf_counter() - t) * 1000
    await client.close()
    u = raw.usage
    comp = Completion(
        text=_extract_text(raw),
        prompt_tokens=getattr(u, "input_tokens", 0),
        completion_tokens=getattr(u, "output_tokens", 0),
        cached_tokens=getattr(getattr(u, "input_tokens_details", None), "cached_tokens", 0),
        ms=ms,
    )
    if trace is not None:
        trace.append({"llm": "ark", "msgs": msgs, "text": comp.text, "prompt_tokens": comp.prompt_tokens,
                      "completion_tokens": comp.completion_tokens, "cached_tokens": comp.cached_tokens, "ms": comp.ms})
    return comp


async def local_complete(msgs: list, *, base_url: str, model: str, max_tokens: int = 512,
                         temperature: float = 0.0, extra_body: dict | None = None,
                         trace: list | None = None) -> Completion:
    """OpenAI-compat（Ollama / vllm-mlx）——D5 本地 LLM-as-reranker。
    `extra_body` 會併入 JSON body（例如 Ollama 原生 `think`/`options`）。"""
    import httpx

    body = {"model": model, "messages": msgs, "stream": False,
            "max_tokens": max_tokens, "temperature": temperature, **(extra_body or {})}
    t = time.perf_counter()
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(base_url.rstrip("/") + "/v1/chat/completions", json=body)
        r.raise_for_status()
        j = r.json()
    ms = (time.perf_counter() - t) * 1000
    u = (j.get("usage") or {})
    cached = (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
    comp = Completion(text=j["choices"][0]["message"]["content"], prompt_tokens=u.get("prompt_tokens", 0),
                      completion_tokens=u.get("completion_tokens", 0), cached_tokens=cached, ms=ms)
    if trace is not None:
        trace.append({"llm": "local", "msgs": msgs, "text": comp.text, "prompt_tokens": comp.prompt_tokens,
                      "completion_tokens": comp.completion_tokens, "cached_tokens": comp.cached_tokens, "ms": ms})
    return comp


def estimate_tokens(chars: int) -> int:
    return max(1, (chars + 3) // 4)


def usd(prompt_tokens: int, completion_tokens: int, cached_tokens: int = 0) -> float:
    p = PRICES
    return ((prompt_tokens - cached_tokens) * p["input"] + cached_tokens * p["cached"] + completion_tokens * p["output"]) / 1e6


@contextmanager
def stage(name: str, events: list | None = None):
    t = time.perf_counter()
    try:
        yield
    finally:
        ms = (time.perf_counter() - t) * 1000
        if events is not None:
            events.append({"stage": name, "ms": ms})