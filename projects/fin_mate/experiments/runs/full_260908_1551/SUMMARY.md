# RAG Lab SUMMARY

- tag: full_260908_1551   runs: 2026-09-08 15:57:23
| strategy | recall@5 | prec@5 | MRR@5 | nDCG@5 | answer-F1 | trap-hit | usd | ms/run |
|---|---|---|---|---|---|---|---|---|
| naive | 0.964 | 0.418 | 0.762 | 0.801 | 0.109 | 2/2 | $0.0011 | 1576.2 |
| advanced | 0.964 | 0.214 | 0.762 | 0.801 | 0.105 | 1/2 | $0.0021 | 1814.0 |
| hybrid | 0.964 | 0.214 | 0.929 | 0.929 | 0.127 | 2/2 | $0.0021 | 1754.0 |
| corrective | 0.607 | 0.287 | 0.524 | 0.532 | 0.077 | 1/2 | $0.0008 | 1354.1 |
| adaptive | 0.964 | 0.418 | 0.762 | 0.801 | 0.112 | 2/2 | $0.0012 | 2079.1 |
| agentic | 0.750 | 0.500 | 0.494 | 1.328 | 0.056 | 2/2 | $0.0023 | 11810.7 |

> 每條 pipe 定義同追蹤方法見 RAG_LAB.md；每個 stage 事件見 `<strategy>/events.jsonl`；逐 call replay 見 `<strategy>/<eid>/transcript.jsonl`。

> agentic 行由 full_agentic_260908_1601 併入（uris 用 raw viking://，recall/prec/MRR 有意義；nDCG 因 _rel 以 token overlap 計會超 1。
