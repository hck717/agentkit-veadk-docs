# report · jbv_original_mini · 37 items

- 原裝：mini 決策（本 account 冇 → =flash 對照）

- QA recall@5: **0.808**  gate-recall@5: 0.808  answer-F1: **0.085**  trap: 2/2
- tool pass: **8/8**  (jev fallback: 0)
- sentiment pass: **6/6**
- memory answer-F1: **0.420**  selection-F1(jev only): n/a

- Jev decisions: 0  median: n/a ms  (total run: 39107 ms)
- cost: **$0.0017**   tokens: 54615+2446

## per-item

| eid | fam | metric | ms | note |
|---|---|---|---|---|
| f1 | qa | r5=1.000 f1=0.000 | 1005 |  |
| f2 | qa | r5=1.000 f1=0.000 | 4059 |  |
| f3 | qa | r5=1.000 f1=0.033 | 1754 |  |
| f4 | qa | r5=1.000 f1=0.000 | 734 |  |
| f5 | qa | r5=0.000 f1=0.000 | 1048 |  |
| f6 | qa | r5=1.000 f1=0.061 | 943 |  |
| f7 | qa | r5=1.000 f1=0.211 | 1673 |  |
| f8 | qa | r5=1.000 f1=0.263 | 1273 |  |
| f9 | qa | r5=1.000 f1=0.233 | 1594 |  |
| f10 | qa | r5=1.000 f1=0.049 | 1676 |  |
| f11 | qa | r5=0.000 f1=0.000 | 857 |  |
| t1 | qa | r5=n/a f1=n/a trap=P | 638 |  |
| t2 | qa | r5=n/a f1=n/a trap=P | 610 |  |
| m1 | qa | r5=0.500 f1=0.000 | 694 |  |
| m2 | qa | r5=1.000 f1=0.261 | 3930 |  |
| tc_calc_01 | tool | PASS | 439 |  |
| tc_calc_02 | tool | PASS | 541 |  |
| tc_calc_03 | tool | PASS | 584 |  |
| tc_calc_04 | tool | PASS | 506 |  |
| tc_calc_05 | tool | PASS | 545 |  |
| tc_news_01 | tool | PASS | 602 |  |
| tc_news_02 | tool | PASS | 724 |  |
| tc_news_03 | tool | PASS | 555 |  |
| sent_3w_01 | sent | PASS pred=positive
微软云收入超过500亿美元，同比增长26% | 415 |  |
| sent_3w_02 | sent | PASS pred=negative
The title indicates that Microsoft shares fell after Azure growth missed expectations. A | 597 |  |
| sent_3w_03 | sent | PASS pred=neutral
The title "Taiwan Semiconductor holds its guidance steady this quarter" | 533 |  |
| sent_3w_04 | sent | PASS pred=positive
解析：标题中提到“Microsoft wins big government cloud deal”（ | 521 |  |
| sent_3w_05 | sent | PASS pred=negative
The title mentions a bank warning about an AI capex bubble and cutting | 524 |  |
| sent_3w_06 | sent | PASS pred=positive
Wells Fargo upgrades Microsoft, which means the financial institution has a positive | 549 |  |
| mem_01 | mem | f1=0.667 selF1=n/a | 660 |  |
| mem_02 | mem | f1=0.462 selF1=n/a | 2002 |  |
| mem_03 | mem | f1=0.000 selF1=n/a | 1418 |  |
| mem_04 | mem | f1=0.667 selF1=n/a | 860 |  |
| mem_05 | mem | f1=0.500 selF1=n/a | 1158 |  |
| mem_06 | mem | f1=0.667 selF1=n/a | 707 |  |
| mem_07 | mem | f1=0.000 selF1=n/a | 1117 |  |
| mem_08 | mem | f1=0.400 selF1=n/a | 1063 |  |
