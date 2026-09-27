# report · jbv_jev_mem · 37 items

- Jev 篩記憶

- QA recall@5: **0.808**  gate-recall@5: 0.808  answer-F1: **0.069**  trap: 2/2
- tool pass: **8/8**  (jev fallback: 0)
- sentiment pass: **6/6**
- memory answer-F1: **0.448**  selection-F1(jev only): 1.000

- Jev decisions: 26  median: 391 ms  (total run: 46948 ms)
- cost: **$0.0018**   tokens: 60179+2547

## per-item

| eid | fam | metric | ms | note |
|---|---|---|---|---|
| f1 | qa | r5=1.000 f1=0.000 | 1007 |  |
| f2 | qa | r5=1.000 f1=0.000 | 4079 |  |
| f3 | qa | r5=1.000 f1=0.032 | 1865 |  |
| f4 | qa | r5=1.000 f1=0.000 | 672 |  |
| f5 | qa | r5=0.000 f1=0.000 | 694 |  |
| f6 | qa | r5=1.000 f1=0.061 | 1068 |  |
| f7 | qa | r5=1.000 f1=0.211 | 1441 |  |
| f8 | qa | r5=1.000 f1=0.256 | 1343 |  |
| f9 | qa | r5=1.000 f1=0.143 | 1913 |  |
| f10 | qa | r5=1.000 f1=0.049 | 1425 |  |
| f11 | qa | r5=0.000 f1=0.000 | 655 |  |
| t1 | qa | r5=n/a f1=n/a trap=P | 730 |  |
| t2 | qa | r5=n/a f1=n/a trap=P | 602 |  |
| m1 | qa | r5=0.500 f1=0.000 | 721 |  |
| m2 | qa | r5=1.000 f1=0.143 | 4239 |  |
| tc_calc_01 | tool | PASS | 415 |  |
| tc_calc_02 | tool | PASS | 494 |  |
| tc_calc_03 | tool | PASS | 529 |  |
| tc_calc_04 | tool | PASS | 578 |  |
| tc_calc_05 | tool | PASS | 580 |  |
| tc_news_01 | tool | PASS | 594 |  |
| tc_news_02 | tool | PASS | 444 |  |
| tc_news_03 | tool | PASS | 576 |  |
| sent_3w_01 | sent | PASS pred=positive
The title states that Microsoft Cloud revenue has exceeded $50 billion and | 461 |  |
| sent_3w_02 | sent | PASS pred=negative
### 解析
標題提到“Microsoft shares fall 4% | 471 |  |
| sent_3w_03 | sent | PASS pred=neutral
 | 373 |  |
| sent_3w_04 | sent | PASS pred=positive
Microsoft赢得大型政府云计算交易，股价飙升，这些都是积极的 | 500 |  |
| sent_3w_05 | sent | PASS pred=negative
The title indicates that a bank is warning about an AI capital expenditure ( | 479 |  |
| sent_3w_06 | sent | PASS pred=positive
Wells Fargo upgrades Microsoft and raises its price target, which is a | 513 |  |
| mem_01 | mem | f1=0.667 selF1=1.000 | 2345 |  |
| mem_02 | mem | f1=0.857 selF1=1.000 | 2274 |  |
| mem_03 | mem | f1=0.000 selF1=1.000 | 1985 |  |
| mem_04 | mem | f1=0.667 selF1=1.000 | 1946 |  |
| mem_05 | mem | f1=0.444 selF1=1.000 | 2074 |  |
| mem_06 | mem | f1=0.667 selF1=1.000 | 2109 |  |
| mem_07 | mem | f1=0.000 selF1=1.000 | 1774 |  |
| mem_08 | mem | f1=0.286 selF1=1.000 | 2980 |  |
