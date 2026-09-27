# report · jbv_original_mini · 37 items

- 原裝：mini 決策（本 account 冇 → =flash 對照）

- QA recall@5: **0.808**  gate-recall@5: 0.808  answer-F1: **0.087**  trap: 2/2
- tool pass: **8/8**  (jev fallback: 0)
- sentiment pass: **6/6**
- memory answer-F1: **0.457**  selection-F1(jev only): n/a

- Jev decisions: 0  median: n/a ms  (total run: 47738 ms)
- cost: **$0.0018**   tokens: 54615+2954

## per-item

| eid | fam | metric | ms | note |
|---|---|---|---|---|
| f1 | qa | r5=1.000 f1=0.039 | 1533 |  |
| f2 | qa | r5=1.000 f1=0.000 | 3949 |  |
| f3 | qa | r5=1.000 f1=0.065 | 2084 |  |
| f4 | qa | r5=1.000 f1=0.000 | 867 |  |
| f5 | qa | r5=0.000 f1=0.000 | 633 |  |
| f6 | qa | r5=1.000 f1=0.000 | 753 |  |
| f7 | qa | r5=1.000 f1=0.211 | 2403 |  |
| f8 | qa | r5=1.000 f1=0.256 | 1585 |  |
| f9 | qa | r5=1.000 f1=0.146 | 1547 |  |
| f10 | qa | r5=1.000 f1=0.049 | 1446 |  |
| f11 | qa | r5=0.000 f1=0.000 | 782 |  |
| t1 | qa | r5=n/a f1=n/a trap=P | 798 |  |
| t2 | qa | r5=n/a f1=n/a trap=P | 646 |  |
| m1 | qa | r5=0.500 f1=0.075 | 4936 |  |
| m2 | qa | r5=1.000 f1=0.291 | 3459 |  |
| tc_calc_01 | tool | PASS | 511 |  |
| tc_calc_02 | tool | PASS | 699 |  |
| tc_calc_03 | tool | PASS | 564 |  |
| tc_calc_04 | tool | PASS | 648 |  |
| tc_calc_05 | tool | PASS | 714 |  |
| tc_news_01 | tool | PASS | 550 |  |
| tc_news_02 | tool | PASS | 1901 |  |
| tc_news_03 | tool | PASS | 774 |  |
| sent_3w_01 | sent | PASS pred=positive
The title states that Microsoft Cloud revenue has exceeded $50 billion and | 544 |  |
| sent_3w_02 | sent | PASS pred=negative
The title indicates that Microsoft's shares fell after Azure growth missed expectations. | 532 |  |
| sent_3w_03 | sent | PASS pred=neutral
“holds its guidance steady” 只是表明維持先前的預 | 514 |  |
| sent_3w_04 | sent | PASS pred=positive
解析：标题中提到“Microsoft wins big government cloud deal（微软 | 468 |  |
| sent_3w_05 | sent | PASS pred=negative
The title indicates that a bank is warning about an AI capital expenditure ( | 495 |  |
| sent_3w_06 | sent | PASS pred=positive
Wells Fargo upgrades Microsoft and raises its price target, which is a | 506 |  |
| mem_01 | mem | f1=1.000 selF1=n/a | 2979 |  |
| mem_02 | mem | f1=0.500 selF1=n/a | 1359 |  |
| mem_03 | mem | f1=0.000 selF1=n/a | 857 |  |
| mem_04 | mem | f1=0.667 selF1=n/a | 1730 |  |
| mem_05 | mem | f1=0.400 selF1=n/a | 1339 |  |
| mem_06 | mem | f1=0.800 selF1=n/a | 791 |  |
| mem_07 | mem | f1=0.000 selF1=n/a | 906 |  |
| mem_08 | mem | f1=0.286 selF1=n/a | 934 |  |
