# RAG Lab SUMMARY

- tag: smoke1   runs: 2026-09-08 11:57:15
| strategy | recall@5 | prec@5 | MRR@5 | nDCG@5 | answer-F1 | trap-hit | usd | ms/run |
|---|---|---|---|---|---|---|---|---|
| naive | 0.833 | 0.344 | 0.444 | 0.523 | 0.000 | 0/1 | $0.0000 | 75.3 |
| advanced | 0.833 | 0.200 | 0.444 | 0.523 | 0.000 | 0/1 | $0.0000 | 116.2 |
| hybrid | 1.000 | 0.267 | 0.833 | 0.875 | 0.000 | 0/1 | $0.0000 | 86.5 |
| corrective | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0/1 | $0.0000 | 118.6 |
| adaptive | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0/1 | $0.0000 | 0.0 |

> 每條 pipe 定義同追蹤方法見 RAG_LAB.md；每個 stage 事件見 `<strategy>/events.jsonl`；逐 call replay 見 `<strategy>/<eid>/transcript.jsonl`。
