# RERANK Lab SUMMARY

- tag: rerank_260909_plumb   runs: 2026-09-09 08:59:32

| variant | recall@3 | prec@3 | MRR@3 | nDCG@3 | recall@5 | answer-F1 | trap | local ms/題 | Ark ms/題 | $ | local tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|
| none | 0.833 | 0.333 | 0.833 | 0.796 | 0.833 | 0.000 | 0/1 | 371.8  | 0.0    | $0.0000 | 0 |
| rrf | 0.833 | 0.333 | 0.778 | 0.769 | 1.000 | 0.000 | 0/1 | 82.1   | 0.0    | $0.0000 | 0 |
| llm | 0.833 | 0.333 | 0.833 | 0.796 | 0.833 | 0.000 | 0/1 | 70.5   | 0.0    | $0.0000 | 0 |

> pool：dense top-15 + grep ≤20（doc-prefix 去重），三 variant 共用同一 pool，只比排序。answer 用 top-5 ctx（multi-hop 要兩份 doc）；scoring 本地 Ollama $0（local tokens 另計）。RRF/LLM 詳情見 RAG_LAB.md §9；main-run 對照：hybrid recall@5=0.964 / MRR@5=0.929。
