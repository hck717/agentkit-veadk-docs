"""JEV bench（phase-2）：5 類任務 × 2-arm 對比「原裝 agent」vs「JEV agent」。

Phase-2 將 Jev 決策層開到成個 agent 嘅所有系統一決策點（唔淨係 tool-choice）：
  tool 揀工具             -> JEV choice（低 conf -> fallback 原裝 chat tool-call）
  rag 檢索 gate           -> JEV score（每份候選 doc 0-3，>=門檻先入 context）
  mem 記憶篩選 pushdown   -> JEV score（篩走唔相關/私隱記憶先餵 answer call）
  sent 情緒               -> JEV choice（3-way）+ 分數，對照 calibration
  wf 多步 workflow + noUL -> 每步 JEV choice + JEV noul（夾 steps_done + budget）

兩 arm 共用同一個 5-tool 工具盤 + 同一堆題目（15 題），共用 System Two 生成層
（最終答案、free-form args、檢索）。唯一唔同：原裝 arm 全部決定都係 chat，
JEV arm 行 `jev/gate.py` 嘅 System One 決策 + policy（門檻/escalation），
per-decision 成本（ms / tokens / μ$）落 `jev/ledger.py`。

用法（root = projects/fin_mate）：
  ./.venv/bin/python -m experiments.jev_bench.run --smoke
  ./.venv/bin/python -m experiments.jev_bench.run --only jev
  ./.venv/bin/python -m experiments.jev_bench.run --out experiments/jev_bench/results/x
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments import _lib  # noqa: E402
from experiments.eval_metrics import answer_f1, recall_at_k  # noqa: E402
from experiments.jev_bench.lib import jev_client  # noqa: E402
from experiments.rag_bench.eval_set import all_doc_uris  # noqa: E402
from experiments.rag_bench.strategies import RRF_K, _rrf, _terms  # noqa: E402
from eval.evaluators import ev_sentiment, extract_json  # noqa: E402

from jev import policy  # noqa: E402
from jev import decisions as D  # noqa: E402
from jev import actions  # noqa: E402
from jev import tier0  # noqa: E402
from jev.gate import decide_choice, decide_score, decide_noul  # noqa: E402

FLASH = "seed-1-6-flash-250715"
BENCH_DIR = Path(__file__).resolve().parents[0]
DS = BENCH_DIR / "datasets"

TOOL5 = D.TOOL5
_TOOL_BY_ID = {o["id"]: o["label"] for o in TOOL5}
_EXEC_TOOLS = {"calc", "read_news_file"}

RAG_CTX_TOP = 5
RAG_KEEP_FLOOR = policy.RAG_KEEP_FLOOR
RAG_KEEP_RATIO = policy.RAG_KEEP_RATIO
MEM_GATE_MIN = policy.MEM_GATE_MIN

TASK_ORDER = ["tool", "rag", "mem", "sent", "wf"]
TASK_NAMES = {"tool": "工具路由", "rag": "RAG 檢索 gating", "mem": "記憶篩選",
              "sent": "情緒分類", "wf": "多步 workflow＋noUL"}

EST = {"tool": 900, "rag": 3000, "mem": 1500, "sent": 400, "wf": 7000}

TOOL_SYSTEM = (
    "你係 fin-mate 金融研究 agent。可以揀嘅工具得呢 5 個（冇其他）："
    "calc（計數）、read_news_file（讀本地新聞 CSV）、fetch_news（抓某股票新聞頭條）、"
    "web_search（網上搜尋）、link_reader（讀 URL）。"
    "你必須輸出嚴格 JSON（唔加任何其他字）：{\"tool\": \"<tool>\", \"args\": {<參數>}}。"
    "calc → {\"expr\": \"<算式>\"}；read_news_file → {\"path\": \"<csv path>\"}；"
    "fetch_news → {\"ticker\": \"<代號>\"}；web_search → {\"query\": \"<查詢>\"}；"
    "link_reader → {\"url\": \"<url>\"}。"
)
SENT_SYSTEM = "你係金融新聞情緒分類器。嚴格跟 prompt 內嘅輸出格式：只輸出 positive / neutral / negative 其中一個字詞。"
MEM_SYSTEM = (
    "你係 fin-mate。下面係 CRM 儲低嘅用戶記憶（STM＝短期、LTM＝長期）+ 用戶問題。"
    "用相關記憶直接答；記憶冇講嘅地方就答「無相關記憶」，唔好作。"
)
CONT_SYSTEM = "你係 fin-mate 任務控制器。用戶任務未完或者仲有下一步就要做 → 答 YES；任務已做完 → 答 NO。只可以答 YES 或 NO。"

ARG_SYS = {
    "calc": "你係 fin-mate。將用戶想計嘅算式轉成嚴格 JSON，只有一個 key：{\"expr\": \"<算式>\"}。",
    "read_news_file": ("你係 fin-mate。output 嚴格 JSON 一個 key："
                       "{\"path\": \"<csv path>\"}（路徑用 data/news/sample_news.csv）。"),
    "fetch_news": ("你係 fin-mate。output 嚴格 JSON：{\"ticker\": \"<代號>\"}"
                   "（可以加 \"limit\": <數量> 指定抓幾多條）。"),
    "web_search": ("你係 fin-mate。output 嚴格 JSON：{\"query\": \"<查詢>\"}"
                   "（可以加 \"n\": <數量> 指定回幾多條）。"),
    "link_reader": "你係 fin-mate。output 嚴格 JSON 一個 key：{\"url\": \"<url>\"}。",
}

VARIANTS = {
    "original": {"desc": "原裝：所有決定全走 LLM chat"},
    "jev": {"desc": "JEV 介面層：System One 決策 + escalation；tool args 仍然 chat 生成"},
    "jev2": {"desc": "JEV 完整版（真 JEV）：System One 決策 + args 確定式填充，除咗最終答案同 escalation 外零 generation"},
    "jev3": {"desc": "JEV tier-0（確定式）：RAG gate 用 RRF、tool 用規則路由、mem 用 marker rule + 並行 score、noUL asymmetric（STOP 一律 honor）、sentiment 退出 System One"},
}

# ── util ────────────────────────────────────────────────────────────────────
def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _fmt(v, nd=3):
    return f"{v:.{nd}f}" if isinstance(v, (int, float)) else "n/a"


def _mu(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def _load_jsonl(path: Path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _id(item):
    return item.get("eid") or item.get("id")


# ── datasets ────────────────────────────────────────────────────────────────
def tool_items():
    return _load_jsonl(DS / "jev5_tool.jsonl")


def rag_items():
    return _load_jsonl(DS / "jev5_rag.jsonl")


def mem_items():
    return _load_jsonl(DS / "jev5_mem.jsonl")


def sent_items():
    return _load_jsonl(DS / "jev5_sent.jsonl")


def wf_items():
    return _load_jsonl(DS / "jev5_wf.jsonl")


def build_items(args):
    def take(rows, n):
        return list(rows[:n] if args.smoke else rows)

    return {"tool": take(tool_items(), 1), "rag": take(rag_items(), 1),
            "mem": take(mem_items(), 1), "sent": take(sent_items(), 1),
            "wf": take(wf_items(), 1)}


# ── OpenViking KB（同 phase-1／D8 fair 同一 stack）─────────────────────────
class OV:
    def __init__(self):
        _lib.load_env()
        import agent_build
        agent_build._patch_openviking_hydrate()
        self._kb = None

    def kb(self):
        if self._kb is None:
            from veadk.knowledgebase import KnowledgeBase
            kb = KnowledgeBase(backend="openviking", index="fin_kb", top_k=15)
            kb._backend.target_uri = "viking://resources/fin_kb/"
            kb._backend.read_limit = 200
            self._kb = kb
        return self._kb

    def dense(self, q, k=15):
        return self.kb().search(q, top_k=k)

    def sparse(self, pattern, limit=64):
        client = self.kb()._backend._ensure_client()
        r = client.grep(uri="viking://resources/fin_kb/", pattern=pattern,
                        case_insensitive=True, node_limit=limit)
        matches = r.get("result", {}).get("matches", []) if isinstance(r, dict) else r
        return [{"uri": m["uri"], "content": m.get("content", "")} for m in matches]


def _label(u, doc_prefixes):
    for key, pre in doc_prefixes.items():
        if u.startswith(pre):
            return key
    return None


def _merge_to_docs(raw_uris, doc_prefixes):
    seen, out = set(), []
    for u in raw_uris:
        lab = _label(u, doc_prefixes)
        if lab is not None and lab not in seen:
            seen.add(lab)
            out.append(lab)
    return out


def _hybrid(ov, q, doc_prefixes):
    entries = ov.dense(q, 15)
    grab = ov.sparse("|".join(_terms(q)))[:20]
    dense_docs = _merge_to_docs([(e.metadata or {}).get("uri", "") for e in entries], doc_prefixes)
    grep_docs = _merge_to_docs([g["uri"] for g in grab], doc_prefixes)
    rrf_scores = {}
    for ranked in (dense_docs, grep_docs):
        for rank, lab in enumerate(ranked):
            rrf_scores[lab] = rrf_scores.get(lab, 0.0) + 1.0 / (RRF_K + rank + 1)
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
    for lab in merged:
        if lab not in best:
            g = next((g for g in grab if _label(g["uri"], doc_prefixes) == lab), None)
            if g and g.get("content"):
                best[lab] = (g["content"], None)
    return merged, best, rrf_scores


def _ctx(labels, best):
    return "\n".join(f"[{i}] <{lab}>\n{best[lab][0].strip()}" for i, lab in enumerate(labels, 1))


def _qa_sys(ctx, lowscore=False):
    base = ("你是 FIN-MATE 金融研究助手。只用畀嘅資料答；資料無提及就答「KB 無資料」唔好作。"
            "每句 claim 後加 inline 標註【KB:檔案名】；結尾列「## 來源」完整 URI。")
    if lowscore:
        base += " 注意：語料訊號偏弱。如果搵唔到直接證據，答「KB 無資料」，唔好拼湊或估。"
    return base + "\n\n資料：\n" + ctx if ctx else base


def _ev_tool5(rec, tool_json):
    g = rec.get("golden") or {}
    tc = extract_json(tool_json or "")
    if not tc:
        return (0.0, False, "no tool-call JSON")
    tool = str(tc.get("tool") or "")
    if tool != g.get("tool"):
        return (0.0, False, f"wrong tool: {tool!r}")
    if tool in _EXEC_TOOLS:
        from eval.evaluators import ev_tool_call
        return ev_tool_call(rec, tool_json, ctx={})
    args = (tc.get("args") or {}) if isinstance(tc.get("args"), dict) else {}
    missing = [k for k in g.get("requires", []) if not str(args.get(k, "")).strip()]
    if missing:
        return (0.0, False, f"missing args: {missing} (args={args})")
    return (1.0, True, f"tool={tool} args={args}")


# ── LLM / event helpers ─────────────────────────────────────────────────────
async def _chat(prompt, system, model, max_tokens=512, trace=None, attempts=3):
    last = None
    for i in range(attempts):
        try:
            return await _lib.ark_complete([{"role": "system", "content": system},
                                            {"role": "user", "content": prompt}],
                                           model=model, max_tokens=max_tokens, trace=trace)
        except Exception as ex:  # noqa: BLE001
            last = ex
            await asyncio.sleep(2 * (i + 1))
    raise last


def _gate_ev(d, item, task, variant, stage, *, extra=None):
    return {"variant": variant, "task": task, "eid": _id(item), "stage": stage,
            "ts": datetime.now().isoformat(), "qtype": d.kind, "gate": d.gate,
            "model": "seed-1-6-flash-250715", "ms": d.ms, "tokens": dict(d.tokens),
            "probabilities": {str(k): round(float(v), 4) for k, v in d.probabilities.items()},
            "confidence": round(float(d.confidence), 4), "score": d.score, "choice": d.choice,
            "noul": d.noul, "escalated": d.escalated, "prompt": d.prompt, "extra": extra or {}}


def _chat_ev(resp, item, task, variant, stage, *, extra=None):
    return {"variant": variant, "task": task, "eid": _id(item), "stage": stage,
            "ts": datetime.now().isoformat(), "model": "ark", "ms": resp.ms,
            "tokens": {"prompt": resp.prompt_tokens, "completion": resp.completion_tokens,
                       "cached": resp.cached_tokens}, "extra": extra or {}}


def _usage_add(total, resp=None, d=None):
    if resp is not None:
        total["prompt"] += resp.prompt_tokens
        total["completion"] += resp.completion_tokens
        total["cached"] += resp.cached_tokens
    if d is not None:
        total["prompt"] += d.tokens.get("prompt", 0)
        total["completion"] += d.tokens.get("completion", 0)
        total["cached"] += d.tokens.get("cached", 0)


def _musd(usage):
    return _lib.usd(usage["prompt"], usage["completion"], usage["cached"]) * 1e6


# ── family runners ──────────────────────────────────────────────────────────
def _candidates(item, merged, best):
    """候選池 = hybrid top-k + 注入嘅 noise doc（「混無關 doc」）。"""
    cands = [(lab, best[lab][0]) for lab in merged[:RAG_CTX_TOP] if lab in best]
    noise = item.get("noise")
    if noise and noise.get("content"):
        cands.append((noise.get("label", "noise"), noise["content"]))
    return cands


async def _run_rag(ov, item, variant, doc_prefixes, events, usage, trace):
    q, task = item["q"], "rag"
    merged, best, rrf_scores = _hybrid(ov, q, doc_prefixes)
    uris = [doc_prefixes[lab] for lab in merged if lab in doc_prefixes]
    gold = set()
    if item.get("cat") != "trap":
        gold = {doc_prefixes[f] for f in item.get("gold_docs", []) if f in doc_prefixes}

    cands = _candidates(item, merged, best)
    kept = []
    gate_rows = []
    lowscore = False
    if variant == "jev3":
        # tier-0：用_hybrid 已有 RRF 分做 pool-relative gate（0ms、deterministic）
        gold_tags = {lab: _tag_gold(lab, gold, doc_prefixes) for lab, _ in cands}
        labels, kept, gate_rows, lowscore = tier0.doc_gate_rrf(best, cands, rrf_scores, gold_tags)
        for row in gate_rows:
            events.append({"variant": variant, "task": task, "eid": _id(item), "stage": "t0_doc_gate",
                           "ts": datetime.now().isoformat(), "det": True, "ms": 0.0,
                           "tokens": {"prompt": 0, "completion": 0, "cached": 0},
                           "doc": row["doc"], "score": row["score"], "gold": row["gold"],
                           "keep": row["keep"], "floor": row["floor"],
                           "lowscore_keep": row.get("lowscore_keep", False)})
    elif variant.startswith("jev"):
        raw = []
        for lab, snippet in cands:
            d = await decide_score(D.doc_state(_id(item), q, lab, snippet),
                                   "呢份候選資料對用戶問題有冇料到？", D.DOC_RELEVANCE_RUBRIC,
                                   gate="doc_gate", levels=4, keep_min=None)
            _usage_add(usage, d=d)
            raw.append((lab, snippet, d))
        pool_max = max((d.score for _, _, d in raw if d.score is not None), default=0.0)
        rel_floor = max(RAG_KEEP_FLOOR, RAG_KEEP_RATIO * pool_max)
        for lab, snippet, d in raw:
            keep = d.score is not None and d.score >= rel_floor
            gold_tag = _tag_gold(lab, gold, doc_prefixes)
            events.append(_gate_ev(d, item, variant, task, "jev_doc_gate",
                                   extra={"doc": lab, "gold": gold_tag, "keep": keep,
                                          "floor": round(rel_floor, 2)}))
            gate_rows.append({"doc": lab, "score": d.score, "gold": gold_tag, "keep": keep})
            if keep:
                kept.append((lab, snippet))
        labels = [lab for lab, _ in kept]
    else:
        labels = [lab for lab, _ in cands]

    ctx = _ctx(labels, {lab: (snippet, None) for lab, snippet in
                        (kept if variant.startswith("jev") else cands)})
    resp = await _chat(q, _qa_sys(ctx, lowscore=lowscore), FLASH, trace=trace)
    _usage_add(usage, resp=resp)
    events.append(_chat_ev(resp, item, task, variant, "answer",
                           extra={"n_ctx": len(labels), "n_cands": len(cands),
                                  "lowscore": lowscore,
                                  "answer": resp.text[:200]}))
    return {"answer": resp.text, "uris": uris, "gated_labels": labels, "labels": merged,
            "n_cands": len(cands), "gate_rows": gate_rows, "lowscore": lowscore,
            "recall5": recall_at_k(gold, uris, 5) if item.get("cat") != "trap" else None}


def _tag_gold(lab, gold, doc_prefixes):
    for f, pre in doc_prefixes.items():
        if lab == f:
            return "gold" if pre in [g for g in gold] else "noise"
    return "noise"


async def _run_mem(item, variant, events, usage, trace):
    q, task = item["prompt"], "mem"
    gold_relevant = set(item.get("gold_relevant", []))
    mem = item["memory"]
    gold = (item.get("golden") or {}).get("answer", "")
    privacy = item.get("privacy_marker") or ""

    kept = []
    gate_rows = []
    if variant == "jev3":
        # tier-0 marker rule（私隱硬規則，0ms）→ 剩低先用 1-token score（並行 => RTT overlap）
        dropped = set()
        for m in mem:
            if tier0.privacy_flagged(m["content"], privacy):
                dropped.add(m["id"])
                events.append({"variant": variant, "task": task, "eid": _id(item),
                               "stage": "t0_mem_rule", "ts": datetime.now().isoformat(),
                               "det": True, "ms": 0.0,
                               "tokens": {"prompt": 0, "completion": 0, "cached": 0},
                               "mem": m["id"], "marker": privacy})
        rem = [m for m in mem if m["id"] not in dropped]
        ds = await asyncio.gather(*(_run_mem_gate(item, variant, events, usage, task,
                                                  m["id"], m["content"], q) for m in rem))
        for m, d in zip(rem, ds):
            gate_rows.append({"mem": m["id"], "score": d.score,
                              "gold": m["id"] in gold_relevant})
            if d.score is not None and d.score >= MEM_GATE_MIN:
                kept.append(m)
    elif variant.startswith("jev"):
        for m in mem:
            d = await _run_mem_gate(item, variant, events, usage, task, m["id"], m["content"], q)
            gate_rows.append({"mem": m["id"], "score": d.score,
                              "gold": m["id"] in gold_relevant})
            if d.score is not None and d.score >= MEM_GATE_MIN:
                kept.append(m)
    else:
        kept = list(mem)

    listing = "\n".join(f"[{m['id']}/{m['kind']}] {m['content']}" for m in kept)
    q_sys = MEM_SYSTEM + (f"\n\n記憶：\n{listing}" if listing else "\n\n（冇記憶）")
    r = await _chat(q, q_sys, FLASH, max_tokens=160, trace=trace)
    _usage_add(usage, resp=r)
    events.append(_chat_ev(r, item, task, variant, "mem_answer",
                           extra={"n_mem": len(mem), "n_kept": len(kept)}))
    selected = {m["id"] for m in kept}
    sel_r = (len(selected & gold_relevant) / len(gold_relevant)) if gold_relevant else None
    sel_p = (len(selected & gold_relevant) / len(selected)) if selected else 0.0
    leak = bool(privacy) and privacy.lower() in r.text.lower()
    return {"answer_f1": answer_f1(gold, r.text), "answer": r.text,
            "relevant": sorted(gold_relevant), "selected": sorted(selected),
            "sel_recall": sel_r, "sel_precision": sel_p, "leak": leak,
            "n_mem": len(mem), "n_kept": len(kept), "gate_rows": gate_rows}


async def _run_mem_gate(item, variant, events, usage, task, mid, content, q):
    d = await decide_score(D.mem_state(_id(item), q, mid, content),
                           "呢條記憶對答用戶問題有冇用？", D.MEM_RELEVANCE_RUBRIC,
                           gate="mem_gate", levels=4, keep_min=MEM_GATE_MIN)
    _usage_add(usage, d=d)
    events.append(_gate_ev(d, item, variant, task, "jev_mem_gate", extra={"mem": mid}))
    return d


async def _run_sent(item, variant, events, usage, trace):
    q, task = item["prompt"], "sent"
    gold = (item.get("golden") or {}).get("label")
    d = None
    use_system_one = variant.startswith("jev") and variant != "jev3"
    if use_system_one:
        d = await decide_choice(D.tool_state(q), "呢條新聞標題係咩情緒？", D.sent_opts(),
                                gate="sent", conf_min=policy.SENT_CONF_MIN)
        _usage_add(usage, d=d)
        events.append(_gate_ev(d, item, variant, task, "jev_sent_choice", extra={"gold": gold}))
    if not use_system_one or d is None or d.escalated or d.choice is None:
        r = await _chat(q, SENT_SYSTEM, FLASH, max_tokens=16, trace=trace)
        _usage_add(usage, resp=r)
        events.append(_chat_ev(r, item, task, variant, "sent_label",
                               extra={"escalated": bool(d and d.escalated)}))
        pred = r.text
        score_level = None
    else:
        level = int(d.choice)
        pred = {v: k for k, v in D.LABEL_LEVEL.items()}[level]
        score_level = level
    score, passed, note = ev_sentiment(item, pred)
    gold_level = D.LABEL_LEVEL.get(gold)
    return {"score": score, "passed": bool(passed), "note": note, "pred": pred, "gold": gold,
            "score_level": score_level, "gold_level": gold_level,
            "score_err": abs(score_level - gold_level) if score_level is not None and gold_level is not None else None}


async def _run_wf(ov, item, variant, doc_prefixes, events, usage, trace):
    q, task = item["q"], "wf"
    steps, gold_last = item["steps"], item.get("gold_stop", len(item["steps"]) - 1)
    cont_gold = item.get("cont", [c == "go" for c in range(len(steps) - 1)])
    steps_done, out = 0, []
    noul_hits = noul_n = 0
    for i, st_ in enumerate(steps):
        ok, note2 = await _run_wf_step(ov, item, variant, doc_prefixes, st_, events, usage, trace)
        out.append({"i": i, "kind": st_["kind"], "ok": ok, "note": note2})
        if not ok:
            break
        steps_done = i + 1
        if i < len(steps) - 1:
            # 之後仲有 step 可跳/可做 → 睇下步數 / budget 先決定繼唔繼續
            cont, escalated = await _wf_continue(q, i + 1, len(steps), note2, variant,
                                                 item, events, usage, trace, cont_gold[i], i + 1)
            noul_n += 1
            noul_hits += int(cont == bool(cont_gold[i]))
            if not cont:
                break

    stop_exact = steps_done == gold_last + 1
    over = steps_done > gold_last + 1
    early = steps_done < gold_last + 1
    final_f1 = None
    last = out[-1] if out else None
    if last and last["kind"] in ("rag", "answer"):
        gold_ans = ""
        for si in steps:
            if si.get("id") == f"s{last['i'] + 1}":
                gold_ans = (si.get("gold") or {}).get("answer", "")
                break
        if gold_ans and last["note"]:
            final_f1 = answer_f1(gold_ans, last["note"])
    return {"steps_done": steps_done, "gold_stop": gold_last + 1, "stop_exact": stop_exact,
            "over": over, "early": early, "final_f1": final_f1,
            "noul_hits": noul_hits, "noul_n": noul_n, "steps": out,
            "cont_gold": cont_gold, "q": q}


async def _wf_continue(q, done, budget, last_outcome, variant, item, events, usage, trace,
                        gold_cont, step_no):
    if variant.startswith("jev"):
        asym = variant == "jev3"
        d = await decide_noul(D.cont_state(q, done, budget, last_outcome=last_outcome or ""),
                              "仲有冇下一步要執行？", gate="cont", conf_min=policy.CONT_CONF_MIN,
                              asymmetric=asym)
        _usage_add(usage, d=d)
        events.append(_gate_ev(d, item, "wf", variant, "jev_cont",
                               extra={"gold": gold_cont, "step": step_no, "asymmetric": asym}))
        if not d.escalated:
            return bool(d.noul), False
        # jev3 asymmetric：STOP 已經 honor 咗（escalated=False）；嚟到呢度 = YES 低 conf → chat 覆核。
        # 低 conf → escalated 落去 chat YES/NO（同 original arm 對稱）
    r = await _chat(f"{q}\n（已完成第 {done} / {budget} 步：{last_outcome[:80] or '—'}）需要繼續下一步嗎？",
                    CONT_SYSTEM, FLASH, max_tokens=8, trace=trace)
    _usage_add(usage, resp=r)
    events.append(_chat_ev(r, item, "wf", variant, "cont_chat",
                           extra={"gold": gold_cont, "step": step_no}))
    return r.text.strip().upper().startswith("YES"), True


async def _run_wf_step(ov, item, variant, doc_prefixes, st_, events, usage, trace):
    if st_["kind"] == "tool":
        fake = {"id": f"{_id(item)}_s{st_.get('id', '?')}", "task": "tool",
                "prompt": st_["prompt"], "context": "", "golden": st_["gold"]}
        r = await _run_tool(fake, variant, events, usage, trace, stage="jev_choice_step")
        return r["passed"], r["tool_json"]
    if st_["kind"] == "rag":
        fake = {"eid": f"{_id(item)}_s{st_.get('id', '?')}", "task": "rag", "cat": "fact",
                "q": st_["prompt"], "gold": (st_.get("gold") or {}).get("answer", ""),
                "gold_docs": st_.get("gold_docs", []), "noise": None}
        res = await _run_rag(ov, fake, variant, doc_prefixes, events, usage, trace)
        found = set(fake.get("gold_docs", [])) & set(res["gated_labels"])
        f1 = answer_f1(fake["gold"], res["answer"])
        return bool(found), res["answer"]
    r = await _chat(st_["prompt"], "你係 fin-mate，深度老師助教。回答用戶問題，簡短一句。",
                    FLASH, max_tokens=120, trace=trace)
    _usage_add(usage, resp=r)
    events.append(_chat_ev(r, item, "wf", variant, "step_answer", extra={"step": st_.get("id")}))
    return True, r.text


async def _run_tool(rec, variant, events, usage, trace, stage="jev_choice_tool"):
    fam, id_ = "tool", rec["id"]
    q, ctx = rec["prompt"], rec.get("context") or ""
    gold_tool = (rec.get("golden") or {}).get("tool")
    fallback = False
    tool_json = None
    if variant == "jev3":
        # tier-0：規則路由 + 確定式 args，填唔到先 escalation（choice call 都唔使）
        routed = tier0.route_tool(f"{q}\n{ctx}")
        events.append({"variant": variant, "task": fam, "eid": id_, "stage": "t0_route",
                       "ts": datetime.now().isoformat(), "det": True,
                       "tool": routed[0] if routed else None,
                       "args": routed[1] if routed else None, "ms": 0.0,
                       "tokens": {"prompt": 0, "completion": 0, "cached": 0},
                       "extra": {"gold": gold_tool}})
        if routed is not None:
            tool_json = json.dumps({"tool": routed[0], "args": routed[1]}, ensure_ascii=False)
        else:
            fallback = True
            r = await _chat(q, TOOL_SYSTEM, FLASH, trace=trace)
            _usage_add(usage, resp=r)
            events.append(_chat_ev(r, rec, fam, variant, "jev_fallback_tool",
                                   extra={"reason": "t0_unfillable"}))
            tool_json = r.text
    elif variant.startswith("jev"):
        state = D.tool_state(q, ctx)
        d = await decide_choice(state, "呢單嘢下一步要揀邊個工具？", TOOL5,
                                gate="tool_choice", conf_min=policy.TOOL_CONF_MIN)
        _usage_add(usage, d=d)
        choice_ev = _gate_ev(d, rec, fam, variant, stage, extra={"gold": gold_tool})
        events.append(choice_ev)
        chosen = None
        if not d.escalated and d.choice is not None:
            chosen = _TOOL_BY_ID.get(d.choice or "")
        if chosen is not None:
            args = None
            tool_json = None
            if variant == "jev2":
                # 真 JEV：args 由 state 確定式填，填唔到先 escalate
                args = actions.fill_args(chosen, f"{q}\n{ctx}")
                events.append({"variant": variant, "task": fam, "eid": id_, "stage": "jev2_det_args",
                               "ts": datetime.now().isoformat(), "det": True, "tool": chosen,
                               "args": args, "ms": 0.0, "tokens": {"prompt": 0, "completion": 0, "cached": 0}})
                if args is not None:
                    tool_json = json.dumps({"tool": chosen, "args": args}, ensure_ascii=False)
            else:
                ra = await _chat(q, ARG_SYS[chosen], FLASH, max_tokens=80, trace=trace)
                _usage_add(usage, resp=ra)
                events.append(_chat_ev(ra, rec, fam, variant, "jev_args_step",
                                       extra={"tool": chosen, "raw": ra.text[:80]}))
                args = extract_json(ra.text) or {}
                if chosen == "calc" and "expr" not in args:
                    args = {"expr": str(args) if args else ""}
                tool_json = json.dumps({"tool": chosen, "args": args}, ensure_ascii=False)
            if tool_json is None:
                fallback = True
                reason = "deterministic_args_unfillable" if variant == "jev2" else "low_conf"
                choice_ev["extra"]["fallback_reason"] = reason
                r = await _chat(q, TOOL_SYSTEM, FLASH, trace=trace)
                _usage_add(usage, resp=r)
                events.append(_chat_ev(r, rec, fam, variant, "jev_fallback_tool",
                                       extra={"reason": reason}))
                tool_json = r.text
        else:
            fallback = True
            r = await _chat(q, TOOL_SYSTEM, FLASH, trace=trace)
            _usage_add(usage, resp=r)
            events.append(_chat_ev(r, rec, fam, variant, "jev_fallback_tool",
                                   extra={"reason": "low_conf"}))
            tool_json = r.text
        choice_ev["extra"]["fallback"] = fallback
    else:
        r = await _chat(q, TOOL_SYSTEM, FLASH, trace=trace)
        _usage_add(usage, resp=r)
        events.append(_chat_ev(r, rec, fam, variant, "tool_json"))
        tool_json = r.text
    score, passed, note = _ev_tool5(rec, tool_json or "")
    return {"score": score, "passed": bool(passed), "note": note, "fallback": fallback,
            "tool_json": tool_json, "gold": gold_tool}


# ── 主 loop ─────────────────────────────────────────────────────────────────
async def _run(args):
    _lib.load_env()
    await jev_client.resolve_decision_model()

    doc_uris = all_doc_uris()
    ov = OV()
    items_by_task = build_items(args)

    out_root = Path(args.out) if args.out else BENCH_DIR / "results" / f"runs_{time.strftime('%y%m%d_%H%M')}"
    out_root.mkdir(parents=True, exist_ok=True)
    variants = [v for v in VARIANTS if not args.only or v in args.only.split(",")]

    run_meta = {"tag": out_root.name, "ts": _now(),
                "design": "5-task x {}-arm（original agent vs JEV 介面層 vs JEV 完整版 vs JEV tier-0）".format(
                    len(variants)),
                "tasks": {t: TASK_NAMES[t] for t in TASK_ORDER},
                "llm": {"prose": FLASH, "decision": jev_client._RESOLVED[0],
                        "mini_fallback": jev_client._RESOLVED[1], "logprobs_ok": jev_client._RESOLVED[2]},
                "thresholds": {"tool_conf_min": policy.TOOL_CONF_MIN, "rag_keep_floor": RAG_KEEP_FLOOR,
                               "rag_keep_ratio": RAG_KEEP_RATIO, "mem_gate_min": MEM_GATE_MIN,
                               "sent_conf_min": policy.SENT_CONF_MIN, "cont_conf_min": policy.CONT_CONF_MIN},
                "prices": _lib.PRICES, "variants": {k: v["desc"] for k, v in VARIANTS.items()},
                "items": {t: [_id(i) for i in its] for t, its in items_by_task.items()},
                "max_tokens_budget": args.max_tokens, "smoke": args.smoke}
    (out_root / "run_meta.json").write_text(json.dumps(run_meta, ensure_ascii=False, indent=2))

    budget, used = args.max_tokens, 0
    summary = {}
    for variant in variants:
        s_dir = out_root / f"jbv_{variant}"
        s_dir.mkdir(parents=True, exist_ok=True)
        all_events, rows = [], []
        t0 = time.perf_counter()
        for task in TASK_ORDER:
            for item in items_by_task[task]:
                if used + EST[task] > budget:
                    continue
                events, usage, trace = [], {"prompt": 0, "completion": 0, "cached": 0}, []
                st = time.perf_counter()
                try:
                    row = {"eid": _id(item), "task": task}
                    if task == "rag":
                        res = await _run_rag(ov, item, variant, doc_uris, events, usage, trace)
                        row.update({"cat": item.get("cat"),
                                    "recall5": res["recall5"],
                                    "answer_f1": (answer_f1(item.get("gold", ""), res["answer"])
                                                  if item.get("cat") != "trap" else None),
                                    "trap_pass": (_trap_pass(res["answer"]) if item.get("cat") == "trap" else None),
                                    "n_cands": res["n_cands"], "n_ctx": len(res["gated_labels"]),
                                    "lowscore": res["lowscore"],
                                    "answer": res["answer"], "gate_rows": res["gate_rows"]})
                    elif task == "tool":
                        r = await _run_tool(item, variant, events, usage, trace)
                        row.update({"passed": r["passed"], "score": r["score"], "note": r["note"],
                                    "fallback": r["fallback"], "gold": r["gold"], "tool_json": r["tool_json"]})
                    elif task == "mem":
                        r = await _run_mem(item, variant, events, usage, trace)
                        row.update({"answer_f1": r["answer_f1"], "sel_recall": r["sel_recall"],
                                    "sel_precision": r["sel_precision"], "leak": r["leak"],
                                    "relevant": r["relevant"], "selected": r["selected"],
                                    "n_mem": r["n_mem"], "n_kept": r["n_kept"],
                                    "answer": r["answer"], "gate_rows": r["gate_rows"]})
                    elif task == "sent":
                        r = await _run_sent(item, variant, events, usage, trace)
                        row.update({"passed": r["passed"], "score": r["score"], "note": r["note"],
                                    "pred": r["pred"], "gold": r["gold"], "score_level": r["score_level"],
                                    "gold_level": r["gold_level"], "score_err": r["score_err"]})
                    else:
                        r = await _run_wf(ov, item, variant, doc_uris, events, usage, trace)
                        row.update({"steps_done": r["steps_done"], "gold_stop": r["gold_stop"],
                                    "stop_exact": r["stop_exact"], "over": r["over"], "early": r["early"],
                                    "final_f1": r["final_f1"], "noul_hits": r["noul_hits"],
                                    "noul_n": r["noul_n"], "steps": r["steps"]})
                except Exception as ex:  # noqa: BLE001
                    row = {"eid": _id(item), "task": task, "error": str(ex)}
                all_events.extend(events)
                row["ms"] = (time.perf_counter() - st) * 1000
                row["n_calls"] = len(events)
                row["usage"] = dict(usage)
                row["musd"] = _musd(usage)
                rows.append(row)
                used += usage["prompt"] + usage["completion"]

        total_ms = (time.perf_counter() - t0) * 1000
        (s_dir / "events.jsonl").write_text(
            "\n".join(json.dumps(e, ensure_ascii=False) for e in all_events) + "\n", encoding="utf-8")
        (s_dir / "rows.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
        (s_dir / "info.json").write_text(json.dumps(
            {"variant": variant, "desc": VARIANTS[variant]["desc"]}, ensure_ascii=False, indent=2))
        summary[variant] = {"rows": rows, "total_ms": total_ms}
        _write_per_run(s_dir, variant, rows, items_by_task)
        print(f"[{variant}] n={len(rows)} {_perf_line(rows)}  total_ms={total_ms:.0f}")

    _write_summary(out_root, summary)
    run_meta["used_tokens"] = used
    (out_root / "run_meta.json").write_text(json.dumps(run_meta, ensure_ascii=False, indent=2))
    print(f"tokens used: {used}/{budget}  $≈{_lib.usd(used, 0):.4f}\ndone → {out_root}")


def _trap_pass(answer):
    a = (answer or "").lower()
    return any(u in a for u in ("無資料", "没有", "no information", "not found", "唔知"))


def _perf_line(rows):
    usd = sum(_lib.usd(*[r["usage"].get(k, 0) for k in ("prompt", "completion", "cached")]) for r in rows)
    return f"usd=${usd:.4f} μusd={sum(r.get('musd') or 0 for r in rows):.0f}"


# ── 匯總 ───────────────────────────────────────────────────────────────────
def _task_agg(rows, task):
    rs = [r for r in rows if r.get("task") == task and r.get("error") is None]
    if task == "tool":
        return {"pass": f"{sum(1 for r in rs if r.get('passed'))}/{len(rs)}",
                "fallback": sum(1 for r in rs if r.get('fallback'))}
    if task == "rag":
        fact = [r for r in rs if r.get("cat") != "trap"]
        traps = [r for r in rs if r.get("cat") == "trap"]
        return {"recall5": _mu([r.get("recall5") for r in fact]),
                "f1": _mu([r.get("answer_f1") for r in fact]),
                "trap": f"{sum(r.get('trap_pass') or 0 for r in traps)}/{len(traps)}" if traps else "—",
                "n_cands": _mu([r.get("n_cands") for r in rs]),
                "n_ctx": _mu([r.get("n_ctx") for r in rs])}
    if task == "mem":
        rs_je = [r for r in rs if r.get("sel_recall") is not None]
        return {"f1": _mu([r.get("answer_f1") for r in rs]),
                "sel_recall": _mu([r.get("sel_recall") for r in rs_je]),
                "leak": sum(1 for r in rs if r.get("leak")),
                "n_kept": _mu([r.get("n_kept") for r in rs])}
    if task == "sent":
        return {"pass": f"{sum(1 for r in rs if r.get('passed'))}/{len(rs)}",
                "score_err": _mu([r.get("score_err") for r in rs])}
    if task == "wf":
        return {"stop_exact": f"{sum(1 for r in rs if r.get('stop_exact'))}/{len(rs)}",
                "over": sum(1 for r in rs if r.get("over")),
                "early": sum(1 for r in rs if r.get("early")),
                "final_f1": _mu([r.get("final_f1") for r in rs]),
                "noul": f"{sum(r.get('noul_hits') or 0 for r in rs)}/{sum(r.get('noul_n') or 0 for r in rs)}"}
    return {}


def _usage_total(rows):
    return {"prompt": sum(r["usage"]["prompt"] for r in rows if r.get("usage")),
            "completion": sum(r["usage"]["completion"] for r in rows if r.get("usage")),
            "cached": sum(r["usage"]["cached"] for r in rows if r.get("usage"))}


def _jestats(out_root, variant):
    ms, conf, noul, t0 = [], [], [], 0
    path = out_root / f"jbv_{variant}" / "events.jsonl"
    if path.exists():
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            st = str(e.get("stage", ""))
            if st.startswith("t0_"):
                t0 += 1
            elif st.startswith("jev_"):
                ms.append(e.get("ms"))
                if e.get("confidence") is not None:
                    conf.append(e["confidence"])
                if e.get("noul") is not None:
                    noul.append(bool(e["noul"]))
    return {"n": len(ms), "med_ms": _mu(ms), "mean_conf": _mu(conf),
            "noul_flags": sum(noul) if noul else None, "noul_n": len(noul), "t0": t0}


def _metric_text(agg, task):
    if task == "tool":
        return agg["pass"]
    if task == "rag":
        return f"{_fmt(agg['recall5'])}/r5  F1={_fmt(agg['f1'])}  trap={agg['trap']}"
    if task == "mem":
        return (f"F1={_fmt(agg['f1'])}")
    if task == "sent":
        return agg["pass"]
    return f"stop {agg['stop_exact']}"


def _write_per_run(s_dir, variant, rows, items_by_task=None):
    u = _usage_total(rows)
    usd = _lib.usd(u["prompt"], u["completion"], u["cached"])
    all_ms = sum(r.get("ms") or 0 for r in rows)
    lines = [f"# report · jbv_{variant} · {len(rows)} items", "",
             f"- {VARIANTS[variant]['desc']}", ""]
    for task in TASK_ORDER:
        agg = _task_agg(rows, task)
        rs = [r for r in rows if r.get("task") == task and r.get("error") is None]
        ms_med = _mu([r.get("ms") for r in rs])
        n_exp = len(items_by_task[task]) if items_by_task else len(rs)
        if task == "tool":
            line = f"- **{TASK_NAMES[task]}**（{n_exp} 題）: {agg['pass']} pass" \
                   + (f"（low-conf fallback {agg['fallback']}）" if agg.get("fallback") else "")
        elif task == "rag":
            line = (f"- **{TASK_NAMES[task]}**（{n_exp} 題）: recall@5={_fmt(agg['recall5'])}  "
                    f"answer-F1={_fmt(agg['f1'])}  trap={agg['trap']}  "
                    f"ctx {_fmt(agg['n_ctx'], 1)}/{_fmt(agg['n_cands'], 1)}")
        elif task == "mem":
            seltxt = f"  sel-R={_fmt(agg['sel_recall'])}" if agg["sel_recall"] is not None else ""
            line = f"- **{TASK_NAMES[task]}**（{n_exp} 題）: answer-F1={_fmt(agg['f1'])}{seltxt}" \
                   + (f"  leak={agg['leak']}" if agg.get("leak") else "")
        elif task == "sent":
            line = f"- **{TASK_NAMES[task]}**（{n_exp} 題）: pass {agg['pass']}" \
                   + (f"  score-err={_fmt(agg['score_err'])}" if agg["score_err"] is not None else "")
        else:
            line = f"- **{TASK_NAMES[task]}**（{n_exp} 題）: stop 啱 {agg['stop_exact']}" \
                   + ((f"（over {agg['over']} / early {agg['early']}）") if (agg.get("over") or agg.get("early")) else "") \
                   + f"  noul {agg['noul']}" + (f"  final-F1={_fmt(agg['final_f1'])}" if agg["final_f1"] is not None else "")
        line += f"  med {ms_med:.0f} ms/題" if ms_med else ""
        lines.append(line)
    js = _jestats(s_dir.parent, variant)
    lines += ["", f"- System One decisions: {js['n']}  median: {_fmt(js['med_ms'], 0)} ms  "
                  f"· tier-0 (確定式): {js['t0']}  "
                  f"(total run: {all_ms:.0f} ms, usd=${usd:.4f}, μusd={usd*1e6:.0f})",
              "", "## per-item", "",
              "| eid | task | metric | ms | n_calls | μusd | note |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        task = r.get("task")
        m = "-"
        if task == "rag":
            m = (f"r5={_fmt(r.get('recall5'))} f1={_fmt(r.get('answer_f1'))}"
                 + (f" trap={'P' if r.get('trap_pass') else 'F'}" if r.get("cat") == "trap" else "")
                 + f" ctx={r.get('n_ctx')}/{r.get('n_cands')}")
        elif task == "tool":
            m = f"{'PASS' if r.get('passed') else 'FAIL'}{' (fb)' if r.get('fallback') else ''}"
        elif task == "mem":
            m = f"f1={_fmt(r.get('answer_f1'))}" + (f" selR={_fmt(r.get('sel_recall'))}" if r.get("sel_recall") is not None else "")
        elif task == "sent":
            m = f"{'PASS' if r.get('passed') else 'FAIL'} pred={r.get('pred','')}" \
                + (f" serr={_fmt(r.get('score_err'))}" if r.get("score_err") is not None else "")
        elif task == "wf":
            m = f"steps {r.get('steps_done')}/{r.get('gold_stop')} {'OK' if r.get('stop_exact') else ('OVER' if r.get('over') else 'EARLY')} noul {r.get('noul_hits')}/{r.get('noul_n')}"
        err = r.get("error") or ""
        lines.append(f"| {r['eid']} | {task} | {m} | {_fmt(r.get('ms', 0), 0)} | {r.get('n_calls', 0)} | "
                     f"{_fmt(r.get('musd') or 0, 0)} | {err[:40]} |")
    (s_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_summary(out_root, summary):
    order = [v for v in VARIANTS if v in summary]
    if not order:
        return
    lines = ["# JEV bench SUMMARY：5 任務 × %d agents" % len(order), "",
             f"- tag: {out_root.name}   runs: {_now()}",
             f"- design: original（全 chat）vs JEV 介面（System One + chat args）"
             f" vs JEV 完整（真 JEV：args 確定式 + 零 generation）"
             f" vs JEV tier-0（確定式規則：RRF gate / 規則路由 / marker rule / noUL asymmetric）", "",
             "## 正確率（pass / recall@5 / F1 / stop-exact）", "",
             "| task | " + " | ".join(order) + " |",
             "|" + "---|" * (len(order) + 1)]
    for task in TASK_ORDER:
        cells = []
        for k in order:
            agg = _task_agg(summary[k]["rows"], task)
            cells.append(_metric_text(agg, task))
        lines.append(f"| {TASK_NAMES[task]} | {' | '.join(cells)} |")
    lines += ["", "## 延時/成本（per-item median ms；total + $ + μ$）", "",
              "| task | " + " | ".join(order) + " |",
              "|" + "---|" * (len(order) + 1)]
    for task in TASK_ORDER:
        cells = []
        for k in order:
            rs = [r for r in summary[k]["rows"] if r.get("task") == task and r.get("error") is None]
            cells.append(f"{_fmt(_mu([r.get('ms') for r in rs]), 0)}")
        lines.append(f"| {TASK_NAMES[task]} | {' | '.join(cells)} |")
    lines.append("| 總計 | " + " | ".join(
        f"{summary[k]['total_ms']/1000:.1f}s ${_fmt(sum(_lib.usd(*[r['usage'][x] for x in ('prompt','completion','cached')]) for r in summary[k]['rows']), 4)}"
        f" ({_fmt(sum(r.get('musd') or 0 for r in summary[k]['rows']), 0)}μ$)"
        for k in order) + " |")
    lines += ["", "## Jev telemetry", "",
              "| 項目 | " + " | ".join(order) + " |",
              "|--" + "|---" * len(order) + "|"]
    for key, label in (("n", "decisions"), ("med_ms", "median ms"),
                       ("mean_conf", "mean confidence"), ("noul", "noul YES flags"),
                       ("t0", "tier-0 (確定式)")):
        vals = []
        for v in order:
            js = _jestats(out_root, v)
            if key == "noul":
                vals.append(f"{js['noul_flags']}/{js['noul_n']}" if js["noul_n"] else "—")
            elif key == "n":
                vals.append(str(js["n"]))
            else:
                vals.append(_fmt(js[key], 0) if key in ("med_ms", "t0") else _fmt(js[key]))
        lines.append(f"| {label} | {' | '.join(vals)} |")
    lines.append(f"| thresholds | tool/sent/cont conf {policy.TOOL_CONF_MIN}/{policy.SENT_CONF_MIN}/{policy.CONT_CONF_MIN} · rag gate floor {policy.RAG_KEEP_FLOOR} / ratio {policy.RAG_KEEP_RATIO} · mem {policy.MEM_GATE_MIN} |")
    lines.append("")
    try:
        lld = json.loads((out_root / "run_meta.json").read_text())["llm"]["decision"]
    except Exception:  # noqa: BLE001
        lld = "?"
    lines.append(f"> decision model = {lld}（seed-1.6-mini 喺本 account 唔存在 → fallback flash，即「決策層 = interface + 1-3 token + probabilities/confidence」嘅純對照）。")
    (out_root / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="JEV bench phase-2 runner（5 tasks × 2 agents）")
    p.add_argument("--smoke", action="store_true", help="每個 task 得 1 題")
    p.add_argument("--only", default="", help="逗號分隔 variant：original,jev,jev2,jev3")
    p.add_argument("--out", default="", help="輸出目錄")
    p.add_argument("--max-tokens", type=int, default=800_000)
    args = p.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()