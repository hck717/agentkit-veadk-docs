"""JEV 確定式動作層：System One 揀完 tool 之後，args 直接由 state/user 抽出，**唔使 generation**。

真 JEV 嘅動作盤係人手定義：每個 action 帶一個確定式 args template，
填到就 zero-cost 執行，填唔到先 escalate 去 System Two（generation）。
呢度就係嗰個「確定式填充器」— bench（`jev2` arm）同 live before-model
decider 共用同一份。

填充器回傳 `None` = 呢個 tool 嘅 args 冇辦法確定式填 —— caller 要 escalate。
"""
from __future__ import annotations

import ast
import operator
import re

NEWS_PATH = "data/news/sample_news.csv"

# ---- 純 regex 抽取 -----------------------------------------------------------
_TICKER = re.compile(r"\$?\b([A-Z]{1,5})\b")
_CSV_PATH = re.compile(r"[\w./\\-]+\.csv")
_URL = re.compile(r"https?://[^\s，。、\"']+")
_TARGET_PCT = re.compile(
    r"(?:target|目標|target 價)[^\d%]{0,20}?([+-]?)\s*([0-9]+(?:\.[0-9]+)?)\s*%", re.IGNORECASE
)
_NUM = re.compile(r"[0-9]+(?:\.[0-9]+)?")
_EXPR_TOK = re.compile(r"\(?[0-9][0-9+\-*/()\s]*[0-9)]")
_NOT_ODD = str.maketrans("（）", "()")

_ARITH_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Pow: operator.pow, ast.USub: operator.neg,
}


def _safe_eval_expr(expr: str) -> bool:
    """算式係咪可以被 allowlist 安全計到。避免撞到非運算字串（例如「開倉價」）。

    `ast.walk` 會連 operator 節點（ast.Mult/Div…，都係 ast.operator subclass）一齊行，
    所以要分開 check operator type，而唔係當佢係 unknown 節點。
    """
    try:
        tree = ast.parse(expr.replace("^", "**"), mode="eval")
    except (SyntaxError, TypeError):
        return False
    for node in ast.walk(tree):
        t = type(node)
        if t is ast.Expression:
            continue
        if t is ast.Constant:
            if not isinstance(node.value, (int, float)):
                return False
            continue
        if t in (ast.BinOp, ast.UnaryOp):
            continue
        if isinstance(node, ast.operator):
            if t not in _ARITH_OPS:
                return False
            continue
        return False
    return True


def _expr_candidates(text: str):
    for m in _EXPR_TOK.finditer(text):
        cand = m.group(0).strip()
        if any(op in cand for op in "+-*/(") and _safe_eval_expr(cand):
            yield cand


# ---- per-tool 填充器 ----------------------------------------------------------
def _fill_calc(text: str) -> dict | None:
    """calc：target ±N% → base*(1±N/100)；否則揀最長嘅合法算式。"""
    text = text.replace("（", "(").replace("）", ")")
    tm = _TARGET_PCT.search(text)
    base = _NUM.search(text)
    if tm and base:
        sign = -1 if tm.group(1) == "-" else 1
        pct = float(tm.group(2))
        expr = f"{base.group(0)}*{1 + sign * pct / 100}"
        return {"expr": expr}
    cands = sorted(_expr_candidates(text), key=len, reverse=True)
    if cands:
        return {"expr": cands[0]}
    return None


def _fill_read_news_file(text: str) -> dict | None:
    m = _CSV_PATH.search(text)
    return {"path": m.group(0)} if m else {"path": NEWS_PATH}


def _fill_fetch_news(text: str) -> dict | None:
    m = _TICKER.search(text)
    return {"ticker": m.group(1)} if m else None


def _fill_web_search(text: str) -> dict | None:
    q = re.sub(r"\s+", " ", text).strip()
    return {"query": q} if q else None


def _fill_link_reader(text: str) -> dict | None:
    m = _URL.search(text)
    return {"url": m.group(0)} if m else None


_fill_web_fetch = _fill_link_reader


def _fill_load_knowledgebase(text: str) -> dict | None:
    q = re.sub(r"\s+", " ", text).strip()
    return {"query": q} if q else None


# tool（label）-> 填充器。「唔喺呢度 = 唔可以確定式填 args -> escalate」。
FILLERS = {
    "calc": _fill_calc,
    "read_news_file": _fill_read_news_file,
    "fetch_news": _fill_fetch_news,
    "web_search": _fill_web_search,
    "web_fetch": _fill_web_fetch,
    "link_reader": _fill_link_reader,
    "load_knowledgebase": _fill_load_knowledgebase,
}


def fill_args(tool: str, text: str) -> dict | None:
    """確定式填 args。None = 填唔到（caller 要 escalate 去 System Two）。"""
    filler = FILLERS.get(tool)
    if filler is None:
        return None
    return filler(text or "")


# ---- live agent 嘅 System One 選項盤（讀工具 + 「唔使工具」）-----------------
# 只有「確定式填到 args」嘅工具先放上盤；其他（run_code/coding/kb 之外）
# 一律落 escalation。N = System One 判斷唔使 tool（-> 照行 System Two 作答）。
LIVE_TOOLS = [
    {"id": "K", "label": "load_knowledgebase", "desc": "本地 fin_kb 語意檢索（company overview / 財報 / 分析師報告 / 業績會議）"},
    {"id": "C", "label": "calc", "desc": "安全計數（+ - * / ** 括號）"},
    {"id": "F", "label": "fetch_news", "desc": "RSS 抓某隻股票嘅新聞頭條連情緒"},
    {"id": "W", "label": "web_search", "desc": "網上搜尋最新報導"},
    {"id": "V", "label": "web_fetch", "desc": "讀指定 URL"},
    {"id": "L", "label": "link_reader", "desc": "讀指定 URL 嘅網頁內容"},
    {"id": "N", "label": "none", "desc": "唔使工具，直接答"},
]
LIVE_TOOL_BY_ID = {o["id"]: o["label"] for o in LIVE_TOOLS}