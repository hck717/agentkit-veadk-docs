# D8 fair redo SUMMARY (BytePlus AI + local OpenViking)

- tag: runs_260914_2335   runs: 2026-09-14 23:40:06
| run | axis | recall@5 | prec@5 | MRR@5 | nDCG@5 | answer-F1 | trap-hit | usd | ms/run |
|---|---|---|---|---|---|---|---|---|---|
| fair_default_naive | default | 0.731 | 0.256 | 0.564 | 0.603 | 0.086 | 2/2 | $0.0013 | 1850 |
| fair_default_hybrid | default | 0.808 | 0.185 | 0.579 | 0.633 | 0.099 | 2/2 | $0.0018 | 1771 |
| fair_chunk_naive | chunk | 0.769 | 0.288 | 0.628 | 0.636 | 0.113 | 2/2 | $0.0008 | 1425 |
| fair_chunk_hybrid | chunk | 0.962 | 0.237 | 0.659 | 0.715 | 0.148 | 2/2 | $0.0011 | 1850 |
| fair_vis_naive | vis | 0.694 | 0.210 | 0.569 | 0.598 | 0.123 | 2/2 | $0.0016 | 1509 |
| fair_vis_hybrid | vis | 0.694 | 0.156 | 0.569 | 0.598 | 0.122 | 2/2 | $0.0024 | 1654 |
| fair_gen_naive | gen | 0.731 | 0.256 | 0.564 | 0.603 | 0.079 | 2/2 | $0.0014 | 1902 |
| fair_gen_hybrid | gen | 0.808 | 0.185 | 0.579 | 0.633 | 0.136 | 2/2 | $0.0018 | 1735 |
| fair_cmb_naive | cmb | 0.722 | 0.261 | 0.625 | 0.629 | 0.140 | 2/2 | $0.0010 | 1216 |
| fair_cmb_hybrid | cmb | 0.806 | 0.194 | 0.636 | 0.665 | 0.145 | 2/2 | $0.0015 | 1697 |

> D4（同 stack）baseline：naive recall@5 0.964 / MRR 0.762 / answer-F1 0.109；hybrid recall@5 0.964 / MRR 0.929 / answer-F1 0.127。
