# RAG Lab SUMMARY

- tag: smoke_all6   runs: 2026-09-08 15:47:52
| strategy | recall@5 | prec@5 | MRR@5 | nDCG@5 | answer-F1 | trap-hit | usd | ms/run |
|---|---|---|---|---|---|---|---|---|
| naive | 0.833 | 0.344 | 0.444 | 0.523 | 0.108 | 1/1 | $0.0004 | 2170.7 |
| advanced | 0.833 | 0.200 | 0.444 | 0.523 | 0.155 | 0/1 | $0.0007 | 2526.7 |
| hybrid | 1.000 | 0.267 | 0.833 | 0.875 | 0.139 | 1/1 | $0.0006 | 2063.3 |
| corrective | 0.833 | 0.344 | 0.444 | 0.523 | 0.132 | 1/1 | $0.0003 | 1967.1 |
| adaptive | 0.500 | 0.233 | 0.278 | 0.313 | 0.113 | 1/1 | $0.0003 | 2339.0 |
| agentic | 0.000 | 0.000 | 0.000 | 0.000 | 0.133 | 1/1 | $0.0007 | 12049.7 |

> 每條 pipe 定義同追蹤方法見 RAG_LAB.md；每個 stage 事件見 `<strategy>/events.jsonl`；逐 call replay 見 `<strategy>/<eid>/transcript.jsonl`。
