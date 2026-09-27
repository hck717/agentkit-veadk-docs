# report · rrf · 4 items
- recall@3: **0.833**  prec@3: 0.333  MRR@3: 0.778  nDCG@3: 0.769
- recall@5: 1.000  MRR@5: 0.778
- answer-F1: **0.208**   trap 唔作: 1/1
- cost: **$0.0004**  mean local ms: 286.6  mean Ark ms: 2125.2  local tokens: 0
- errors: —

## per-item

| eid | cat | recall@3 | prec@3 | mrr@3 | ndcg@3 | recall@5 | answer_F1 | trap | local_ms | ark_ms | $ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| f1 | fact | 1.000 | 0.333 | 1.000 | 1.000 | 1.000 | 0.162 | - | 723.7 | 1317.8 | $0.000046 |
| f9 | fact | 1.000 | 0.333 | 1.000 | 1.000 | 1.000 | 0.320 | - | 135.5 | 1490.9 | $0.000078 |
| t1 | trap | n/a | n/a | n/a | n/a | n/a | n/a | PASS | 144.1 | 520.5 | $0.000067 |
| m1 | multi_hop | 0.500 | 0.333 | 0.333 | 0.307 | 1.000 | 0.140 | - | 143.2 | 5171.7 | $0.000168 |
