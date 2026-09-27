"""D8 fair redo runner：BytePlus AI（Ark LLM）＋ 本地 OpenViking DB（server-side Ollama nomic-embed-text）。

與原裝 RAG（D4）同一堆基建：veadk KnowledgeBase(backend='openviking') ＋ kb.search（dense find + L2 hydrate）
＋ grep sparse ＋ RRF(k=60)。差別只有 axis：
  default — fin_kb，8 txt，prompt=normal        （同日 control，對 D4）
  chunk   — fin_kb_chunk（8 txt @ 256/50 分塊）, prompt=normal   （軸 1）
  vis     — fin_kb_vis（8 txt + vis 文本）, prompt=normal        （軸 2）
  gen     — fin_kb，prompt=normalized            （軸 3）
  cmb     — fin_kb_cmb（分塊 + vis 文本）, prompt=normalized     （軸 4 = 1+2+3）

兩策略照抄 strategies.py：naive = dense k=5；hybrid = dense k=15 + grep -> RRF(k=60)。
chunk/cmb 嘅 retrieval 係「part 級」（每 part 一個 folder）；計分前按 doc_uris.json 併返做
doc 級 ranking（首現保序、去重），同 D4 default（每 doc 一個 folder）可比。

用法：python experiments/rag_optimization/scripts/run_fair.py [--only default,chunk,vis,gen,cmb]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

RAG_OPT = Path(__file__).resolve().parents[1]
PROJ = RAG_OPT.parents[1]
if str(PROJ) not in sys.path:
    sys.path.insert(0, str(PROJ))

from experiments import _lib  # noqa: E402
from experiments.eval_metrics import answer_f1, mrr_at_k, ndcg_at_k, precision_at_k, recall_at_k  # noqa: E402
from experiments.rag_bench.eval_set import CURRENT_ITEMS, LOCAL_DOCS, d7_items  # noqa: E402
from experiments.rag_bench.strategies import RRF_K, STOP, _rrf, _terms, _toks  # noqa: E402
from experiments.run_d7 import USELESS_ANS, _sys_prompt, _trap_pass  # noqa: E402

EST_TOKENS_PER_ITEM = 1800
D8 = {"naive": 5, "hybrid": 15}

FAIR_DIR = RAG_OPT / "results" / "fair"
DOC_URIS_JSON = FAIR_DIR / "doc_uris.json"

AXES = {
    "default": {"index": "fin_kb", "items": "text", "gen": "normal"},
    "chunk": {"index": "fin_kb_chunk", "items": "text", "gen": "normal"},
    "vis": {"index": "fin_kb_vis", "items": "vis", "gen": "normal"},
    "gen": {"index": "fin_kb", "items": "text", "gen": "normalized"},
    "cmb": {"index": "fin_kb_cmb", "items": "vis", "gen": "normalized"},
}
STRAT_NAMES = ("naive", "hybrid")


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _ctx(entries, extra=None, n=2000):
    """entries: list[(doclabel, text)]; extra: dict[doclabel -> grep snippet]."""
    lines = []
    for i, (label, text) in enumerate(entries, 1):
        lines.append(f"[{i}] <{label}>\n{text[:n].strip()}")
    for label, snip in (extra or {}).items():
        lines.append(f"[-] <{label} | grep>\n{snip.strip()[:n]}")
    return "\n".join(lines)


async def _answer(q, gen_style, ctx, trace):
    msgs = [{"role": "system", "content": _sys_prompt(gen_style)}, {"role": "user", "content": q}]
    if gen_style == "normal":
        msgs[0]["content"] += ctx
    else:
        msgs[0]["content"] += "\n\n資料：\n" + ctx
    return await _lib.ark_complete(msgs, max_tokens=512, trace=trace)


def _label(u, doc_prefixes):
    """retrieved uri → gold doc key（match 唔到 → None）。"""
    for key, pre in doc_prefixes.items():
        if u.startswith(pre):
            return key
    return None


class AxisKB:
    """KBs（dense channel）。"""

    def __init__(self):
        _lib.load_env()
        import agent_build

        agent_build._patch_openviking_hydrate()
        self.kbs = {}

    def kb(self, index: str):
        if index not in self.kbs:
            from veadk.knowledgebase import KnowledgeBase

            kb = KnowledgeBase(backend="openviking", index=index, top_k=5)
            kb._backend.target_uri = f"viking://resources/{index}/"
            kb._backend.read_limit = 200
            self.kbs[index] = kb
        return self.kbs[index]

    def grep_uri(self, index: str):
        return f"viking://resources/{index}/"


def _dense(axk, index, q, k):
    return axk.kb(index).search(q, top_k=k)


def _sparse(axk, index, pattern, limit=64):
    client = axk.kb(index)._backend._ensure_client()
    r = client.grep(uri=axk.grep_uri(index), pattern=pattern, case_insensitive=True, node_limit=limit)
    matches = r.get("result", {}).get("matches", []) if isinstance(r, dict) else r
    return [{"uri": m["uri"], "content": m.get("content", "")} for m in matches]


def _merge_to_docs(raw_uris, doc_prefixes):
    """ordered doc-level dedupe（首現保序）。"""
    seen, out = set(), []
    for u in raw_uris:
        lab = _label(u, doc_prefixes)
        if lab is not None and lab not in seen:
            seen.add(lab)
            out.append(lab)
    return out


async def _run_one(axk, ex, q, eid, cat, gen_style, strategy, doc_prefixes, index):
    events = []
    t = time.perf_counter()
    if strategy == "naive":
        entries = _dense(axk, index, q, D8["naive"])
        doc_order = _merge_to_docs([(e.metadata or {}).get("uri", "") for e in entries], doc_prefixes)
        best = {}
        for e in entries:
            u = (e.metadata or {}).get("uri", "")
            lab = _label(u, doc_prefixes)
            if lab is None:
                continue
            sc = float((e.metadata or {}).get("score") or 0.0)
            if lab not in best or sc > best[lab][1]:
                best[lab] = ((e.content or "")[:2000], sc)
        ctx_nodes = [(lab, best[lab][0]) for lab in doc_order if lab in best]
        extra = {}
    else:
        entries = _dense(axk, index, q, D8["hybrid"])
        grab = _sparse(axk, index, "|".join(_terms(q)))[:20]
        dense_docs = _merge_to_docs([(e.metadata or {}).get("uri", "") for e in entries], doc_prefixes)
        grep_docs = _merge_to_docs([g["uri"] for g in grab], doc_prefixes)
        merged = _rrf([dense_docs, grep_docs], k=RRF_K)
        best = {}
        for e in entries:
            u = (e.metadata or {}).get("uri", "")
            lab = _label(u, doc_prefixes)
            if lab is None or lab not in merged:
                continue
            sc = float((e.metadata or {}).get("score") or 0.0)
            if lab not in best or sc > best[lab][1]:
                best[lab] = ((e.content or "")[:2000], sc)
        extra = {}
        for lab in merged:
            if lab not in best:
                g = next((g for g in grab if _label(g["uri"], doc_prefixes) == lab), None)
                if g and g.get("content"):
                    extra[lab] = g["content"]
        ctx_nodes = [(lab, best[lab][0]) for lab in merged if lab in best]
        doc_order = [lab for lab in merged if lab in best or lab in extra]
    ms_retr = (time.perf_counter() - t) * 1000
    score = max((float((e.metadata or {}).get("score") or 0.0) for e in entries), default=0.0)

    # uris：doc 級 prefixes（計分睇呢啲）
    uris = [doc_prefixes[lab] for lab in doc_order if lab in doc_prefixes]
    events.append({"strategy": strategy, "eid": eid, "category": cat, "stage": "retrieve",
                   "ts": datetime.now().isoformat(), "ms": ms_retr, "tokens": {}, "score": score,
                   "uris": uris, "detail": {"dense": len(entries), "grep": len(grab) if strategy == "hybrid" else 0,
                                            "rrf_k": RRF_K if strategy == "hybrid" else 0,
                                            "n_ctx_docs": len(doc_order)}})
    trace = []
    ans = await _answer(q, gen_style, _ctx(ctx_nodes, extra), trace)
    events.append({"strategy": strategy, "eid": eid, "category": cat, "stage": "answer",
                   "ts": datetime.now().isoformat(), "ms": ans.ms,
                   "tokens": {"prompt": ans.prompt_tokens, "completion": ans.completion_tokens,
                              "cached": ans.cached_tokens}})
    return dict(strategy=strategy, eid=eid, category=cat, uris=uris, answer=ans.text,
                events=events, extra={"usage": {"prompt": ans.prompt_tokens, "completion": ans.completion_tokens,
                                                "cached": ans.cached_tokens}, "transcript": trace, "ms": ans.ms})


def _mu(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def _fmt(v, nd=3):
    return f"{v:.{nd}f}" if isinstance(v, (int, float)) and v is not None else "n/a"


def _write_per_run(s_dir, ax, strat, rows, errors):
    fact = [r for r in rows if r["cat"] != "trap"]
    traps = [r for r in rows if r["cat"] == "trap"]
    lines = [f"# report · fair_{ax}_{strat} · {len(rows)} items", "",
             f"- recall@5: **{_fmt(_mu([r['recall5'] for r in fact]))}**  prec@5: {_fmt(_mu([r['prec5'] for r in fact]))}  "
             f"MRR@5: {_fmt(_mu([r['mrr5'] for r in fact]))}  nDCG@5: {_fmt(_mu([r['ndcg5'] for r in fact]))}",
             f"- answer-F1: **{_fmt(_mu([r['answer_f1'] for r in fact]))}**"
             + (f"  trap 唔作: {sum(r['trap_pass'] for r in traps)}/{len(traps)}" if traps else ""),
             f"- cost: **${_fmt(sum(r['usd'] for r in rows), 4)}**  mean/run: {_fmt(sum(r['ms'] for r in rows) / max(len(rows), 1), 0)} ms",
             f"- errors: {errors or '—'}", "", "## per-item", "",
             "| eid | cat | recall@5 | prec@5 | mrr@5 | ndcg@5 | answer_F1 | trap | usd |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['eid']} | {r['cat']} | {_fmt(r['recall5'])} | {_fmt(r['prec5'])} | {_fmt(r['mrr5'])} "
                     f"| {_fmt(r['ndcg5'])} | {_fmt(r['answer_f1'])} | {'PASS' if r['cat'] == 'trap' and r['trap_pass'] else '-'} "
                     f"| ${_fmt(r['usd'], 6)} |")
    (s_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


async def _run(args):
    _lib.load_env()
    doc_uris = json.loads(DOC_URIS_JSON.read_text())
    from experiments.rag_bench.eval_set import all_doc_uris

    doc_uris["fin_kb"] = all_doc_uris()  # 8 txt（default/gen 軸）
    out_root = Path(args.out) if args.out else FAIR_DIR / f"runs_{time.strftime('%y%m%d_%H%M')}"
    out_root.mkdir(parents=True, exist_ok=True)

    text_items = CURRENT_ITEMS
    vis_items = d7_items(vis=True)
    items_by_axis = {"text": text_items, "vis": vis_items}

    axk = AxisKB()
    gold_prefixes = {axis: {k: v for k, v in idx_map.items() if v} for axis, idx_map in doc_uris.items()}

    budget = args.max_tokens
    used = 0
    summary = {}
    run_meta = {"tag": out_root.name, "ts": _now(),
                "backend": "OpenViking(self-hosted) + host Ollama nomic-embed-text (server-side)",
                "llm": "BytePlus AI = Ark seed-1-6-flash-250715", "prices": _lib.PRICES,
                "rrf_k": RRF_K, "axes": AXES, "max_tokens_budget": budget,
                "gold_map": "results/fair/doc_uris.json", "retrieve_only": args.retrieve_only}
    (out_root / "run_meta.json").write_text(json.dumps(run_meta, ensure_ascii=False, indent=2))

    axes = [a for a in AXES if not args.only or a in args.only.split(",")]

    for ax in axes:
        cfg = AXES[ax]
        index = cfg["index"]
        kdocs = gold_prefixes[index]
        items = items_by_axis[cfg["items"]]
        for strat in STRAT_NAMES:
            if args.only_strat and strat not in args.only_strat.split(","):
                continue
            s_dir = out_root / f"fair_{ax}_{strat}"
            s_dir.mkdir(parents=True, exist_ok=True)
            if args.smoke:
                items_run = [i for i in items if i["eid"] in {"f1", "mb4"}]
            else:
                items_run = items
            results, all_events = [], []
            for item in items_run:
                if used + EST_TOKENS_PER_ITEM > budget and not args.retrieve_only:
                    continue
                try:
                    res = await _run_one(axk, {}, item["q"], item["eid"], item["cat"], cfg["gen"], strat,
                                         kdocs, index)
                except Exception as ex:  # noqa: BLE001
                    res = {"strategy": strat, "eid": item["eid"], "category": item["cat"], "uris": [],
                           "answer": "", "events": [{"stage": "ERROR", "detail": {"err": str(ex)}}],
                           "extra": {"usage": {"prompt": 0, "completion": 0, "cached": 0}}, "error": str(ex)}
                res["ms"] = sum(e.get("ms") or 0 for e in res.get("events", []))
                usage = res.get("extra", {}).get("usage") or {"prompt": 0, "completion": 0, "cached": 0}
                used += usage.get("prompt", 0) + usage.get("completion", 0)
                all_events.extend(res.get("events", []))
                t_dir = s_dir / item["eid"]
                t_dir.mkdir(parents=True, exist_ok=True)
                (t_dir / "transcript.jsonl").write_text(
                    "\n".join(json.dumps(e, ensure_ascii=False) for e in res.get("extra", {}).get("transcript", [])) + "\n")
                if res.get("answer"):
                    (t_dir / "answer.txt").write_text(res["answer"], encoding="utf-8")
                results.append(res)

            golds = {}
            for i in items:
                gname = set(i["gold_docs"]) if i["cat"] != "trap" else set()
                golds[i["eid"]] = {"cat": i["cat"], "answer": i.get("gold", "")}
                if i["cat"] != "trap":
                    golds[i["eid"]]["gold"] = {kdocs[d] for d in gname if d in kdocs}
            rows = []
            for r in results:
                g = golds[r["eid"]]
                row = {"eid": r["eid"], "cat": r["category"], "axis": ax}
                gset = g.get("gold", set())
                row["recall5"] = recall_at_k(gset, r["uris"], 5) if g["cat"] != "trap" else None
                row["prec5"] = precision_at_k(gset, r["uris"], 5) if g["cat"] != "trap" else None
                row["mrr5"] = mrr_at_k(gset, r["uris"], 5) if g["cat"] != "trap" else None
                row["ndcg5"] = ndcg_at_k(gset, r["uris"], 5) if g["cat"] != "trap" else None
                row["answer_f1"] = answer_f1(g["answer"] or "", r["answer"] or "") if g["cat"] != "trap" else None
                row["usd"] = _lib.usd(r.get("extra", {}).get("usage", {}).get("prompt", 0),
                                      r.get("extra", {}).get("usage", {}).get("completion", 0),
                                      r.get("extra", {}).get("usage", {}).get("cached", 0))
                row["ms"] = r.get("ms") or 0
                row["trap_pass"] = _trap_pass(r.get("answer")) if r["category"] == "trap" else None
                row["tokens"] = r.get("extra", {}).get("usage", {})
                rows.append(row)
            (s_dir / "events.jsonl").write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in all_events) + "\n")
            (s_dir / "info.json").write_text(json.dumps({"axis": ax, "strategy": strat, **cfg}, ensure_ascii=False))
            summary[f"fair_{ax}_{strat}"] = {"rows": rows,
                                             "errors": [r["eid"] for r in results if "error" in r],
                                             "axis": ax, "strategy": strat}
            _write_per_run(s_dir, ax, strat, rows, summary[f"fair_{ax}_{strat}"]["errors"])
            print(f"[fair_{ax}_{strat}] n={len(rows)} recall5={_fmt(_mu([r['recall5'] for r in rows if r['cat']!='trap']))} "
                  f"F1={_fmt(_mu([r['answer_f1'] for r in rows if r['cat']!='trap']))} used_tokens={used}")

    _write_summary(out_root, summary)
    run_meta["used_tokens"] = used
    (out_root / "run_meta.json").write_text(json.dumps(run_meta, ensure_ascii=False, indent=2))
    print(f"tokens used: {used}/{budget}\ndone → {out_root}")


def _write_summary(out_root, summary):
    lines = ["# D8 fair redo SUMMARY (BytePlus AI + local OpenViking)", "", f"- tag: {out_root.name}   runs: {_now()}",
             "| run | axis | recall@5 | prec@5 | MRR@5 | nDCG@5 | answer-F1 | trap-hit | usd | ms/run |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for k, s in summary.items():
        r = s["rows"]
        fact = [x for x in r if x["cat"] != "trap"]
        traps = [x for x in r if x["cat"] == "trap"]
        traps_hit = f"{sum(x['trap_pass'] for x in traps)}/{len(traps)}" if traps else "—"
        lines.append(f"| {k} | {s['axis']} | {_fmt(_mu([x['recall5'] for x in fact]))} | "
                     f"{_fmt(_mu([x['prec5'] for x in fact]))} | {_fmt(_mu([x['mrr5'] for x in fact]))} | "
                     f"{_fmt(_mu([x['ndcg5'] for x in fact]))} | {_fmt(_mu([x['answer_f1'] for x in fact]))} | "
                     f"{traps_hit} | ${_fmt(sum(x['usd'] for x in r), 4)} | "
                     f"{_fmt(sum(x['ms'] for x in r) / max(len(r), 1), 0)} |")
    lines.append("")
    lines.append("> D4（同 stack）baseline：naive recall@5 0.964 / MRR 0.762 / answer-F1 0.109；"
                 "hybrid recall@5 0.964 / MRR 0.929 / answer-F1 0.127。")
    (out_root / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="D8 fair redo runner (OpenViking + Ark LLM)")
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--only", default="", help="逗號分隔軸：default,chunk,vis,gen,cmb")
    p.add_argument("--only-strat", default="", help="逗號分隔：naive,hybrid")
    p.add_argument("--out", default="")
    p.add_argument("--max-tokens", type=int, default=800_000)
    p.add_argument("--retrieve-only", action="store_true")
    args = p.parse_args()
    if args.retrieve_only:
        async def _stub(msgs, model=None, *, max_tokens=512, caching=False, trace=None):
            from experiments.run_d7 import _stub as s
            return await s(msgs, model, max_tokens=max_tokens, caching=caching, trace=trace)

        _lib.ark_complete = _stub
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()