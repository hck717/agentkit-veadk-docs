# report · jbv_jev_full · 37 items

- Jev 全層

- QA recall@5: **0.808**  gate-recall@5: 0.308  answer-F1: **0.072**  trap: 0/2
- tool pass: **8/8**  (jev fallback: 0)
- sentiment pass: **6/6**
- memory answer-F1: **0.470**  selection-F1(jev only): 1.000

- Jev decisions: 150  median: 413 ms  (total run: 94556 ms)
- cost: **$0.0021**   tokens: 69907+2967

## per-item

| eid | fam | metric | ms | note |
|---|---|---|---|---|
| f1 | qa | r5=1.000 f1=0.063 | 3940 |  |
| f2 | qa | r5=1.000 f1=0.000 | 5796 |  |
| f3 | qa | r5=1.000 f1=0.000 | 3135 |  |
| f4 | qa | r5=1.000 f1=0.000 | 4482 |  |
| f5 | qa | r5=0.000 f1=0.000 | 3378 |  |
| f6 | qa | r5=1.000 f1=0.083 | 3667 |  |
| f7 | qa | r5=1.000 f1=0.211 | 3511 |  |
| f8 | qa | r5=1.000 f1=0.263 | 4252 |  |
| f9 | qa | r5=1.000 f1=0.118 | 3413 |  |
| f10 | qa | r5=1.000 f1=0.000 | 3551 |  |
| f11 | qa | r5=0.000 f1=0.065 | 5089 |  |
| t1 | qa | r5=n/a f1=n/a trap=F | 5546 |  |
| t2 | qa | r5=n/a f1=n/a trap=F | 4568 |  |
| m1 | qa | r5=0.500 f1=0.000 | 3174 |  |
| m2 | qa | r5=1.000 f1=0.136 | 6953 |  |
| tc_calc_01 | tool | PASS | 1322 |  |
| tc_calc_02 | tool | PASS | 1132 |  |
| tc_calc_03 | tool | PASS | 1306 |  |
| tc_calc_04 | tool | PASS | 1231 |  |
| tc_calc_05 | tool | PASS | 2025 |  |
| tc_news_01 | tool | PASS | 1287 |  |
| tc_news_02 | tool | PASS | 1306 |  |
| tc_news_03 | tool | PASS | 1232 |  |
| sent_3w_01 | sent | PASS pred=positive | 354 |  |
| sent_3w_02 | sent | PASS pred=negative | 383 |  |
| sent_3w_03 | sent | PASS pred=neutral | 322 |  |
| sent_3w_04 | sent | PASS pred=positive | 401 |  |
| sent_3w_05 | sent | PASS pred=negative | 446 |  |
| sent_3w_06 | sent | PASS pred=positive | 401 |  |
| mem_01 | mem | f1=0.667 selF1=1.000 | 2114 |  |
| mem_02 | mem | f1=0.857 selF1=1.000 | 2124 |  |
| mem_03 | mem | f1=0.000 selF1=1.000 | 2728 |  |
| mem_04 | mem | f1=0.667 selF1=1.000 | 1965 |  |
| mem_05 | mem | f1=0.500 selF1=1.000 | 2065 |  |
| mem_06 | mem | f1=0.667 selF1=1.000 | 2147 |  |
| mem_07 | mem | f1=0.000 selF1=1.000 | 1493 |  |
| mem_08 | mem | f1=0.400 selF1=1.000 | 2318 |  |
