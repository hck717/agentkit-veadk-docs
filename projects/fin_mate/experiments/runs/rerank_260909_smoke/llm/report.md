# report · llm · 4 items
- recall@3: **0.833**  prec@3: 0.333  MRR@3: 0.778  nDCG@3: 0.769
- recall@5: 0.833  MRR@5: 0.778
- answer-F1: **0.130**   trap 唔作: 1/1
- cost: **$0.0003**  mean local ms: 1586.8  mean Ark ms: 1783.8  local tokens: 5229
- errors: —

## per-item

| eid | cat | recall@3 | prec@3 | mrr@3 | ndcg@3 | recall@5 | answer_F1 | trap | local_ms | ark_ms | $ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| f1 | fact | 1.000 | 0.333 | 1.000 | 1.000 | 1.000 | 0.133 | - | 1068.3 | 1583.1 | $0.000057 |
| f9 | fact | 1.000 | 0.333 | 1.000 | 1.000 | 1.000 | 0.162 | - | 2153.7 | 881.9 | $0.000058 |
| t1 | trap | n/a | n/a | n/a | n/a | n/a | n/a | PASS | 1483.1 | 446.0 | $0.000049 |
| m1 | multi_hop | 0.500 | 0.333 | 0.333 | 0.307 | 0.500 | 0.094 | - | 1641.9 | 4224.3 | $0.000165 |
