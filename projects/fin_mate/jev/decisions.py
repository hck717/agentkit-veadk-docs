"""JEV 決策層：每個決策點嘅 gate 規格（state packing + 選項/rubric）。

定義「要決策嗰一刻要砌啲乜 state、有咩選項、點樣判 esch」。
state 只 pack 必要嗰面（query + snippet / 問題 + 選項），唔好連 KB/記憶全文
入 prompt —— 慳 token 就係由呢度開始。
"""
from __future__ import annotations

# ---- 5-tool 工具盤（兩 arm 共用，即 JEV Choice 選項盤） -----------------------
TOOL5 = [
    {"id": "C", "label": "calc", "desc": "安全計數（+ - * / ** 括號）"},
    {"id": "R", "label": "read_news_file", "desc": "讀本地新聞 CSV 並標注情緒"},
    {"id": "F", "label": "fetch_news", "desc": "RSS 抓某隻股票嘅新聞頭條連情緒"},
    {"id": "S", "label": "web_search", "desc": "網上搜尋，攞最新報導"},
    {"id": "L", "label": "link_reader", "desc": "讀指定 URL 嘅網頁內容"},
]
_TOOL_BY_ID = {o["id"]: o["label"] for o in TOOL5}

# ---- RAG doc relevance（0..3 分級） ------------------------------------------
DOC_RELEVANCE_RUBRIC = [
    "完全冇關／冇嘢答到條問題",
    "擦邊：提同一公司，但冇直接答案",
    "部分相關：有部分線索",
    "直接相關：有直接答案",
]

# ---- 記憶 relevance（0..3 分級） ---------------------------------------------
MEM_RELEVANCE_RUBRIC = [
    "同用戶問題無關",
    "擦邊：同名但唔係用戶問嗰樣",
    "部分相關：有部分線索",
    "直接相關：直接用得到去答",
]

# ---- 情緒 3-way（level） -----------------------------------------------------
MINUS_ONE_TWO_THREE = {  # level id -> 中文標籤
    "0": "negative（負面）",
    "1": "neutral（中性）",
    "2": "positive（正面）",
}
LABEL_LEVEL = {"negative": 0, "neutral": 1, "positive": 2}


def sent_opts() -> list[dict]:
    return [{"id": k, "label": v} for k, v in sorted(MINUS_ONE_TWO_THREE.items())]


def tool_state(q: str, ctx: str = "") -> str:
    return f"用戶請求：{q}\n已畀資料：{ctx or '（無）'}"


def doc_state(item_eid: str, q: str, label: str, snippet: str) -> str:
    s = snippet.strip().replace("\n", " ")
    return f"用戶問題：{q}\n候選資料 <{label}>：\n{s[:400]}"


def mem_state(item_eid: str, q: str, mid: str, content: str) -> str:
    return f"用戶問題：{q}\n候選記憶 [{mid}]：\n{content.strip()[:400]}"


def cont_state(q: str, steps_done: int, budget: int, last_outcome: str = "") -> str:
    return (f"用戶任務：{q}\n已做步驟：{steps_done} / 總預算：{budget}\n"
            f"最後一步結果：{last_outcome[:120] or '（—）'}")