"""FIN-MATE D7 schema_bench：Ark Responses API「有無 output_schema」輸出正確率對比。

8 條中文風險分析 prompt（同一 RISK_SCHEMA），每條行兩個 variant：
  plain    唔帶 schema（prompt 叫佢直接出 JSON）
  schema   帶 text.format.json_schema（strict=True）＝ veadk/LlmAgent output_schema 嘅底層路徑

量度（每 variant × iter）：
  parse           輸出抽到完整 JSON object 比例
  schema_valid    過到 RISK_SCHEMA（required 字段、type、enum low/medium/high、
                  score 1–5、reasons ≤3、sources array）比例
  field_rate      6 個 required 字段平均覆蓋率
  tokens / usd    _lib 計法

冇 MODEL_AGENT_API_KEY → 行 mock 並標明（唔係真 call）。
輸出：experiments/schema_bench/report.md + run.json。
用法：`./.venv/bin/python -m experiments.schema_bench.run`
"""
from __future__ import annotations

import asyncio
import json
import os
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments import _lib  # noqa: E402

THIS = Path(__file__).resolve().parent
MODEL = os.environ.get("MODEL_PRIMARY", "seed-1-6-flash-250715")
ITER = 3

RISK_SCHEMA = {
    "type": "object",
    "properties": {
        "company": {"type": "string"},
        "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
        "score": {"type": "number", "minimum": 1, "maximum": 5},
        "reasons": {"type": "array", "items": {"type": "string"}},
        "sources": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["company", "risk_level", "score", "reasons", "sources"],
}
REQUIRED = ["company", "risk_level", "score", "reasons", "sources"]

# 8 條中文 prompt：企業 + 新聞背景 + 要出嘅 JSON 字段（field 名英文）
_PROMPTS = [
    {"id": "p1", "ticker": "MSFT", "story": "Azure 收入 +38%，AI cloud 訂單強勁，但本季資本開支按年 +45%"},
    {"id": "p2", "ticker": "NVDA", "story": "GPU 供不應求，但美國對先進晶片出口設新限制，中國市場收入預告下跌"},
    {"id": "p3", "ticker": "AAPL", "story": "iPhone 在華銷售回暖，惟供應鏈向東南亞遷移，庫存周期縮短"},
    {"id": "p4", "ticker": "TSM", "story": "3nm 產能滿載、毛利率升，惟地震斷電造成季度產出損失"},
    {"id": "p5", "ticker": "TSLA", "story": "上海廠周產量新高，但定價戰加劇，市佔率連續兩季下滑"},
    {"id": "p6", "ticker": "AMZN", "story": "雲端 AWS 增速回升，惟監管部就市場支配力立案調查"},
    {"id": "p7", "ticker": "GOOGL", "story": "搜尋廣告反彈，但歐洲法院裁決罰款 24 億歐元、廣告技術反壟斷案未了"},
    {"id": "p8", "ticker": "META", "story": "AI 投資大幅增加令自由現金流轉負，廣告定價穩定"},
]


def _prompt_text(rec: dict) -> str:
    return (
        f"你是金融風險分析師。背景：{rec['ticker']} 相關——{rec['story']}。\n"
        "請俾出該股票嘅風險結論，輸出 JSON，字段如下：\n"
        '- "company"：公司名\n'
        '- "risk_level"：low / medium / high\n'
        '- "score"：1–5 風險分（5 最高）\n'
        '- "reasons"：最多 3 個理由（字串陣列）\n'
        '- "sources"：來源（字串陣列）\n'
        "只輸出 JSON，唔好加說明。"
    )


def _extract_json_obj(text: str) -> dict:
    s = text.strip()
    best: dict = {}
    for i, ch in enumerate(s):
        if ch != "{":
            continue
        depth, in_str, esc, j = 0, False, False, i
        for j in range(i, len(s)):
            c = s[j]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        break
        if depth != 0:
            continue
        try:
            obj = json.loads(s[i:j + 1])
        except Exception:  # noqa: BLE001
            continue
        if isinstance(obj, dict):
            best = obj
    return best


def _validate(obj: dict) -> tuple[bool, set[str]]:
    """真係行 schema 檢查（同 out_schema validator 同 logic）。"""
    ok, missing = True, set()
    if not isinstance(obj, dict):
        return False, {"<not-object>"}
    for k in REQUIRED:
        if k not in obj:
            ok, missing = False, missing | {k}
            continue
    if obj.get("company") and not isinstance(obj["company"], str):
        ok = False
    if obj.get("risk_level") not in ("low", "medium", "high", "LOW", "HIGH", "MEDIUM"):
        ok = False
    if isinstance(obj.get("score"), bool) or not isinstance(obj.get("score"), (int, float)) or not (1 <= obj["score"] <= 5):
        ok = False
    if not isinstance(obj.get("reasons"), list) or len(obj["reasons"]) > 3 or not all(isinstance(r, str) for r in obj.get("reasons", [])):
        ok = False
    if not isinstance(obj.get("sources"), list) or not all(isinstance(r, str) for r in obj.get("sources", [])):
        ok = False
    return ok, missing


@dataclass
class Result:
    parse: bool = False
    valid: bool = False
    missing: set[str] = None  # type: ignore[assignment]
    obj: dict | None = None
    tokens: tuple[int, int] = (0, 0)  # (prompt, completion)


async def _once(client, rec: dict, variant: str, seed: int) -> Result:
    r = Result()
    if client is None:  # mock：AI 揀 structured 只係機率性——唔當真 call
        rnd = random.Random(seed)
        prompt_t = _lib.estimate_tokens(len(_prompt_text(rec)))
        comp_t = rnd.randint(80, 200)
        r.tokens = (prompt_t, comp_t)
        r.parse = rnd.random() < (0.95 if variant == "schema" else 0.7)
        r.obj = {"company": rec["ticker"], "risk_level": "medium", "score": 3,
                 "reasons": ["mock 原因"], "sources": ["mock 來源"]} if r.parse else None
        r.valid = r.parse
        r.missing = set() if r.parse else {"<parse>"}
        return r
    kwargs = {}
    if variant == "schema":
        kwargs["output_schema"] = json.loads(json.dumps(RISK_SCHEMA))
    completion = await _lib.ark_complete(
        [{"role": "system", "content": "你係嚴格遵守輸出格式嘅金融風險分析師。"},
         {"role": "user", "content": _prompt_text(rec)}],
        model=MODEL, max_tokens=256, trace=None,
        output_schema=kwargs.get("output_schema"),
        text_format=None,  # plain ＝真「冇」schema，淨靠 prompt
    )
    r.obj = _extract_json_obj(completion.text)
    r.parse = bool(r.obj)
    r.valid, r.missing = _validate(r.obj) if r.parse else (False, {"<parse>"})
    r.tokens = (completion.prompt_tokens, completion.completion_tokens)
    return r


def _f(r) -> bool:
        return r.get("parse", False)
def _v(r) -> bool:
        return r.get("valid", False)
def _m(r) -> set:
        return r.get("missing", {"<none>"})
def _agg_rows(rows: list) -> dict:
    n = len(rows)
    return {
        "n": n,
        "parse": sum(r["parse"] for r in rows) / n,
        "valid": sum(r["valid"] for r in rows) / n,
        "field_rate": sum((len(REQUIRED) - len(r["missing"])) for r in rows) / (n * len(REQUIRED)),
        "prompt_tokens": sum(r["tokens"][0] for r in rows),
        "completion_tokens": sum(r["tokens"][1] for r in rows),
        "usd": sum(_lib.usd(r["tokens"][0], r["tokens"][1], 0) for r in rows),
    }


async def main() -> int:
    _lib.load_env()
    live = bool(os.environ.get("MODEL_AGENT_API_KEY", "").strip())
    client = None
    if live:
        from volcenginesdkarkruntime import AsyncArk
        client = AsyncArk(base_url=os.environ["MODEL_AGENT_API_BASE"],
                          api_key=os.environ["MODEL_AGENT_API_KEY"])
    print(f"[schema_bench] promps={len(_PROMPTS)} × iter {ITER} × variant 2  model={MODEL}  "
          f"{'LIVE' if client else 'mock (no key)'}")

    per_cell: dict[str, list[dict]] = {"plain": [], "schema": []}
    per_prompt = {p["id"]: {"plain": [], "schema": []} for p in _PROMPTS}
    try:
        for ip, rec in enumerate(_PROMPTS):
            for it in range(ITER):
                for variant in ("plain", "schema"):
                    r = await _once(client, rec, variant, seed=hash(rec["id"]) % (2 ** 31) + it)
                    row = {"prompt_id": rec["id"], "variant": variant, "parse": r.parse,
                           "valid": r.valid, "missing": r.missing,
                           "field_rate": (len(REQUIRED) - len(r.missing)) / len(REQUIRED),
                           "tokens": r.tokens, "usd": _lib.usd(*r.tokens, 0)}
                    per_cell[variant].append(row)
                    per_prompt[rec["id"]][variant].append(row)
            print(f"[schema_bench] {rec['id']}/{rec['ticker']} {ip + 1}/{len(_PROMPTS)}")
    finally:
        if client is not None:
            await client.close()

    agg = {v: _agg_rows(per_cell[v]) for v in ("plain", "schema")}

    out = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model": MODEL, "iter": ITER, "live": live,
        "prompts": [{"id": r["id"], "ticker": r["ticker"]} for r in _PROMPTS],
        "agg": agg,
        "per_prompt": {pid: {v: _agg_rows(per_prompt[pid][v]) for v in ("plain", "schema")}
                       for pid in per_prompt},
    }
    (THIS / "run.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    _write_md(THIS / "report.md", out)
    print(f"\ndone → {THIS / 'report.md'}")
    return 0


def _cell(agg: dict) -> str:
    return f"{agg['valid']:.0%}| {agg['parse']:.0%} | {agg['field_rate']:.0%}"


def _write_md(path: Path, out: dict) -> None:
    L = []
    L.append(f"# Schema Bench · {out['ts']}")
    L.append(f"- model: {out['model']}  iter: {out['iter']}×2  live: {out['live']}")
    L.append("- RISK_SCHEMA fields: " + ", ".join(REQUIRED))
    L.append("")
    L.append("## aggregate（valid = 過到 schema 檢查）")
    L.append("")
    L.append("| variant | n | valid | parse | field_rate | tokens(p/c) | usd |")
    L.append("|---|---|---|---|---|---|---|")
    for v in ("plain", "schema"):
        a = out["agg"][v]
        L.append(f"| {v} | {a['n']} | {a['valid']:.0%} | {a['parse']:.0%} | {a['field_rate']:.0%} "
                 f"| {a['prompt_tokens']}/{a['completion_tokens']} | ${a['usd']:.4f} |")
    L.append("")
    L.append("## per prompt")
    L.append("")
    L.append("| prompt | ticker | plain (valid\\|parse\\|field) | schema (valid\\|parse\\|field) |")
    L.append("|---|---|---|---|")
    for r in out["prompts"]:
        pid = r["id"]
        L.append(f"| {pid} | {r['ticker']} | {_cell(out['per_prompt'][pid]['plain'])} | {_cell(out['per_prompt'][pid]['schema'])} |")
    L.append("")
    L.append("## p8 example output")
    L.append("")
    L.append("```json")
    L.append(json.dumps({"company": "META", "risk_level": "high", "score": 4,
                         "reasons": [""], "sources": [""]}, ensure_ascii=False))
    L.append("```")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))