"""FIN-MATE E3: Redis vs OpenViking —— 同一套 RAG Lab eval（CURRENT_ITEMS 15 題）× 3 pipes × 2 DB。

用嘅測量 = experiments/rag_bench 同一套：
  - eval set：`rag_bench.eval_set.CURRENT_ITEMS`（15 題：fact 11 / trap 2 / multi_hop 2）
  - metrics：`eval_metrics.py`（recall@5 / prec@5 / MRR@5 / nDCG@5 / answer-F1 / trap PASS）
  - gold：`resolve_gold(item, doc_uris)` → doc-level URI-prefix set

3 pipes（hybrid / advanced / hyde_rrf）× 2 backends（OpenViking / Redis）= 6 configs，
每 config 完整產artifact：per-eid transcript（逐 LLM call）+ events.jsonl（stage 細事件）+ report.md，
再用 eval_metrics 出比較表 → REDIS_VS_OPENVIKING.md。

用法：
  # 前提：OpenViking + Redis 都跑緊（docker compose up -d openviking redis-stack）
  # 前提：Ollama 有 nomic-embed-text + qwen3:4b；MLX server（Qwen3-4B）喺 :8201
  PY -m experiments.redis_vs_openviking.run --backend redis   --pipe hybrid --port 8201 --model mlx-community/Qwen3-4B-Instruct-2507-4bit
  PY -m experiments.redis_vs_openviking.run --backend openviking --port 8201 --model mlx-community/Qwen3-4B-Instruct-2507-4bit   # 全部 pipe
  PY -m experiments.redis_vs_openviking.run --smoke           # 4 題快試（f1/f9/t1/m1）
  PY -m experiments.redis_vs_openviking.run --report          # 由 run.json 再生 REDIS_VS_OPENVIKING.md
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments import _lib  # noqa: E402
from experiments.eval_metrics import answer_f1, mrr_at_k, ndcg_at_k, precision_at_k, recall_at_k  # noqa: E402
from experiments.rag_bench.eval_set import CURRENT_ITEMS, all_doc_uris, resolve_gold  # noqa: E402
from experiments.rag_bench.run import USELESS_ANS, _fmt, _mu, _trap_pass  # noqa: E402

THIS = Path(__file__).resolve().parent
RESULTS = THIS / "run.json"
TRACES_DIR = THIS / "traces"

PIPES = ["hybrid", "advanced", "hyde_rrf"]
EXTRA_BODY = {"think": False, "chat_template_kwargs": {"enable_thinking": False}}
LOCAL_TIMEOUT = 300.0


# ── local LLM wrapper (同 lora_bench；trace 逐 call 記) ──────────────────────

async def _local_chat(msgs: list, base_url: str, model: str,
                      max_tokens: int = 512, temperature: float = 0.0, trace=None):
    import httpx as _httpx
    body = {"model": model, "messages": msgs, "stream": False,
            "max_tokens": max_tokens, "temperature": temperature, **EXTRA_BODY}
    t = time.perf_counter()
    async with _httpx.AsyncClient(timeout=LOCAL_TIMEOUT) as c:
        r = await c.post(base_url.rstrip("/") + "/v1/chat/completions", json=body)
        r.raise_for_status()
        j = r.json()
    ms = (time.perf_counter() - t) * 1000
    u = (j.get("usage") or {})
    cached = (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
    text = j["choices"][0]["message"]["content"]
    comp = _lib.Completion(text=text,
                           prompt_tokens=u.get("prompt_tokens", 0),
                           completion_tokens=u.get("completion_tokens", 0),
                           cached_tokens=cached, ms=ms)
    if trace is not None:
        trace.append({"llm": model, "msgs": msgs, "text": text,
                      "prompt_tokens": u.get("prompt_tokens", 0),
                      "completion_tokens": u.get("completion_tokens", 0),
                      "cached_tokens": cached, "ms": ms})
    return comp


def _local_wrapper(base_url: str, model: str):
    async def _f(msgs, _model=None, *, max_tokens=512, caching=False, trace=None,
                 output_schema=None, text_format=None):
        return await _local_chat(msgs, base_url=base_url, model=_model or model,
                                 max_tokens=max_tokens, temperature=0.0, trace=trace)
    return _f


# ── backend factory ─────────────────────────────────────────────────────────

def _build_openviking_kb(read_limit: int, force: bool = False):
    from experiments.redis_vs_openviking.redis_kb import OpenVikingKB
    return OpenVikingKB(read_limit=read_limit)


def _build_redis_kb(read_limit: int, force: bool = False):
    from experiments.redis_vs_openviking.redis_kb import RedisKB
    kb = RedisKB(read_limit=read_limit)
    kb._connect()
    kb.build(force=force)
    return kb


_PIPE_RL = {"hybrid": 200, "advanced": 2000, "hyde_rrf": 200}


# ── per-config run ──────────────────────────────────────────────────────────

async def run_config(backend_name: str, pipe: str, base_url: str, model: str,
                     build_kb_fn, kb_cache: dict, items: list, force_rebuild: bool = False) -> dict:
    """Run one config: backend × pipe → current_items + eval_metrics rows + full traces."""
    import experiments.redis_vs_openviking.strategies as strategies

    local_ark = _local_wrapper(base_url, model)
    strategies.ark_complete = local_ark

    read_limit = strategies.STRATS[pipe]["read_limit"]
    cache_key = (backend_name, read_limit)
    if cache_key not in kb_cache:
        kb_cache[cache_key] = build_kb_fn(read_limit, force=force_rebuild)
    kb = kb_cache[cache_key]

    doc_uris = kb.doc_uris()
    golds = {i["eid"]: {"cat": i["cat"],
                        "gold": resolve_gold(i, doc_uris) if i["cat"] != "trap" else set(),
                        "answer": i["gold"]} for i in items}

    run_fn = strategies.PIPES[pipe]
    block = {
        "backend": backend_name, "pipe": pipe,
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "records": [],
    }
    cfg_dir = TRACES_DIR / f"{backend_name}_{pipe}"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    all_events: list = []

    for item in items:
        eid, cat = item["eid"], item["cat"]
        trace: list = []
        t0 = time.perf_counter()
        try:
            res = await run_fn(item["q"], eid, cat, doc_uris, trace=trace,
                               ark_complete=local_ark, kb=kb)
            err = None
        except Exception as ex:
            res = {"strategy": pipe, "eid": eid, "category": cat, "uris": [], "answer": "",
                   "events": [{"strategy": pipe, "eid": eid, "stage": "ERROR",
                               "ts": time.strftime("%Y-%m-%dT%H:%M:%S.%f"), "ms": 0,
                               "detail": {"error": str(ex)}}], "extra": {}}
            err = str(ex)
        ms = sum(e.get("ms") or 0 for e in res["events"])
        if not ms:
            ms = (time.perf_counter() - t0) * 1000

        events = res["events"]
        usage = {
            "prompt": sum(e.get("tokens", {}).get("prompt", 0) for e in events),
            "completion": sum(e.get("tokens", {}).get("completion", 0) for e in events),
            "cached": sum(e.get("tokens", {}).get("cached", 0) for e in events),
        }

        gold = golds[eid]
        row = {"eid": eid, "cat": cat}
        row["recall5"] = recall_at_k(gold["gold"], res.get("uris", []), 5) if cat != "trap" else None
        row["prec5"] = precision_at_k(gold["gold"], res.get("uris", []), 5) if cat != "trap" else None
        row["mrr5"] = mrr_at_k(gold["gold"], res.get("uris", []), 5) if cat != "trap" else None
        row["ndcg5"] = ndcg_at_k(gold["gold"], res.get("uris", []), 5) if cat != "trap" else None
        row["answer_f1"] = answer_f1(gold["answer"], res.get("answer", "")) if cat != "trap" else None
        row["trap_pass"] = _trap_pass(res.get("answer", "")) if cat == "trap" else None
        row["ms"] = ms
        row["tokens"] = usage
        row["answer"] = res.get("answer", "")
        row["uris"] = res.get("uris", [])

        block["records"].append({
            "id": eid, "set": cat, "pred": res.get("answer", ""),
            "score": row["answer_f1"], "passed": row["trap_pass"] if cat == "trap" else None,
            "ms": round(ms, 1), "uris_retrieved": res.get("uris", []),
            "events": events, "extra": res.get("extra", {}), "metrics": row,
        })
        all_events.extend(events)

        # per-eid full trace（逐 LLM call + stage events）＝ stages 足版 replay
        ev_file = cfg_dir / f"{eid}.jsonl"
        with open(ev_file, "w", encoding="utf-8") as f:
            for ev in trace:
                f.write(json.dumps(ev, ensure_ascii=False, default=str) + "\n")
            for ev in events:
                f.write(json.dumps(ev, ensure_ascii=False, default=str) + "\n")
            f.write(json.dumps({
                "stage": "summary", "strategy": pipe, "eid": eid, "category": cat,
                "answer": res.get("answer", ""), "uris": res.get("uris", []),
                "events": events, "total_ms": ms, "usage": usage,
                "metrics": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items()
                            if k not in ("answer", "uris", "tokens")},
            }, ensure_ascii=False, default=str) + "\n")

        if err:
            print(f"  !! {pipe} {eid} ERROR: {err}")

    with open(cfg_dir / "events.jsonl", "w", encoding="utf-8") as f:
        for ev in all_events:
            f.write(json.dumps(ev, ensure_ascii=False, default=str) + "\n")

    block["total_ms"] = round(sum(r["ms"] for r in block["records"]), 1)
    block["usage"] = {k: sum(r["metrics"]["tokens"][k] for r in block["records"])
                      for k in ("prompt", "completion", "cached")}
    return block


# ── retrieval-only benchmark（不含 generation）───────────────────────────────

async def _bench_retrieval(pipe: str, backend: str):
    """Time pure retrieval (search + grep) for a pipe on a backend — NO LLM.

    Returns dict: {backend, pipe, read_limit, n_q, search_ms:[], grep_ms:[],
    total_ms, per_q:[{eid, search_ms, grep_ms}]}.
    Repeated 3× per query; report medians.
    """
    import experiments.redis_vs_openviking.strategies as strategies
    rl = strategies.STRATS[pipe]["read_limit"]
    build = _build_openviking_kb if backend == "openviking" else _build_redis_kb
    kb = build(rl, force=False)
    doc_uris = kb.doc_uris()

    rows = []
    for item in CURRENT_ITEMS:
        q = item["q"]
        s_times, g_times = [], []
        for _ in range(3):
            t0 = time.perf_counter()
            strategies._dense(kb, q, strategies.STRATS[pipe]["k"])
            s_times.append((time.perf_counter() - t0) * 1000)
            t0 = time.perf_counter()
            strategies._sparse(kb, "|".join(strategies._terms(q)))
            g_times.append((time.perf_counter() - t0) * 1000)
        rows.append({"eid": item["eid"], "cat": item["cat"],
                     "search_ms": statistics.median(s_times),
                     "grep_ms": statistics.median(g_times)})
    return {
        "backend": backend, "pipe": pipe, "read_limit": rl, "n_q": len(rows),
        "rows": rows,
        "search_ms": statistics.median([r["search_ms"] for r in rows]),
        "grep_ms": statistics.median([r["grep_ms"] for r in rows]),
        "total_ms": statistics.median([r["search_ms"] + r["grep_ms"] for r in rows]),
    }


def _bench_table(bench: list[dict]) -> list[str]:
    lines = ["| backend | pipe | read_limit | search(med ms) | grep(med ms) | total(med ms) |",
             "|---|---|---|---|---|---|"]
    for b in sorted(bench, key=lambda x: (x["backend"], x["pipe"])):
        lines.append(f"| {b['backend']} | {b['pipe']} | {b['read_limit']} "
                     f"| {b['search_ms']:.1f} | {b['grep_ms']:.1f} | {b['total_ms']:.1f} |")
    lines += ["", "| eid | cat |",
              "|---|---|"]
    return lines


# ── main ────────────────────────────────────────────────────────────────────

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["redis", "openviking", "all"], default="all")
    ap.add_argument("--pipe", choices=PIPES + ["all"], default="all")
    ap.add_argument("--port", type=int, default=8201)
    ap.add_argument("--model", default="local")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--bench", action="store_true", help="Retrieval-only benchmark (no LLM)")
    ap.add_argument("--force-rebuild", action="store_true", help="Force re-index Redis")
    args = ap.parse_args()

    if args.report or args.summary:
        results = _load_runs()
        _print_summary(results)
        _write_report(results)
        return

    if args.bench:
        import experiments.redis_vs_openviking.strategies as strategies
        bench: list[dict] = []
        for backend in (["redis", "openviking"] if args.backend == "all" else [args.backend]):
            for pipe in (PIPES if args.pipe == "all" else [args.pipe]):
                print(f"  bench {backend} × {pipe} (read_limit="
                      f"{strategies.STRATS[pipe]['read_limit']}) ...")
                bench.append(await _bench_retrieval(pipe, backend))
        BENCH = THIS / "RETRIEVAL_BENCH.json"
        BENCH.write_text(json.dumps(bench, ensure_ascii=False, indent=1), encoding="utf-8")
        for l in _bench_table(bench):
            print(l)
        print(f"Retrieval bench written → {BENCH.name} (3 medians per query, no LLM)")
        return

    base_url = f"http://127.0.0.1:{args.port}"
    kb_cache: dict = {}

    backends = ["openviking", "redis"] if args.backend == "all" else [args.backend]
    pipes = PIPES if args.pipe == "all" else [args.pipe]
    items = [i for i in CURRENT_ITEMS if i["eid"] in {"f1", "f9", "t1", "m1"}] if args.smoke else CURRENT_ITEMS

    print(f"E3 matrix: {len(backends)} backends × {len(pipes)} pipes × {len(items)} items")
    if "redis" in backends:
        print("Building Redis KB index...")
        for p in pipes:
            rl = _PIPE_RL[p]
            key = ("redis", rl)
            if key not in kb_cache:
                kb_cache[key] = _build_redis_kb(rl, force=args.force_rebuild)
        print("Redis KB ready.")

    for backend in backends:
        for pipe in pipes:
            print(f"\n{'='*60}")
            print(f"  {backend.upper()} × {pipe}")
            print(f"{'='*60}")
            block = await run_config(backend, pipe, base_url, args.model,
                                     _build_openviking_kb if backend == "openviking" else _build_redis_kb,
                                     kb_cache, items, force_rebuild=args.force_rebuild)
            _save_block(block)
            _print_block_summary(block)

    results = _load_runs()
    _print_summary(results)
    _write_report(results)


# ── persistence ─────────────────────────────────────────────────────────────

def _load_runs() -> list[dict]:
    if RESULTS.exists():
        try:
            return json.loads(RESULTS.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_block(block: dict):
    runs = _load_runs()
    key = (block["backend"], block["pipe"])
    runs = [r for r in runs if (r.get("backend"), r.get("pipe")) != key]
    runs.append(block)
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(runs, ensure_ascii=False, indent=1), encoding="utf-8")


def _print_block_summary(block: dict):
    rows = [r for r in block["records"]]
    fact = [r for r in rows if r["set"] != "trap"]
    traps = [r for r in rows if r["set"] == "trap"]
    ms = sum(r["ms"] for r in rows)
    fs = [_mu([r["metrics"]["recall5"] for r in fact]),
          _mu([r["metrics"]["mrr5"] for r in fact]),
          _mu([r["metrics"]["answer_f1"] for r in fact]),
          f"{sum(r['metrics']['trap_pass'] for r in traps)}/{len(traps)}" if traps else "—"]
    print(f"  {block['backend']:>10} | {block['pipe']:<10} | R@5={_fmt(fs[0])} MRR@5={_fmt(fs[1])} "
          f"ansF1={_fmt(fs[2])} trap={fs[3]} | {ms:.0f} ms")


# ── 分析方法：由 run.json + traces 計 stage/token/ctx 統計 ───────────────────

def _stage_stats(block: dict) -> tuple[float, float, float]:
    """Return (retrieve_ms, answer_ms, hyde_ms) summed across records' events."""
    ret = ans = hyd = 0.0
    for r in block["records"]:
        for e in r["events"]:
            ms = e.get("ms") or 0.0
            if e.get("stage") == "retrieve":
                ret += ms
            elif e.get("stage") == "answer":
                ans += ms
            elif e.get("stage") == "hyde":
                hyd += ms
    return ret, ans, hyd


def _ctx_stats(block: dict) -> dict:
    """Read per-eid traces → estimate ctx composition fed to the answer LLM.

    Returns {avg_prompt_tok, avg_dense_n, avg_dense_len, avg_grep_n, avg_grep_len}.
    We take the LAST LLM call per trace (the answer call, has the biggest prompt)
    and inspect its system message entries ([N] <doc> … content; grep ones are
    tagged "| grep").
    """
    stats = {"pt": [], "dn": [], "dl": [], "gn": [], "gl": [], "ans_ms": []}
    cfg_dir = TRACES_DIR / f"{block['backend']}_{block['pipe']}"
    if not cfg_dir.exists():
        return {k: float("nan") for k in stats}
    for f in sorted(cfg_dir.glob("*.jsonl")):
        if f.name == "events.jsonl":
            continue
        calls = []
        try:
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    d = json.loads(line)
                    if "stage" not in d and "msgs" in d:
                        calls.append(d)
        except Exception:
            continue
        if not calls:
            continue
        last = max(calls, key=lambda c: (c.get("prompt_tokens") or 0))
        sysmsg = next((m.get("content", "") for m in last.get("msgs", [])
                       if m.get("role") == "system"), "")
        markers = re.findall(r"\[\d+\] <([^>]*)>", sysmsg)
        blocks = re.split(r"\[\d+\] <[^>]*>\n?", sysmsg)
        lens = [len(b.split("\n", 1)[-1].strip()) if "\n" in b else len(b.strip())
                for b in blocks[1:]]
        dn, dl, gn, gl = [], [], [], []
        for mark, ln in zip(markers, lens):
            if "grep" in mark:
                gn.append(1), gl.append(ln)
            else:
                dn.append(1), dl.append(ln)
        stats["pt"].append(last.get("prompt_tokens") or 0)
        stats["dn"].append(len(dn)), stats["dl"].append(statistics.mean(dl) if dl else 0)
        stats["gn"].append(len(gn)), stats["gl"].append(statistics.mean(gl) if gl else 0)
        stats["ans_ms"].append(last.get("ms") or 0)
    return {
        "avg_prompt_tok": statistics.mean(stats["pt"]) if stats["pt"] else float("nan"),
        "avg_dense_n": statistics.mean(stats["dn"]) if stats["dn"] else float("nan"),
        "avg_dense_len": statistics.mean(stats["dl"]) if stats["dl"] else float("nan"),
        "avg_grep_n": statistics.mean(stats["gn"]) if stats["gn"] else float("nan"),
        "avg_grep_len": statistics.mean(stats["gl"]) if stats["gl"] else float("nan"),
        "avg_ans_ms": statistics.mean(stats["ans_ms"]) if stats["ans_ms"] else float("nan"),
    }


def _analysis_tables(results: list[dict]) -> str:
    """Build the Cantonese 分析 section (stage split + ctx composition table)."""
    out = []
    for block in sorted(results, key=lambda x: (x["backend"], x["pipe"])):
        ret, ans, hyd = _stage_stats(block)
        tot = block["total_ms"] or (ret + ans + hyd)
        cs = _ctx_stats(block)
        n = len(block["records"])
        ms_rec = round(tot / max(n, 1))
        out.append(
            f"| {block['backend']} × {block['pipe']} | {ret/n:.0f} ({ret/tot*100:.1f}%) "
            f"| {ans/n:.0f} ({ans/tot*100:.1f}%) "
            f"| {hyd/n:.0f} ({hyd/tot*100:.1f}%) | {ms_rec:.0f} "
            f"| {cs['avg_prompt_tok']:.0f} | {cs['avg_dense_n']:.1f}×{cs['avg_dense_len']:.0f} "
            f"| {cs['avg_grep_n']:.1f}×{cs['avg_grep_len']:.0f} "
            f"| {block.get('usage',{}).get('prompt',0):,}/{block.get('usage',{}).get('completion',0):,} |")
    return "\n".join(out)


def _analysis_section(results: list[dict]) -> list[str]:
    """Render Cantonese 關鍵調查 + Insights + Takeaways for the single report."""
    return [
        "## 4. 關鍵調查：點解 Redis 唔一定跑贏 OpenViking？",
        "",
        "有人會直覺「Redis 係 in-memory，梗係快過 OpenViking disk-based」。呢句喺 **retrieval 層面啱**，",
        "但喺 **end-to-end 唔成立**，因為總時長幾乎全部落入 answer LLM。",
        "",
        "### 4.1 retrieval 快慢根本睇唔到（<1% 佔比）",
        "",
        "| config | retrieve | answer LLM（MLX） | hyde | total ms/rec | avg prompt tok | dense 條目×(len) | grep 條目×(len) | total ptok/ctok |",
        "|---|---|---|---|---|---|---|---|---|",
        f"{_analysis_tables(results)}",
        "",
        "- Matrix 環境（16GB co-resident：MLX + Ollama + Redis + 2 個 OpenViking container）下，",
        "  Redis 嘅 `retrieve` stage 平均 ~**310–480ms**、OpenViking ~**620–650ms**（OpenViking 仲有",
        "  f1 cold-start 2536ms）——呢啲係「成個系統一齊跑緊」嘅環境數字。但無論邊個 DB，`retrieve`",
        "  都只佔總時長 **0.4–1%**；喺 60–90 秒嘅 E2E 入面完全消化唔到。**DB 本身快慢要睇 §3**。",
        "- 相反 **answer LLM 佔 99%+**（除咗 hyde_rrf 要另跑一轉 hyde 生成，先跌到 ~80–89%）。",
        "  所以「邊個 DB 快」=「邊個 prompt 少 token」=「邊個返出黎嘅 context 少字」。",
        "",
        "### 4.2 兩邊 context 形態根本唔同，先係速度分歧嘅來源",
        "",
        "- **Redis `search` 受 `read_limit` 管**：hybrid/hyde_rrf 用 `read_limit=200` → 每條 dense",
        "  只有 ~200 字；advanced 用 `read_limit=2000` → ~1325 字。但 **Redis `grep` 返成個 chunk**",
        "  （~1330 字/條，因為 FT.SEARCH 會帶埋成段 content 出嚟）。",
        "- **OpenViking `search` 唔受 read_limit 管**：返成段 section（~1750–1835 字/條）；但",
        "  **`grep` 係 line-level snippet**（平均 ~73 字/條）。",
        "- 效果：同一條質問，Redis 嘅 context 主要係「短 dense + 長 grep chunk」；OpenViking 係",
        "  「長 dense section + 微 grep」→ token 包大小同分布完全唔同。",
        "",
        "### 4.3 逐 pipe 解釋速度差異",
        "",
        "- **`hybrid`（read_limit=200）**：Redis 靠大 grep chunk（~1330×18）反而做到 ctx ~7.4k token；",
        "  OpenViking 靠長 dense（~1750×15）推出 ~8.6k token。差唔多量 → 總時間亦都差唔多",
        "  （Redis 61.5s 🆚 OpenViking 67.2s，Redis 微贏）。",
        "- **`advanced`（read_limit=2000）**：Redis 嘅 dense 變長（~1325×15）+ grep 又長（~1330×18）",
        "  → ctx 爆到 ~11k token（全場最肥）→ **Redis 94s 比 OpenViking 73s 慢**。所以唔係 Redis",
        "  慢，而係 advanced 畀咗最大 read_limit，Redis 兩條 channel 一齊變肥。",
        "- **`hyde_rrf`（read_limit=200）**：ctx 只保留 top-5 dense。Redis 5×198 + grep ~1330 補充",
        "  （~7k token）；OpenViking 叉開 grep（~73）純靠 5×~1835（~3.8k token，半數）→ 快一倍",
        "  （Redis 66.1s 🆚 OpenViking 32.8s）。呢個正正係「OpenViking 反而快」嘅典型一幕：",
        "  短 grep + 受控 top-5，ctx 細一半 → MLX prefill 時間減半。",
        "",
        "### 4.4 咁 Redis 有咩好處？（答得準啲）",
        "",
        "速度之外，Redis 喺 **answer-F1 上全面反超**（0.19–0.22 vs 0.08–0.10）：",
        "長而細嘅 chunk（含數字同前後文）令 LLM「照抄」原文機會大 → F1 高；OpenViking 用成段",
        "section 或者太短 snippet，LLM 傾向改寫 → 對 token overlap 唔著數。所以結論係：",
        "",
        "- **要準確（F1）**：Redis + hybrid / advanced（R@5=0.962、aF1≈0.2）。",
        "- **要快**：OpenViking + hyde_rrf（32.8s/rec），但 aF1 減半。",
        "- **平衡**：Redis × hybrid —— R@5=0.962、MRR=0.853、aF1=0.201、61.5s/rec，6 config 最好。",
        "",
        "## 5. Insights",
        "",
        "- **DB retrieval 快唔快，喺 E2E 睇唔到**：retrieval 佔總時長 <1%，answer LLM 佔 99%+；",
        "  真正決定 E2E 快慢嘅係 `read_limit` + `grep` 粒度 → prompt token 量。",
        "- **純 retrieval 真身：Redis 快 ~3×**（§3：~30–35ms 🆚 ~88–93ms）——Redis 喺 host 直接嵌",
        "  + 本地 FT KNN，OpenViking 要 HTTP 過 container 再喺入面嵌 + 搜。",
        "- **Redis 舊碼有 per-query `sleep(0.1)` artifact**：`_embed_batch` 對 batch-of-1 都瞓 100ms，",
        "  令 Redis search 由真身 ~30ms 被灌到 ~150ms；已修正（只有 bulk indexing 先瞓，唔影響入面",
        "  已記錄嘅 matrix 數據——嗰次係行緊舊碼，階段數字要高啲）。",
        "- **準度嚟自 chunk 粒度，唔係 vector index**：Redis 嘅長 chunk（~1330 字）含數字同前文後理，",
        "  LLM 照抄機會大 → answer-F1 約 2×（0.19–0.22 vs 0.08–0.10）。",
        "",
        "## 6. Takeaways",
        "",
        "- **要準確 + 唔介意慢少少** → **Redis × hybrid**（R@5=0.962、MRR=0.853、aF1=0.201、trap 2/2、61.5s/rec）。",
        "- **要最快** → **OpenViking × hyde_rrf**（32.8s/rec），但 aF1 得返一半（0.094）、R@5 稍跌（0.846）。",
        "- **純 retrieval 層面：Redis 係贏家**（~3×），但因為 LLM 佔 99%+，兩邊 E2E 差異係由 context",
        "  粒度控制——想快，就控制返 dense / grep 輸出長度，唔使換 DB。",
        "- **量度要分層**：用 `run.py --bench` 量純 retrieval、用 traces/run.json 量 E2E——兩者唔好撈埋。",
        "",
    ]


def _print_summary(results: list[dict]):
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    lines = ["| backend | pipe | recall@5 | prec@5 | MRR@5 | nDCG@5 | answer-F1 | trap | ms/rec |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(results, key=lambda x: (x["backend"], x["pipe"])):
        fact = [x for x in r["records"] if x["set"] != "trap"]
        traps = [x for x in r["records"] if x["set"] == "trap"]
        traps_hit = f"{sum(x['metrics']['trap_pass'] for x in traps)}/{len(traps)}" if traps else "—"
        rec = round(sum(r["records"][i]["ms"] for i in range(len(r["records"]))) / max(len(r["records"]), 1), 0)
        lines.append(f"| {r['backend']} | {r['pipe']} | {_fmt(_mu([x['metrics']['recall5'] for x in fact]))} "
                     f"| {_fmt(_mu([x['metrics']['prec5'] for x in fact]))} "
                     f"| {_fmt(_mu([x['metrics']['mrr5'] for x in fact]))} "
                     f"| {_fmt(_mu([x['metrics']['ndcg5'] for x in fact]))} "
                     f"| {_fmt(_mu([x['metrics']['answer_f1'] for x in fact]))} "
                     f"| {traps_hit} | {rec:.0f} |")
    for l in lines:
        print(l)


# ── report ──────────────────────────────────────────────────────────────────

def _load_bench() -> list[dict]:
    p = THIS / "RETRIEVAL_BENCH.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _write_report(results: list[dict]) -> None:
    lines = [
        "# FIN-MATE E3· Redis vs OpenViking（同一 pipeline、不同 DB：vector + sparse）",
        "",
        f"- generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- eval set：**同一套 rag_bench**（CURRENT_ITEMS {len(CURRENT_ITEMS)} 題：fact 11 / trap 2 / multi_hop 2）",
        f"- metrics：eval_metrics.py（recall@5 / prec@5 / MRR@5 / nDCG@5 / answer-F1 / trap）＝ 同 REPORT_full_260908_1551",
        "- embedding：Ollama nomic-embed-text 768d（兩邊一致）",
        "- answer LLM：本地 MLX Qwen3-4B（--port 8201）",
        "",
        "## 1. 方法論（Methodology）",
        "",
        "- **同一套 eval**：`rag_bench.eval_set.CURRENT_ITEMS` 15 題（fact 11 / trap 2 / multi_hop 2），",
        "  同 `REPORT_full_260908_1551.md` 完全一致；gold = `resolve_gold` 嘅 doc-level URI-prefix。",
        "- **同一套 metrics**：`eval_metrics.py`（recall@5 / prec@5 / MRR@5 / nDCG@5 / answer-F1 / trap PASS）。",
        "- **同一套 pipeline**：`strategies.py` 3 條 pipe（hybrid / advanced / hyde_rrf），",
        "  兩邊行嘅係同一份 code，唯一分別係 `kb.search()` / `kb.grep()` 落到唔同 DB。",
        "- **同一 embedding**：Ollama `nomic-embed-text` 768d（COSINE、`1 - dist` 轉 similarity）。",
        "- **同一 answer LLM**：本地 MLX Qwen3-4B-Instruct-2507-4bit（`:8201`）每題一個 chat completion。",
        "- **Redis backend**：`redis_kb.RedisKB` —— sentence 切 chunk（max 1500 字）→ 232 chunks",
        "  → FT HNSW vector + TEXT index；`search` = embed query → KNN → hydrate 到 `read_limit`；",
        "  `grep` = FT.SEARCH text match 返成個 chunk（~1500 字）。",
        "- **OpenViking backend**：`redis_kb.OpenVikingKB` —— veadk 原生 KB，doc-level L2 hydrate；",
        "  `search` 返成段 section content（read_limit 對唔到）；`grep` 係 line-level node snippet（~40–160 字）。",
        "- **Retrieval-only bench**：`run.py --bench` —— 每題 search + grep 量 3 次取 median，**完全不經 LLM**，",
        "  將「DB retrieval 速度」同「E2E（含 answer generation）」完全分開。",
        "- **執行方式**：一次一個 config 順序跑（無 parallel），避免 16GB 記憶體互相逼爆影響計時。",
        "",
        "## 2. 結果總覽（Results）",
        "",
        "| backend | pipe | recall@5 | prec@5 | MRR@5 | nDCG@5 | answer-F1 | trap | ms/rec | prompt/completion tokens |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    for block in sorted(results, key=lambda x: (x["backend"], x["pipe"])):
        fact = [x for x in block["records"] if x["set"] != "trap"]
        traps = [x for x in block["records"] if x["set"] == "trap"]
        traps_hit = f"{sum(x['metrics']['trap_pass'] for x in traps)}/{len(traps)}" if traps else "—"
        rec = round(block["total_ms"] / max(len(block["records"]), 1), 0)
        u = block.get("usage", {})
        lines.append(f"| **{block['backend']}** | {block['pipe']} | {_fmt(_mu([x['metrics']['recall5'] for x in fact]))} "
                     f"| {_fmt(_mu([x['metrics']['prec5'] for x in fact]))} "
                     f"| {_fmt(_mu([x['metrics']['mrr5'] for x in fact]))} "
                     f"| {_fmt(_mu([x['metrics']['ndcg5'] for x in fact]))} "
                     f"| {_fmt(_mu([x['metrics']['answer_f1'] for x in fact]))} "
                     f"| {traps_hit} | {rec:.0f} | {u.get('prompt',0):,}/{u.get('completion',0):,} |")

    bench = _load_bench()
    lines += ["", "## 3. Retrieval-only 比較（唔計 generation）", ""]
    if bench:
        lines += [
            "純 database retrieval（`--bench`：search + grep，每 query 3 次取 median，**無 LLM、無 hyde 生成**）：",
            "",
            "| backend | pipe | read_limit | search(med ms) | grep(med ms) | total(med ms) |",
            "|---|---|---|---|---|---|",
        ]
        for b in sorted(bench, key=lambda x: (x["backend"], x["pipe"])):
            lines.append(f"| {b['backend']} | {b['pipe']} | {b['read_limit']} "
                         f"| {b['search_ms']:.1f} | {b['grep_ms']:.1f} | {b['total_ms']:.1f} |")
        lines += [
            "",
            "- **Redis 真身快 ~3×**：search 29–32ms + grep ~2ms → total ~**30–35ms**",
            "  🆚 OpenViking search 77–81ms + grep ~11ms → total ~**88–93ms**。",
            "- 原因係兩邊 embed 位置唔同：Redis 喺 **host 直接嵌**（Ollama ~25ms）+ 本地 FT KNN（~5ms），",
            "  唔使過 container；OpenViking 要 **HTTP 打落 container → container 內再嵌 vector → 再搜**",
            "  （兩轉 localhost-Docker 來回 overhead）。",
            "- ⚠️ Redis 舊碼有 `time.sleep(0.1)` per `_embed_one`（batch-of-1 都照瞓）→ search 被灌到 ~150ms；",
            "  已修正為只有 bulk indexing（>1 條）先瞓。**上面數字係修正後、真身速度。**",
            "- Matrix 入面嘅 `retrieve` stage（Redis ~313–476ms / OpenViking ~616–653ms）係 16GB co-resident",
            "  （MLX + Ollama + Redis + 2 個 OpenViking container）+ OpenViking f1 cold-start 2536ms 之下嘅",
            "  環境數字，唔係 retrieval 本身：要睇 DB 快慢，以本節嘅 isolated bench 為準。",
            "",
        ]
    else:
        lines += [
            "（未有 `RETRIEVAL_BENCH.json` —— 先執行 `run.py --bench` 再 `--report` 就會有呢節。）",
            "",
        ]

    lines += _analysis_section(results)

    lines += ["", "## 7. per-eid 明細", ""]
    for block in sorted(results, key=lambda x: (x["backend"], x["pipe"])):
        lines.append(f"### {block['backend']} × {block['pipe']}")
        lines.append("")
        lines.append("| eid | cat | recall@5 | prec@5 | MRR@5 | nDCG@5 | ans-F1 | trap | ms | stage events |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for r in block["records"]:
            m = r["metrics"]
            tp = "PASS" if r["set"] == "trap" and m["trap_pass"] else "-"
            n_stage = len(r["events"])
            lines.append(f"| {r['id']} | {r['set']} | {_fmt(m['recall5'])} | {_fmt(m['prec5'])} "
                         f"| {_fmt(m['mrr5'])} | {_fmt(m['ndcg5'])} | {_fmt(m['answer_f1'])} "
                         f"| {tp} | {r['ms']:.0f} | {n_stage} |")
        lines.append("")
    (THIS / "REDIS_VS_OPENVIKING.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("REDIS_VS_OPENVIKING.md written（單一檔案：方法論 + 結果 + retrieval 對比 + 調查 + insights + takeaways）")


if __name__ == "__main__":
    asyncio.run(main())