# RAG Lab SUMMARY

- tag: smoke_all7   runs: 2026-09-08 15:50:53
| strategy | recall@5 | prec@5 | MRR@5 | nDCG@5 | answer-F1 | trap-hit | usd | ms/run |
|---|---|---|---|---|---|---|---|---|
| naive | 0.833 | 0.344 | 0.444 | 0.523 | 0.137 | 1/1 | $0.0004 | 2122.9 |
| advanced | 0.833 | 0.200 | 0.444 | 0.523 | 0.124 | 0/1 | $0.0007 | 2530.0 |
| hybrid | 1.000 | 0.267 | 0.833 | 0.875 | 0.117 | 1/1 | $0.0007 | 2265.0 |
| corrective | 0.833 | 0.344 | 0.444 | 0.523 | 0.117 | 1/1 | $0.0003 | 2209.7 |
| adaptive | 0.833 | 0.344 | 0.444 | 0.523 | 0.107 | 0/1 | $0.0004 | 3235.8 |
| agentic | 0.000 | 0.000 | 0.000 | 0.000 | 0.069 | 1/1 | $0.0007 | 12776.5 |

> 每條 pipe 定義同追蹤方法見 RAG_LAB.md；每個 stage 事件見 `<strategy>/events.jsonl`；逐 call replay 見 `<strategy>/<eid>/transcript.jsonl`。
