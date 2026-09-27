"""JEV 決策層：per-decision ledger。

每粒 decision 記低 ms / prompt / completion / cached tokens + 換算 μ$，
讓 bench 可以做「原裝 vs JEV」嘅成本/延時對照（μ$ 精度避免 $0.0017 rounding 磨平）。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from experiments import _lib

U = 1e6  # USD -> μUSD


@dataclass
class Ledger:
    ms: float = 0.0
    prompt: int = 0
    completion: int = 0
    cached: int = 0
    n_calls: int = 0
    gates: dict = field(default_factory=dict)  # gate name -> count

    def add(self, *, ms=0.0, tokens=None, gate=None):
        self.ms += ms
        t = tokens or {}
        self.prompt += t.get("prompt", 0)
        self.completion += t.get("completion", 0)
        self.cached += t.get("cached", 0)
        self.n_calls += 1
        if gate:
            self.gates[gate] = self.gates.get(gate, 0) + 1

    def add_d(self, d, gate=None):
        self.add(ms=d.ms, tokens=d.tokens, gate=gate)

    def add_resp(self, resp, gate=None):
        self.add(ms=resp.ms,
                 tokens={"prompt": resp.prompt_tokens, "completion": resp.completion_tokens,
                         "cached": resp.cached_tokens},
                 gate=gate)

    def usd(self) -> float:
        return _lib.usd(self.prompt, self.completion, self.cached)

    def musd(self) -> float:
        return self.usd() * U


def now_ms() -> float:
    return time.perf_counter() * 1000