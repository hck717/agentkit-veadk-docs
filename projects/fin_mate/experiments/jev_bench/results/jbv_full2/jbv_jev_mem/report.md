# report · jbv_jev_mem · 37 items

- Jev 篩記憶

- QA recall@5: **0.808**  gate-recall@5: 0.808  answer-F1: **0.080**  trap: 2/2
- tool pass: **8/8**  (jev fallback: 0)
- sentiment pass: **6/6**
- memory answer-F1: **0.446**  selection-F1(jev only): 1.000

- Jev decisions: 26  median: 443 ms  (total run: 55057 ms)
- cost: **$0.0019**   tokens: 60179+3092

## per-item

| eid | fam | metric | ms | note |
|---|---|---|---|---|
| f1 | qa | r5=1.000 f1=0.000 | 1082 |  |
| f2 | qa | r5=1.000 f1=0.018 | 4614 |  |
| f3 | qa | r5=1.000 f1=0.033 | 1692 |  |
| f4 | qa | r5=1.000 f1=0.000 | 535 |  |
| f5 | qa | r5=0.000 f1=0.000 | 882 |  |
| f6 | qa | r5=1.000 f1=0.061 | 1054 |  |
| f7 | qa | r5=1.000 f1=0.194 | 1826 |  |
| f8 | qa | r5=1.000 f1=0.256 | 1358 |  |
| f9 | qa | r5=1.000 f1=0.143 | 1307 |  |
| f10 | qa | r5=1.000 f1=0.049 | 1359 |  |
| f11 | qa | r5=0.000 f1=0.000 | 686 |  |
| t1 | qa | r5=n/a f1=n/a trap=P | 803 |  |
| t2 | qa | r5=n/a f1=n/a trap=P | 703 |  |
| m1 | qa | r5=0.500 f1=0.071 | 4444 |  |
| m2 | qa | r5=1.000 f1=0.222 | 4299 |  |
| tc_calc_01 | tool | PASS | 414 |  |
| tc_calc_02 | tool | PASS | 631 |  |
| tc_calc_03 | tool | PASS | 568 |  |
| tc_calc_04 | tool | PASS | 516 |  |
| tc_calc_05 | tool | PASS | 508 |  |
| tc_news_01 | tool | PASS | 526 |  |
| tc_news_02 | tool | PASS | 508 |  |
| tc_news_03 | tool | PASS | 755 |  |
| sent_3w_01 | sent | PASS pred=positive
The title states that Microsoft Cloud revenue has exceeded $50 billion and | 581 |  |
| sent_3w_02 | sent | PASS pred=negative
The title indicates that Microsoft shares fell 4% because Azure growth missed | 580 |  |
| sent_3w_03 | sent | PASS pred=neutral
The title "Taiwan Semiconductor holds its guidance steady this quarter" | 754 |  |
| sent_3w_04 | sent | PASS pred=positive
解析：标题中提到“Microsoft wins big government cloud deal（微软 | 501 |  |
| sent_3w_05 | sent | PASS pred=negative
The title indicates that a bank is warning about an AI capital expenditure ( | 637 |  |
| sent_3w_06 | sent | PASS pred=positive
Wells Fargo upgrades Microsoft and raises its price target, which is a | 1572 |  |
| mem_01 | mem | f1=0.667 selF1=1.000 | 2630 |  |
| mem_02 | mem | f1=1.000 selF1=1.000 | 2473 |  |
| mem_03 | mem | f1=0.000 selF1=1.000 | 2336 |  |
| mem_04 | mem | f1=0.667 selF1=1.000 | 1979 |  |
| mem_05 | mem | f1=0.571 selF1=1.000 | 2831 |  |
| mem_06 | mem | f1=0.667 selF1=1.000 | 2280 |  |
| mem_07 | mem | f1=0.000 selF1=1.000 | 2329 |  |
| mem_08 | mem | f1=0.000 selF1=1.000 | 2505 |  |
