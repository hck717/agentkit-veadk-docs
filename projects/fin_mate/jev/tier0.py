"""JEV tier-0 層：0ms / 0 tokens / 0 LLM call 嘅確定式決策（jeV3 bench arm + live 共用）。

jeV3 嘅核心：凡係「deterministic 就夠」嘅決策點，唔好叫 1-token LLM（嗰種都仲係一個
~500ms serial RTT）。tier-0 全部係 pure function，無 side effect、無 network：

  route_tool(text)        -> (tool_label, args) | None   規則路由 + 確定式 args
  doc_gate_rrf(...)       -> (labels, kept, rows, lowscore)  用 _hybrid 已有 RRF 分做 pool-relative
  privacy_flagged(text)   -> bool                         私隱 marker 硬規則（eg「總倉位」）
"""
from __future__ import annotations

import re

from . import policy
from . import actions

# ── route_tool：規則路由（System One 揀 tool 呢一層都可以係 determinant）───────
_SEARCH_VERB = re.compile(r"(上網搜|搜尋|搜索|搜一搜|查吓|查一下|上網查|最新報導|最新報道|查報道)", re.IGNORECASE)
_CALC_HINT = re.compile(r"(calc|計算|計數|計到|計下|計吓|計返|target|目標價|目標|%)", re.IGNORECASE)
_EXPR_OP = re.compile(r"[0-9]\s*[+\-*/^]\s*[0-9]")


def _calcish(t: str) -> bool:
    """calc 提示：關鍵字 / 百分比 / 帶運算符嘅算式（例如「計（42*17+9)/3」）。"""
    return bool(_CALC_HINT.search(t) or _EXPR_OP.search(t))


def route_tool(text: str) -> tuple[str, dict] | None:
    """rule 路由：`(tool_label, args)` 或 `None`（= 填唔到 → caller escalate chat）。

    次序 = 由最 specific 到最 generic：
      1. `.csv` path              -> read_news_file
      2. URL                      -> link_reader
      3. calc 提示詞（% / target / 計…）-> calc
      4. 搜尋動詞                  -> web_search（query = 原句）
      5. ticker（\$?[A-Z]{1,5}）   -> fetch_news
    args 一律重用 `actions.fill_args`（同一份確定式填充器）。
    """
    t = (text or "").strip()
    if not t:
        return None
    if actions._CSV_PATH.search(t):
        return ("read_news_file", actions.fill_args("read_news_file", t))
    if actions._URL.search(t):
        return ("link_reader", actions.fill_args("link_reader", t))
    if _calcish(t) and actions.fill_args("calc", t) is not None:
        return ("calc", actions.fill_args("calc", t))
    if _SEARCH_VERB.search(t):
        return ("web_search", actions.fill_args("web_search", t))
    if actions._TICKER.search(t):
        return ("fetch_news", actions.fill_args("fetch_news", t))
    return None


# ── privacy marker 硬規則（0ms 守衛）─────────────────────────────────────────
def privacy_flagged(content: str | None, markers: str | list[str] | None) -> bool:
    """content 入面有冇任何私隱 marker（例如「總倉位」）。確定式、無 LLM。"""
    if not content or not markers:
        return False
    mks = [markers] if isinstance(markers, str) else list(markers or [])
    return any((mk and str(mk) in content) for mk in mks)


# ── doc_gate_rrf：用 _hybrid 已有嘅 RRF 分做 pool-relative 門檻（0ms）─────────
def doc_gate_rrf(best: dict, cands: list[tuple[str, str]], rrf_scores: dict,
                 gold_tags: dict | None = None, *,
                 ratio: float = policy.T0_RRF_RATIO,
                 abs_floor: float = policy.T0_RRF_ABS):
    """keep = rrf_score ≥ max(abs_floor, ratio × pool_max)。

    RRF 係 deterministic（同一 query + 同一 corpus = 同一分），冇 run-to-run judge drift；
    noise doc 唔喺检索結果入面 -> score 0 -> 必剪。
    好彩全池都低分 -> 照留 top-1 兼 `lowscore=True`（answer 層知道「KB 弱」，答無資料好過迫）。
    回傳 (labels, kept[(lab,snippet)], rows, lowscore)。
    """
    scores = {lab: float(rrf_scores.get(lab, 0.0)) for lab, _ in cands}
    if not scores:
        return [], [], [], True
    pool_max = max(scores.values())
    rel_floor = max(abs_floor, ratio * pool_max)
    rows, kept = [], []
    for lab, snippet in cands:
        s = scores[lab]
        keep = s >= rel_floor
        rows.append({"doc": lab, "score": round(s, 6),
                     "gold": (gold_tags or {}).get(lab, "noise"),
                     "keep": keep, "floor": round(rel_floor, 6)})
        if keep:
            kept.append((lab, snippet))
    lowscore = False
    if not kept:
        lowscore = True
        top = max(cands, key=lambda x: scores.get(x[0], 0.0))
        snippet = top[1] or (best.get(top[0], ("", None))[0])
        kept = [(top[0], snippet)]
        for r in rows:
            if r["doc"] == top[0]:
                r["keep"] = True
                r["lowscore_keep"] = True
    elif len(kept) == 1 and (gold_tags or {}).get(kept[0][0]) != "gold":
        # 淨係留到一條而佢又唔係 gold -> 語料偏弱（trap 或 gate 錯），flag 俾 answer 層
        lowscore = True
        for r in rows:
            if r["doc"] == kept[0][0]:
                r["lowscore_keep"] = True
    return [lab for lab, _ in kept], kept, rows, lowscore