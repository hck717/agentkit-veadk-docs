"""FIN-MATE 新聞工具：抓取與讀取金融新聞並附情緒標記。

依賴：`feedparser`（RSS 解析）。純 function + type hint + docstring，
會被 VeADK 自動包裝成 FunctionTool。
"""
from __future__ import annotations

import csv
import os
import re
from typing import Any

# 簡易英文金融新聞情緒詞典
_POSITIVE = {
    "beat", "growth", "profit", "up", "rise", "surge", "jump", "gain", "record",
    "outperform", "upgrade", "strong", "raise", "soar", "boost", "exceed",
    "expansion", "momentum", "buoy", "rally", "climb",
}
_NEGATIVE = {
    "miss", "loss", "down", "drop", "fall", "plunge", "decline", "cut", "weak",
    "downgrade", "below", "slump", "tumble", "shortfall", "layoff", "lawsuit",
    "selloff", "pressure", "concern", "risk", "worry", "bubble",
}
_WORD_RE = re.compile(r"[a-z]+")


def _score_text(text: str) -> tuple[int, int, int]:
    """回傳 (正面, 負面, 中性) 字詞計數。"""
    words = _WORD_RE.findall(text.lower())
    pos = sum(1 for w in words if w in _POSITIVE)
    neg = sum(1 for w in words if w in _NEGATIVE)
    if pos == 0 and neg == 0:
        return 0, 0, 1
    neu = 0 if pos != neg else 0
    return pos, neg, neu


def _label(pos: int, neg: int) -> str:
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def fetch_news(ticker: str, limit: int = 5) -> list[dict[str, Any]]:
    """抓取指定股票的近期新聞標題。

    從 Google News RSS 抓取 `ticker` 相關標題與連結，附簡易情緒標記
    （positive / negative / neutral）。

    Args:
        ticker: 股票代號（例：MSFT）。
        limit: 回傳新聞條目上限，預設 5。

    Returns:
        新聞列表，每項為 {title, link, sentiment} 之 dict。
    """
    import feedparser  # 延遲 import，避免無需 RSS 時仍要求套件

    url = (
        "https://news.google.com/rss/search"
        f"?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"
    )
    feed = feedparser.parse(url)
    entries: list[dict[str, Any]] = []
    for entry in feed.entries[:limit]:
        title = entry.get("title", "")
        link = entry.get("link", "")
        pos, neg, _ = _score_text(title)
        entries.append(
            {
                "ticker": ticker,
                "title": title,
                "link": link,
                "sentiment": _label(pos, neg),
            }
        )
    return entries


def read_news_file(path: str) -> list[dict[str, Any]]:
    """讀取本地新聞 CSV 檔並標注情緒。

    CSV 需有 `title`（及可選 `ticker` / `link`）欄位。此為讀取操作，但
    若路徑不存在會嘗試從 `data/news` 相對目錄解析。

    Args:
        path: CSV 檔案路徑。

    Returns:
        每行新聞 dict，加入 sentiment 欄位。
    """
    if not os.path.isabs(path):
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
        candidate = os.path.abspath(os.path.join(base, path))
        if os.path.exists(candidate):
            path = candidate
    if not os.path.exists(path):
        raise FileNotFoundError(f"News file not found: {path}")

    rows: list[dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            title = row.get("title", "")
            pos, neg, _ = _score_text(title)
            entry = dict(row)
            entry["sentiment"] = _label(pos, neg)
            rows.append(entry)
    return rows
