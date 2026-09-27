# D7 corpus-shaping RAG SUMMARY

- tag: d7_final   runs: 2026-09-14 22:03:40
| run | axis | recall@5 | prec@5 | MRR@5 | nDCG@5 | answer-F1 | trap-hit | usd | ms/run |
|---|---|---|---|---|---|---|---|---|---|
| d7_default_naive | default | 0.885 | 0.654 | 0.846 | 0.837 | 0.136 | 2/2 | $0.0008 | 1400 |
| d7_default_hybrid | default | 0.962 | 0.236 | 0.776 | 0.823 | 0.138 | 1/2 | $0.0020 | 2042 |
| d7_chunk_naive | chunk | 0.923 | 0.686 | 0.872 | 0.860 | 0.093 | 2/2 | $0.0006 | 1449 |
| d7_chunk_hybrid | chunk | 0.962 | 0.240 | 0.904 | 0.915 | 0.124 | 2/2 | $0.0013 | 1797 |
| d7_mm_naive | mm | 0.861 | 0.528 | 0.782 | 0.787 | 0.187 | 2/2 | $0.0010 | 1104 |
| d7_mm_hybrid | mm | 0.917 | 0.206 | 0.619 | 0.690 | 0.202 | 1/2 | $0.0028 | 1889 |
| d7_gen_naive | gen | 0.885 | 0.654 | 0.846 | 0.837 | 0.129 | 2/2 | $0.0008 | 1268 |
| d7_gen_hybrid | gen | 0.962 | 0.236 | 0.776 | 0.823 | 0.148 | 1/2 | $0.0021 | 2321 |

> 對比 D4（OpenViking + Ark embed）：naive recall@5 0.964 / MRR 0.762 / answer-F1 0.109；hybrid recall@5 0.964 / MRR 0.929 / answer-F1 0.127（RESULTS.md）。
