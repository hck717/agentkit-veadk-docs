"""RAG 實驗室 runner：16 題 x 現役 pipe（naive/advanced/hybrid/corrective/adaptive/hyde），產三層 artifact + per-strategy report 同 SUMMARY。
agentic 已退役（唔再跑；`--only agentic` 會 KeyError）。

用法：
  python -m experiments.rag_bench.run --smoke           # 4 題快試
  python -m experiments.rag_bench.run --only hybrid     # 淨行一條 pipe
  python -m experiments.rag_bench.run --retrieve-only   # 唔起模型（stub LLM），淨驗 retrieval/plumbing

輸出結構（`--out` 預設 experiments/runs/<timestamag>）：
  run_meta.json                # 全域 config（model/prices/k/gate）> 可重現
  <strategy>/info.json         # 該 pipe config
  <strategy>/events.jsonl      # 全 item 嘅 stage 細到事件（trace 用）
  <strategy>/<eid>/transcript.jsonl  # 全 LLM call + function_call/response
  <strategy>/report.md / SUMMARY.md
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments import _lib  # noqa: E402
from experiments.eval_metrics import answer_f1, mrr_at_k, ndcg_at_k, precision_at_k, recall_at_k  # noqa: E402
from experiments.rag_bench import strategies  # noqa: E402
from experiments.rag_bench.eval_set import CURRENT_ITEMS, all_doc_uris, resolve_gold  # noqa: E402

USELESS_ANS = ("無資料", "没有", "no information", "not found", "唔知")

# 每 pipe 每題粗略 token/次（q + system + ctx + output 預算）。用嚟喺跑之前守 budget：
# 實際用量會喺每題之後用 responses usage 校正。agentic 已退役（唔喺 EST 內）。
EST_TOKENS_PER_ITEM = {"naive": 1500, "advanced": 10000, "hybrid": 1800,
                       "corrective": 2200, "adaptive": 1600, "hyde": 2200, "hyde_rrf": 2500}


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _cost(tokens):
    return _lib.usd(tokens.get("prompt", 0), tokens.get("completion", 0), tokens.get("cached", 0))


async def _run_agent_subprocess(item, s_dir, timeout):
    """Agentic 每題 spawn fresh subprocess（`python -c` 內嵌已實證體）：
    veadk Agent + ADK Runner 一定要喺無 active loop 嘅 sync 環境行，且經 `python -m`/module call 會甩
    litellm threadpool——所以直接用 -c 內嵌。JSON 落 <-eid>/item.json；超時 kill + 記 ERROR。"""
    eid = item["eid"]
    out_file = s_dir / eid / "item.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    q = item["q"]
    code = (
        "import sys, asyncio, time, json\n"
        "sys.path.insert(0, '.')\n"
        "from experiments import _lib\n"
        "from experiments.rag_bench import strategies as S\n"
        "from experiments.rag_bench.eval_set import all_doc_uris\n"
        "from google.adk.runners import Runner\n"
        "from google.adk.sessions.in_memory_session_service import InMemorySessionService\n"
        "from google.genai import types\n"
        f"q={q!r}; eid={eid!r}; cat={item['cat']!r}; out={str(out_file)!r}\n"
        "_lib.load_env()\n"
        "kb=S._kb(S.STRATS['agentic']['read_limit']); before=S._ov_snapshot(); agent=S._build_agent(kb)\n"
        "events=[]; t0=time.perf_counter()\n"
        "ss=InMemorySessionService()\n"
        "sid='rag-'+eid\n"
        "new_msg=types.Content(role='user', parts=[types.Part(text=q)])\n"
        "asyncio.run(ss.create_session(app_name='rag_bench', user_id='bench', session_id=sid))\n"
        "runner=Runner(agent=agent, app_name='rag_bench', session_service=ss)\n"
        "tr=[]\n"
        "for ev in runner.run(user_id='bench', session_id=sid, new_message=new_msg):\n"
        "    kind='final' if ev.is_final_response() else 'function_call' if ev.get_function_calls() else ('function_response' if ev.get_function_responses() else 'llm')\n"
        "    p={'kind':kind,'ts':str(getattr(ev,'timestamp',''))}\n"
        "    if ev.content is not None and ev.content.parts:\n"
        "        p['parts']=[]\n"
        "        for x in ev.content.parts:\n"
        "            xv=getattr(x,'text',None)\n"
        "            if xv is None: continue\n"
        "            p['parts'] += [str(y) for y in (xv if isinstance(xv,list) else [xv])]\n"
        "    for fc in ev.get_function_calls() or []:\n"
        "        p.setdefault('calls',[]).append({'name':getattr(fc,'name',''),'args':getattr(fc,'args',{})})\n"
        "    for fr in ev.get_function_responses() or []:\n"
        "        p.setdefault('responses',[]).append({'name':getattr(fr,'name',''),'response':getattr(fr,'response','')})\n"
        "    if ev.usage_metadata is not None:\n"
        "        um=ev.usage_metadata\n"
        "        p['usage']={'prompt':getattr(um,'prompt_token_count',0) or 0,'completion':getattr(um,'response_token_count',0) or 0,'cached':getattr(um,'cached_content_token_count',0) or 0}\n"
        "    tr.append(p)\n"
"ms=(time.perf_counter()-t0)*1000\n"
         "_final=[]\n"
         "for _ev in tr:\n"
         "    if _ev['kind']=='final': _final += _ev.get('parts') or []\n"
         "answer='\\n'.join(str(_p) for _p in _final)\n"
         "usage={'prompt':sum(e.get('usage',{}).get('prompt',0) for e in tr),'completion':sum(e.get('usage',{}).get('completion',0) for e in tr),'cached':sum(e.get('usage',{}).get('cached',0) for e in tr)}\n"
        "tools=[c.get('name') for e in tr for c in e.get('calls',[])]\n"
        "cite=S._cite(tr, answer); after=S._ov_snapshot()\n"
        "S._emit(events,'agentic',eid,cat,'agent',ms=ms,tokens=usage,detail={'tool_calls':tools,'citation':cite,'observer_delta':{'vectors':after.get('vectors')}})\n"
        "res={'strategy':'agentic','eid':eid,'category':cat,'uris':cite.get('retrieved',[]),'answer':answer,'events':events,'extra':{'transcript':tr,'usage':usage,'citation':cite,'tools':tools}}\n"
        "open(out,'w').write(json.dumps(res, ensure_ascii=False, default=str))\n"
    )
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-c", code,
        stdout=open(s_dir / eid / "sub.log", "w"), stderr=subprocess.STDOUT, cwd=str(ROOT))
    (s_dir / eid / "sub.code.py").write_text(code)
    try:
        await asyncio.wait_for(proc.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise TimeoutError(f"agentic {eid} 超時 {timeout}s")
    with open(s_dir / eid / "sub.log", "a") as _f:
        _f.write(f"\n[rc={proc.returncode}]\n")
    if not out_file.exists():
        raise RuntimeError(f"agentic {eid} subprocess 無輸出")
    return json.loads(out_file.read_text(encoding="utf-8"))


async def _stub_complete(msgs, model=None, *, max_tokens=512, caching=False, trace=None):
    import experiments._lib as lib
    c = lib.Completion(text="", prompt_tokens=0, completion_tokens=0, cached_tokens=0, ms=0.0)
    if trace is not None:
        trace.append({"llm": "stub", "msgs": msgs, "text": "", "prompt_tokens": 0,
                      "completion_tokens": 0, "cached_tokens": 0, "ms": 0})
    return c


def _trap_pass(answer):
    a = (answer or "").lower()
    return any(u in a for u in USELESS_ANS)


def _item_rows(results, golds):
    rows = []
    for r in results:
        gold = golds[r["eid"]]
        row = {"eid": r["eid"], "cat": r["category"]}
        row["answer_f1"] = answer_f1(gold["answer"] or "", r["answer"] or "") if gold["cat"] != "trap" else None
        if r["category"] == "trap":
            row["trap_pass"] = _trap_pass(r["answer"])
        row["recall5"] = recall_at_k(gold["gold"], r["uris"], 5) if gold["cat"] != "trap" else None
        row["prec5"] = precision_at_k(gold["gold"], r["uris"], 5) if gold["cat"] != "trap" else None
        row["mrr5"] = mrr_at_k(gold["gold"], r["uris"], 5) if gold["cat"] != "trap" else None
        row["ndcg5"] = ndcg_at_k(gold["gold"], r["uris"], 5) if gold["cat"] != "trap" else None
        row["usd"] = _cost(r.get("usage", r.get("tokens", {})))
        row["ms"] = r["ms"]
        row["tokens"] = r.get("usage", r.get("tokens", {}))
        rows.append(row)
    return rows


async def _run(args):
    _lib.load_env()
    key = os.environ.get("MODEL_AGENT_API_KEY", "")
    if args.retrieve_only:
        strategies.ark_complete = _stub_complete
        print(f"[retrieve-only] stub LLM，唔會真正 call model")
    elif not key:
        print("[warn] MODEL_AGENT_API_KEY 空 → 用 --retrieve-only 驗 retrieval/plumbing；填返 .env 先跑真 bench")

    strat_names = args.only.split(",") if args.only else list(strategies.STRATS)
    items = CURRENT_ITEMS if not args.smoke else [i for i in CURRENT_ITEMS if i["eid"] in {"f1", "f9", "t1", "m1"}]
    if args.retrieve_only:
        strat_names = [s for s in strat_names if s != "agentic"]

    out_root = Path(args.out) if args.out else ROOT / "experiments" / "runs" / time.strftime("%y%m%d_%H%M")
    out_root.mkdir(parents=True, exist_ok=True)
    doc_uris = all_doc_uris()
    golds = {i["eid"]: {"cat": i["cat"], "gold": resolve_gold(i, doc_uris) if i["cat"] != "trap" else set(),
                        "answer": i["gold"]} for i in items}
    budget = args.max_tokens
    used_tokens = 0

    run_meta = {"tag": out_root.name, "ts": _now(), "models": {"primary": os.environ.get("MODEL_PRIMARY", "?"),
               "agent": os.environ.get("MODEL_AGENT_MODEL_NAME", "?")}, "prices": _lib.PRICES,
               "gate": strategies.GATE, "rrf_k": strategies.RRF_K, "max_tokens_budget": budget,
               "strats": {k: v["desc"] for k, v in strategies.STRATS.items()},
               "n_items": len(items), "items": [i["eid"] for i in items], "retrieve_only": args.retrieve_only}
    (out_root / "run_meta.json").write_text(json.dumps(run_meta, ensure_ascii=False, indent=2))

    summary = {}
    for strat in strat_names:
        s_dir = out_root / strat
        s_dir.mkdir(parents=True, exist_ok=True)
        (s_dir / "info.json").write_text(json.dumps(strategies.STRATS[strat], ensure_ascii=False, indent=2))
        results, all_events = [], []
        est = EST_TOKENS_PER_ITEM[strat]
        for item in items:
            if used_tokens + est > budget and not args.retrieve_only:
                res = {"strategy": strat, "eid": item["eid"], "category": item["cat"], "uris": [], "answer": "",
                       "events": [{"strategy": strat, "eid": item["eid"], "stage": "BUDGET_SKIP",
                                   "tokens": {"used": used_tokens, "budget": budget}}],
                       "usage": {"prompt": 0, "completion": 0, "cached": 0}, "ms": 0,
                       "error": f"BUDGET_SKIP used={used_tokens}/budget={budget}"}
                all_events.extend(res["events"])
                results.append(res)
                continue
            t0 = time.perf_counter()
            trace = []
            try:
                if strat == "agentic" and not args.retrieve_only:
                    # 每題 fresh subprocess：agentic loop 喺同一進程會 hang，且逐題隔離 + 硬 timeout
                    res = await _run_agent_subprocess(item, s_dir, args.agent_timeout)
                else:
                    trace = []
                    res = await strategies.run(strat, item["q"], item["eid"], item["cat"], doc_uris, trace=trace)
                res["ms"] = sum(e.get("ms") or 0 for e in res["events"])
                res["usage"] = res.get("extra", {}).get("usage") or {
                    "prompt": sum(e.get("tokens", {}).get("prompt", 0) for e in res["events"]),
                    "completion": sum(e.get("tokens", {}).get("completion", 0) for e in res["events"]),
                    "cached": sum(e.get("tokens", {}).get("cached", 0) for e in res["events"])}
                res["ms"] = res.get("ms") or (time.perf_counter() - t0) * 1000
            except Exception as ex:
                res = {"strategy": strat, "eid": item["eid"], "category": item["cat"], "uris": [],
                       "answer": "", "events": [{"strategy": strat, "eid": item["eid"], "stage": "ERROR"}],
                       "usage": {"prompt": 0, "completion": 0, "cached": 0}, "ms": 0, "error": str(ex)}
            all_events.extend(res["events"])
            # transcript：agentic 用 Runner event；其他用 LLM trace（都係逐 call）
            t_dir = s_dir / item["eid"]
            t_dir.mkdir(parents=True, exist_ok=True)
            t_out = (res.get("extra", {}).get("transcript") if res.get("extra", {}).get("transcript")
                     else [e for e in trace])
            (t_dir / "transcript.jsonl").write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in t_out) + "\n")
            if res["answer"]:
                (t_dir / "answer.txt").write_text(res["answer"], encoding="utf-8")
            results.append(res)
            used_tokens += (res["usage"].get("prompt", 0) or 0) + (res.get("usage", {}).get("completion", 0) or 0)

        (s_dir / "events.jsonl").write_text(
            "\n".join(json.dumps(e, ensure_ascii=False) for e in all_events) + "\n")
        rows = _item_rows(results, golds)
        summary[strat] = {"rows": rows, "n": len(rows), "errors": [r["eid"] for r in results if "error" in r]}
        _write_report(s_dir, strat, summary[strat])
        print(f"[{strat}] n={len(rows)} err={summary[strat]['errors']} tokens={used_tokens}")

    run_meta["used_tokens"] = used_tokens
    (out_root / "run_meta.json").write_text(json.dumps(run_meta, ensure_ascii=False, indent=2))
    print(f"tokens used: {used_tokens}/{budget}")
    _write_summary(out_root, summary)
    print(f"done → {out_root}")


def _mu(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def _fmt(v, nd=3):
    return f"{v:.{nd}f}" if isinstance(v, (int, float)) and v is not None else "n/a"


def _write_report(s_dir, strat, s):
    rows = s["rows"]
    fact = [r for r in rows if r["cat"] != "trap"]
    traps = [r for r in rows if r["cat"] == "trap"]
    head = f"""# report · {strat} · {s['n']} items\n"""
    lines = [head, f"- recall@5: **{_fmt(_mu([r['recall5'] for r in fact]))}**  prec@5: {_fmt(_mu([r['prec5'] for r in fact]))}  "
                  f"MRR@5: {_fmt(_mu([r['mrr5'] for r in fact]))}  nDCG@5: {_fmt(_mu([r['ndcg5'] for r in fact]))}",
             f"- answer-F1: **{_fmt(_mu([r['answer_f1'] for r in fact]))}**  trap 唔作: {sum(r['trap_pass'] for r in traps)}/{len(traps)}"
             if traps else f"- answer-F1: **{_fmt(_mu([r['answer_f1'] for r in fact]))}**",
             f"- cost: **${_fmt(sum(r['usd'] for r in rows), 4)}**  mean/call-set: {_fmt(sum(r['ms'] for r in rows) / max(len(rows), 1), 1)} ms",
             f"- errors: {s['errors'] or '—'}",
             "", "## per-item", "", "| eid | cat | recall@5 | prec@5 | mrr@5 | ndcg@5 | answer_F1 | trap | usd |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['eid']} | {r['cat']} | {_fmt(r['recall5'])} | {_fmt(r['prec5'])} | {_fmt(r['mrr5'])} "
                     f"| {_fmt(r['ndcg5'])} | {_fmt(r['answer_f1'])} | {'PASS' if r['cat'] == 'trap' and r['trap_pass'] else '-'} "
                     f"| ${_fmt(r['usd'], 6)} |")
    (s_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_summary(out_root, summary):
    lines = ["# RAG Lab SUMMARY", "", f"- tag: {out_root.name}   runs: {_now()}",
             "| strategy | recall@5 | prec@5 | MRR@5 | nDCG@5 | answer-F1 | trap-hit | usd | ms/run |",
             "|---|---|---|---|---|---|---|---|---|"]
    for k in strategies.STRATS:
        if k not in summary:
            continue
        r = summary[k]["rows"]
        fact = [x for x in r if x["cat"] != "trap"]
        traps = [x for x in r if x["cat"] == "trap"]
        traps_hit = f"{sum(x['trap_pass'] for x in traps)}/{len(traps)}" if traps else "—"
        lines.append(f"| {k} | {_fmt(_mu([x['recall5'] for x in fact]))} | {_fmt(_mu([x['prec5'] for x in fact]))} "
                     f"| {_fmt(_mu([x['mrr5'] for x in fact]))} | {_fmt(_mu([x['ndcg5'] for x in fact]))} "
                     f"| {_fmt(_mu([x['answer_f1'] for x in fact]))} | {traps_hit} "
                     f"| ${_fmt(sum(x['usd'] for x in r), 4)} | {_fmt(sum(x['ms'] for x in r) / max(len(r), 1), 1)} |")
    lines.append("")
    lines.append("> 每條 pipe 定義同追蹤方法見 RAG_LAB.md；每個 stage 事件見 `<strategy>/events.jsonl`；"
                 "逐 call replay 見 `<strategy>/<eid>/transcript.jsonl`。")
    (out_root / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="RAG 實驗室 runner（6 pipe x 題）")
    p.add_argument("--smoke", action="store_true", help="得 4 題（f1/f9/t1/m1）")
    p.add_argument("--only", default="", help="逗號分隔 pipe 名")
    p.add_argument("--out", default="", help="輸出目錄")
    p.add_argument("--retrieve-only", action="store_true", help="stub LLM，只驗 retrieval/plumbing")
    p.add_argument("--max-tokens", type=int, default=500_000, help="全 run token 上限（預設 500K）")
    p.add_argument("--agent-timeout", type=int, default=240, help="agentic 每題 subprocess 硬 timeout 秒數")
    args = p.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()