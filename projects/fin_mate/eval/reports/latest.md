# FIN-MATE Eval Report · 260909_2255

- generated: 2026-09-09 22:56:42
- records: 34   judged: 2

## per-set

| set | n | score | pass | exact_mean | judge_rate | tokens | usd | ms |
|---|---|---|---|---|---|---|---|---|
| fact_single | 11 | 0.164 | 3/11 | 0.164 | n/a | 52297 | $0.0013 | 16568 |
| fact_multi | 4 | 1.000 | 4/4 | 1.000 | 1.000 | 13829 | $0.0005 | 12383 |
| calc_expr | 5 | 1.000 | 5/5 | 1.000 | n/a | 771 | $0.0000 | 2530 |
| news_extract | 3 | 1.000 | 3/3 | 1.000 | n/a | 437 | $0.0000 | 1893 |
| sent_3way | 6 | 1.000 | 6/6 | 1.000 | n/a | 694 | $0.0001 | 4087 |
| sent_score | 5 | 1.000 | 5/5 | 1.000 | n/a | 688 | $0.0001 | 3005 |
| **overall** | 34 | 0.729 | 26/34 | 0.713 | 1.000 | 68716 | $0.0020 | 40467 |

## per-record

| id | set | evaluator | score | pass | ms | note |
|---|---|---|---|---|---|---|
| qa_fs_01 | fact_single | f1 | 0.182 | FAIL | 3468 | f1=0.182 |
| qa_fs_02 | fact_single | f1 | 0.026 | FAIL | 3666 | f1=0.026 |
| qa_fs_03 | fact_single | f1 | 0.000 | FAIL | 874 | f1=0.000 |
| qa_fs_04 | fact_single | f1 | 0.000 | FAIL | 803 | f1=0.000 |
| qa_fs_05 | fact_single | f1 | 0.000 | FAIL | 774 | f1=0.000 |
| qa_fs_06 | fact_single | f1 | 0.080 | FAIL | 1058 | f1=0.080 |
| qa_fs_07 | fact_single | f1 | 0.279 | PASS | 1242 | f1=0.279 |
| qa_fs_08 | fact_single | f1 | 0.240 | FAIL | 1124 | f1=0.240 |
| qa_fs_09 | fact_single | f1 | 0.545 | PASS | 992 | f1=0.545 |
| qa_fs_10 | fact_single | f1 | 0.370 | PASS | 1257 | f1=0.370 |
| qa_fs_11 | fact_single | f1 | 0.080 | FAIL | 1310 | f1=0.080 |
| qa_fm_01 | fact_multi | llm_judge | 1.000 | PASS | 5244 | verdict='PASS' ms=2056 |
| qa_fm_02 | fact_multi | llm_judge | 1.000 | PASS | 6217 | verdict='PASS' ms=1930 |
| qa_fm_03 | fact_multi | trap | 1.000 | PASS | 548 | hit=['無資料'] |
| qa_fm_04 | fact_multi | trap | 1.000 | PASS | 374 | hit=['無資料'] |
| tc_calc_01 | calc_expr | tool_call | 1.000 | PASS | 432 | computed 37.0 vs want 37.0 |
| tc_calc_02 | calc_expr | tool_call | 1.000 | PASS | 446 | computed 1.0 vs want 1.0 |
| tc_calc_03 | calc_expr | tool_call | 1.000 | PASS | 691 | computed 17.064000000000004 vs want 17.064 |
| tc_calc_04 | calc_expr | tool_call | 1.000 | PASS | 526 | computed 65.0 vs want 65.0 |
| tc_calc_05 | calc_expr | tool_call | 1.000 | PASS | 435 | computed 39.682539682539684 vs want 39.6825396825 |
| tc_news_01 | news_extract | tool_call | 1.000 | PASS | 521 | row 0: MSFT/positive |
| tc_news_02 | news_extract | tool_call | 1.000 | PASS | 665 | row 1: 005930/negative |
| tc_news_03 | news_extract | tool_call | 1.000 | PASS | 707 | row 2: TSM/neutral |
| sent_3w_01 | sent_3way | sentiment | 1.000 | PASS | 562 |  |
| sent_3w_02 | sent_3way | sentiment | 1.000 | PASS | 859 |  |
| sent_3w_03 | sent_3way | sentiment | 1.000 | PASS | 670 |  |
| sent_3w_04 | sent_3way | sentiment | 1.000 | PASS | 701 |  |
| sent_3w_05 | sent_3way | sentiment | 1.000 | PASS | 626 |  |
| sent_3w_06 | sent_3way | sentiment | 1.000 | PASS | 670 |  |
| sent_sc_01 | sent_score | sentiment | 1.000 | PASS | 621 |  |
| sent_sc_02 | sent_score | sentiment | 1.000 | PASS | 509 |  |
| sent_sc_03 | sent_score | sentiment | 1.000 | PASS | 625 |  |
| sent_sc_04 | sent_score | sentiment | 1.000 | PASS | 698 |  |
| sent_sc_05 | sent_score | sentiment | 1.000 | PASS | 552 |  |
