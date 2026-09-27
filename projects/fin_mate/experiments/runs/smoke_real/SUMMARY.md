# RAG Lab SUMMARY

- tag: smoke_real   runs: 2026-09-08 12:08:36
| strategy | recall@5 | prec@5 | MRR@5 | nDCG@5 | answer-F1 | trap-hit | usd | ms/run |
|---|---|---|---|---|---|---|---|---|
| naive | 0.833 | 0.344 | 0.444 | 0.523 | 0.102 | 1/1 | $0.0004 | 2467.1 |
| advanced | 0.833 | 0.200 | 0.444 | 0.523 | 0.135 | 0/1 | $0.0007 | 2435.1 |
| hybrid | 1.000 | 0.267 | 0.833 | 0.875 | 0.134 | 1/1 | $0.0007 | 2315.6 |
| corrective | 0.667 | 0.278 | 0.333 | 0.421 | 0.085 | 0/1 | $0.0001 | 776.7 |
| adaptive | 0.500 | 0.233 | 0.278 | 0.313 | 0.054 | 1/1 | $0.0003 | 2222.9 |
| agentic | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0/1 | $0.0000 | 0.0 |

> 每條 pipe 定義同追蹤方法見 RAG_LAB.md；每個 stage 事件見 `<strategy>/events.jsonl`；逐 call replay 見 `<strategy>/<eid>/transcript.jsonl`。
