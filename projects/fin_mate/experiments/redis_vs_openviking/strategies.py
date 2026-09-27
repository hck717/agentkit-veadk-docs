"""E3 RAG pipes（backend-agnostic）：hybrid / advanced / hyde_rrf。
從 rag_bench.strategies 搬運，改為用 `kb.search` + `kb.grep` 統一接口，
支援 OpenVikingKB 同 RedisKB 兩個 backend——pipeline 完全一樣。
"""
from __future__ import annotations

import re
import time

from experiments.rag_bench.strategies import (
    GATE, RRF_K, MAX_CTX, STOP, STRATS, TXT, OVERVIEW,
    _toks, _terms, _pref, _dedupe, _doc, _score, _ans_msgs,
)

# ── backend-agnostic helpers ────────────────────────────────────────────────


def _dense(kb, q: str, k: int):
    """Backend-agnostic dense search → entries with .content + .metadata['uri']."""
    return kb.search(q, top_k=k)


def _sparse(kb, pattern: str, limit: int = 64):
    """Backend-agnostic sparse grep → [{"uri","content"}]."""
    return kb.grep(pattern, limit=limit, uri_prefix=TXT)


def _rrf(lists, k=RRF_K):
    scores = {}
    for ranked in lists:
        for rank, u in enumerate(ranked):
            key = _pref(u)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
    return [u for u, _ in sorted(scores.items(), key=lambda x: -x[1])]


def _emit(events, strat, eid, cat, stage, ms=None, tokens=None, score=None, uris=None, detail=None):
    events.append({"strategy": strat, "eid": eid, "category": cat, "stage": stage,
                   "ts": time.strftime("%Y-%m-%dT%H:%M:%S.%f"), "ms": ms,
                   "tokens": tokens or {}, "score": score, "uris": uris or [], "detail": detail or {}})


def _ctx(entries, doc_uris, extra=None):
    lines = []
    for i, e in enumerate(entries, 1):
        u = (e.metadata or {}).get("uri") or ""
        lines.append(f"[{i}] <{_doc(u, doc_uris)}>\n{(e.content or '')[:MAX_CTX].strip()}")
    for i, (u, snip) in enumerate((extra or {}).items(), len(lines) + 1):
        # Truncate grep content to MAX_CTX to avoid blowing up prompt size
        lines.append(f"[{i}] <{_doc(u, doc_uris)} | grep>\n{str(snip)[:MAX_CTX].strip()}")
    return "\n".join(lines)


# ── hybrid (dense + sparse → RRF) ──────────────────────────────────────────

async def run_hybrid(q, eid, cat, doc_uris, *, trace, ark_complete, kb):
    strat, events = "hybrid", []
    t = time.perf_counter()
    entries = _dense(kb, q, STRATS[strat]["k"])
    grab = _sparse(kb, "|".join(_terms(q)))[:20]
    ms = (time.perf_counter() - t) * 1000
    merged = _dedupe(_rrf([[(e.metadata or {}).get("uri", "") for e in entries],
                           [g["uri"] for g in grab]], k=RRF_K))
    extra = {g["uri"]: g["content"][:MAX_CTX] for g in grab if _pref(g["uri"]) in merged}
    uris = [u for u in merged]
    _emit(events, strat, eid, cat, "retrieve", ms=ms, score=_score(entries), uris=uris,
          detail={"dense": len(entries), "grep": len(grab), "rrf_k": RRF_K})
    ctx = _ctx(entries, doc_uris, extra=extra)
    ans = await ark_complete(_ans_msgs(q, ctx), max_tokens=512, trace=trace)
    _emit(events, strat, eid, cat, "answer", ms=ans.ms,
          tokens={"prompt": ans.prompt_tokens, "completion": ans.completion_tokens,
                  "cached": ans.cached_tokens})
    return dict(strategy=strat, eid=eid, category=cat, uris=uris, answer=ans.text, events=events)


# ── advanced (dense + sparse → gate) ────────────────────────────────────────

async def run_advanced(q, eid, cat, doc_uris, *, trace, ark_complete, kb):
    strat, events = "advanced", []
    t = time.perf_counter()
    entries = _dense(kb, q, STRATS[strat]["k"])
    grab = [g for g in _sparse(kb, "|".join(_terms(q)))][:20]
    ms = (time.perf_counter() - t) * 1000
    extra = {g["uri"]: g["content"][:MAX_CTX] for g in grab}
    uris = _dedupe([(e.metadata or {}).get("uri", "") for e in entries] + [g["uri"] for g in grab])
    sc = _score(entries)
    _emit(events, strat, eid, cat, "retrieve", ms=ms, score=sc, uris=uris,
          detail={"channel": "find+grep", "grep_hits": len(grab)})
    passed = sc >= GATE or bool(grab)
    _emit(events, strat, eid, cat, "gate", score=1.0 if passed else 0.0, detail={"threshold": GATE})
    ctx = _ctx(entries, doc_uris, extra=extra) if passed else ""
    ans = await ark_complete(_ans_msgs(q, ctx, passed), max_tokens=512, trace=trace)
    _emit(events, strat, eid, cat, "answer", ms=ans.ms,
          tokens={"prompt": ans.prompt_tokens, "completion": ans.completion_tokens,
                  "cached": ans.cached_tokens})
    return dict(strategy=strat, eid=eid, category=cat, uris=uris if passed else [],
                answer=ans.text, events=events)


# ── hyde_rrf (HyDE + 3-channel RRF) ────────────────────────────────────────

async def _hyde(q, trace, ark_complete):
    c = await ark_complete(
        [{"role": "system",
          "content": "你是 FIN-MATE 金融研究助手。針對問題寫一段「假設報告係點答呢條問題」嘅第 3 身研究段落"
                     "（60–120 tokens）——仿 MSFT 研報語氣，含數字同公司/業務名詞。唔好加來源標註或者【KB:】。"},
         {"role": "user", "content": q}],
        max_tokens=140, trace=trace)
    return c


async def run_hyde_rrf(q, eid, cat, doc_uris, *, trace, ark_complete, kb):
    strat, events = "hyde_rrf", []
    t = time.perf_counter()
    hyde = await _hyde(q, trace, ark_complete)
    hyp = (hyde.text or "").strip() or q
    _emit(events, strat, eid, cat, "hyde", ms=(time.perf_counter() - t) * 1000,
          tokens={"prompt": hyde.prompt_tokens, "completion": hyde.completion_tokens,
                  "cached": hyde.cached_tokens},
          detail={"hyp_len": len(hyp), "fallback": hyp == q})
    t = time.perf_counter()
    entries_q = _dense(kb, q, STRATS[strat]["k"])
    entries_h = _dense(kb, hyp, STRATS[strat]["k"])
    grab = _sparse(kb, "|".join(_terms(q)))[:20]
    ms = (time.perf_counter() - t) * 1000
    q_uris = [(e.metadata or {}).get("uri", "") for e in entries_q]
    h_uris = [(e.metadata or {}).get("uri", "") for e in entries_h]
    grep_uris = [g["uri"] for g in grab]
    merged = _rrf([q_uris, h_uris, grep_uris], k=RRF_K)
    merged = _dedupe(merged)
    extra = {g["uri"]: g.get("content", "")[:MAX_CTX] for g in grab if _pref(g["uri"]) in merged}
    uris = [u for u in merged]
    _emit(events, strat, eid, cat, "retrieve", ms=ms, score=_score(entries_q), uris=uris,
          detail={"dense_q": len(entries_q), "dense_h": len(entries_h), "grep": len(grab),
                  "rrf_k": RRF_K, "hyp_len": len(hyp)})
    top_prefs = merged[:5]
    all_entries = {((e.metadata or {}).get("uri", "")): e for e in entries_q}
    all_entries.update({((e.metadata or {}).get("uri", "")): e for e in entries_h})
    best = {}
    for u, e in all_entries.items():
        p = _pref(u)
        if p in top_prefs:
            sc = float((e.metadata or {}).get("score") or 0.0)
            if p not in best or sc > float((best[p].metadata or {}).get("score") or 0.0):
                best[p] = e
    ctx = _ctx(list(best.values()), doc_uris, extra=extra)
    ans = await ark_complete(_ans_msgs(q, ctx), max_tokens=512, trace=trace)
    _emit(events, strat, eid, cat, "answer", ms=ans.ms,
          tokens={"prompt": ans.prompt_tokens, "completion": ans.completion_tokens,
                  "cached": ans.cached_tokens})
    return dict(strategy=strat, eid=eid, category=cat, uris=uris, answer=ans.text, events=events,
                extra={"hyde": hyp})


# ── dispatch ────────────────────────────────────────────────────────────────

PIPES = {"hybrid": run_hybrid, "advanced": run_advanced, "hyde_rrf": run_hyde_rrf}
