# report · adaptive · 4 items

- recall@5: **0.500**  prec@5: 0.233  MRR@5: 0.278  nDCG@5: 0.313
- answer-F1: **0.054**  trap 唔作: 1/1
- cost: **$0.0003**  mean/call-set: 2222.9 ms
- errors: ['f9']

## per-item

| eid | cat | recall@5 | prec@5 | mrr@5 | ndcg@5 | answer_F1 | trap | usd |
|---|---|---|---|---|---|---|---|---|
| f1 | fact | 1.000 | 0.500 | 0.500 | 0.631 | 0.058 | - | $0.000100 |
| f9 | fact | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | - | $0.000000 |
| t1 | trap | n/a | n/a | n/a | n/a | n/a | PASS | $0.000044 |
| m1 | multi_hop | 0.500 | 0.200 | 0.333 | 0.307 | 0.103 | - | $0.000168 |
