# RERANK Lab SUMMARY

- tag: rerank_260909_full   runs: 2026-09-09 09:03:44

| variant | recall@3 | prec@3 | MRR@3 | nDCG@3 | recall@5 | answer-F1 | trap | local ms/題 | Ark ms/題 | $ | local tokens |
|---|---|---|---|---|---|---|---|---|---|---|---|
| none | 0.962 | 0.359 | 0.923 | 0.918 | 0.962 | 0.111 | 2/2 | 138.3  | 1528.9 | $0.0010 | 0 |
| rrf | 0.923 | 0.333 | 0.910 | 0.899 | 0.962 | 0.039 | 1/2 | 126.8  | 562.7  | $0.0002 | 0 |
| llm | 0.923 | 0.333 | 0.872 | 0.860 | 0.962 | 0.108 | 2/2 | 2855.1 | 1544.2 | $0.0010 | 17871 |

> pool：dense top-15 + grep ≤20（doc-prefix 去重），三 variant 共用同一 pool，只比排序。answer 用 top-5 ctx（multi-hop 要兩份 doc）；scoring 本地 Ollama $0（local tokens 另計）。RRF/LLM 詳情見 RAG_LAB.md §9；main-run 對照：hybrid recall@5=0.964 / MRR@5=0.929。
