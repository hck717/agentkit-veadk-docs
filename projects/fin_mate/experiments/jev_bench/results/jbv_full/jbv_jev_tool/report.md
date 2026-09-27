# report · jbv_jev_tool · 37 items

- Jev 揀工具 + Noul

- QA recall@5: **0.808**  gate-recall@5: 0.808  answer-F1: **0.090**  trap: 2/2
- tool pass: **8/8**  (jev fallback: 0)
- sentiment pass: **6/6**
- memory answer-F1: **0.329**  selection-F1(jev only): n/a

- Jev decisions: 30  median: 502 ms  (total run: 61269 ms)
- cost: **$0.0018**   tokens: 57418+2601

## per-item

| eid | fam | metric | ms | note |
|---|---|---|---|---|
| f1 | qa | r5=1.000 f1=0.000 | 1041 |  |
| f2 | qa | r5=1.000 f1=0.000 | 3157 |  |
| f3 | qa | r5=1.000 f1=0.033 | 1729 |  |
| f4 | qa | r5=1.000 f1=0.000 | 881 |  |
| f5 | qa | r5=0.000 f1=0.000 | 652 |  |
| f6 | qa | r5=1.000 f1=0.061 | 1084 |  |
| f7 | qa | r5=1.000 f1=0.211 | 9733 |  |
| f8 | qa | r5=1.000 f1=0.263 | 1574 |  |
| f9 | qa | r5=1.000 f1=0.143 | 1447 |  |
| f10 | qa | r5=1.000 f1=0.100 | 1319 |  |
| f11 | qa | r5=0.000 f1=0.000 | 904 |  |
| t1 | qa | r5=n/a f1=n/a trap=P | 739 |  |
| t2 | qa | r5=n/a f1=n/a trap=P | 830 |  |
| m1 | qa | r5=0.500 f1=0.069 | 10319 |  |
| m2 | qa | r5=1.000 f1=0.288 | 3038 |  |
| tc_calc_01 | tool | PASS | 1467 |  |
| tc_calc_02 | tool | PASS | 1240 |  |
| tc_calc_03 | tool | PASS | 1731 |  |
| tc_calc_04 | tool | PASS | 1353 |  |
| tc_calc_05 | tool | PASS | 1943 |  |
| tc_news_01 | tool | PASS | 1805 |  |
| tc_news_02 | tool | PASS | 1636 |  |
| tc_news_03 | tool | PASS | 1683 |  |
| sent_3w_01 | sent | PASS pred=positive | 383 |  |
| sent_3w_02 | sent | PASS pred=negative | 383 |  |
| sent_3w_03 | sent | PASS pred=neutral | 381 |  |
| sent_3w_04 | sent | PASS pred=positive | 404 |  |
| sent_3w_05 | sent | PASS pred=negative | 458 |  |
| sent_3w_06 | sent | PASS pred=positive | 405 |  |
| mem_01 | mem | f1=0.462 selF1=n/a | 757 |  |
| mem_02 | mem | f1=0.375 selF1=n/a | 924 |  |
| mem_03 | mem | f1=0.000 selF1=n/a | 493 |  |
| mem_04 | mem | f1=0.667 selF1=n/a | 573 |  |
| mem_05 | mem | f1=0.400 selF1=n/a | 1227 |  |
| mem_06 | mem | f1=0.444 selF1=n/a | 892 |  |
| mem_07 | mem | f1=0.000 selF1=n/a | 906 |  |
| mem_08 | mem | f1=0.286 selF1=n/a | 1774 |  |
