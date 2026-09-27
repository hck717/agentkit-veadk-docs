# report · none · 4 items
- recall@3: **0.833**  prec@3: 0.333  MRR@3: 0.833  nDCG@3: 0.796
- recall@5: 0.833  MRR@5: 0.833
- answer-F1: **0.084**   trap 唔作: 1/1
- cost: **$0.0003**  mean local ms: 168.3  mean Ark ms: 1105.0  local tokens: 0
- errors: —

## per-item

| eid | cat | recall@3 | prec@3 | mrr@3 | ndcg@3 | recall@5 | answer_F1 | trap | local_ms | ark_ms | $ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| f1 | fact | 1.000 | 0.333 | 1.000 | 1.000 | 1.000 | 0.107 | - | 139.6 | 1606.0 | $0.000064 |
| f9 | fact | 1.000 | 0.333 | 1.000 | 1.000 | 1.000 | 0.146 | - | 172.0 | 1064.0 | $0.000061 |
| t1 | trap | n/a | n/a | n/a | n/a | n/a | n/a | PASS | 182.0 | 482.5 | $0.000067 |
| m1 | multi_hop | 0.500 | 0.333 | 0.500 | 0.387 | 0.500 | 0.000 | - | 179.6 | 1267.6 | $0.000079 |
