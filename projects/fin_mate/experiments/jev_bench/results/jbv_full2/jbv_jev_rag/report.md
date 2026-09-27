# report · jbv_jev_rag · 37 items

- Jev Score gate 檢索

- QA recall@5: **0.808**  gate-recall@5: 0.308  answer-F1: **0.102**  trap: 1/2
- tool pass: **8/8**  (jev fallback: 0)
- sentiment pass: **6/6**
- memory answer-F1: **0.389**  selection-F1(jev only): n/a

- Jev decisions: 94  median: 480 ms  (total run: 94997 ms)
- cost: **$0.0020**   tokens: 61540+3515

## per-item

| eid | fam | metric | ms | note |
|---|---|---|---|---|
| f1 | qa | r5=1.000 f1=0.091 | 3457 |  |
| f2 | qa | r5=1.000 f1=0.031 | 5456 |  |
| f3 | qa | r5=1.000 f1=0.074 | 3477 |  |
| f4 | qa | r5=1.000 f1=0.000 | 4736 |  |
| f5 | qa | r5=0.000 f1=0.235 | 3934 |  |
| f6 | qa | r5=1.000 f1=0.083 | 3798 |  |
| f7 | qa | r5=1.000 f1=0.214 | 4288 |  |
| f8 | qa | r5=1.000 f1=0.233 | 7596 |  |
| f9 | qa | r5=1.000 f1=0.103 | 4149 |  |
| f10 | qa | r5=1.000 f1=0.000 | 4924 |  |
| f11 | qa | r5=0.000 f1=0.000 | 5576 |  |
| t1 | qa | r5=n/a f1=n/a trap=F | 7329 |  |
| t2 | qa | r5=n/a f1=n/a trap=P | 3235 |  |
| m1 | qa | r5=0.500 f1=0.105 | 8912 |  |
| m2 | qa | r5=1.000 f1=0.158 | 6820 |  |
| tc_calc_01 | tool | PASS | 487 |  |
| tc_calc_02 | tool | PASS | 1560 |  |
| tc_calc_03 | tool | PASS | 483 |  |
| tc_calc_04 | tool | PASS | 554 |  |
| tc_calc_05 | tool | PASS | 489 |  |
| tc_news_01 | tool | PASS | 525 |  |
| tc_news_02 | tool | PASS | 537 |  |
| tc_news_03 | tool | PASS | 540 |  |
| sent_3w_01 | sent | PASS pred=positive
微软云服务收入突破500亿美元，同比增长26 | 494 |  |
| sent_3w_02 | sent | PASS pred=negative
The title indicates that Microsoft shares fell after Azure growth missed expectations. A | 527 |  |
| sent_3w_03 | sent | PASS pred=neutral
“holds its guidance steady” 只是表明保持了之前的指引 | 702 |  |
| sent_3w_04 | sent | PASS pred=positive
The title states that Microsoft has won a major government cloud deal and its | 440 |  |
| sent_3w_05 | sent | PASS pred=negative
The title mentions a bank warning of an AI capex bubble and cutting | 561 |  |
| sent_3w_06 | sent | PASS pred=positive
Wells Fargo upgrades Microsoft and raises the price target to $60 | 537 |  |
| mem_01 | mem | f1=0.750 selF1=n/a | 555 |  |
| mem_02 | mem | f1=0.273 selF1=n/a | 1649 |  |
| mem_03 | mem | f1=0.000 selF1=n/a | 1167 |  |
| mem_04 | mem | f1=0.667 selF1=n/a | 677 |  |
| mem_05 | mem | f1=0.333 selF1=n/a | 2337 |  |
| mem_06 | mem | f1=0.800 selF1=n/a | 702 |  |
| mem_07 | mem | f1=0.000 selF1=n/a | 782 |  |
| mem_08 | mem | f1=0.286 selF1=n/a | 1001 |  |
