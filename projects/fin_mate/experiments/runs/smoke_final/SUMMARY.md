# RAG Lab SUMMARY

- tag: smoke_final   runs: 2026-09-08 12:00:03
| strategy | recall@5 | prec@5 | MRR@5 | nDCG@5 | answer-F1 | trap-hit | usd | ms/run |
|---|---|---|---|---|---|---|---|---|
| naive | 0.833 | 0.344 | 0.444 | 0.523 | 0.000 | 0/1 | $0.0000 | 71.1 |
| advanced | 0.833 | 0.200 | 0.444 | 0.523 | 0.000 | 0/1 | $0.0000 | 86.3 |
| hybrid | 1.000 | 0.267 | 0.833 | 0.875 | 0.000 | 0/1 | $0.0000 | 100.4 |
| corrective | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0/1 | $0.0000 | 178.0 |
| adaptive | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0/1 | $0.0000 | 0.0 |

> 每條 pipe 定義同追蹤方法見 RAG_LAB.md；每個 stage 事件見 `<strategy>/events.jsonl`；逐 call replay 見 `<strategy>/<eid>/transcript.jsonl`。
