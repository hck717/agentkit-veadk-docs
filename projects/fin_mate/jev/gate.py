"""JEV 決策層：DecisionGate —— system one 決策 @ 決策點。

每粒決策點 = 一串 question specs（choice / score / noul）+ policy（門檻 / escalation）。
gate 負責：
  1. 砌 state（唔好全文入 prompt）
  2. 開 System One 決策（`lib.jev_client`，1–3 token + logprobs）
  3. 套 policy：低 confidence/低分 → escalate（fallback 原裝 chat 或確定性 path）
  4. 出 `JevDecision`（可以變成 event / 入 ledger）

都係 pure async、無 side effect；bench runner 同 live agent 都係咁用。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from experiments.jev_bench.lib import jev_client

from . import policy
from .ledger import Ledger


@dataclass
class JevDecision:
    kind: str                       # choice | score | noul
    gate: str                       # gate 名（tool_choice / doc_gate / mem_gate / sent / cont）
    choice: str | None = None       # choice gate：揀中 option id
    score: float | None = None      # score gate：0..levels-1
    noul: bool | None = None        # noul gate
    confidence: float = 0.0
    probabilities: dict = field(default_factory=dict)
    escalated: bool = False         # 低 conf / failed → 行咗 escalation
    ms: float = 0.0
    tokens: dict = field(default_factory=dict)
    prompt: str = ""


async def _maybe_resolve_model():
    if not jev_client._RESOLVED:
        await jev_client.resolve_decision_model()


async def decide_choice(state: str, question: str, options: list[dict], *,
                        gate: str, conf_min: float = policy.TOOL_CONF_MIN) -> JevDecision:
    """choice gate：揀一個 option。低 confidence / failed → escalated（caller 行 fallback）。"""
    await _maybe_resolve_model()
    d = await jev_client.choice(state, question, options)
    esc = d.failed or policy.should_fallback(d.confidence, conf_min)
    return JevDecision(kind="choice", gate=gate, choice=d.choice, confidence=d.confidence,
                       probabilities=d.probabilities, escalated=esc, ms=d.ms,
                       tokens=dict(d.tokens), prompt=d.prompt)


async def decide_score(state: str, question: str, rubric: list[str],
                       *, gate: str, levels: int = 4,
                       keep_min: float | None = None) -> JevDecision:
    """score gate：0..levels-1 分。keep_min 唔係 None 時 escalated = keep(e) false。"""
    await _maybe_resolve_model()
    d = await jev_client.score(state, question, rubric, levels=levels)
    keep = policy.gate_keep(d.score, keep_min) if keep_min is not None else True
    esc = d.failed or (keep_min is not None and not keep)
    return JevDecision(kind="score", gate=gate, score=d.score, choice=d.choice,
                       confidence=d.confidence, probabilities=d.probabilities,
                       escalated=esc, ms=d.ms, tokens=dict(d.tokens), prompt=d.prompt)


async def decide_noul(state: str, question: str, *, gate: str,
                      conf_min: float = policy.CONT_CONF_MIN,
                      asymmetric: bool = False) -> JevDecision:
    """noUL gate：仲有冇後續。低 confidence → escalated。

    `asymmetric=True`（jeV3）：System One 答 **STOP（noul=False）一律 honor**，唔睇 confidence
    ——因為「停止」係低風險、可以平價補救／檢查嘅動作，而「繼續」先係要成本嘅；
    所以只有 **YES（noul=True）** 先要過 conf_min（低 conf → escalated 去 chat 覆核）。
    呢個直接修正 js5_wf_02：System One 答啱 STOP（conf 0.025）但俾 chat 覆蓋 -> OVER。
    """
    await _maybe_resolve_model()
    d = await jev_client.noul(state, question)
    if d.failed:
        esc = True
    elif asymmetric:
        esc = bool(d.noul) and policy.should_fallback(d.confidence, conf_min)
    else:
        esc = policy.should_fallback(d.confidence, conf_min)
    return JevDecision(kind="noul", gate=gate, noul=d.noul, confidence=d.confidence,
                       probabilities=d.probabilities, escalated=esc, ms=d.ms,
                       tokens=dict(d.tokens), prompt=d.prompt)