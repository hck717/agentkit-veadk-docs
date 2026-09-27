# report · jbv_jev_rag · 37 items

- Jev Score gate 檢索

- QA recall@5: **0.875**  gate-recall@5: 0.333  answer-F1: **0.090**  trap: 1/2
- tool pass: **8/8**  (jev fallback: 0)
- sentiment pass: **6/6**
- memory answer-F1: **0.394**  selection-F1(jev only): n/a

- Jev decisions: 87  median: 564 ms  (total run: 259784 ms)
- cost: **$0.0018**   tokens: 54036+2953

## per-item

| eid | fam | metric | ms | note |
|---|---|---|---|---|
| f1 | qa | r5=1.000 f1=0.090 | 73535 |  |
| f2 | qa | r5=1.000 f1=0.000 | 8414 |  |
| f3 | qa | r5=1.000 f1=0.000 | 4718 |  |
| f4 | qa | r5=1.000 f1=0.000 | 6334 |  |
| f5 | qa | r5=n/a f1=n/a | 80997 | Connection error., request_id: 202609211 |
| f6 | qa | r5=1.000 f1=0.083 | 28247 |  |
| f7 | qa | r5=1.000 f1=0.174 | 6491 |  |
| f8 | qa | r5=1.000 f1=0.256 | 4095 |  |
| f9 | qa | r5=1.000 f1=0.118 | 4130 |  |
| f10 | qa | r5=1.000 f1=0.222 | 4214 |  |
| f11 | qa | r5=0.000 f1=0.000 | 4571 |  |
| t1 | qa | r5=n/a f1=n/a trap=F | 6769 |  |
| t2 | qa | r5=n/a f1=n/a trap=P | 2870 |  |
| m1 | qa | r5=0.500 f1=0.000 | 3351 |  |
| m2 | qa | r5=1.000 f1=0.135 | 7341 |  |
| tc_calc_01 | tool | PASS | 454 |  |
| tc_calc_02 | tool | PASS | 452 |  |
| tc_calc_03 | tool | PASS | 495 |  |
| tc_calc_04 | tool | PASS | 450 |  |
| tc_calc_05 | tool | PASS | 497 |  |
| tc_news_01 | tool | PASS | 482 |  |
| tc_news_02 | tool | PASS | 594 |  |
| tc_news_03 | tool | PASS | 609 |  |
| sent_3w_01 | sent | PASS pred=positive
Microsoft Cloud revenue exceeding $50 billion with a 26% | 547 |  |
| sent_3w_02 | sent | PASS pred=negative
The title indicates that Microsoft shares fell after Azure growth missed expectations. A | 538 |  |
| sent_3w_03 | sent | PASS pred=neutral
The title "Taiwan Semiconductor holds its guidance steady this quarter" | 453 |  |
| sent_3w_04 | sent | PASS pred=positive
解析：标题中提到“Microsoft wins big government cloud deal（微软 | 494 |  |
| sent_3w_05 | sent | PASS pred=negative
The title indicates that a bank is warning about an AI capex bubble | 454 |  |
| sent_3w_06 | sent | PASS pred=positive
Wells Fargo 上調了對微軟的評級並 | 602 |  |
| mem_01 | mem | f1=0.667 selF1=n/a | 644 |  |
| mem_02 | mem | f1=0.353 selF1=n/a | 1006 |  |
| mem_03 | mem | f1=0.000 selF1=n/a | 897 |  |
| mem_04 | mem | f1=0.667 selF1=n/a | 528 |  |
| mem_05 | mem | f1=0.400 selF1=n/a | 1040 |  |
| mem_06 | mem | f1=0.667 selF1=n/a | 816 |  |
| mem_07 | mem | f1=0.000 selF1=n/a | 746 |  |
| mem_08 | mem | f1=0.400 selF1=n/a | 910 |  |
