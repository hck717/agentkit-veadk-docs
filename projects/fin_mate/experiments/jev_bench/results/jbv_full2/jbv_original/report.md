# report · jbv_original · 37 items

- 原裝：flash 全程

- QA recall@5: **0.808**  gate-recall@5: 0.808  answer-F1: **0.087**  trap: 2/2
- tool pass: **8/8**  (jev fallback: 0)
- sentiment pass: **6/6**
- memory answer-F1: **0.409**  selection-F1(jev only): n/a

- Jev decisions: 0  median: n/a ms  (total run: 41613 ms)
- cost: **$0.0017**   tokens: 54615+2670

## per-item

| eid | fam | metric | ms | note |
|---|---|---|---|---|
| f1 | qa | r5=1.000 f1=0.000 | 1062 |  |
| f2 | qa | r5=1.000 f1=0.000 | 2230 |  |
| f3 | qa | r5=1.000 f1=0.033 | 2211 |  |
| f4 | qa | r5=1.000 f1=0.000 | 713 |  |
| f5 | qa | r5=0.000 f1=0.000 | 670 |  |
| f6 | qa | r5=1.000 f1=0.061 | 1139 |  |
| f7 | qa | r5=1.000 f1=0.197 | 1893 |  |
| f8 | qa | r5=1.000 f1=0.250 | 1301 |  |
| f9 | qa | r5=1.000 f1=0.146 | 1361 |  |
| f10 | qa | r5=1.000 f1=0.100 | 1068 |  |
| f11 | qa | r5=0.000 f1=0.000 | 616 |  |
| t1 | qa | r5=n/a f1=n/a trap=P | 666 |  |
| t2 | qa | r5=n/a f1=n/a trap=P | 634 |  |
| m1 | qa | r5=0.500 f1=0.108 | 4949 |  |
| m2 | qa | r5=1.000 f1=0.236 | 4416 |  |
| tc_calc_01 | tool | PASS | 481 |  |
| tc_calc_02 | tool | PASS | 528 |  |
| tc_calc_03 | tool | PASS | 546 |  |
| tc_calc_04 | tool | PASS | 646 |  |
| tc_calc_05 | tool | PASS | 591 |  |
| tc_news_01 | tool | PASS | 652 |  |
| tc_news_02 | tool | PASS | 523 |  |
| tc_news_03 | tool | PASS | 526 |  |
| sent_3w_01 | sent | PASS pred=positive
The title states that Microsoft Cloud revenue has exceeded $50 billion and | 1571 |  |
| sent_3w_02 | sent | PASS pred=negative
 | 371 |  |
| sent_3w_03 | sent | PASS pred=neutral
该标题只是陈述了台湾半导体本季度维持其指引这一 | 533 |  |
| sent_3w_04 | sent | PASS pred=positive
解析：标题中提到“Microsoft wins big government cloud deal”（ | 552 |  |
| sent_3w_05 | sent | PASS pred=negative
The title mentions a bank warning about an AI capex bubble and cutting | 642 |  |
| sent_3w_06 | sent | PASS pred=positive
Wells Fargo upgrades Microsoft and raises its price target, which is a | 589 |  |
| mem_01 | mem | f1=0.750 selF1=n/a | 525 |  |
| mem_02 | mem | f1=0.500 selF1=n/a | 692 |  |
| mem_03 | mem | f1=0.000 selF1=n/a | 1180 |  |
| mem_04 | mem | f1=0.667 selF1=n/a | 737 |  |
| mem_05 | mem | f1=0.400 selF1=n/a | 1526 |  |
| mem_06 | mem | f1=0.667 selF1=n/a | 728 |  |
| mem_07 | mem | f1=0.000 selF1=n/a | 1195 |  |
| mem_08 | mem | f1=0.286 selF1=n/a | 1350 |  |
