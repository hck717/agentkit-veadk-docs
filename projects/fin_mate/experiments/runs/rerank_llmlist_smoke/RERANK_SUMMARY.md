# RERANK Lab SUMMARY

- tag: rerank_llmlist_smoke   runs: 2026-09-09 09:58:41

| variant | recall@3 | prec@3 | MRR@3 | nDCG@3 | recall@5 | answer-F1 | trap | local ms/題 | Ark ms/題 | $ | local tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|
| llm_listwise | 0.667 | 0.222 | 0.667 | 0.667 | 0.833 | 0.193 | 1/1 | 815.2  | 2823.7 | $0.0004 | 2443 |

> pool：dense top-15 + grep ≤20（doc-prefix 去重），三 variant 共用同一 pool，只比排序。answer 用 top-5 ctx（multi-hop 要兩份 doc）；scoring 本地 Ollama $0（local tokens 另計）。RRF/LLM 詳情見 RAG_LAB.md §9；main-run 對照：hybrid recall@5=0.964 / MRR@5=0.929。
