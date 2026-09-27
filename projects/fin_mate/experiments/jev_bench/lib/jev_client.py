"""Jev-style「System One」decide client：經 Ark ChatCompletions 做 1-token 選擇決策。

跟 daseinlabs/open-jev / TypeSafe System One 嘅合約（`state` + 帶 type 嘅 `questions` → 帶
probability/confidence 嘅 structured answers），但 backend 唔係本地 Gemma，而係 ByteDance
seed-1.6-mini（auto-detect；fallback seed-1-6-flash-250715）經 Ark `/chat/completions`：
`logprobs=true, top_logprobs=20, max_tokens=1` —— 淨係讀第一個 token 位置嘅 top-logprobs 去計每個
option 嘅 softmax 機率，**唔使 decode 成段 output**（~1 output token per decision）。

三種 question type：
  choice(state, question, options)   -> {choice, probabilities, confidence}
  score(state, question, rubric, n)  -> {score: probability-weighted mean of 0..n-1, confidence}
  noul(state, question)              -> {noul: P(yes)>=0.5, confidence}

每個 decision 回傳 tokens/ms（照 `_lib.usd` 計價），方便 bench 落 logs。
"""
from __future__ import annotations

import asyncio
import math
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments import _lib  # noqa: E402

# seed-1.6 mini 候選 id：env override 優先，再逐個 probe（404/失敗 -> 下一個），
# 全部唔得就 fallback flash。真實存在嘅 mini id 唔喺公開 model list，所以要 probe。
MINI_CANDIDATES = [
    "seed-1-6-mini",
    "seed-1-6-mini-250615",
    "seed-1-6-mini-250715",
    "seed-1-6-mini-260215",
    "seed-1-6-mini-260428",
    "seed-1-6-mini-260915",
]
FALLBACK_MODEL = "seed-1-6-flash-250715"

FLOOR_LOGPROB = -24.0  # 唔喺 top-logprobs 嘅 option -> 用呢個下限（≈1e-10）

# 實測（2026-09）：seed-1-6-* 全部係 reasoning model，chat/completions 直接開 logprobs 會 400；
# 要連 `thinking: {"type": "disabled"}` 先會返 logprobs。另外模型第一粒 token 例牌係空白，
# 真正答案喺第二粒開始——所以 `_top_tokens` 會 skip 空白開頭嘅 position。
_EXTRA = {"thinking": {"type": "disabled"}}
MAX_DECISION_TOKENS = 3

_RESOLVED: list = []  # [model_id, used_fallback, lp_ok]


@dataclass
class JevAnswer:
    qtype: str
    model: str
    choice: str | None = None          # 揀中嘅 option id
    probabilities: dict = field(default_factory=dict)   # option id -> prob
    confidence: float = 0.0            # 1 - H/H_max（logit distribution 層）
    score: float | None = None         # score 用：proba-weighted mean
    noul: bool | None = None           # noul 用：P(yes) >= 0.5
    entropy: float = 0.0
    tokens: dict = field(default_factory=dict)
    ms: float = 0.0
    prompt: str = ""
    failed: bool = False
    error: str = ""


def load_env() -> None:
    _lib.load_env()


def _client():
    from volcenginesdkarkruntime import AsyncArk

    return AsyncArk(base_url=os.environ["MODEL_AGENT_API_BASE"], api_key=os.environ["MODEL_AGENT_API_KEY"])


async def _query(client, model: str, msgs: list[dict]) -> tuple:
    """一次 decision 查詢（thinking off + logprobs）；回傳 (raw, ms)。"""
    t = time.perf_counter()
    raw = await client.chat.completions.create(
        model=model,
        messages=msgs,
        max_tokens=MAX_DECISION_TOKENS,
        temperature=0.0,
        logprobs=True,
        top_logprobs=20,
        **_EXTRA,
    )
    return raw, (time.perf_counter() - t) * 1000


def _top_tokens(raw) -> list:
    """揀第一個「非空白開頭」嘅 token position 嘅 top_logprobs -> [(token, logprob), ...]。

    seed-1-6 chat 開頭例牌出 `\\n\\n`（空白 token），max_tokens=1 會截到個空白而非答案；
    so 用 max_tokens=3 再 skip 空白 position，攞真正答題嗰粒。"""
    content = []
    try:
        lp = raw.choices[0].logprobs
        content = getattr(lp, "content", None) or []
    except Exception as ex:  # noqa: BLE001
        raise ValueError(f"logprobs parse fail: {ex}") from ex
    for slot in content:
        toks = [(t.token, float(t.logprob)) for t in (getattr(slot, "top_logprobs", None) or [])]
        if not toks:
            continue
        chosen = getattr(slot, "token", None)
        if chosen is not None and not any(t == chosen for t, _ in toks):
            toks.insert(0, (chosen, float(getattr(slot, "logprob", 0.0))))
        first_tok = toks[0][0]
        if first_tok and not first_tok.strip():
            continue  # 開頭空白 token → 下一個 position
        return toks
    return []


def _softmax_ids(option_ids: list[str], raw) -> dict:
    """option id（單 token）-> softmax prob。冇喺 top-N 就落 FLOOR。"""
    lp = dict(_top_tokens(raw))
    logits = []
    for oid in option_ids:
        logits.append(lp.get(oid, FLOOR_LOGPROB))
    m = max(logits)
    exps = [math.exp(x - m) for x in logits]
    s = sum(exps) or 1.0
    return {oid: e / s for oid, e in zip(option_ids, exps)}


def _confidence(probs: dict) -> float:
    n = len(probs)
    if n <= 1:
        return 1.0
    h = -sum(p * math.log(p) for p in probs.values() if p > 0)
    return max(0.0, 1.0 - h / math.log(n))


def _usage_tokens(raw) -> dict:
    u = getattr(raw, "usage", None)
    if u is None:
        return {"prompt": 0, "completion": 0, "cached": 0}
    cached = 0
    det = getattr(u, "prompt_tokens_details", None)
    if det is not None:
        cached = getattr(det, "cached_tokens", 0) or 0
    return {"prompt": getattr(u, "prompt_tokens", 0) or 0,
            "completion": getattr(u, "completion_tokens", 0) or 0,
            "cached": cached}


async def probe_model(model: str) -> bool:
    """model id 存唔存在（plain call，唔開 logprobs——reasoning model 開 logprobs 會 400）。"""
    _lib.load_env()
    try:
        client = _client()
        msgs = [{"role": "user", "content": "答一個字：ok"}]
        await client.chat.completions.create(model=model, messages=msgs, max_tokens=2,
                                             temperature=0.0, **_EXTRA)
        await client.close()
        return True
    except Exception:  # noqa: BLE001
        await client.close()
        return False


async def _lp_smoke(model: str) -> bool:
    """logprobs + thinking-off 開唔開到（seed-1-6-flash 都開到）。"""
    _lib.load_env()
    try:
        client = _client()
        raw, _ = await _query(client, model, [{"role": "user", "content": "答 Y 定 N：1+1=2？"}])
        await client.close()
        return bool(_top_tokens(raw))
    except Exception:  # noqa: BLE001
        await client.close()
        return False


async def resolve_decision_model() -> tuple[str, bool, bool]:
    """env `JEV_MODEL` 優先（要存在 + logprobs OK）；否則 probe MINI_CANDIDATES；
    全失敗 fallback seed-1-6-flash-250715。回傳 (model_id, used_fallback, lp_ok)。cached。"""
    if _RESOLVED:
        return tuple(_RESOLVED)
    _lib.load_env()
    env_model = os.environ.get("JEV_MODEL", "").strip()
    cands = ([env_model] if env_model else []) + [m for m in MINI_CANDIDATES if m != env_model]
    found = None
    for m in cands:
        exists = await probe_model(m)
        print(f"[jev] probe {m!r:30s} -> {'OK' if exists else 'n/a'}")
        if exists:
            found = m
            break
    if found is None:
        found = FALLBACK_MODEL
        used_fallback = True
    else:
        used_fallback = not found.startswith("seed-1-6-mini")
    ok = await _lp_smoke(found)
    _RESOLVED[:] = [found, used_fallback, ok]
    print(f"[jev] decision model = {found} (fallback={used_fallback}, logprobs={'OK' if ok else 'N/A'})")
    return found, used_fallback, ok


async def decide(msgs: list[dict], option_ids: list[str], *,
                 model: str | None = None, qtype: str = "choice",
                 noul_yes: str = "Y", noul_no: str = "N") -> JevAnswer:
    """Send System One decision。msgs = [system, user]；option_ids = 單 token 代號。"""
    mdl = model or (await resolve_decision_model())[0]
    ans = JevAnswer(qtype=qtype, model=mdl)
    ans.prompt = (msgs[1]["content"] if len(msgs) > 1 else "")[:200]
    try:
        client = _client()
        raw, ms = await _query(client, mdl, msgs)
        await client.close()
        ans.ms = ms
        ans.tokens = _usage_tokens(raw)
        probs = _softmax_ids(option_ids, raw)
        ans.probabilities = probs
        ans.entropy = -sum(p * math.log(p) for p in probs.values() if p > 0)
        ans.confidence = _confidence(probs)
        choice = max(probs, key=probs.get)
        ans.choice = choice
        if qtype == "score":
            levels = list(range(len(option_ids)))
            ans.score = sum(probs[oid] * lv for oid, lv in zip(option_ids, levels))
        elif qtype == "noul":
            ans.noul = probs.get(noul_yes, 0.0) >= 0.5
    except Exception as ex:  # noqa: BLE001
        ans.failed = True
        ans.error = str(ex)
    return ans


async def choice(state: str, question: str, options: list[dict], *,
                 model: str | None = None, sys_prompt: str | None = None) -> JevAnswer:
    """options: list[{"id": "C", "label": "calc", "desc": "..."}]。"""
    sys_p = sys_prompt or "你是 FIN-MATE 決策引擎（System One）。收到 state + 問題，只可以答一個選項代號（單個 token），唔好加解釋。"
    lines = [f"{i}. [{o['id']}] {o['label']}" + (f" — {o['desc']}" if o.get("desc") else "")
             for i, o in enumerate(options, 1)]
    user = f"state：\n{state}\n\n問題：{question}\n\n選項：\n" + "\n".join(lines) + "\n\n回答（只出代號）："
    return await decide([{"role": "system", "content": sys_p}, {"role": "user", "content": user}],
                        [o["id"] for o in options], model=model, qtype="choice")


async def score(state: str, question: str, rubric: list[str] | None = None, *,
                model: str | None = None, levels: int = 4) -> JevAnswer:
    """0..levels-1 分。rubric[i] = 分數 i 嘅定義。"""
    opts = [{"id": str(i), "label": f"{i} 分"} for i in range(levels)]
    sys_p = ("你是 FIN-MATE 評分引擎（System One）。收到 state + 問題，按 rubric 對 state 內容評分，"
             "只可以答一個數字代號（0-9，單個 token），唔好加解釋。")
    rub = "\n".join(f"- {i} 分：{rubric[i]}" for i in range(min(levels, len(rubric or []))))
    user = f"state：\n{state}\n\n問題：{question}\n" + (f"\nrubric：\n{rub}\n" if rub else "") + \
        "\n\n選項：" + "、".join(f"「{i}」({i} 分)" for i in range(levels)) + "\n\n回答（只出數字）："
    return await decide([{"role": "system", "content": sys_p}, {"role": "user", "content": user}],
                        [str(i) for i in range(levels)], model=model, qtype="score")


async def noul(state: str, question: str, *, model: str | None = None) -> JevAnswer:
    """yes/no 決策：noul = P(Y)>=0.5。"""
    sys_p = ("你是 FIN-MATE 完成判斷引擎（System One）。收到 state + 問題，判斷「係定唔係」，"
             "只可以答 Y 或 N（單個 token），唔好加解釋。")
    user = f"state：\n{state}\n\n問題：{question}\n\n選項：\n1. [Y] 係\n2. [N] 唔係\n\n回答（只出代號）："
    return await decide([{"role": "system", "content": sys_p}, {"role": "user", "content": user}],
                        ["Y", "N"], model=model, qtype="noul")


async def _smoke():
    _lib.load_env()
    mdl, fb, lp = await resolve_decision_model()
    a = await choice("user asked: 計 38-1", "下一步揀邊個工具？", [
        {"id": "C", "label": "calc", "desc": "計數"}, {"id": "N", "label": "news", "desc": "讀新聞"}], model=mdl)
    print("choice:", a.choice, a.probabilities, f"conf={a.confidence:.3f}", a.tokens, f"{a.ms:.0f}ms", "fallback", fb)
    s = await score("doc snippet: Azure grew 38% YoY", "呢段資料有冇講 Azure 增長？", [
        "無關", "擦邊", "部分相關", "直接答案"], model=mdl)
    print("score:", s.score, s.probabilities, f"conf={s.confidence:.3f}")
    n = await noul("已完成 calc", "仲有冇後續要做？", model=mdl)
    print("noul:", n.noul, n.probabilities, f"conf={n.confidence:.3f}")


if __name__ == "__main__":
    asyncio.run(_smoke())