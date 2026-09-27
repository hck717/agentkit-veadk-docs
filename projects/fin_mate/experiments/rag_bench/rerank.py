"""Rerank Lab（D5）：固定 candidate pool × {none, RRF(k=60), 本地 LLM-as-reranker(Qwen3-4B)}。

只 run「新 type」variant——唔會 retest 現有 pipe（naive/advanced/hybrid/corrective/adaptive/agentic）。

- Pool（3 variant 共用同一 pool，只比排序）：dense `kb.search(q, top_k=15)` @read_limit=200
  + OpenViking grep（kw≤3, limit≤20），doc-prefix 去重 → ~15–25 候選。
- none：pool 原序（dense 15 先行、grep 補足）＝ rerank 前 baseline。$0。
- rrf：`_rrf([dense, grep], k=60)`（路程同 main run hybrid）。
- llm：Qwen3-4B pointwise（Ollama `/api/chat`，think:false、temp 0）每候選 score 0–3 → desc（tie 原序）。$0（本機）。
- answer：揀中 top-5 組 ctx → Ark answer（multi-hop 要兩份 doc）；metric @3 主 + @5 參考。

Budget：scoring $0（Ollama 本機，token 另計 local）；只有 answer 經 Ark → 獨立 `--max-tokens`（預設 150K）。

用法：
  python -m experiments.rag_bench.rerank --smoke --llm-stub --retrieve-only   # plumbing（$0，唔撳 Ollama/Ark）
  python -m experiments.rag_bench.rerank --smoke                             # 4 題真跑
  python -m experiments.rag_bench.rerank --out experiments/runs/rerank_<tag> --max-tokens 150000
  python -m experiments.rag_bench.rerank --rrf-sweep                        # k×w 暖靴表（retrieve-only、$0）
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments import _lib  # noqa: E402
from experiments.eval_metrics import answer_f1, mrr_at_k, ndcg_at_k, precision_at_k, recall_at_k  # noqa: E402
from experiments.rag_bench import strategies as S  # noqa: E402
from experiments.rag_bench.eval_set import CURRENT_ITEMS, all_doc_uris, resolve_gold  # noqa: E402

POOL_D = 15          # dense 候選
GREP_LIMIT = 20      # grep 候選上限
TOP_K = 3            # ranking metric 主機 k
ANS_K = 5            # answer 生成 ctx 用 top-5（multi-hop 要兩份 doc）
USELESS_ANS = ("無資料", "没有", "no information", "not found", "唔知")

OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:4b-instruct-2507-q4_K_M")
RERANK_CE_MODEL = os.environ.get("RERANK_CE_MODEL", "BAAI/bge-reranker-v2-m3")

_CE = None


def _cross_encoder():
    """lazy singleton（bge-reranker-v2-m3，multilingual；CPU——見 §11 方法論）。"""
    global _CE
    if _CE is None:
        from sentence_transformers import CrossEncoder
        _CE = CrossEncoder(RERANK_CE_MODEL, device="cpu")
    return _CE

VARIANTS = ["none", "rrf", "ce", "llm", "llm_listwise"]
VAR_DESC = {
    "none": "pool 原序（dense 15 先行、grep 補）＝ rerank 前 baseline；$0",
    "rrf": "RRF(k=60) 融合 dense+grep；$0（路徑同 main run hybrid）",
    "ce": "bge-reranker-v2-m3 cross-encoder sigmoid score desc；$0（本機 CPU）",
    "llm": "Qwen3-4B pointwise score 0–3 → desc（tie 原序）；$0（Ollama 本機）",
    "llm_listwise": "Qwen3-4B listwise（一次過排全部候選）→ 輸出 id 順序；$0（Ollama 本機）",
}


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _trap_pass(answer):
    a = (answer or "").lower()
    return any(u in a for u in USELESS_ANS)


def _mu(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def _fmt(v, nd=3):
    return f"{v:.{nd}f}" if isinstance(v, (int, float)) and v is not None else "n/a"


async def _stub_ark_complete(msgs, model=None, *, max_tokens=512, caching=False, trace=None):
    c = _lib.Completion(text="", prompt_tokens=0, completion_tokens=0, cached_tokens=0, ms=0.0)
    if trace is not None:
        trace.append({"llm": "stub", "msgs": msgs, "text": "", "prompt_tokens": 0,
                      "completion_tokens": 0, "cached_tokens": 0, "ms": 0})
    return c


async def _qwen_score(query, uri, content, trace):
    """Ollama native /api/chat（Qwen3 need think:false）→ pointwise score 0–3。"""
    import httpx

    msgs = [
        {"role": "system", "content": "你是無偏見嘅檢索評分器。只回一個整數，唔加任何字：0=無關 / 1=相關 / 2=間接關鍵證據 / 3=直接答到條問題。"},
        {"role": "user", "content": f"問題：{query}\n\n候選文件：\n{content[:400]}\n\n只回整數 0–3。"},
    ]
    body = {"model": OLLAMA_MODEL, "messages": msgs, "stream": False, "think": False,
            "temperature": 0, "options": {"num_predict": 8}}
    t = time.perf_counter()
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(OLLAMA_BASE.rstrip("/") + "/api/chat", json=body)
        r.raise_for_status()
        j = r.json()
    ms = (time.perf_counter() - t) * 1000
    txt = ((j.get("message") or {}).get("content") or "").strip()
    m = re.search(r"\b([0-3])\b", txt)
    score = int(m.group(1)) if m else 0
    toks = int(j.get("prompt_eval_count", 0) or 0) + int(j.get("eval_count", 0) or 0)
    if trace is not None:
        trace.append({"llm": "qwen3", "uri": uri, "score": score, "output": txt, "ms": ms, "local_tokens": toks})
    return score, ms, toks


async def _qwen_listwise(query, pool, by_uri, idx, trace):
    """Ollama listwise：一次過排晒全部候選 → 輸出 id 順序；parse fail → 原 pool 序。"""
    import httpx

    cand_lines = []
    for i, u in enumerate(pool):
        content = (by_uri.get(u, "") or "")[:150].replace("\n", " ")
        cand_lines.append(f"[{i}] {S._pref(u)} — {content}")
    msgs = [
        {"role": "system", "content": "你是無偏見嘅檢索排序器。按相關度由高到低排出候選編號，只回編號（逗號或空格分隔），唔加任何字、唔重複、一定要包含所有編號。"},
        {"role": "user", "content": f"問題：{query}\n\n候選：\n" + "\n".join(cand_lines) + "\n\n只回重新排序後嘅編號序列："},
    ]
    body = {"model": OLLAMA_MODEL, "messages": msgs, "stream": False, "think": False,
            "temperature": 0, "options": {"num_predict": 512}}
    t = time.perf_counter()
    async with httpx.AsyncClient(timeout=180) as c:
        r = await c.post(OLLAMA_BASE.rstrip("/") + "/api/chat", json=body)
        r.raise_for_status()
        j = r.json()
    ms = (time.perf_counter() - t) * 1000
    txt = ((j.get("message") or {}).get("content") or "").strip()
    nums = [int(m) for m in re.findall(r"\d+", txt)]
    order, seen = [], set()
    for n in nums:
        if 0 <= n < len(pool) and n not in seen:
            seen.add(n)
            order.append(pool[n])
    for i, u in enumerate(pool):
        if i not in seen:
            order.append(u)
            seen.add(i)
    toks = int(j.get("prompt_eval_count", 0) or 0) + int(j.get("eval_count", 0) or 0)
    detail = {"parsed": sorted(seen) == list(range(len(pool))), "n": len(order),
              "output": txt[:200], "local_tokens": toks}
    if trace is not None:
        trace.append({"llm": "qwen3_listwise", "uri": pool[0], "score": None,
                      "output": txt, "ms": ms, "local_tokens": toks})
    return order, detail


def _build_pool(kb, q, trace=None):
    entries = S._dense(kb, q, POOL_D)
    grab = S._sparse(kb, "|".join(S._terms(q)), GREP_LIMIT)
    dense_uris = [(e.metadata or {}).get("uri", "") for e in entries]
    grep_uris = [g["uri"] for g in grab]
    pool = S._dedupe(dense_uris + grep_uris)
    by_uri = {}
    for e in entries:
        by_uri[(e.metadata or {}).get("uri", "")] = e.content or ""
    for g in grab:
        by_uri.setdefault(g["uri"], g.get("content", ""))
    return {"entries": entries, "grab": grab, "dense_uris": dense_uris, "grep_uris": grep_uris,
            "pool": pool, "by_uri": by_uri}


def _rrf_w(ranked_lists, weights, k):
    """RRF 合併；返回真正 chunk uri（src 畀 dye）。metric 喺 doc 層面照用 _pref()。"""
    scores = {}
    src = {}
    for ranked, w in zip(ranked_lists, weights):
        for rank, u in enumerate(ranked):
            key = S._pref(u)
            scores[key] = scores.get(key, 0.0) + w / (k + rank + 1)
            src.setdefault(key, u)
    return [src[u] for u, _ in sorted(scores.items(), key=lambda x: -x[1])]


def _pref_to_chunk(pref, pool_data):
    """doc-prefix → 真實 chunk uri（pdf/entries 優先，grep 次之）。RRF 用。"""
    for u in pool_data["dense_uris"]:
        if S._pref(u) == pref:
            return u
    for u in pool_data["grep_uris"]:
        if S._pref(u) == pref:
            return u
    return pref


async def _rerank_order(variant, q, pool_data, idx, llm_stub, trace):
    pool, dense_uris, grep_uris = pool_data["pool"], pool_data["dense_uris"], pool_data["grep_uris"]
    detail = {}
    if variant == "none":
        return pool, 0.0, detail
    if variant == "rrf":
        t = time.perf_counter()
        prefs = S._rrf([dense_uris, grep_uris], k=S.RRF_K)
        order = S._dedupe([_pref_to_chunk(p, pool_data) for p in prefs])
        detail = {"rrf_k": S.RRF_K, "rrf_top1": (prefs[0] if prefs else None),
                  "n_pref": len(prefs), "n_chunk": len(order)}
        return order, (time.perf_counter() - t) * 1000, detail
    if variant == "ce":
        t = time.perf_counter()
        if llm_stub:
            scored = [(len(pool) - i, u, 0.0) for i, u in enumerate(pool)]
            detail = {"ce_model": "stub"}
        else:
            _ce = _cross_encoder()
            pairs = [[q, (pool_data["by_uri"].get(u, "") or "")[:400]] for u in pool]
            scores = _ce.predict(pairs, batch_size=16, show_progress_bar=False)
            scores = [float(s) for s in scores]
            scored = list(zip(scores, range(len(pool)), pool))
            detail = {"ce_model": RERANK_CE_MODEL,
                      "scores": {S._pref(u): s for s, _, u in scored}}
        scored.sort(key=lambda x: (-x[0], x[1]))
        order = [u for _, _, u in scored]
        return order, (time.perf_counter() - t) * 1000, detail
    if variant == "llm_listwise":
        t = time.perf_counter()
        order = pool
        if llm_stub:
            detail = {"listwise": "stub"}
        else:
            try:
                order, detail = await _qwen_listwise(q, pool, pool_data["by_uri"], idx, trace)
            except Exception as ex:
                detail = {"listwise_error": str(ex), "fallback": True}
        return order, (time.perf_counter() - t) * 1000, detail
    t0 = time.perf_counter()
    scored = []
    if llm_stub:
        for i, u in enumerate(pool):
            scored.append((len(pool) - i, u, 0.0))
            if trace is not None:
                trace.append({"llm": "qwen3-stub", "uri": u, "score": len(pool) - i})
    else:
        for u in pool:
            sc, ms, _ = await _qwen_score(q, u, pool_data["by_uri"].get(u, ""), trace)
            scored.append((sc, u, ms))
    rerank_ms = (time.perf_counter() - t0) * 1000
    scored.sort(key=lambda x: (-x[0], idx[x[1]]))
    order = [u for _, u, _ in scored]
    detail = {"scores": {S._pref(u): s for s, u, _ in scored}}
    return order, rerank_ms, detail


def _ctx_selected(top_uris, entries, grab, doc_uris):
    chosen, extra = [], {}
    for uri in top_uris:
        hit = next((e for e in entries if (e.metadata or {}).get("uri") == uri), None)
        if hit is not None:
            chosen.append(hit)
        else:
            g = next((x for x in grab if x["uri"] == uri), None)
            if g is not None:
                extra[uri] = g.get("content", "")
    return S._ctx(chosen, doc_uris, extra=extra)


async def run_variant(variant, q, eid, cat, doc_uris, *, trace, top_k=TOP_K, ans_k=ANS_K, llm_stub=False):
    strat, events = f"rr:{variant}", []
    kb = S._kb(200)
    t = time.perf_counter()
    pool_data = _build_pool(kb, q)
    retrieve_ms = (time.perf_counter() - t) * 1000
    p = pool_data["pool"]
    _emit(events, strat, eid, cat, "retrieve", ms=retrieve_ms, uris=p,
          detail={"dense": len(pool_data["dense_uris"]), "grep": len(pool_data["grep_uris"]),
                  "pool": len(p)})
    idx = {u: i for i, u in enumerate(p)}
    order, rerank_ms, detail = await _rerank_order(variant, q, pool_data, idx, llm_stub, trace)
    uris = order[:ans_k]
    _emit(events, strat, eid, cat, "rerank", ms=rerank_ms, uris=uris, detail={"variant": variant, **detail})
    ctx = _ctx_selected(uris, pool_data["entries"], pool_data["grab"], doc_uris)
    ans = await S.ark_complete(S._ans_msgs(q, ctx), max_tokens=512, trace=trace)
    _emit(events, strat, eid, cat, "answer", ms=ans.ms,
          tokens={"prompt": ans.prompt_tokens, "completion": ans.completion_tokens, "cached": ans.cached_tokens})
    local_tokens = sum(int(e.get("local_tokens", 0) or 0) for e in (trace or []) if e.get("llm") == "qwen3") \
        + sum(int(e.get("local_tokens", 0) or 0) for e in (trace or []) if e.get("llm") == "qwen3_listwise")
    usage = {"prompt": ans.prompt_tokens, "completion": ans.completion_tokens, "cached": ans.cached_tokens}
    return dict(strategy=strat, eid=eid, category=cat, uris=uris, answer=ans.text, events=events,
                usage=usage, extra={"local_tokens": local_tokens, "local_ms": retrieve_ms + rerank_ms,
                                    "ark_ms": ans.ms, "variant": variant})


def _emit(events, strat, eid, cat, stage, ms=None, tokens=None, score=None, uris=None, detail=None):
    events.append({"strategy": strat, "eid": eid, "category": cat, "stage": stage,
                   "ts": time.strftime("%Y-%m-%dT%H:%M:%S.%f"), "ms": ms,
                   "tokens": tokens or {}, "score": score, "uris": uris or [], "detail": detail or {}})


def _item_rows(results, golds, top_k):
    rows = []
    for r in results:
        gold = golds[r["eid"]]
        row = {"eid": r["eid"], "cat": r["category"]}
        row["answer_f1"] = answer_f1(gold["answer"] or "", r["answer"] or "") if gold["cat"] != "trap" else None
        if r["category"] == "trap":
            row["trap_pass"] = _trap_pass(r["answer"])
        row["recall3"] = recall_at_k(gold["gold"], r["uris"], top_k) if gold["cat"] != "trap" else None
        row["prec3"] = precision_at_k(gold["gold"], r["uris"], top_k) if gold["cat"] != "trap" else None
        row["mrr3"] = mrr_at_k(gold["gold"], r["uris"], top_k) if gold["cat"] != "trap" else None
        row["ndcg3"] = ndcg_at_k(gold["gold"], r["uris"], top_k) if gold["cat"] != "trap" else None
        row["recall5"] = recall_at_k(gold["gold"], r["uris"], 5) if gold["cat"] != "trap" else None
        row["mrr5"] = mrr_at_k(gold["gold"], r["uris"], 5) if gold["cat"] != "trap" else None
        row["usd"] = _lib.usd(r.get("usage", {}).get("prompt", 0), r.get("usage", {}).get("completion", 0),
                               r.get("usage", {}).get("cached", 0))
        extra = r.get("extra", {})
        row["local_ms"] = extra.get("local_ms", 0.0)
        row["ark_ms"] = extra.get("ark_ms", 0.0)
        row["local_tokens"] = extra.get("local_tokens", 0)
        rows.append(row)
    return rows


def _write_report(s_dir, variant, s):
    rows = s["rows"]
    fact = [r for r in rows if r["cat"] != "trap"]
    traps = [r for r in rows if r["cat"] == "trap"]
    lines = [f"# report · {variant} · {s['n']} items",
             f"- recall@3: **{_fmt(_mu([r['recall3'] for r in fact]))}**  prec@3: {_fmt(_mu([r['prec3'] for r in fact]))}  "
             f"MRR@3: {_fmt(_mu([r['mrr3'] for r in fact]))}  nDCG@3: {_fmt(_mu([r['ndcg3'] for r in fact]))}",
             f"- recall@5: {_fmt(_mu([r['recall5'] for r in fact]))}  MRR@5: {_fmt(_mu([r['mrr5'] for r in fact]))}",
             f"- answer-F1: **{_fmt(_mu([r['answer_f1'] for r in fact]))}**   trap 唔作: "
             f"{sum(r['trap_pass'] for r in traps)}/{len(traps)}" if traps else f"- answer-F1: **{_fmt(_mu([r['answer_f1'] for r in fact]))}**",
             f"- cost: **${_fmt(sum(r['usd'] for r in rows), 4)}**  mean local ms: {_fmt(_mu([r['local_ms'] for r in rows]), 1)}  "
             f"mean Ark ms: {_fmt(_mu([r['ark_ms'] for r in rows]), 1)}  local tokens: {sum(r['local_tokens'] for r in rows)}",
             f"- errors: {s['errors'] or '—'}",
             "", "## per-item", "",
             "| eid | cat | recall@3 | prec@3 | mrr@3 | ndcg@3 | recall@5 | answer_F1 | trap | local_ms | ark_ms | $ |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['eid']} | {r['cat']} | {_fmt(r['recall3'])} | {_fmt(r['prec3'])} | {_fmt(r['mrr3'])} "
                     f"| {_fmt(r['ndcg3'])} | {_fmt(r['recall5'])} | {_fmt(r['answer_f1'])} | "
                     f"{'PASS' if r['cat'] == 'trap' and r['trap_pass'] else '-'} "
                     f"| {_fmt(r['local_ms'], 1)} | {_fmt(r['ark_ms'], 1)} | ${_fmt(r['usd'], 6)} |")
    (s_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_summary(out_root, summary, top_k):
    lines = ["# RERANK Lab SUMMARY", "", f"- tag: {out_root.name}   runs: {_now()}", "",
             f"| variant | recall@{top_k} | prec@{top_k} | MRR@{top_k} | nDCG@{top_k} | recall@5 | answer-F1 | trap | "
             "local ms/題 | Ark ms/題 | $ | local tokens |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k in VARIANTS:
        if k not in summary:
            continue
        r = summary[k]["rows"]
        fact = [x for x in r if x["cat"] != "trap"]
        traps = [x for x in r if x["cat"] == "trap"]
        traps_hit = f"{sum(x['trap_pass'] for x in traps)}/{len(traps)}" if traps else "—"
        lines.append(f"| {k} | {_fmt(_mu([x['recall3'] for x in fact]))} | {_fmt(_mu([x['prec3'] for x in fact]))} "
                     f"| {_fmt(_mu([x['mrr3'] for x in fact]))} | {_fmt(_mu([x['ndcg3'] for x in fact]))} "
                     f"| {_fmt(_mu([x['recall5'] for x in fact]))} | {_fmt(_mu([x['answer_f1'] for x in fact]))} "
                     f"| {traps_hit} | {_fmt(_mu([r['local_ms'] for r in fact]), 1):<6s} "
                     f"| {_fmt(_mu([r['ark_ms'] for r in fact]), 1):<6s} | ${_fmt(sum(x['usd'] for x in r), 4)} "
                     f"| {sum(x['local_tokens'] for x in r)} |")
    lines.append("")
    lines.append("> pool：dense top-15 + grep ≤20（doc-prefix 去重），三 variant 共用同一 pool，只比排序。"
                 "answer 用 top-5 ctx（multi-hop 要兩份 doc）；scoring 本地 Ollama $0（local tokens 另計）。"
                 "RRF/LLM 詳情見 RAG_LAB.md §9；main-run 對照：hybrid recall@5=0.964 / MRR@5=0.929。")
    (out_root / "RERANK_SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


async def _run(args):
    _lib.load_env()
    if args.retrieve_only:
        S.ark_complete = _stub_ark_complete
        print("[retrieve-only] stub Ark answer，唔會真正 call model（Qwen 照真跑除非 --llm-stub）")

    variants = args.only.split(",") if args.only else list(VARIANTS)
    items = CURRENT_ITEMS if not args.smoke else [i for i in CURRENT_ITEMS if i["eid"] in {"f1", "f9", "t1", "m1"}]

    out_root = Path(args.out) if args.out else ROOT / "experiments" / "runs" / ("rerank_" + time.strftime("%y%m%d_%H%M"))
    out_root.mkdir(parents=True, exist_ok=True)
    doc_uris = all_doc_uris()
    golds = {i["eid"]: {"cat": i["cat"], "gold": resolve_gold(i, doc_uris) if i["cat"] != "trap" else set(),
                        "answer": i["gold"]} for i in items}
    budget = args.max_tokens
    used_tokens = local_tokens = 0

    run_meta = {"tag": out_root.name, "ts": _now(), "models": {"primary": os.environ.get("MODEL_PRIMARY", "?"),
                "local_reranker": OLLAMA_MODEL}, "prices": _lib.PRICES, "pool_dense": POOL_D,
                "grep_limit": GREP_LIMIT, "top_k": args.top_k, "ans_k": ANS_K, "rrf_k": S.RRF_K,
                "variants": VAR_DESC, "n_items": len(items), "items": [i["eid"] for i in items],
                "retrieve_only": args.retrieve_only, "llm_stub": args.llm_stub,
                "max_tokens_budget": budget}
    (out_root / "run_meta.json").write_text(json.dumps(run_meta, ensure_ascii=False, indent=2))

    summary = {}
    for variant in variants:
        s_dir = out_root / variant
        s_dir.mkdir(parents=True, exist_ok=True)
        (s_dir / "info.json").write_text(json.dumps({"variant": variant, "desc": VAR_DESC[variant],
                                                     "top_k": args.top_k, "ans_k": ANS_K},
                                                    ensure_ascii=False, indent=2))
        results, all_events = [], []
        for item in items:
            if used_tokens + 2200 > budget and not args.retrieve_only:
                res = {"strategy": f"rr:{variant}", "eid": item["eid"], "category": item["cat"], "uris": [],
                       "answer": "", "events": [{"strategy": f"rr:{variant}", "eid": item["eid"],
                                                 "stage": "BUDGET_SKIP", "tokens": {"used": used_tokens, "budget": budget}}],
                       "usage": {"prompt": 0, "completion": 0, "cached": 0}, "ms": 0, "extra": {},
                       "error": f"BUDGET_SKIP used={used_tokens}/budget={budget}"}
                all_events.extend(res["events"]); results.append(res); continue
            t0 = time.perf_counter()
            trace = []
            try:
                res = await run_variant(variant, item["q"], item["eid"], item["cat"], doc_uris,
                                        trace=trace, top_k=args.top_k, llm_stub=args.llm_stub)
                res["ms"] = sum(e.get("ms") or 0 for e in res["events"])
            except Exception as ex:
                res = {"strategy": f"rr:{variant}", "eid": item["eid"], "category": item["cat"], "uris": [],
                       "answer": "", "events": [{"strategy": f"rr:{variant}", "eid": item["eid"], "stage": "ERROR"}],
                       "usage": {"prompt": 0, "completion": 0, "cached": 0}, "ms": 0, "extra": {}, "error": str(ex)}
            all_events.extend(res["events"])
            t_dir = s_dir / item["eid"]
            t_dir.mkdir(parents=True, exist_ok=True)
            t_out = res.get("extra", {}).get("transcript") or trace
            (t_dir / "transcript.jsonl").write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in t_out) + "\n")
            if res["answer"]:
                (t_dir / "answer.txt").write_text(res["answer"], encoding="utf-8")
            results.append(res)
            used_tokens += (res["usage"].get("prompt", 0) or 0) + (res["usage"].get("completion", 0) or 0)
            local_tokens += res.get("extra", {}).get("local_tokens", 0)

        (s_dir / "events.jsonl").write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in all_events) + "\n")
        rows = _item_rows(results, golds, args.top_k)
        summary[variant] = {"rows": rows, "n": len(rows), "errors": [r["eid"] for r in results if "error" in r]}
        _write_report(s_dir, variant, summary[variant])
        print(f"[rr:{variant}] n={len(rows)} err={summary[variant]['errors']} ark_tokens={used_tokens} "
              f"local_tokens={local_tokens}")

    run_meta["used_tokens"] = used_tokens
    run_meta["local_tokens"] = local_tokens
    (out_root / "run_meta.json").write_text(json.dumps(run_meta, ensure_ascii=False, indent=2))
    print(f"Ark tokens used: {used_tokens}/{budget}  local(Ollama) tokens: {local_tokens}")
    _write_summary(out_root, summary, args.top_k)
    print(f"done → {out_root}")


async def _rrf_sweep(args):
    """retrieve-only：對 15 題掃 k × w_sparse，MRR@3 為主 + recall@5。$0。"""
    _lib.load_env()
    doc_uris = all_doc_uris()
    golds = {i["eid"]: resolve_gold(i, doc_uris) if i["cat"] != "trap" else set() for i in CURRENT_ITEMS}
    kb = S._kb(200)
    pools = []
    for item in CURRENT_ITEMS:
        if item["cat"] == "trap":
            pools.append(None); continue
        pools.append(_build_pool(kb, item["q"]))
    out_root = Path(args.out) if args.out else ROOT / "experiments" / "runs" / ("rrf_sweep_" + time.strftime("%y%m%d_%H%M"))
    out_root.mkdir(parents=True, exist_ok=True)
    lines = ["# RRF k × w sweep（retrieve-only，MRR@3 主，recall@5 做 constraint）", "",
             "| k | w_sparse | MRR@3 | recall@5 | recall@3 |", "|---|---|---|---|---|"]
    best = None
    for k in [10, 20, 40, 60, 100, 200]:
        for w in [0.5, 1.0, 1.5, 2.0]:
            mrr3, rec3, rec5 = [], [], []
            for i, item in enumerate(CURRENT_ITEMS):
                if item["cat"] == "trap" or pools[i] is None:
                    continue
                pd = pools[i]
                order = _rrf_w([pd["dense_uris"], pd["grep_uris"]], [1.0, w], k)
                g = golds[item["eid"]]
                mrr3.append(mrr_at_k(g, order, 3)); rec3.append(recall_at_k(g, order, 3))
                rec5.append(recall_at_k(g, order, 5))
            m, r3, r5 = _mu(mrr3), _mu(rec3), _mu(rec5)
            lines.append(f"| {k} | {w:g} | {_fmt(m)} | {_fmt(r5)} | {_fmt(r3)} |")
            if best is None or m > best[0]:
                best = (m, k, w, r5)
    lines += ["", f"> 最佳（MRR@3 計）：k={best[1]}  w_sparse={best[2]:g}  MRR@3={_fmt(best[0])}  "
                  f"recall@5={_fmt(best[3])}（現行 k=60 / w=1 做對照）"]
    (out_root / "RRF_SWEEP.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("sweep done →", out_root / "RRF_SWEEP.md")


def main():
    p = argparse.ArgumentParser(description="Rerank Lab（D5）：none / RRF / Qwen3-4B pointwise")
    p.add_argument("--smoke", action="store_true", help="得 4 題（f1/f9/t1/m1）")
    p.add_argument("--only", default="", help="逗號分隔 variant 名（none,rrf,llm）")
    p.add_argument("--out", default="", help="輸出目錄")
    p.add_argument("--retrieve-only", action="store_true", help="stub Ark answer；Qwen 照真跑除非連 --llm-stub")
    p.add_argument("--llm-stub", action="store_true", help="mock 本地 reranker（確定性），唔撳 Ollama")
    p.add_argument("--top-k", type=int, default=TOP_K, help="ranking metric 主機 k（預設 3）")
    p.add_argument("--max-tokens", type=int, default=150_000, help="Ark token 上限（scoring $0 唔扣）")
    p.add_argument("--rrf-sweep", action="store_true", help="retrieve-only 掃 RRF k×w，出 RRF_SWEEP.md")
    args = p.parse_args()
    if args.rrf_sweep:
        asyncio.run(_rrf_sweep(args))
    else:
        asyncio.run(_run(args))


if __name__ == "__main__":
    main()