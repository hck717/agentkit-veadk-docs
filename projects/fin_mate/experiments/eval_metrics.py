"""RAG 實驗室自有平分：recall@k / precision@k / MRR@k / nDCG@k / answer-F1（token overlap）。

gold = doc-level URI prefix 集合（`eval_set` 每題馘 gold_docs filename → resolve_gold() 轉 URI）。
retrieved = 有順序嘅 URI list。全部純 function，無 I/O。
"""
from __future__ import annotations

import re
from math import log2


def _rel(gold: set[str], uri: str) -> bool:
    return bool(uri and any(uri.startswith(g) for g in gold))


def recall_at_k(gold: set[str], uris: list[str], k: int = 5) -> float:
    gold = set(gold or [])
    if not gold:
        return 0.0
    return len({g for g in gold for u in uris[:k] if u and u.startswith(g)}) / len(gold)


def precision_at_k(gold: set[str], uris: list[str], k: int = 5) -> float:
    top = list(uris[:k])
    return sum(1 for u in top if _rel(gold, u)) / len(top) if top else 0.0


def mrr_at_k(gold: set[str], uris: list[str], k: int = 5) -> float:
    for i, u in enumerate(uris[:k], 1):
        if _rel(gold, u):
            return 1.0 / i
    return 0.0


def ndcg_at_k(gold: set[str], uris: list[str], k: int = 5) -> float:
    gold = set(gold or [])
    top = list(uris[:k])
    if not top or not gold:
        return 0.0
    rel = [1.0 if _rel(gold, u) else 0.0 for u in top]
    dcg = sum(r / log2(i + 1) for i, r in enumerate(rel, 1))
    idcg = sum(1.0 / log2(i + 1) for i in range(1, min(len(gold), len(top)) + 1))
    return dcg / idcg if idcg else 0.0


def _tok(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (s or "").lower())


def answer_f1(gold: str, pred: str) -> float:
    g, p = _tok(gold), _tok(pred)
    if not g or not p:
        return 0.0
    inter = sum(min(g.count(t), p.count(t)) for t in set(g) & set(p))
    prec, rec = inter / len(p), inter / len(g)
    return 2 * prec * rec / (prec + rec) if prec + rec else 0.0


if __name__ == "__main__":
    gold = {"viking://resources/fin_kb/msft_txt/A/", "viking://resources/fin_kb/msft_txt/B/"}
    uris = ["viking://resources/fin_kb/msft_txt/A/1.md", "viking://resources/fin_kb/msft_txt/C/1.md",
            "viking://resources/fin_kb/msft_txt/B/1.md"]
    assert recall_at_k(gold, uris, 3) == 1.0
    assert precision_at_k(gold, uris, 3) == 2 / 3
    assert mrr_at_k(gold, uris, 3) == 1.0
    assert abs(ndcg_at_k(gold, uris, 3) - (1 + 0.5) / (1 + 1 / log2(3))) < 1e-9
    assert answer_f1("Microsoft Cloud revenue was 50 billion", "cloud revenue was 50b") > 0.5
    assert recall_at_k(gold, uris, 1) == 0.5
    print("eval_metrics OK")