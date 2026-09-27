# RAG Lab SUMMARY

- tag: smoke_real2   runs: 2026-09-08 12:30:47
| strategy | recall@5 | prec@5 | MRR@5 | nDCG@5 | answer-F1 | trap-hit | usd | ms/run |
|---|---|---|---|---|---|---|---|---|
| naive | 0.833 | 0.344 | 0.444 | 0.523 | 0.122 | 1/1 | $0.0004 | 1985.7 |
| advanced | 0.833 | 0.200 | 0.444 | 0.523 | 0.176 | 0/1 | $0.0007 | 2494.9 |
| hybrid | 1.000 | 0.267 | 0.833 | 0.875 | 0.140 | 1/1 | $0.0007 | 2389.3 |
| corrective | 0.500 | 0.233 | 0.278 | 0.313 | 0.067 | 1/1 | $0.0003 | 1974.2 |
| adaptive | 0.833 | 0.344 | 0.444 | 0.523 | 0.118 | 1/1 | $0.0004 | 10128.4 |
| agentic | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0/1 | $0.0000 | 0.0 |

> 每條 pipe 定義同追蹤方法見 RAG_LAB.md；每個 stage 事件見 `<strategy>/events.jsonl`；逐 call replay 見 `<strategy>/<eid>/transcript.jsonl`。
