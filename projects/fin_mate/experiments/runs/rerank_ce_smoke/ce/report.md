# report · ce · 4 items
- recall@3: **0.833**  prec@3: 0.333  MRR@3: 0.833  nDCG@3: 0.796
- recall@5: 1.000  MRR@5: 0.833
- answer-F1: **0.140**   trap 唔作: 1/1
- cost: **$0.0004**  mean local ms: 4049.8  mean Ark ms: 1980.6  local tokens: 0
- errors: —

## per-item

| eid | cat | recall@3 | prec@3 | mrr@3 | ndcg@3 | recall@5 | answer_F1 | trap | local_ms | ark_ms | $ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| f1 | fact | 1.000 | 0.333 | 1.000 | 1.000 | 1.000 | 0.118 | - | 13223.4 | 1093.2 | $0.000044 |
| f9 | fact | 1.000 | 0.333 | 1.000 | 1.000 | 1.000 | 0.211 | - | 946.9 | 1974.4 | $0.000099 |
| t1 | trap | n/a | n/a | n/a | n/a | n/a | n/a | PASS | 935.1 | 607.2 | $0.000067 |
| m1 | multi_hop | 0.500 | 0.333 | 0.500 | 0.387 | 1.000 | 0.092 | - | 1093.6 | 4247.8 | $0.000167 |
