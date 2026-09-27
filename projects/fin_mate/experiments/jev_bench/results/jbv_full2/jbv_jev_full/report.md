# report · jbv_jev_full · 37 items

- Jev 全層

- QA recall@5: **0.808**  gate-recall@5: 0.308  answer-F1: **0.082**  trap: 1/2
- tool pass: **8/8**  (jev fallback: 0)
- sentiment pass: **6/6**
- memory answer-F1: **0.493**  selection-F1(jev only): 1.000

- Jev decisions: 150  median: 437 ms  (total run: 99410 ms)
- cost: **$0.0020**   tokens: 69183+2723

## per-item

| eid | fam | metric | ms | note |
|---|---|---|---|---|
| f1 | qa | r5=1.000 f1=0.071 | 4484 |  |
| f2 | qa | r5=1.000 f1=0.000 | 4672 |  |
| f3 | qa | r5=1.000 f1=0.000 | 3192 |  |
| f4 | qa | r5=1.000 f1=0.000 | 5888 |  |
| f5 | qa | r5=0.000 f1=0.235 | 3799 |  |
| f6 | qa | r5=1.000 f1=0.000 | 3702 |  |
| f7 | qa | r5=1.000 f1=0.214 | 4202 |  |
| f8 | qa | r5=1.000 f1=0.263 | 4133 |  |
| f9 | qa | r5=1.000 f1=0.108 | 3910 |  |
| f10 | qa | r5=1.000 f1=0.000 | 3505 |  |
| f11 | qa | r5=0.000 f1=0.000 | 6118 |  |
| t1 | qa | r5=n/a f1=n/a trap=F | 6402 |  |
| t2 | qa | r5=n/a f1=n/a trap=P | 2818 |  |
| m1 | qa | r5=0.500 f1=0.000 | 3686 |  |
| m2 | qa | r5=1.000 f1=0.169 | 7306 |  |
| tc_calc_01 | tool | PASS | 1278 |  |
| tc_calc_02 | tool | PASS | 1610 |  |
| tc_calc_03 | tool | PASS | 1306 |  |
| tc_calc_04 | tool | PASS | 1670 |  |
| tc_calc_05 | tool | PASS | 1155 |  |
| tc_news_01 | tool | PASS | 1338 |  |
| tc_news_02 | tool | PASS | 1308 |  |
| tc_news_03 | tool | PASS | 1704 |  |
| sent_3w_01 | sent | PASS pred=positive | 354 |  |
| sent_3w_02 | sent | PASS pred=negative | 416 |  |
| sent_3w_03 | sent | PASS pred=neutral | 347 |  |
| sent_3w_04 | sent | PASS pred=positive | 456 |  |
| sent_3w_05 | sent | PASS pred=negative | 451 |  |
| sent_3w_06 | sent | PASS pred=positive | 614 |  |
| mem_01 | mem | f1=0.750 selF1=1.000 | 2676 |  |
| mem_02 | mem | f1=0.857 selF1=1.000 | 2128 |  |
| mem_03 | mem | f1=0.000 selF1=1.000 | 2383 |  |
| mem_04 | mem | f1=0.667 selF1=1.000 | 2234 |  |
| mem_05 | mem | f1=0.500 selF1=1.000 | 2096 |  |
| mem_06 | mem | f1=0.667 selF1=1.000 | 1989 |  |
| mem_07 | mem | f1=0.000 selF1=1.000 | 1918 |  |
| mem_08 | mem | f1=0.500 selF1=1.000 | 2164 |  |
