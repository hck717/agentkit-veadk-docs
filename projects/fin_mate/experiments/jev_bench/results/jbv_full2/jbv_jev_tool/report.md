# report · jbv_jev_tool · 37 items

- Jev 揀工具 + Noul

- QA recall@5: **0.808**  gate-recall@5: 0.808  answer-F1: **0.076**  trap: 2/2
- tool pass: **8/8**  (jev fallback: 0)
- sentiment pass: **6/6**
- memory answer-F1: **0.442**  selection-F1(jev only): n/a

- Jev decisions: 30  median: 435 ms  (total run: 43424 ms)
- cost: **$0.0017**   tokens: 57418+2375

## per-item

| eid | fam | metric | ms | note |
|---|---|---|---|---|
| f1 | qa | r5=1.000 f1=0.000 | 1080 |  |
| f2 | qa | r5=1.000 f1=0.000 | 4586 |  |
| f3 | qa | r5=1.000 f1=0.033 | 1598 |  |
| f4 | qa | r5=1.000 f1=0.000 | 598 |  |
| f5 | qa | r5=0.000 f1=0.000 | 524 |  |
| f6 | qa | r5=1.000 f1=0.061 | 1124 |  |
| f7 | qa | r5=1.000 f1=0.211 | 1410 |  |
| f8 | qa | r5=1.000 f1=0.263 | 1206 |  |
| f9 | qa | r5=1.000 f1=0.146 | 1170 |  |
| f10 | qa | r5=1.000 f1=0.049 | 1550 |  |
| f11 | qa | r5=0.000 f1=0.000 | 636 |  |
| t1 | qa | r5=n/a f1=n/a trap=P | 1808 |  |
| t2 | qa | r5=n/a f1=n/a trap=P | 614 |  |
| m1 | qa | r5=0.500 f1=0.000 | 617 |  |
| m2 | qa | r5=1.000 f1=0.231 | 4303 |  |
| tc_calc_01 | tool | PASS | 1453 |  |
| tc_calc_02 | tool | PASS | 1223 |  |
| tc_calc_03 | tool | PASS | 1452 |  |
| tc_calc_04 | tool | PASS | 1317 |  |
| tc_calc_05 | tool | PASS | 1236 |  |
| tc_news_01 | tool | PASS | 1224 |  |
| tc_news_02 | tool | PASS | 1372 |  |
| tc_news_03 | tool | PASS | 1356 |  |
| sent_3w_01 | sent | PASS pred=positive | 390 |  |
| sent_3w_02 | sent | PASS pred=negative | 489 |  |
| sent_3w_03 | sent | PASS pred=neutral | 416 |  |
| sent_3w_04 | sent | PASS pred=positive | 383 |  |
| sent_3w_05 | sent | PASS pred=negative | 427 |  |
| sent_3w_06 | sent | PASS pred=positive | 534 |  |
| mem_01 | mem | f1=0.667 selF1=n/a | 596 |  |
| mem_02 | mem | f1=0.429 selF1=n/a | 963 |  |
| mem_03 | mem | f1=0.000 selF1=n/a | 898 |  |
| mem_04 | mem | f1=0.667 selF1=n/a | 782 |  |
| mem_05 | mem | f1=0.571 selF1=n/a | 1027 |  |
| mem_06 | mem | f1=0.800 selF1=n/a | 766 |  |
| mem_07 | mem | f1=0.000 selF1=n/a | 1069 |  |
| mem_08 | mem | f1=0.400 selF1=n/a | 1228 |  |
