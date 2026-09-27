# report · jbv_original · 37 items

- 原裝：flash 全程

- QA recall@5: **0.808**  gate-recall@5: 0.808  answer-F1: **0.085**  trap: 2/2
- tool pass: **8/8**  (jev fallback: 0)
- sentiment pass: **6/6**
- memory answer-F1: **0.412**  selection-F1(jev only): n/a

- Jev decisions: 0  median: n/a ms  (total run: 41640 ms)
- cost: **$0.0017**   tokens: 54615+2493

## per-item

| eid | fam | metric | ms | note |
|---|---|---|---|---|
| f1 | qa | r5=1.000 f1=0.000 | 979 |  |
| f2 | qa | r5=1.000 f1=0.000 | 4594 |  |
| f3 | qa | r5=1.000 f1=0.032 | 2112 |  |
| f4 | qa | r5=1.000 f1=0.000 | 839 |  |
| f5 | qa | r5=0.000 f1=0.000 | 1949 |  |
| f6 | qa | r5=1.000 f1=0.061 | 1242 |  |
| f7 | qa | r5=1.000 f1=0.214 | 1688 |  |
| f8 | qa | r5=1.000 f1=0.256 | 1692 |  |
| f9 | qa | r5=1.000 f1=0.146 | 1653 |  |
| f10 | qa | r5=1.000 f1=0.100 | 1070 |  |
| f11 | qa | r5=0.000 f1=0.000 | 961 |  |
| t1 | qa | r5=n/a f1=n/a trap=P | 800 |  |
| t2 | qa | r5=n/a f1=n/a trap=P | 716 |  |
| m1 | qa | r5=0.500 f1=0.000 | 747 |  |
| m2 | qa | r5=1.000 f1=0.295 | 5381 |  |
| tc_calc_01 | tool | PASS | 498 |  |
| tc_calc_02 | tool | PASS | 582 |  |
| tc_calc_03 | tool | PASS | 662 |  |
| tc_calc_04 | tool | PASS | 522 |  |
| tc_calc_05 | tool | PASS | 525 |  |
| tc_news_01 | tool | PASS | 536 |  |
| tc_news_02 | tool | PASS | 597 |  |
| tc_news_03 | tool | PASS | 524 |  |
| sent_3w_01 | sent | PASS pred=positive
Microsoft Cloud revenue surpassing $50 billion with a 26 | 468 |  |
| sent_3w_02 | sent | PASS pred=negative
The title indicates that Microsoft's shares fell after Azure growth missed expectations. | 489 |  |
| sent_3w_03 | sent | PASS pred=neutral
 | 356 |  |
| sent_3w_04 | sent | PASS pred=positive
解析：标题中提到“Microsoft wins big government cloud deal（微软 | 564 |  |
| sent_3w_05 | sent | PASS pred=negative
The title mentions a bank warning about an AI capex bubble and cutting | 653 |  |
| sent_3w_06 | sent | PASS pred=positive
Wells Fargo upgrades Microsoft and raises its price target, which is a | 524 |  |
| mem_01 | mem | f1=0.667 selF1=n/a | 656 |  |
| mem_02 | mem | f1=0.400 selF1=n/a | 983 |  |
| mem_03 | mem | f1=0.000 selF1=n/a | 1181 |  |
| mem_04 | mem | f1=0.667 selF1=n/a | 672 |  |
| mem_05 | mem | f1=0.364 selF1=n/a | 1259 |  |
| mem_06 | mem | f1=0.800 selF1=n/a | 828 |  |
| mem_07 | mem | f1=0.000 selF1=n/a | 847 |  |
| mem_08 | mem | f1=0.400 selF1=n/a | 1292 |  |
