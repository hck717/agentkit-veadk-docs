"""D7 corpus-shaping RAG 實驗 runner：8 runs = default/chunk/mm/gen × naive/hybrid。

軸：
  default   — corpus=8 txt, chunk 512/50, gen=normal        （本地控制，≈ D4 語料）
  chunk     — corpus=8 txt, chunk 256/50, gen=normal        （chunking 軸）
  mm        — corpus=8 txt + kb_vis(table/chart/scan/html), chunk 512/50, gen=normal（多模態軸，+5 needle）
  gen       — corpus=8 txt, chunk 512/50, gen=normalized     （generation 軸）

全部用本地 bge-small-en-v1.5 embedding（無 Ark embedding key）＋ Ark LLM 作答（`_lib.ark_complete`）。
naive = dense top-5；hybrid = dense top-15 + sparse grep → RRF(k=60) 融合（mirror strategies.py）。

用法：
  python -m experiments.run_d7 --smoke            # 2 題 x 8 runs 快試
  python -m experiments.run_d7 --only mm,gen      # 只行指定軸
  python -m experiments.run_d7 --out dir          # 指定輸出目錄（預設 experiments/runs/<ts>/d7_...）
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

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments import _lib  # noqa: E402
from experiments.eval_metrics import answer_f1, mrr_at_k, ndcg_at_k, precision_at_k, recall_at_k  # noqa: E402
from experiments.mv_backend import D7Backend  # noqa: E402
from experiments.rag_bench.eval_set import CURRENT_ITEMS, d7_items, resolve_gold_local  # noqa: E402
from experiments.rag_bench.strategies import RRF_K, STOP  # noqa: E402

USELESS_ANS = ("無資料", "没有", "no information", "not found", "唔知")
EST_TOKENS_PER_ITEM = 1800
D7 = {"naive": 5, "hybrid": 15}

TEXT_DIR = ROOT / "data" / "kb" / "msft_txt"
VIS_DIR = ROOT / "data" / "kb_vis"


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _docid(fp: str) -> str:
    return Path(fp).name


def _toks(q):
    return [t for t in re.findall(r"[A-Za-z0-9]+(?:\.\d+)?", str(q)) if t.lower() not in STOP and len(t) >= 2]


def _terms(q, n=3):
    ts = _toks(q)
    ts.sort(key=lambda w: (w[0].isupper() or w[0][0].isdigit(), len(w)), reverse=True)
    return ts[:n] or _toks(q)[:1]


def _rrf(lists, k=RRF_K):
    scores = {}
    for ranked in lists:
        for rank, u in enumerate(ranked):
            scores[u] = scores.get(u, 0.0) + 1.0 / (k + rank + 1)
    return [u for u, _ in sorted(scores.items(), key=lambda x: -x[1])]


def _dedupe(ids):
    seen, out = set(), []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


# ── generation prompts ──────────────────────────────────────────────────────
def _sys_prompt(gen_style: str) -> str:
    base = "你是 FIN-MATE 金融研究助手。只用畀嘅資料答；資料無提及就答「KB 無資料」唔好作。"
    if gen_style == "normalized":
        return base + (
            "\n規則："
            "\n1. 每句 claim 後加 inline 標註【KB:檔案名】。"
            "\n2. 一定要引用精確數字（百分比、金額、年度/季度、倍數），唔好省略或改寫到變義。"
            "\n3. 若資料只覆蓋答案一部分，明確標出「資料冇提供」嘅點，唔准靠記憶補。"
            "\n4. 結尾列「## 來源」，每個來源格式 `檔案全名`。"
        )
    return base + "每句 claim 後加 inline 標註【KB:檔案名】；結尾列「## 來源」檔案全名。都係唔好靠估或者著。\n\n資料：\n"


def _ctx(nodes, extra=None):
    """nodes: list[(docid, text)]；extra: dict[docid -> snippet]（grep channel）。"""
    lines = []
    for i, (fid, text) in enumerate(nodes, 1):
        lines.append(f"[{i}] <{fid}>\n{text[:2000].strip()}")
    for fid, snip in (extra or {}).items():
        lines.append(f"[-] <{fid} | grep>\n{snip.strip()[:2000]}")
    return "\n".join(lines)


# ── corpus builders ─────────────────────────────────────────────────────────
def _extractors():
    from llama_index.readers.file.html import HTMLTagReader
    from llama_index.readers.file.pymu_pdf import PyMuPDFReader
    from llama_index.readers.file.tabular import CSVReader

    return {".csv": CSVReader(concat_rows=True), ".html": HTMLTagReader(), ".pdf": PyMuPDFReader()}


def _text_files() -> list[str]:
    return [str(p) for p in sorted(TEXT_DIR.glob("*.txt"))]


def _vis_files() -> list[str]:
    return [str(p) for p in sorted(VIS_DIR.glob("*")) if p.suffix != ".png"]


def _build_index(chunk_size: int, vis: bool, embed_model_name: str = "BAAI/bge-small-en-v1.5") -> D7Backend:
    backend = D7Backend(chunk_size=chunk_size, chunk_overlap=50, embed_model_name=embed_model_name, index="d7")
    files = _text_files() + (_vis_files() if vis else [])
    backend.add_from_files(files, file_extractor=_extractors() if vis else {})
    return backend


# ── strategies (local) ──────────────────────────────────────────────────────
def _dense(backend, q, k):
    return backend.retrieve(q, top_k=k)


def _sparse(backend, pattern, limit=64):
    out = []
    for node in backend._vector_index.docstore.docs.values():
        txt = node.text or ""
        if re.search(pattern, txt, re.IGNORECASE):
            fid = _docid(node.metadata.get("file_path", ""))
            if fid not in [o[0] for o in out]:
                out.append((fid, txt))
    return out[:limit]


def _node_ent(backend, q, strategy, events, doc_uris=None):
    if strategy == "naive":
        hits = _dense(backend, q, D7["naive"])
        uris = _dedupe([_docid(n.metadata.get("file_path", "")) for n in hits])
        by_id = {}
        for n in hits:
            by_id.setdefault(_docid(n.metadata.get("file_path", "")), []).append(n)
        ctx_nodes = [(fid, by_id[fid][0].text) for fid in uris]
        return uris, ctx_nodes, {}
    hits = _dense(backend, q, D7["hybrid"])
    dense_ids = [_docid(n.metadata.get("file_path", "")) for n in hits]
    grab = _sparse(backend, "|".join(_terms(q)))[:20]
    merged = _dedupe(_rrf([dense_ids, [g[0] for g in grab]]))
    best = {}
    for n in hits:
        fid = _docid(n.metadata.get("file_path", ""))
        sc = float(n.metadata.get("score") or 0)
        if fid in merged and (fid not in best or sc > best[fid][1]):
            best[fid] = (n.text, sc)
    ctx_nodes = [(fid, best[fid][0]) for fid in merged if fid in best]
    extra = {fid: snip for fid, snip in grab if fid in merged}
    return merged, ctx_nodes, extra


async def _answer(q, fid, cat, gen_style, ctx, trace):
    msgs = [{"role": "system", "content": _sys_prompt(gen_style)}, {"role": "user", "content": q}]
    if gen_style == "normal":
        msgs[0]["content"] += ctx  # normal prompt embeds 資料 right after 來源 line
    else:
        msgs[0]["content"] += "\n\n資料：\n" + ctx
    return await _lib.ark_complete(msgs, max_tokens=512, trace=trace)


def _trap_pass(answer):
    a = (answer or "").lower()
    return any(u in a for u in USELESS_ANS)


async def _run_one(backend, q, eid, cat, gen_style, strategy):
    events = []
    t = time.perf_counter()
    uris, ctx_nodes, extra = _node_ent(backend, q, strategy, events)
    ms_retr = (time.perf_counter() - t) * 1000
    probes = _dense(backend, q, 5)
    score = max((float(n.metadata.get("score") or 0) for n in probes), default=0.0)
    events.append({"strategy": strategy, "eid": eid, "category": cat, "stage": "retrieve",
                   "ts": datetime.now().isoformat(), "ms": ms_retr, "tokens": {}, "score": score,
                   "uris": uris, "detail": {"n_ctx_docs": len(ctx_nodes), "n_grep": len(extra)}})
    trace = []
    ans = await _answer(q, eid, cat, gen_style, _ctx(ctx_nodes, extra), trace)
    events.append({"strategy": strategy, "eid": eid, "category": cat, "stage": "answer",
                   "ts": datetime.now().isoformat(), "ms": ans.ms,
                   "tokens": {"prompt": ans.prompt_tokens, "completion": ans.completion_tokens,
                              "cached": ans.cached_tokens}})
    return dict(strategy=strategy, eid=eid, category=cat, uris=uris, answer=ans.text,
                events=events, extra={"usage": {"prompt": ans.prompt_tokens, "completion": ans.completion_tokens,
                                                "cached": ans.cached_tokens}, "transcript": trace, "ms": ans.ms})


AXES = {
    "default": {"chunk_size": 512, "vis": False, "gen": "normal"},
    "chunk": {"chunk_size": 256, "vis": False, "gen": "normal"},
    "mm": {"chunk_size": 512, "vis": True, "gen": "normal"},
    "gen": {"chunk_size": 512, "vis": False, "gen": "normalized"},
}
STRAT_NAMES = ("naive", "hybrid")


def _mu(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def _fmt(v, nd=3):
    return f"{v:.{nd}f}" if isinstance(v, (int, float)) and v is not None else "n/a"


def _write_report(s_dir, strat, s, items):
    rows = s["rows"]
    fact = [r for r in rows if r["cat"] != "trap"]
    traps = [r for r in rows if r["cat"] == "trap"]
    lines = [f"# report · d7_{s['axis']}_{strat} · {len(rows)} items", "",
             f"- recall@5: **{_fmt(_mu([r['recall5'] for r in fact]))}**  prec@5: {_fmt(_mu([r['prec5'] for r in fact]))}  "
             f"MRR@5: {_fmt(_mu([r['mrr5'] for r in fact]))}  nDCG@5: {_fmt(_mu([r['ndcg5'] for r in fact]))}",
             f"- answer-F1: **{_fmt(_mu([r['answer_f1'] for r in fact]))}**"
             + (f"  trap 唔作: {sum(r['trap_pass'] for r in traps)}/{len(traps)}" if traps else ""),
             f"- cost: **${_fmt(sum(r['usd'] for r in rows), 4)}**  mean/run: {_fmt(sum(r['ms'] for r in rows) / max(len(rows), 1), 0)} ms",
             f"- errors: {s['errors'] or '—'}", "", "## per-item", "",
             "| eid | cat | recall@5 | prec@5 | mrr@5 | ndcg@5 | answer_F1 | trap | usd |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['eid']} | {r['cat']} | {_fmt(r['recall5'])} | {_fmt(r['prec5'])} | {_fmt(r['mrr5'])} "
                     f"| {_fmt(r['ndcg5'])} | {_fmt(r['answer_f1'])} | {'PASS' if r['cat'] == 'trap' and r['trap_pass'] else '-'} "
                     f"| ${_fmt(r['usd'], 6)} |")
    (s_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


async def _run(args):
    _lib.load_env()
    out_root = Path(args.out) if args.out else ROOT / "experiments" / "runs" / time.strftime("%y%m%d_%H%M")
    out_root.mkdir(parents=True, exist_ok=True)

    axes = [a for a in AXES if not args.only or a in args.only.split(",")]
    items_full = d7_items(vis=True)   # full 20 for mm; text runs filter needles out
    text_items = CURRENT_ITEMS

    # build indices (cache per (chunk,vis))
    indexes = {}
    for ax in axes:
        key = f"{AXES[ax]['chunk_size']}-{AXES[ax]['vis']}"
        if key not in indexes:
            t = time.perf_counter()
            cfg = AXES[ax]
            indexes[key] = _build_index(cfg["chunk_size"], cfg["vis"])
            print(f"[idx] {key} built in {time.perf_counter()-t:.1f}s")

    golds = {}
    for i in items_full:
        golds[i["eid"]] = {"cat": i["cat"], "gold": resolve_gold_local(i) if i["cat"] != "trap" else set(),
                           "answer": i["gold"]}

    budget = args.max_tokens
    used = 0
    summary = {}
    run_meta = {"tag": out_root.name, "ts": _now(), "embed": indexes[list(indexes)[0]].embed_model_name,
                "prices": _lib.PRICES, "rrf_k": RRF_K, "n_items_text": len(text_items),
                "n_items_mm": len(items_full), "axes": AXES, "max_tokens_budget": budget,
                "model": "seed-1-6-flash-250715 (Ark)", "retrieve_only": args.retrieve_only}
    (out_root / "run_meta.json").write_text(json.dumps(run_meta, ensure_ascii=False, indent=2))

    for ax in axes:
        cfg = AXES[ax]
        idx = indexes[f"{cfg['chunk_size']}-{cfg['vis']}"]
        for strat in STRAT_NAMES:
            s_dir = out_root / f"d7_{ax}_{strat}"
            s_dir.mkdir(parents=True, exist_ok=True)
            items = items_full if cfg["vis"] else text_items
            if args.smoke:
                items = [i for i in items if i["eid"] in {"f1", "mb4"}]
            results, all_events = [], []
            for item in items:
                if used + EST_TOKENS_PER_ITEM > budget and not args.retrieve_only:
                    continue
                try:
                    res = await _run_one(idx, item["q"], item["eid"], item["cat"], cfg["gen"], strat)
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
            rows = []
            for r in results:
                g = golds[r["eid"]]
                row = {"eid": r["eid"], "cat": r["category"], "axis": ax}
                row["recall5"] = recall_at_k(g["gold"], r["uris"], 5) if g["cat"] != "trap" else None
                row["prec5"] = precision_at_k(g["gold"], r["uris"], 5) if g["cat"] != "trap" else None
                row["mrr5"] = mrr_at_k(g["gold"], r["uris"], 5) if g["cat"] != "trap" else None
                row["ndcg5"] = ndcg_at_k(g["gold"], r["uris"], 5) if g["cat"] != "trap" else None
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
            summary[f"d7_{ax}_{strat}"] = {"rows": rows, "errors": [r["eid"] for r in results if "error" in r],
                                           "axis": ax, "strategy": strat}
            _write_report(s_dir, strat, summary[f"d7_{ax}_{strat}"], items)
            print(f"[d7_{ax}_{strat}] n={len(rows)} recall5={_fmt(_mu([r['recall5'] for r in rows if r['cat']!='trap']))} "
                  f"F1={_fmt(_mu([r['answer_f1'] for r in rows if r['cat']!='trap']))} used_tokens={used}")

    _write_summary(out_root, summary)
    run_meta["used_tokens"] = used
    (out_root / "run_meta.json").write_text(json.dumps(run_meta, ensure_ascii=False, indent=2))
    print(f"tokens used: {used}/{budget}\ndone → {out_root}")


def _write_summary(out_root, summary):
    lines = ["# D7 corpus-shaping RAG SUMMARY", "", f"- tag: {out_root.name}   runs: {_now()}",
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
    lines.append("> 對比 D4（OpenViking + Ark embed）：naive recall@5 0.964 / MRR 0.762 / answer-F1 0.109；"
                 "hybrid recall@5 0.964 / MRR 0.929 / answer-F1 0.127（RESULTS.md）。")
    (out_root / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="D7 corpus-shaping RAG runner")
    p.add_argument("--smoke", action="store_true", help="每 run 得 2 題（f1/mb4）")
    p.add_argument("--only", default="", help="逗號分隔軸：default,chunk,mm,gen")
    p.add_argument("--out", default="", help="輸出目錄（預設 experiments/runs/<ts>）")
    p.add_argument("--max-tokens", type=int, default=500_000)
    p.add_argument("--retrieve-only", action="store_true", help="stub LLM，只驗 retrieval")
    args = p.parse_args()
    if args.retrieve_only:
        import experiments.rag_bench.strategies as S

        S.ark_complete = _stub
    asyncio.run(_run(args))


async def _stub(msgs, model=None, *, max_tokens=512, caching=False, trace=None):
    c = _lib.Completion(text="", prompt_tokens=0, completion_tokens=0, cached_tokens=0, ms=0.0)
    if trace is not None:
        trace.append({"llm": "stub", "msgs": msgs, "text": "", "tokens": (0, 0, 0), "ms": 0})
    return c


if __name__ == "__main__":
    main()