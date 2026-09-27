# D7 corpus-shaping RAG SUMMARY

- tag: 260914_2158   runs: 2026-09-14 21:59:03
| run | axis | recall@5 | prec@5 | MRR@5 | nDCG@5 | answer-F1 | trap-hit | usd | ms/run |
|---|---|---|---|---|---|---|---|---|---|
| d7_mm_naive | mm | 1.000 | 0.333 | 1.000 | 1.000 | 0.170 | — | $0.0001 | 1303 |
| d7_mm_hybrid | mm | 1.000 | 0.200 | 0.625 | 0.715 | 0.153 | — | $0.0003 | 1182 |

> 對比 D4（OpenViking + Ark embed）：naive recall@5 0.964 / MRR 0.762 / answer-F1 0.109；hybrid recall@5 0.964 / MRR 0.929 / answer-F1 0.127（RESULTS.md）。
