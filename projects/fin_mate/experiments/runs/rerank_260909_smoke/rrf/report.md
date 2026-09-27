# report · rrf · 4 items
- recall@3: **0.833**  prec@3: 0.333  MRR@3: 0.778  nDCG@3: 0.769
- recall@5: 1.000  MRR@5: 0.778
- answer-F1: **0.000**   trap 唔作: 0/1
- cost: **$0.0001**  mean local ms: 148.8  mean Ark ms: 1430.9  local tokens: 0
- errors: —

## per-item

| eid | cat | recall@3 | prec@3 | mrr@3 | ndcg@3 | recall@5 | answer_F1 | trap | local_ms | ark_ms | $ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| f1 | fact | 1.000 | 0.333 | 1.000 | 1.000 | 1.000 | 0.000 | - | 118.9 | 431.6 | $0.000002 |
| f9 | fact | 1.000 | 0.333 | 1.000 | 1.000 | 1.000 | 0.000 | - | 146.6 | 331.5 | $0.000002 |
| t1 | trap | n/a | n/a | n/a | n/a | n/a | n/a | - | 148.3 | 4408.9 | $0.000109 |
| m1 | multi_hop | 0.500 | 0.333 | 0.333 | 0.307 | 1.000 | 0.000 | - | 181.5 | 551.6 | $0.000002 |
