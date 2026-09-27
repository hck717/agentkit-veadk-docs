"""FIN-MATE D6 評估 — golden datasets 產生器。

六個 prompt sets（`eval/golden_datasets/{qa,tool_call,sentiment}/*.jsonl`）：

  QA
    fact_single   (S1)  單一文檔事實抽取      — 由 eval_set.ITEMS cat=fact 派生（f1..f11）
    fact_multi    (S2)  兩 docs 合成 + trap     — 由 eval_set.ITEMS multi_hop + trap 派生（m1,m2,t1,t2）
  tool_call
    calc_expr     (S3)  正確 calc(expr) tool call + 結果
    news_extract  (S4)  read_news_file → 抽 {ticker,sentiment} 結構化欄位
  sentiment
    sent_3way     (S5)  headline → positive/neutral/negative（對齊 news_tools 詞典）
    sent_score    (S6)  嚴格 JSON {label,score,driver}

統一 JSONL schema（每 record 一個 dict）：
  set / id / type / prompt / evaluator / context / golden / meta

gold 唔 hardcode URI（沿用 eval_set.py 教訓）——QA 只記 `gold_docs` filename（run_eval
用 `all_doc_uris()` 即時 map）。`context` 只供 engine_bench（inline 背景），run_eval 唔用。

用法：`./.venv/bin/python -m eval.rebuild_goldens`（root = projects/fin_mate）。
異動 eval_set 之後 rerun，輸出會被每次覆寫（deterministic）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.rag_bench.eval_set import ITEMS as EVA_SET_ITEMS  # noqa: E402

OUT = ROOT / "eval" / "golden_datasets"

USELESS_ANS = ("無資料", "没有", "no information", "not found", "唔知")


def _write(subdir: str, name: str, records: list[dict]) -> None:
    p = OUT / subdir / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    print(f"  {p.relative_to(ROOT)}  n={len(records)}")


def build() -> None:
    fact = [i for i in EVA_SET_ITEMS if i["cat"] == "fact" and i["eid"] != "f12"]
    multi = [i for i in EVA_SET_ITEMS if i["cat"] == "multi_hop"]
    traps = [i for i in EVA_SET_ITEMS if i["cat"] == "trap"]

    s1 = []
    for idx, item in enumerate(fact, 1):
        s1.append({
            "set": "fact_single",
            "id": f"qa_fs_{idx:02d}",
            "type": "qa",
            "prompt": item["q"],
            "context": f"KB excerpt: {item['gold']}",
            "golden": {"answer": item["gold"], "gold_docs": list(item["gold_docs"])},
            "evaluator": "f1",
            "meta": {"eid": item["eid"], "src_cat": item["cat"], "lang": "yue"},
        })

    s2 = []
    for idx, item in enumerate(multi + traps, 1):
        is_trap = item["cat"] == "trap"
        s2.append({
            "set": "fact_multi",
            "id": f"qa_fm_{idx:02d}",
            "type": "qa",
            "prompt": item["q"],
            "context": f"KB excerpt: {item['gold']}" if not is_trap else "",
            "golden": {"answer": item["gold"], "gold_docs": list(item["gold_docs"])},
            "evaluator": "trap" if is_trap else "llm_judge",
            "meta": {"eid": item["eid"], "src_cat": item["cat"], "is_trap": is_trap,
                     "useless_ans": list(USELESS_ANS), "lang": "yue"},
        })

    s3 = [
        {"set": "calc_expr", "id": f"tc_calc_{i:02d}", "type": "tool_call",
         "prompt": p, "context": "",
         "golden": {"tool": g["tool"], "args": g["args"], "result": g["result"],
                    "variants": g["variants"], "check": "result"},
         "evaluator": "tool_call", "meta": {"lang": "yue", "source": g["src"]}}
        for i, (p, g) in enumerate([
            ("Deutsche 話 MSFT F2Q 嘅 Azure 增長 38% 係 constant currency，高過 guidance 1 point。計返 Azure guidance 增長率。用 calc 工具計。",
             {"tool": "calc", "args": {"expr": "38-1"}, "result": 37.0, "variants": ["38-1", "38 - 1", "38.0-1.0"], "src": "Deutsche"}),
            ("Mizuho 話 MSFT F2Q 總收入 81.3B，Street 預期 80.3B。計 beat 咗幾多 billion。用 calc 工具計。",
             {"tool": "calc", "args": {"expr": "81.3-80.3"}, "result": 1.0, "variants": ["81.3-80.3", "81.3 - 80.3"], "src": "Mizuho"}),
            ("China Renaissance 話 2026E EPS 17.11 係 consensus 15.80 嘅 8% 之上。驗證：consensus × 1.08 幾多？用 calc 工具計。",
             {"tool": "calc", "args": {"expr": "15.80*1.08"}, "result": 17.064, "variants": ["15.8*1.08", "15.80*1.08", "15.8 * 1.08"], "src": "CRR"}),
            ("Microsoft E7 定 $99，E5 定 $60。E7 高過 E5 幾多 percent？用 calc 工具計。",
             {"tool": "calc", "args": {"expr": "(99-60)/60*100"}, "result": 65.0, "variants": ["(99-60)/60*100", "(99-60)/60", "(99.0-60.0)/60.0*100"], "src": "Barclays/WF"}),
            ("Microsoft Cloud 季度收入首破 $50B、同比升 26%。計返上年同期幾多 B。用 calc 工具計。",
             {"tool": "calc", "args": {"expr": "50/1.26"}, "result": 39.6825396825, "variants": ["50/1.26", "50.0/1.26"], "src": "EC2"}),
        ], 1)]

    s4 = [
        {"set": "news_extract", "id": f"tc_news_{i:02d}", "type": "tool_call",
         "prompt": p, "context": "",
         "golden": {"tool": "read_news_file", "args": {"path": "data/news/sample_news.csv"},
                    "fields": ["ticker", "sentiment"], "expect": g, "row": i - 1, "check": "fields"},
         "evaluator": "tool_call", "meta": {"lang": "yue"}}
        for i, (p, g) in enumerate([
            ("用 read_news_file 讀 data/news/sample_news.csv 嘅第一行新聞，話我知佢嘅 ticker 同 sentiment。",
             {"ticker": "MSFT", "sentiment": "positive"}),
            ("read_news_file 讀 data/news/sample_news.csv 第二行，報告 ticker 同 sentiment。",
             {"ticker": "005930", "sentiment": "negative"}),
            ("read_news_file 讀 data/news/sample_news.csv 第三行，報告 ticker 同 sentiment。",
             {"ticker": "TSM", "sentiment": "neutral"}),
        ], 1)]

    s5 = [
        {"set": "sent_3way", "id": f"sent_3w_{i:02d}", "type": "sentiment",
         "prompt": f"將下面標題分類做 positive / neutral / negative（輸出一個字詞即可）：\n{h[0]}",
         "context": "",
         "golden": {"label": h[1], "classes": ["positive", "neutral", "negative"]},
         "evaluator": "sentiment", "meta": {}}
        for i, h in enumerate([
            ("Microsoft Cloud revenue tops $50 billion, up 26% year over year", "positive"),
            ("Microsoft shares fall 4% after Azure growth misses expectations", "negative"),
            ("Taiwan Semiconductor holds its guidance steady this quarter", "neutral"),
            ("Microsoft wins big government cloud deal, shares surge", "positive"),
            ("Bank warns of AI capex bubble, cuts cloud estimates", "negative"),
            ("Wells Fargo upgrades Microsoft, raises price target to $600", "positive"),
        ], 1)]

    s6 = [
        {"set": "sent_score", "id": f"sent_sc_{i:02d}", "type": "sentiment",
         "prompt": ("以嚴格 JSON 回應（唔加其他字）："
                    "{\"label\": \"positive|neutral|negative\", \"score\": -1.0..1.0, \"driver\": \"一句講原因\"}\n"
                    f"標題：{h[0]}"),
         "context": "",
         "golden": {"label": h[1], "classes": ["positive", "neutral", "negative"],
                    "score_range": h[2], "require_driver": True},
         "evaluator": "sentiment", "meta": {"strict_json": True}}
        for i, h in enumerate([
            ("Microsoft Cloud revenue tops $50 billion, up 26% year over year", "positive", [0.3, 1.0]),
            ("Microsoft shares fall 4% after Azure growth misses expectations", "negative", [-1.0, -0.3]),
            ("Taiwan Semiconductor holds its guidance steady this quarter", "neutral", [-0.2, 0.2]),
            ("Bank warns of AI capex bubble, cuts cloud estimates", "negative", [-1.0, -0.3]),
            ("Wells Fargo upgrades Microsoft, raises price target to $600", "positive", [0.3, 1.0]),
        ], 1)]

    _write("qa", "fact_single.jsonl", s1)
    _write("qa", "fact_multi.jsonl", s2)
    _write("tool_call", "calc_expr.jsonl", s3)
    _write("tool_call", "news_extract.jsonl", s4)
    _write("sentiment", "sent_3way.jsonl", s5)
    _write("sentiment", "sent_score.jsonl", s6)
    total = len(s1) + len(s2) + len(s3) + len(s4) + len(s5) + len(s6)
    print(f"total records: {total}")


if __name__ == "__main__":
    build()