"""JEV 決策層：policy（門檻 + escalation）。

門檻統一放呢度，bench 同 live agent 共用。所有信心/分數低過門檻嘅決策
都設有 escalation path（fallback 返原裝 chat，或者行確定性替代）。
"""
from __future__ import annotations

# ---- 決策信心門檻（confidence ∈ [0,1]）---------------------------------------
TOOL_CONF_MIN = 0.5         # 揀工具：低過 → fallback 原裝 chat tool-call
SENT_CONF_MIN = 0.4         # 情緒 label：低過 → fallback chat classifier
CONT_CONF_MIN = 0.5         # noUL 續步判斷

# ---- 分數門檻（0..levels-1 分級） -------------------------------------------
RAG_KEEP_FLOOR = 0.50       # RAG doc gate：絕對底線（防止 pool 全低分時過度裁剪）
RAG_KEEP_RATIO = 0.60       # RAG doc gate：相對 pool 最高分嘅比例（對抗 0-3 judge scale drift）
MEM_GATE_MIN = 2.0          # 記憶 relevance score ≥ 先餵去 answer call
SENT_LEVELS = 3             # negative=0 / neutral=1 / positive=2

# ---- tier-0 確定式層（jeV3：0ms / 0 tokens / 0 call）----------------------
T0_RRF_ABS = 1e-9           # RRF gate 絕對下限（淨係排除技術性 0，唔係 0-3 嘅 0.50）
T0_RRF_RATIO = 0.60         # RRF gate：相對 pool 最高分嘅比例（scale-free，同 RAG_KEEP_RATIO 同一精神）
T0_MEM_MARKER_DROP = True   # 私隱 marker 硬規則（regex，0ms）——jeV3 mem gate 前置
NOUL_STOP_ALWAYS_HONORED = True  # jeV3 noUL：System One 答 STOP 一律 honor，唔 escalation 去 chat

DEFAULT_LEVELS = 4          # score() 預設分級數


def gate_keep(score_value: float | None, threshold: float) -> bool:
    """評分過唔過門檻。None（decision 失敗）→ escalate（唔當 keep）。"""
    return score_value is not None and float(score_value) >= threshold


def should_fallback(confidence: float | None, threshold: float) -> bool:
    """confidence 過唔過到信心門檻（Failed / too low → fallback）。"""
    return confidence is None or float(confidence) < threshold