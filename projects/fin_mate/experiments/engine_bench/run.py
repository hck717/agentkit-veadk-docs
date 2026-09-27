"""FIN-MATE D6 引擎對比：同一 prompt 集（6 sets 抽 12）→ Ollama vs Ark。

量度（每 prompt × iter，concurrency 1）：
  TTFT         首批 token 前嘅時間（Ollama = prompt_eval_duration；Ark = streaming 第一個 delta）
  total_ms     完成一輪嘅總時間
  throughput   tokens/s（Ollama = eval_count/eval_duration；Ark = 總 tokens/total）
  usage / $    用 _lib.usd；Ollama $0、Ark 用真 usage。

冇 MODEL_AGENT_API_KEY → Ark 欄行 `ark(mock)`：用 seeded 參數分佈模擬，唔係真 call，
report 會標明。做完真 Ark 嘅 measurements 存 `<this>/measurements_ark.jsonl` 留待下次 mock 用。

輸出：experiments/engine_bench/report.md + run.json。
用法：`./.venv/bin/python -m experiments.engine_bench.run`
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments import _lib  # noqa: E402

THIS = Path(__file__).resolve().parent
GOLDEN_ROOT = ROOT / "eval" / "golden_datasets"
OLLAMA_BASE = "http://localhost:11434"
OLLAMA_MODEL = "qwen3:4b-instruct-2507-q4_K_M"
ARK_MODEL = "seed-1-6-flash-250715"

SET_FILES = {
    "qa/fact_single", "qa/fact_multi", "tool_call/calc_expr",
    "tool_call/news_extract", "sentiment/sent_3way", "sentiment/sent_score",
}
N_PER_SET = 2
ITER = 10


def load_prompts(seed: int = 7) -> list[dict]:
    rng = random.Random(seed)
    recs = []
    for rel in sorted(SET_FILES):
        lines = (GOLDEN_ROOT / f"{rel}.jsonl").read_text(encoding="utf-8").splitlines()
        pool = [json.loads(l) for l in lines if l.strip()]
        for r in rng.sample(pool, min(N_PER_SET, len(pool))):
            text = r["prompt"]
            if r["type"] == "qa" and r.get("context"):
                text = f"{text}\n\n背景資料：{r['context']}\n\n請根據背景資料回答。"
            recs.append({"prompt_id": r["id"], "prompt": text, "set": r["set"]})
    return recs


# ---- Ollama ----------------------------------------------------------

async def _ollama_once(prompt: str) -> dict:
    import httpx

    body = {"model": OLLAMA_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False, "think": False, "temperature": 0,
            "options": {"num_predict": 128}}
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=180) as c:
        r = await c.post(OLLAMA_BASE.rstrip("/") + "/api/chat", json=body)
        r.raise_for_status()
        j = r.json()
    total_ms = (time.perf_counter() - t0) * 1000
    ttft = int(j.get("prompt_eval_duration", 0) or 0) / 1e6  # ns→ms（約首 token）
    eval_ns = int(j.get("eval_duration", 0) or 0) / 1e9
    out_tok = int(j.get("eval_count", 0) or 0)
    in_tok = int(j.get("prompt_eval_count", 0) or 0)
    tok_s = out_tok / eval_ns if eval_ns > 0 else 0.0
    return {"ttft_ms": ttft, "total_ms": total_ms, "prompt_tokens": in_tok,
            "completion_tokens": out_tok, "cached": 0, "tok_per_s": tok_s,
            "output": ((j.get("message") or {}).get("content") or "")[:20]}


# ---- Ark ／ mock -----------------------------------------------------

async def _ark_once(prompt: str, client) -> dict:
    t0 = time.perf_counter()
    stream = await client.responses.create(
        model=ARK_MODEL, input=[{"role": "user", "content": prompt}],
        stream=True, max_output_tokens=128,
        thinking={"type": "disabled"}, temperature=0)
    ttft = None
    text = ""
    total_ms = 0
    usage = None
    try:
        async for ev in stream:
            typ = getattr(ev, "type", "")
            now = (time.perf_counter() - t0) * 1000
            if ttft is None and typ in ("response.content_part.delta", "response.output_text.delta"):
                ttft = now
            if typ in ("response.content_part.delta", "response.output_text.delta"):
                text += str(getattr(ev, "delta", "") or "")
            if typ == "response.completed":
                total_ms = now
                resp = getattr(ev, "response", None)
                usage = getattr(resp, "usage", None) or getattr(ev, "usage", None)
    finally:
        await stream.close()
    total_ms = total_ms or ((time.perf_counter() - t0) * 1000)
    ttft = ttft or total_ms
    if usage:
        p_in = getattr(usage, "input_tokens", None) or 0
        c_out = getattr(usage, "output_tokens", None) or 0
        cached = getattr(getattr(usage, "input_tokens_details", None), "cached_tokens", 0) or 0
        prompt_t = p_in or _lib.estimate_tokens(len(prompt))
        comp_t = c_out or (_lib.estimate_tokens(len(text)) or 16)
        if not p_in:
            cached = 0
    else:
        prompt_t = _lib.estimate_tokens(len(prompt))
        comp_t = _lib.estimate_tokens(len(text)) or 16
        cached = 0
    tok_s = (prompt_t + comp_t) / (total_ms / 1000) if total_ms > 0 else 0.0
    return {"ttft_ms": ttft, "total_ms": total_ms, "prompt_tokens": prompt_t,
            "completion_tokens": comp_t, "cached": cached, "tok_per_s": tok_s,
            "output": text[:20]}


def _mock_ark_once(prompt: str, seed: int) -> dict:
    rnd = random.Random(seed)
    prompt_t = _lib.estimate_tokens(len(prompt))
    comp_t = rnd.randint(24, 80)
    ttft = rnd.lognormvariate(math.log(600), 0.35)
    tok_s = rnd.uniform(25, 50)
    total_ms = (prompt_t + comp_t) / tok_s * 1000
    return {"ttft_ms": ttft, "total_ms": total_ms, "prompt_tokens": prompt_t,
            "completion_tokens": comp_t, "cached": 0, "tok_per_s": tok_s,
            "output": "(mock)"}


# ---- 統計 / report ---------------------------------------------------

def _pct(vals, p):
    if not vals:
        return None
    s = sorted(vals)
    k = min(len(s) - 1, int(round(p / 100 * (len(s) - 1))))
    return s[k]


def _agg(records: list[dict]) -> dict:
    ttfts = [r["ttft_ms"] for r in records]
    return {"n": len(records),
            "ttft_p50": _pct(ttfts, 50), "ttft_p95": _pct(ttfts, 95),
            "ttft_mean": sum(ttfts) / len(ttfts),
            "total_mean": sum(r["total_ms"] for r in records) / len(records),
            "tok_s": sum(r["tok_per_s"] for r in records) / len(records),
            "prompt_tokens": sum(r["prompt_tokens"] for r in records),
            "completion_tokens": sum(r["completion_tokens"] for r in records),
            "cached": sum(r["cached"] for r in records),
            "usd": sum(_lib.usd(r["prompt_tokens"], r["completion_tokens"], r["cached"]) for r in records),
            "mock": records[0].get("mock", False)}


def _write_md(path, prompts, by_engine) -> None:
    lines = [f"# Engine Bench · {time.strftime('%Y-%m-%d %H:%M:%S')}",
             f"- prompts: {len(prompts)} × iter {ITER}（concurrency 1）",
             f"- ollama: {OLLAMA_MODEL}（local, $0）  ark: {ARK_MODEL}",
             f"- prompt ids: {', '.join(p['prompt_id'] for p in prompts)}",
             "", "## per-engine aggregate", "",
             "| engine | n | TTFT p50 ms | TTFT p95 ms | mean tot ms | tok/s | tokens(p/c) | usd |",
             "|---|---|---|---|---|---|---|---|"]
    for eng, agg in by_engine.items():
        mock = " (mock)" if agg["mock"] else ""
        lines.append(f"| {eng}{mock} | {agg['n']} | {agg['ttft_p50']:.0f} | {agg['ttft_p95']:.0f} "
                     f"| {agg['total_mean']:.0f} | {agg['tok_s']:.1f} "
                     f"| {agg['prompt_tokens']}/{agg['completion_tokens']} | ${agg['usd']:.4f} |")
    lines += ["", "## per prompt", "", "| prompt | engine | TTFT p50 ms | TTFT p95 ms | mean tot ms | tok/s | tok(p) | usd |",
              "|---|---|---|---|---|---|---|---|"]
    for rec in prompts:
        for eng in by_engine:
            agg = by_engine[eng]
            sub = agg.get("per_prompt", {}).get(rec["prompt_id"])
            if not sub:
                continue
            mock = " (mock)" if sub["mock"] else ""
            prefix = f"{eng}{mock}" if eng == "ark" else eng
            lines.append(f"| {rec['prompt_id']} | {prefix} | {sub['ttft_p50']:.0f} | {sub['ttft_p95']:.0f} "
                         f"| {sub['total_mean']:.0f} | {sub['tok_s']:.1f} "
                         f"| {sub['prompt_tokens']} | ${sub['usd']:.4f} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _existing_counts() -> tuple[dict[str, int], dict[str, int]]:
    counts = {"ollama": {}, "ark": {}}
    for eng in counts:
        f = THIS / f"measurements_{eng}.jsonl"
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            recd = json.loads(line)
            counts[eng][recd["prompt_id"]] = counts[eng].get(recd["prompt_id"], 0) + 1
    return counts["ollama"], counts["ark"]


async def main() -> int:
    _lib.load_env()
    prompts = load_prompts()
    print(f"[bench] prompts={len(prompts)}  iter={ITER}  ollama={OLLAMA_MODEL}")

    need_bar, need_ark = {}, {}
    mc_oll, mc_ark = _existing_counts()
    for rec in prompts:
        pid = rec["prompt_id"]
        need_bar[pid] = max(0, ITER - mc_oll.get(pid, 0))
        need_ark[pid] = max(0, ITER - mc_ark.get(pid, 0))
    todo = [r for r in prompts if need_bar[r["prompt_id"]] or need_ark[r["prompt_id"]]]
    print(f"[bench] resume: {len(prompts) - len(todo)} prompts done, {len(todo)} to run")

    ark_client = None
    ark_mock = not os.environ.get("MODEL_AGENT_API_KEY", "").strip()
    if not ark_mock:
        from volcenginesdkarkruntime import AsyncArk
        ark_client = AsyncArk(base_url=os.environ["MODEL_AGENT_API_BASE"],
                              api_key=os.environ["MODEL_AGENT_API_KEY"])
    print(f"[bench] ark: {'mock (no key)' if ark_mock else 'live'}")

    by_engine = {"ollama": {"records": [], "per_prompt": {}},
                 "ark": {"records": [], "per_prompt": {}}}
    meas_files = {}
    try:
        for rec in todo:
            pid = rec["prompt_id"]
            print(f"[bench] {pid} (set={rec['set']})")
            n_oll, n_ark = need_bar[pid], need_ark[pid]
            for it in range(max(n_oll, n_ark)):
                if it < n_oll:
                    m = await _ollama_once(rec["prompt"])
                    m["prompt_id"], m["iter"] = pid, it
                    m["engine"] = "ollama"; m["mock"] = False
                    by_engine["ollama"]["records"].append(m)
                else:
                    m = None
                if it < n_ark:
                    if ark_mock:
                        a = _mock_ark_once(rec["prompt"], seed=hash(pid) % (2 ** 31) + it)
                    else:
                        a = await _ark_once(rec["prompt"], ark_client)
                    a["prompt_id"], a["iter"] = pid, it
                    a["engine"] = "ark"; a["mock"] = ark_mock
                    by_engine["ark"]["records"].append(a)
                    meas_files.setdefault("ark", open(THIS / "measurements_ark.jsonl", "a", encoding="utf-8")).write(
                        json.dumps(a, ensure_ascii=False) + "\n")
                if m is not None:
                    meas_files.setdefault("ollama", open(THIS / "measurements_ollama.jsonl", "a", encoding="utf-8")).write(
                        json.dumps(m, ensure_ascii=False) + "\n")
                for f in meas_files.values():
                    f.flush()
    finally:
        for f in meas_files.values():
            f.close()
        if ark_client is not None:
            await ark_client.close()

    for eng in by_engine:
        by_engine[eng]["records"] = []
        f = THIS / f"measurements_{eng}.jsonl"
        if f.exists():
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    by_engine[eng]["records"].append(json.loads(line))

    for eng, d in by_engine.items():
        agg = _agg(d["records"])
        per = {}
        for r in d["records"]:
            per.setdefault(r["prompt_id"], []).append(r)
        d.update(agg)
        d["per_prompt"] = {pid: _agg(rows) for pid, rows in per.items()}

    run = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
           "ollama_model": OLLAMA_MODEL, "ark_model": ARK_MODEL,
           "iter": ITER, "prompts": [{"id": p["prompt_id"], "set": p["set"]} for p in prompts],
           "engines": {eng: {k: v for k, v in d.items() if k != "per_prompt"} for eng, d in by_engine.items()}}
    (THIS / "run.json").write_text(json.dumps(run, ensure_ascii=False, indent=2))
    _write_md(THIS / "report.md", prompts, by_engine)
    print(f"\ndone → {THIS / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))