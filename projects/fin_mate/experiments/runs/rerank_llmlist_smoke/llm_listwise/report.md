# report · llm_listwise · 4 items
- recall@3: **0.667**  prec@3: 0.222  MRR@3: 0.667  nDCG@3: 0.667
- recall@5: 0.833  MRR@5: 0.750
- answer-F1: **0.193**   trap 唔作: 1/1
- cost: **$0.0004**  mean local ms: 798.0  mean Ark ms: 2247.0  local tokens: 2443
- errors: —

## per-item

| eid | cat | recall@3 | prec@3 | mrr@3 | ndcg@3 | recall@5 | answer_F1 | trap | local_ms | ark_ms | $ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| f1 | fact | 1.000 | 0.333 | 1.000 | 1.000 | 1.000 | 0.118 | - | 766.5 | 1615.4 | $0.000044 |
| f9 | fact | 1.000 | 0.333 | 1.000 | 1.000 | 1.000 | 0.320 | - | 905.2 | 1709.1 | $0.000082 |
| t1 | trap | n/a | n/a | n/a | n/a | n/a | n/a | PASS | 746.6 | 516.7 | $0.000074 |
| m1 | multi_hop | 0.000 | 0.000 | 0.000 | 0.000 | 0.500 | 0.142 | - | 773.8 | 5146.5 | $0.000165 |
