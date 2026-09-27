"""FIN-MATE D6 評估器：exact / f1 / trap / tool_call / sentiment / llm_judge。

每個 evaluator = `ev_xxx(rec, pred, *, ctx) -> (score, passed, note)`：
  score  float 0..1；passed bool；note str。
`llm_judge` 係 async（本地 Ollama qwen3），其餘同步。`run_eval` 統一 dispatch。
tool_call 嘅 `pred` 要係 model 輸出嘅 JSON tool call；執行用真 tools/ 實體
（calc / read_news_file），並同 golden 對 args + result / fields。
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Any

from experiments import _lib  # noqa: E402
from experiments.eval_metrics import answer_f1  # noqa: E402

OLLAMA_BASE = "http://localhost:11434"
OLLAMA_MODEL = "qwen3:4b-instruct-2507-q4_K_M"

F1_PASS = 0.25  # token 重疊低過呢個當唔 pass（會喺 meta 可 override）

USELESS_ANS = ("無資料", "没有", "no information", "not found", "唔知")


def _norm(s: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", (s or "").lower()))


def extract_json(text: str) -> dict | None:
    """逐字括號配對抽第一個 balanced `{...}` 做 dict；失敗 None。"""
    if not text:
        return None
    depth = start = 0
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    obj = json.loads(text[start : i + 1])
                    return obj if isinstance(obj, dict) else None
                except Exception:  # noqa: BLE001
                    return None
    return None


# ---- sync evaluators -------------------------------------------------------

def ev_exact(rec: dict, pred: str, *, ctx: dict | None = None):
    g = rec.get("golden") or {}
    expected = g.get("answer") or g.get("label") or ""
    ok = _norm(pred) == _norm(expected)
    return (1.0 if ok else 0.0, ok, f"expect={expected[:40]!r}" if not ok else "")


def ev_f1(rec: dict, pred: str, *, ctx: dict | None = None):
    g = rec.get("golden") or {}
    f1 = answer_f1(g.get("answer") or "", pred or "")
    thr = float((rec.get("meta") or {}).get("f1_pass", F1_PASS))
    return (f1, f1 >= thr, f"f1={f1:.3f}")


def ev_trap(rec: dict, pred: str, *, ctx: dict | None = None):
    dl = (pred or "").lower()
    m = [u for u in USELESS_ANS if u.lower() in dl]
    return (1.0 if m else 0.0, bool(m), f"hit={m}" if m else f"pred={pred[:60]!r}")


def _tool_result(rec: dict, tc: dict, *, ctx: dict) -> tuple[dict, str]:
    """執行真 tool；回傳 (result_dict, note)。"""
    g = rec.get("golden") or {}
    args = (tc.get("args") or {}) if isinstance(tc.get("args"), dict) else {}
    tool = str(tc.get("tool") or "")
    if tool != g.get("tool"):
        return {}, f"wrong tool: {tool!r}"
    if tool == "calc":
        try:
            from tools.calc import calc
        except Exception:  # noqa: BLE001
            return {}, "calc import fail"
        expr = str(args.get("expr") or "")
        res = calc(expr)
        var = [(str(v), calc(v)["result"]) for v in g.get("variants", [])]
        return {"tool": "calc", "expr": expr, "result": res.get("result")}, ""
    if tool == "read_news_file":
        try:
            from tools.news_tools import read_news_file
        except Exception:  # noqa: BLE001
            return {}, "read_news_file import fail"
        try:
            rows = read_news_file(str(args.get("path") or ""))
        except Exception as exc:  # noqa: BLE001
            return {}, f"read_news_file error: {exc}"
        return {"tool": "read_news_file", "rows": rows}, ""
    return {}, f"unknown tool: {tool!r}"


def _calc_match(g, res) -> tuple[bool, str]:
    got = res.get("result")
    if got is None:
        for v in g.get("variants", []):
            from tools.calc import calc

            r2 = calc(v)["result"]
            if r2 is not None:
                got = r2
                break
    want = g.get("result")
    if got is None or want is None:
        return False, f"no computable result (expr={res.get('expr')!r})"
    ok = abs(float(got) - float(want)) < 1e-6
    return ok, f"computed {got} vs want {want}"


def _news_match(g, res) -> tuple[bool, str]:
    rows = res.get("rows") or []
    row_idx = int(g.get("row", 0))
    if row_idx >= len(rows):
        return False, f"row idx {row_idx} out of {len(rows)}"
    row = rows[row_idx]
    expect = g.get("expect") or {}
    for f in g.get("fields", []):
        if str(row.get(f, "")).strip() != str(expect.get(f, "")):
            return False, f"field {f}: got {row.get(f)!r} want {expect.get(f)!r}"
    return True, f"row {row_idx}: {row.get('ticker')}/{row.get('sentiment')}"


def ev_tool_call(rec: dict, pred: str, *, ctx: dict | None = None):
    g = rec.get("golden") or {}
    tc = extract_json(pred)
    if not tc:
        return (0.0, False, "no tool-call JSON in pred")
    res, note = _tool_result(rec, tc, ctx=ctx or {})
    if not res:
        return (0.0, False, note)
    if g.get("tool") == "calc":
        ok, note2 = _calc_match(g, res)
    else:
        ok, note2 = _news_match(g, res)
    note = (note2 if ok else note2 + f"; args={tc.get('args')}")
    return (1.0 if ok else 0.0, ok, note)


def _label_from(pred: str, classes: list[str]) -> str | None:
    dl = pred.lower()
    best, cnt = None, -1
    for c in classes:
        n = dl.count(c)
        if n > cnt:
            cnt, best = n, c
    return best if cnt > 0 else None


def ev_sentiment(rec: dict, pred: str, *, ctx: dict | None = None):
    g = rec.get("golden") or {}
    classes = g.get("classes") or []
    if (rec.get("meta") or {}).get("strict_json"):
        obj = extract_json(pred)
        if not obj:
            return (0.0, False, "no JSON")
        label = obj.get("label") or obj.get("sentiment") or ""
        got = _label_from(str(label), classes)
        score = obj.get("score")
        drv = str(obj.get("driver") or "").strip()
        lo, hi = g.get("score_range", [-1.0, 1.0])
        ok = (got == g.get("label")
              and isinstance(score, (int, float)) and lo <= float(score) <= hi
              and (not g.get("require_driver", True) or bool(drv)))
        return (1.0 if ok else 0.0, ok,
                f"label={got} score={score} driver={drv[:20]!r}" if not ok else "")
    got = _label_from(pred, classes)
    ok = got == g.get("label")
    return (1.0 if ok else 0.0, ok, f"pred={pred[:50]!r}" if not ok else "")


# ---- async judge -----------------------------------------------------------

async def ev_llm_judge(rec: dict, pred: str, *, ctx: dict | None = None):
    """本地 qwen3 (Ollama原生 /api/chat, think:false, temp 0) → PASS/FAIL，with cache。"""
    import httpx

    cache = (ctx or {}).get("judge_cache")  # list[dict]
    q = rec.get("prompt", "")
    g = rec.get("golden") or {}
    expected = g.get("answer") or ""
    rubric = (rec.get("meta") or {}).get("judge_rubric") or (
        "根據文件內容判斷答案係咪正確並完整涵蓋問題要求嘅關鍵事實（多份文件要綜合）。只答 PASS 或 FAIL。")
    key = hashlib.sha256(
        (rec.get("id", "") + "\0" + q + "\0" + (pred or "") + "\0" + expected + "\0" + rubric).encode()
    ).hexdigest()
    if cache is not None:
        for e in cache:
            if e.get("key") == key:
                return e["score"], e["passed"], f"cached; {e.get('note')}"

    sys_p = ("你係公平嘅評分員。依期望事實同問題，判定候選答案 PASS 定 FAIL。"
             "只回 PASS 或 FAIL 一個字詞，唔加其他字。")
    user_p = (f"問題：{q}\n\n期望（事實底線）：{expected}\n\n"
              f"候選答案：{pred or '(空)'}\n\n評分準則：{rubric}\n\n判定：")
    body = {"model": OLLAMA_MODEL, "messages": [{"role": "system", "content": sys_p},
                                                {"role": "user", "content": user_p}],
            "stream": False, "think": False, "temperature": 0, "options": {"num_predict": 16}}
    t = time.perf_counter()
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(OLLAMA_BASE.rstrip("/") + "/api/chat", json=body)
        r.raise_for_status()
        j = r.json()
    ms = (time.perf_counter() - t) * 1000
    txt = ((j.get("message") or {}).get("content") or "").strip()
    up = txt.upper()
    if up == "PASS":
        score, passed = 1.0, True
    elif up == "FAIL":
        score, passed = 0.0, False
    else:
        score, passed = 0.0, False
    note = f"verdict={txt!r} ms={ms:.0f}"
    if cache is not None:
        cache.append({"key": key, "score": score, "passed": passed, "note": note})
    return score, passed, note


EVALUATORS = {
    "exact": ev_exact,
    "f1": ev_f1,
    "trap": ev_trap,
    "tool_call": ev_tool_call,
    "sentiment": ev_sentiment,
    "llm_judge": ev_llm_judge,
}


if __name__ == "__main__":
    import asyncio

    r = {"id": "t", "prompt": "q", "golden": {"answer": "a b c"}, "meta": {}}
    assert ev_exact(r, "a b c")[1] is True
    assert ev_f1(r, "a b d")[0] == answer_f1("a b c", "a b d")
    assert ev_trap(r, "KB 無資料")[1] is True
    assert extract_json('x {"tool": "calc", "args": {"expr": "1+1"}} y')["tool"] == "calc"
    print("evaluators OK")