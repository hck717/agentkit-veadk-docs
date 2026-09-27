# FIN-MATE Eval Report · 260909_2254

- generated: 2026-09-09 22:55:14
- records: 34   judged: 2

## per-set

| set | n | score | pass | exact_mean | judge_rate | tokens | usd | ms |
|---|---|---|---|---|---|---|---|---|
| fact_single | 11 | 0.145 | 2/11 | 0.145 | n/a | 52265 | $0.0013 | 16503 |
| fact_multi | 4 | 1.000 | 4/4 | 1.000 | 1.000 | 13856 | $0.0005 | 11803 |
| calc_expr | 5 | 1.000 | 5/5 | 1.000 | n/a | 773 | $0.0000 | 2217 |
| news_extract | 3 | 1.000 | 3/3 | 1.000 | n/a | 443 | $0.0000 | 1478 |
| sent_3way | 6 | 1.000 | 6/6 | 1.000 | n/a | 744 | $0.0001 | 4708 |
| sent_score | 5 | 1.000 | 5/5 | 1.000 | n/a | 698 | $0.0001 | 3146 |
| **overall** | 34 | 0.723 | 25/34 | 0.706 | 1.000 | 68779 | $0.0020 | 39855 |

## per-record

| id | set | evaluator | score | pass | ms | note |
|---|---|---|---|---|---|---|
| qa_fs_01 | fact_single | f1 | 0.068 | FAIL | 3273 | f1=0.068 |
| qa_fs_02 | fact_single | f1 | 0.037 | FAIL | 1875 | f1=0.037 |
| qa_fs_03 | fact_single | f1 | 0.041 | FAIL | 1761 | f1=0.041 |
| qa_fs_04 | fact_single | f1 | 0.000 | FAIL | 754 | f1=0.000 |
| qa_fs_05 | fact_single | f1 | 0.000 | FAIL | 682 | f1=0.000 |
| qa_fs_06 | fact_single | f1 | 0.083 | FAIL | 745 | f1=0.083 |
| qa_fs_07 | fact_single | f1 | 0.279 | PASS | 1323 | f1=0.279 |
| qa_fs_08 | fact_single | f1 | 0.188 | FAIL | 1952 | f1=0.188 |
| qa_fs_09 | fact_single | f1 | 0.667 | PASS | 1028 | f1=0.667 |
| qa_fs_10 | fact_single | f1 | 0.231 | FAIL | 1326 | f1=0.231 |
| qa_fs_11 | fact_single | f1 | 0.000 | FAIL | 1784 | f1=0.000 |
| qa_fm_01 | fact_multi | llm_judge | 1.000 | PASS | 5057 | verdict='PASS' ms=2214 |
| qa_fm_02 | fact_multi | llm_judge | 1.000 | PASS | 5559 | verdict='PASS' ms=2000 |
| qa_fm_03 | fact_multi | trap | 1.000 | PASS | 597 | hit=['無資料'] |
| qa_fm_04 | fact_multi | trap | 1.000 | PASS | 590 | hit=['無資料'] |
| tc_calc_01 | calc_expr | tool_call | 1.000 | PASS | 414 | computed 37.0 vs want 37.0 |
| tc_calc_02 | calc_expr | tool_call | 1.000 | PASS | 422 | computed 1.0 vs want 1.0 |
| tc_calc_03 | calc_expr | tool_call | 1.000 | PASS | 434 | computed 17.064000000000004 vs want 17.064 |
| tc_calc_04 | calc_expr | tool_call | 1.000 | PASS | 481 | computed 65.0 vs want 65.0 |
| tc_calc_05 | calc_expr | tool_call | 1.000 | PASS | 466 | computed 39.682539682539684 vs want 39.6825396825 |
| tc_news_01 | news_extract | tool_call | 1.000 | PASS | 469 | row 0: MSFT/positive |
| tc_news_02 | news_extract | tool_call | 1.000 | PASS | 534 | row 1: 005930/negative |
| tc_news_03 | news_extract | tool_call | 1.000 | PASS | 476 | row 2: TSM/neutral |
| sent_3w_01 | sent_3way | sentiment | 1.000 | PASS | 612 |  |
| sent_3w_02 | sent_3way | sentiment | 1.000 | PASS | 965 |  |
| sent_3w_03 | sent_3way | sentiment | 1.000 | PASS | 922 |  |
| sent_3w_04 | sent_3way | sentiment | 1.000 | PASS | 709 |  |
| sent_3w_05 | sent_3way | sentiment | 1.000 | PASS | 820 |  |
| sent_3w_06 | sent_3way | sentiment | 1.000 | PASS | 680 |  |
| sent_sc_01 | sent_score | sentiment | 1.000 | PASS | 645 |  |
| sent_sc_02 | sent_score | sentiment | 1.000 | PASS | 458 |  |
| sent_sc_03 | sent_score | sentiment | 1.000 | PASS | 841 |  |
| sent_sc_04 | sent_score | sentiment | 1.000 | PASS | 592 |  |
| sent_sc_05 | sent_score | sentiment | 1.000 | PASS | 610 |  |
