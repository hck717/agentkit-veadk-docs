# report · naive · 4 items

- recall@5: **0.833**  prec@5: 0.344  MRR@5: 0.444  nDCG@5: 0.523
- answer-F1: **0.137**  trap 唔作: 1/1
- cost: **$0.0004**  mean/call-set: 2122.9 ms
- errors: —

## per-item

| eid | cat | recall@5 | prec@5 | mrr@5 | ndcg@5 | answer_F1 | trap | usd |
|---|---|---|---|---|---|---|---|---|
| f1 | fact | 1.000 | 0.500 | 0.500 | 0.631 | 0.095 | - | $0.000093 |
| f9 | fact | 1.000 | 0.333 | 0.500 | 0.631 | 0.162 | - | $0.000054 |
| t1 | trap | n/a | n/a | n/a | n/a | n/a | PASS | $0.000044 |
| m1 | multi_hop | 0.500 | 0.200 | 0.333 | 0.307 | 0.153 | - | $0.000168 |
