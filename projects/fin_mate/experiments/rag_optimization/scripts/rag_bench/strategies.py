"""RAG 實驗室 pipe（D4/D5）。盡用 veadk/agentkit builtin RAG：`kb.search`（dense find + L2 hydrate）、
`LoadKnowledgebaseTool`（agentic，已退役）。自訂只有：sparse grep、RRF、LLM 控制、event log、HyDE。
現役 pipe：naive / advanced / hybrid / corrective / adaptive / hyde。agentic 由 run set 移除（結果保留喺 REPORT）。
每 stage 記 `runs/<strategy>/events.jsonl`；全 LLM/tool replay 由 run.py 落 `runs/<strategy>/<eid>/transcript.jsonl`。
"""
from __future__ import annotations

import asyncio
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments._lib import ark_complete, build_kb, estimate_tokens  # noqa: E402
from experiments.rag_bench.eval_set import OVERVIEW, TXT  # noqa: E402

GATE = 0.35          # advanced score gate（低過 → 當無料）
RRF_K = 60           # RRF 常數 k
MAX_CTX = 2000       # 注入每句 content 上限
STOP = set("the a an is are was were of to in on for and or but with from by at as it its this that these those "
           "what how why when where which who does do did has have had be been being not no yes mr ms corp company "
           "microsoft windows azure cloud".split())

STRATS = {
    "naive":     {"read_limit": 200, "k": 5,  "desc": "dense find top_k=5 + L2 hydrate（= prod baseline）"},
    "advanced":  {"read_limit": 2000, "k": 15, "desc": "dense find k=15 粗水化 + grep 擴 query + dedupe + score gate"},
    "hybrid":    {"read_limit": 200, "k": 15, "desc": "dense find k=15 + sparse grep terms -> RRF(k=60) 融合"},
    "corrective": {"read_limit": 1000, "k": 5, "desc": "find -> LLM self-check -> rewrite -> re-find -> 再差 skip 注入"},
    "adaptive":  {"read_limit": 200, "k": 5,  "desc": "LLM router 決定查唔查（trap/SKIP 就唔查）"},
    "hyde":      {"read_limit": 200, "k": 5,  "desc": "LLM 生成 hypothetical doc -> 用埋當 query dense find（HyDE，k=5）"},
    "hyde_rrf":  {"read_limit": 200, "k": 15, "desc": "HyDE hypothesis → 3-channel RRF(dense_q + dense_h + grep) → answer"},
}

_KB: dict[int, object] = {}


def _kb(read_limit: int):
    if read_limit not in _KB:
        _KB[read_limit] = build_kb(read_limit)
    return _KB[read_limit]


def _emit(events, strat, eid, cat, stage, ms=None, tokens=None, score=None, uris=None, detail=None):
    events.append({"strategy": strat, "eid": eid, "category": cat, "stage": stage,
                   "ts": time.strftime("%Y-%m-%dT%H:%M:%S.%f"), "ms": ms,
                   "tokens": tokens or {}, "score": score, "uris": uris or [], "detail": detail or {}})


def _toks(q):
    return [t for t in re.findall(r"[A-Za-z0-9]+(?:\.\d+)?", str(q)) if t.lower() not in STOP and len(t) >= 2]


def _terms(q, n=3):
    ts = _toks(q)
    ts.sort(key=lambda w: (w[0].isupper() or w[0][0].isdigit(), len(w)), reverse=True)
    return ts[:n] or _toks(q)[:1]


def _pref(u):
    if u.startswith(TXT):
        p = u[len(TXT):].split("/")
        return TXT + p[0] + "/" if p and p[0] else u
    if u.startswith(OVERVIEW):
        return OVERVIEW
    return u.split("/")[-1]


def _dedupe(uris):
    seen, out = set(), []
    for u in uris:
        if u and _pref(u) not in seen:
            seen.add(_pref(u))
            out.append(u)
    return out


def _doc(u, doc_uris):
    for f, pre in doc_uris.items():
        if u.startswith(pre):
            return f.rsplit(".", 1)[0][:44]
    return u.split("/")[-2] if "/" in u else u


def _dense(kb, q, k):
    """veadk builtin KnowledgeBase.search -> dense find + L2 hydrate（read_limit 粗/細）。"""
    return kb.search(q, top_k=k)


def _sparse(kb, pattern, limit=64):
    """OpenViking grep（sparse keyword channel，掃全套 doc subtree）。"""
    client = kb._backend._ensure_client()
    r = client.grep(uri=TXT, pattern=pattern, case_insensitive=True, node_limit=limit)
    matches = r.get("result", {}).get("matches", []) if isinstance(r, dict) else r
    return [{"uri": m["uri"], "content": m.get("content", "")} for m in matches]


def _rrf(lists, k=RRF_K):
    scores = {}
    for ranked in lists:
        for rank, u in enumerate(ranked):
            key = _pref(u)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
    return [u for u, _ in sorted(scores.items(), key=lambda x: -x[1])]


def _ctx(entries, doc_uris, extra=None):
    lines = []
    for i, e in enumerate(entries, 1):
        u = (e.metadata or {}).get("uri") or ""
        lines.append(f"[{i}] <{_doc(u, doc_uris)}>\n{(e.content or '')[:MAX_CTX].strip()}")
    for i, (u, snip) in enumerate((extra or {}).items(), len(lines) + 1):
        lines.append(f"[{i}] <{_doc(u, doc_uris)} | grep>\n{snip}".strip())
    return "\n".join(lines)


def _ans_msgs(q, ctx, include_ctx=True):
    base = "你是 FIN-MATE 金融研究助手。只用畀嘅資料答；資料無提及就答「KB 無資料」唔好作。"
    sys_prompt = base + ("每句 claim 後加 inline 標註【KB:檔案名】；結尾列「## 來源」完整 URI。\n\n資料：\n" + ctx
                         if include_ctx and ctx else "")
    return [{"role": "system", "content": sys_prompt}, {"role": "user", "content": q}]


async def _judge(q, ctx, trace):
    c = await ark_complete([{"role": "system", "content": "判斷以下資料夠唔夠答問題。只回一步：PASS=夠可答 / CORRECT=差少少但改 query 可成 / FAIL=無關或唔夠"},
                            {"role": "user", "content": f"問題: {q}\n資料:\n{ctx}"}], max_tokens=12, trace=trace)
    d = (c.text or "").strip().upper()
    return ("PASS" if d.startswith("PASS") else "CORRECT" if d.startswith("CORRECT") else "FAIL"), d


async def _rewrite(q, trace):
    c = await ark_complete([{"role": "system", "content": "寫一條更精準嘅知識庫查詢（一句）。"},
                            {"role": "user", "content": f"問題: {q}"}], max_tokens=80, trace=trace)
    return (c.text or "").strip() or q


async def _router(q, trace):
    c = await ark_complete([{"role": "system", "content": "只回一步：SEARCH=要查知識庫 / SKIP=唔使查（閒談或資料庫明顯無）"},
                            {"role": "user", "content": f"問題: {q}"}], max_tokens=8, trace=trace)
    return (c.text or "").strip().upper().startswith("SEARCH")


def _score(entries):
    vals = [float((e.metadata or {}).get("score") or 0.0) for e in entries]
    return max(vals) if vals else 0.0


async def run_naive(q, eid, cat, doc_uris, *, trace):
    strat, events = "naive", []
    kb = _kb(STRATS[strat]["read_limit"])
    t = time.perf_counter()
    entries = _dense(kb, q, STRATS[strat]["k"])
    ms = (time.perf_counter() - t) * 1000
    uris = _dedupe([(e.metadata or {}).get("uri", "") for e in entries])
    _emit(events, strat, eid, cat, "retrieve", ms=ms, score=_score(entries), uris=uris, detail={"channel": "find"})
    ans = await ark_complete(_ans_msgs(q, _ctx(entries, doc_uris)), max_tokens=512, trace=trace)
    _emit(events, strat, eid, cat, "answer", ms=ans.ms,
          tokens={"prompt": ans.prompt_tokens, "completion": ans.completion_tokens, "cached": ans.cached_tokens})
    return dict(strategy=strat, eid=eid, category=cat, uris=uris, answer=ans.text, events=events)


async def run_advanced(q, eid, cat, doc_uris, *, trace):
    strat, events = "advanced", []
    kb = _kb(STRATS[strat]["read_limit"])
    t = time.perf_counter()
    entries = _dense(kb, q, STRATS[strat]["k"])
    grab = [g for g in _sparse(kb, "|".join(_terms(q)))][:20]
    ms = (time.perf_counter() - t) * 1000
    extra = {g["uri"]: g["content"] for g in grab}
    uris = _dedupe([(e.metadata or {}).get("uri", "") for e in entries] + [g["uri"] for g in grab])
    sc = _score(entries)
    _emit(events, strat, eid, cat, "retrieve", ms=ms, score=sc, uris=uris, detail={"channel": "find+grep", "grep_hits": len(grab)})
    passed = sc >= GATE or bool(grab)
    _emit(events, strat, eid, cat, "gate", score=1.0 if passed else 0.0, detail={"threshold": GATE})
    ctx = _ctx(entries, doc_uris, extra=extra) if passed else ""
    ans = await ark_complete(_ans_msgs(q, ctx, passed), max_tokens=512, trace=trace)
    _emit(events, strat, eid, cat, "answer", ms=ans.ms,
          tokens={"prompt": ans.prompt_tokens, "completion": ans.completion_tokens, "cached": ans.cached_tokens})
    return dict(strategy=strat, eid=eid, category=cat, uris=uris if passed else [], answer=ans.text, events=events)


async def run_hybrid(q, eid, cat, doc_uris, *, trace):
    strat, events = "hybrid", []
    kb = _kb(STRATS[strat]["read_limit"])
    t = time.perf_counter()
    entries = _dense(kb, q, STRATS[strat]["k"])
    grab = _sparse(kb, "|".join(_terms(q)))[:20]
    ms = (time.perf_counter() - t) * 1000
    merged = _dedupe(_rrf([[(e.metadata or {}).get("uri", "") for e in entries], [g["uri"] for g in grab]], k=RRF_K))
    extra = {g["uri"]: g["content"] for g in grab if _pref(g["uri"]) in merged}
    uris = [u for u in merged]
    _emit(events, strat, eid, cat, "retrieve", ms=ms, score=_score(entries), uris=uris,
          detail={"dense": len(entries), "grep": len(grab), "rrf_k": RRF_K})
    ctx = _ctx(entries, doc_uris, extra=extra)
    ans = await ark_complete(_ans_msgs(q, ctx), max_tokens=512, trace=trace)
    _emit(events, strat, eid, cat, "answer", ms=ans.ms,
          tokens={"prompt": ans.prompt_tokens, "completion": ans.completion_tokens, "cached": ans.cached_tokens})
    return dict(strategy=strat, eid=eid, category=cat, uris=uris, answer=ans.text, events=events)


async def run_corrective(q, eid, cat, doc_uris, *, trace):
    strat, events = "corrective", []
    kb = _kb(STRATS[strat]["read_limit"])
    t = time.perf_counter()
    entries = _dense(kb, q, STRATS[strat]["k"])
    ms = (time.perf_counter() - t) * 1000
    uris = _dedupe([(e.metadata or {}).get("uri", "") for e in entries])
    ctx = _ctx(entries, doc_uris)
    _emit(events, strat, eid, cat, "retrieve", ms=ms, score=_score(entries), uris=uris, detail={"channel": "find"})
    decision, raw = await _judge(q, ctx, trace)
    _emit(events, strat, eid, cat, "judge", score=1.0 if decision == "PASS" else 0.0, detail={"decision": raw})
    inject, retried = True, 0
    if decision != "PASS":
        q2 = await _rewrite(q, trace)
        _emit(events, strat, eid, cat, "rewrite", detail={"q2": q2})
        retried = 1
        t = time.perf_counter()
        entries2 = _dense(kb, q2, STRATS[strat]["k"])
        _emit(events, strat, eid, cat, "retry", ms=(time.perf_counter() - t) * 1000,
              score=_score(entries2), uris=_dedupe([(e.metadata or {}).get("uri", "") for e in entries2]))
        decision2, raw2 = await _judge(q, _ctx(entries2, doc_uris), trace)
        _emit(events, strat, eid, cat, "judge2", score=1.0 if decision2 == "PASS" else 0.0, detail={"decision": raw2})
        if decision2 == "PASS":
            entries = entries2
        else:
            inject = False
            _emit(events, strat, eid, cat, "gate", score=0.0, detail={"skip_inject": True})
    ans = await ark_complete(_ans_msgs(q, _ctx(entries, doc_uris), inject), max_tokens=512, trace=trace)
    _emit(events, strat, eid, cat, "answer", ms=ans.ms,
          tokens={"prompt": ans.prompt_tokens, "completion": ans.completion_tokens, "cached": ans.cached_tokens},
          detail={"retry_count": retried, "injected": inject})
    return dict(strategy=strat, eid=eid, category=cat, uris=uris if inject else [], answer=ans.text,
                events=events, extra={"retried": retried, "injected": inject})


async def run_adaptive(q, eid, cat, doc_uris, *, trace):
    strat, events = "adaptive", []
    t = time.perf_counter()
    should = await _router(q, trace)
    _emit(events, strat, eid, cat, "router", ms=(time.perf_counter() - t) * 1000,
          score=1.0 if should else 0.0, detail={"decision": "SEARCH" if should else "SKIP"})
    uris, ctx, inject = [], "", False
    if should:
        kb = _kb(STRATS[strat]["read_limit"])
        t = time.perf_counter()
        entries = _dense(kb, q, STRATS[strat]["k"])
        _emit(events, strat, eid, cat, "retrieve", ms=(time.perf_counter() - t) * 1000,
              score=_score(entries), uris=_dedupe([(e.metadata or {}).get("uri", "") for e in entries]))
        uris = _dedupe([(e.metadata or {}).get("uri", "") for e in entries])
        ctx, inject = _ctx(entries, doc_uris), True
    ans = await ark_complete(_ans_msgs(q, ctx, inject), max_tokens=512, trace=trace)
    _emit(events, strat, eid, cat, "answer", ms=ans.ms,
          tokens={"prompt": ans.prompt_tokens, "completion": ans.completion_tokens, "cached": ans.cached_tokens},
          detail={"searched": should})
    return dict(strategy=strat, eid=eid, category=cat, uris=uris, answer=ans.text, events=events,
                extra={"searched": should})


async def _hyde(q, trace):
    c = await ark_complete([{"role": "system", "content": "你是 FIN-MATE 金融研究助手。針對問題寫一段「假設報告係點答呢條問題」嘅第 3 身研究段落（60–120 tokens）——仿 MSFT 研報語氣，含數字同公司/業務名詞。唔好加來源標註或者【KB:】。"},
                            {"role": "user", "content": q}], max_tokens=140, trace=trace)
    return c


async def run_hyde(q, eid, cat, doc_uris, *, trace):
    strat, events = "hyde", []
    t = time.perf_counter()
    hyde = await _hyde(q, trace)
    hyp = (hyde.text or "").strip() or q
    _emit(events, strat, eid, cat, "hyde", ms=(time.perf_counter() - t) * 1000,
          tokens={"prompt": hyde.prompt_tokens, "completion": hyde.completion_tokens, "cached": hyde.cached_tokens},
          detail={"hyp_len": len(hyp), "fallback": hyp == q})
    kb = _kb(STRATS[strat]["read_limit"])
    t = time.perf_counter()
    entries = _dense(kb, hyp, STRATS[strat]["k"])
    ms = (time.perf_counter() - t) * 1000
    uris = _dedupe([(e.metadata or {}).get("uri", "") for e in entries])
    _emit(events, strat, eid, cat, "retrieve", ms=ms, score=_score(entries), uris=uris,
          detail={"channel": "find(hyde_query)"})
    ans = await ark_complete(_ans_msgs(q, _ctx(entries, doc_uris)), max_tokens=512, trace=trace)
    _emit(events, strat, eid, cat, "answer", ms=ans.ms,
          tokens={"prompt": ans.prompt_tokens, "completion": ans.completion_tokens, "cached": ans.cached_tokens})
    return dict(strategy=strat, eid=eid, category=cat, uris=uris, answer=ans.text, events=events,
                extra={"hyde": hyp})


async def run_hyde_rrf(q, eid, cat, doc_uris, *, trace):
    """HyDE + 3-channel RRF：用 h 做 dense + grep，同 q 嘅 dense 合併——融合.hyde 召回 + hybrid rank。"""
    strat, events = "hyde_rrf", []
    t = time.perf_counter()
    hyde = await _hyde(q, trace)
    hyp = (hyde.text or "").strip() or q
    _emit(events, strat, eid, cat, "hyde", ms=(time.perf_counter() - t) * 1000,
          tokens={"prompt": hyde.prompt_tokens, "completion": hyde.completion_tokens, "cached": hyde.cached_tokens},
          detail={"hyp_len": len(hyp), "fallback": hyp == q})
    kb = _kb(STRATS[strat]["read_limit"])
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
    extra = {g["uri"]: g.get("content", "") for g in grab if _pref(g["uri"]) in merged}
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
          tokens={"prompt": ans.prompt_tokens, "completion": ans.completion_tokens, "cached": ans.cached_tokens})
    return dict(strategy=strat, eid=eid, category=cat, uris=uris, answer=ans.text, events=events,
                extra={"hyde": hyp})


_AGENT_INSTR = (
    "你是 FIN-MATE 金融研究 RAG 實驗 agent。規則："
    "（1）用 load_knowledgebase 查資料答，最多查 2 次；計數用 calc。"
    "（2）每句 claim 即刻加 inline 標註【KB:檔案名】（由資料 URI 度睇返檔案名）或者【CALC】。"
    "（3）結尾列「## 來源」完整 URI。"
    "（4）KB 查唔到就答「KB 無資料」，唔好靠估或作。完成就答，唔好重複查。"
)


# ─── agentic 已退役（2026-09-08）：唔再跑、唔再入 STRATS/dispatch；以下 functions 留作記錄 ───


def _build_agent(kb):
    from veadk import Agent
    import agent_build
    tools = []
    try:
        from tools.calc import calc
        tools.append(calc)
    except Exception:
        pass
    return Agent(name="rag_bench", description="RAG 實驗 agent", instruction=_AGENT_INSTR, tools=tools,
                 knowledgebase=kb, model_name=[agent_build.MODEL_PRIMARY],
                 tracers=[], auto_save_session=False)  # tracers 唔加：veadk OTel + litellm 相撞會甩 threadpool


def _ov_snapshot():
    import json as _json
    import os
    import urllib.request
    base = os.environ.get("DATABASE_OPENVIKING_URL", "http://localhost:1933")
    key = os.environ.get("DATABASE_OPENVIKING_API_KEY", "")
    out = {}
    for name, path in (("retrieval", "/api/v1/observer/retrieval"), ("vectors", "/api/v1/debug/vector/count")):
        try:
            req = urllib.request.Request(base + path, headers={"X-API-Key": key})
            data = _json.load(urllib.request.urlopen(req, timeout=10))
            out[name] = data
        except Exception as e:
            out[name] = {"error": str(e)}
    return out


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _cite(transcript, answer):
    """citation verifier：markers 對返 agent 實質用過嘅 source（load_knowledgebase 返嘅 URI / calc）。"""
    kb_obs, kb_raw, calc_called = set(), [], False
    for td in transcript:
        for fc in td.get("calls", []):
            if (fc.get("name") or "").lower() == "calc":
                calc_called = True
        for fr in td.get("responses", []):
            out = str(fr.get("response", ""))
            raw = re.findall(r"viking://resources/fin_kb/[^\s\"']+", out)
            kb_raw += raw
            kb_obs |= {_norm(_pref(u)) for u in raw}
    cited = {_norm(m) for m in re.findall(r"【KB:([^】]+)】", answer)}
    good = {m for m in cited if any(m in o or o in m for o in kb_obs)}
    sents = [s for s in re.split(r"[。\n]", answer) if s.strip()]
    coverage = sum(1 for s in sents if "【KB:" in s or "【CALC】" in s) / len(sents) if sents else 0.0
    return {"cited": len(cited), "precision": round(len(good) / len(cited), 3) if cited else 1.0,
            "falsified": sorted(cited - good), "calc_called": calc_called,
            "calc_markers": len(re.findall(r"【CALC】", answer)), "coverage": round(coverage, 3),
            "retrieved": sorted(set(kb_raw))}


async def run_agentic(q, eid, cat, doc_uris, *, trace, agent_timeout: int = 180):
    return await asyncio.to_thread(run_agentic_sync, q, eid, cat, doc_uris)


def run_agentic_sync(q, eid, cat, doc_uris):
    """Sync 版畀 agent_worker 用：Runner 嘅 sync generator 一定要喺**冇 active event loop** 嘅環境跑，
    唔係 litellm 會甩 "cannot schedule new futures after shutdown"。hang 由 run.py subprocess 硬 timeout 管。"""
    import asyncio as _ai
    from google.adk.runners import Runner
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.genai import types
    strat, events = "agentic", []
    kb = _kb(STRATS[strat]["read_limit"])
    before = _ov_snapshot()
    agent = _build_agent(kb)
    t = time.perf_counter()
    session_service = InMemorySessionService()
    new_message = types.Content(role="user", parts=[types.Part(text=q)])
    session_id = f"rag-{eid}"
    _ai.run(session_service.create_session(app_name="rag_bench", user_id="bench", session_id=session_id))
    runner = Runner(agent=agent, app_name="rag_bench", session_service=session_service)
    transcript = []
    for ev in runner.run(user_id="bench", session_id=session_id, new_message=new_message):
        kind = "final" if ev.is_final_response() else "function_call" if ev.get_function_calls() else \
            "function_response" if ev.get_function_responses() else "llm"
        payload = {"kind": kind, "ts": str(getattr(ev, "timestamp", ""))}
        if ev.content is not None and ev.content.parts:
            payload["parts"] = []
            for _x in ev.content.parts:
                _txt = getattr(_x, "text", None)
                if _txt is None:
                    continue
                payload["parts"] += [str(_y) for _y in (_txt if isinstance(_txt, list) else [_txt])]
        for fc in ev.get_function_calls() or []:
            payload.setdefault("calls", []).append({"name": getattr(fc, "name", ""), "args": getattr(fc, "args", {})})
        for fr in ev.get_function_responses() or []:
            payload.setdefault("responses", []).append({"name": getattr(fr, "name", ""), "response": getattr(fr, "response", "")})
        if ev.usage_metadata is not None:
            um = ev.usage_metadata
            payload["usage"] = {"prompt": getattr(um, "prompt_token_count", 0) or 0,
                                "completion": getattr(um, "response_token_count", 0) or 0,
                                "cached": getattr(um, "cached_content_token_count", 0) or 0}
        transcript.append(payload)
    ms = (time.perf_counter() - t) * 1000
    _final = []
    for _ev in transcript:
        if _ev["kind"] == "final":
            _final += _ev.get("parts") or []
    answer = "\n".join(str(_p) for _p in _final)
    usage = {"prompt": sum(e.get("usage", {}).get("prompt", 0) for e in transcript),
             "completion": sum(e.get("usage", {}).get("completion", 0) for e in transcript),
             "cached": sum(e.get("usage", {}).get("cached", 0) for e in transcript)}
    tools_called = [c.get("name") for e in transcript for c in e.get("calls", [])]
    cite = _cite(transcript, answer)
    after = _ov_snapshot()
    _emit(events, strat, eid, cat, "agent", ms=ms, tokens=usage, detail={"tool_calls": tools_called,
          "citation": cite, "observer_delta": {"vectors": after.get("vectors")}})
    return dict(strategy=strat, eid=eid, category=cat, uris=cite["retrieved"], answer=answer, events=events,
                extra={"transcript": transcript, "usage": usage, "citation": cite, "tools": tools_called})


async def run(name, q, eid, cat, doc_uris, *, trace, agent_timeout: int = 180):
    if name == "agentic":
        raise KeyError("agentic 已退役（單一細 KB 冇 routing/多源價值），唔再跑；結果保留喺 REPORT")
    fn = {"naive": run_naive, "advanced": run_advanced, "hybrid": run_hybrid,
          "corrective": run_corrective, "adaptive": run_adaptive,
          "hyde": run_hyde, "hyde_rrf": run_hyde_rrf}[name]
    return await fn(q, eid, cat, doc_uris, trace=trace)