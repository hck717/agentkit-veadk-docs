# FIN-MATE Eval Report · 260909_2252

- generated: 2026-09-09 22:53:01
- records: 34   judged: 2

## per-set

| set | n | score | pass | exact_mean | judge_rate | tokens | usd | ms |
|---|---|---|---|---|---|---|---|---|
| fact_single | 11 | 0.125 | 1/11 | 0.125 | n/a | 52407 | $0.0014 | 18614 |
| fact_multi | 4 | 1.000 | 4/4 | 1.000 | 1.000 | 14053 | $0.0005 | 12527 |
| calc_expr | 5 | 1.000 | 5/5 | 1.000 | n/a | 774 | $0.0000 | 2094 |
| news_extract | 3 | 1.000 | 3/3 | 1.000 | n/a | 443 | $0.0000 | 1545 |
| sent_3way | 6 | 1.000 | 6/6 | 1.000 | n/a | 727 | $0.0001 | 3999 |
| sent_score | 5 | 1.000 | 5/5 | 1.000 | n/a | 689 | $0.0001 | 3012 |
| **overall** | 34 | 0.717 | 24/34 | 0.699 | 1.000 | 69093 | $0.0021 | 41790 |

## per-record

| id | set | evaluator | score | pass | ms | note |
|---|---|---|---|---|---|---|
| qa_fs_01 | fact_single | f1 | 0.122 | FAIL | 3327 | f1=0.122 |
| qa_fs_02 | fact_single | f1 | 0.044 | FAIL | 2171 | f1=0.044 |
| qa_fs_03 | fact_single | f1 | 0.089 | FAIL | 1440 | f1=0.089 |
| qa_fs_04 | fact_single | f1 | 0.000 | FAIL | 778 | f1=0.000 |
| qa_fs_05 | fact_single | f1 | 0.000 | FAIL | 602 | f1=0.000 |
| qa_fs_06 | fact_single | f1 | 0.235 | FAIL | 2132 | f1=0.235 |
| qa_fs_07 | fact_single | f1 | 0.279 | PASS | 1601 | f1=0.279 |
| qa_fs_08 | fact_single | f1 | 0.136 | FAIL | 2499 | f1=0.136 |
| qa_fs_09 | fact_single | f1 | 0.154 | FAIL | 1294 | f1=0.154 |
| qa_fs_10 | fact_single | f1 | 0.231 | FAIL | 1411 | f1=0.231 |
| qa_fs_11 | fact_single | f1 | 0.080 | FAIL | 1359 | f1=0.080 |
| qa_fm_01 | fact_multi | llm_judge | 1.000 | PASS | 4814 | verdict='PASS' ms=2011 |
| qa_fm_02 | fact_multi | llm_judge | 1.000 | PASS | 4936 | verdict='PASS' ms=1965 |
| qa_fm_03 | fact_multi | trap | 1.000 | PASS | 1636 | hit=['無資料'] |
| qa_fm_04 | fact_multi | trap | 1.000 | PASS | 1140 | hit=['無資料'] |
| tc_calc_01 | calc_expr | tool_call | 1.000 | PASS | 367 | computed 37.0 vs want 37.0 |
| tc_calc_02 | calc_expr | tool_call | 1.000 | PASS | 463 | computed 1.0 vs want 1.0 |
| tc_calc_03 | calc_expr | tool_call | 1.000 | PASS | 438 | computed 17.064000000000004 vs want 17.064 |
| tc_calc_04 | calc_expr | tool_call | 1.000 | PASS | 426 | computed 65.0 vs want 65.0 |
| tc_calc_05 | calc_expr | tool_call | 1.000 | PASS | 400 | computed 39.682539682539684 vs want 39.6825396825 |
| tc_news_01 | news_extract | tool_call | 1.000 | PASS | 480 | row 0: MSFT/positive |
| tc_news_02 | news_extract | tool_call | 1.000 | PASS | 463 | row 1: 005930/negative |
| tc_news_03 | news_extract | tool_call | 1.000 | PASS | 602 | row 2: TSM/neutral |
| sent_3w_01 | sent_3way | sentiment | 1.000 | PASS | 506 |  |
| sent_3w_02 | sent_3way | sentiment | 1.000 | PASS | 569 |  |
| sent_3w_03 | sent_3way | sentiment | 1.000 | PASS | 582 |  |
| sent_3w_04 | sent_3way | sentiment | 1.000 | PASS | 784 |  |
| sent_3w_05 | sent_3way | sentiment | 1.000 | PASS | 909 |  |
| sent_3w_06 | sent_3way | sentiment | 1.000 | PASS | 649 |  |
| sent_sc_01 | sent_score | sentiment | 1.000 | PASS | 555 |  |
| sent_sc_02 | sent_score | sentiment | 1.000 | PASS | 533 |  |
| sent_sc_03 | sent_score | sentiment | 1.000 | PASS | 570 |  |
| sent_sc_04 | sent_score | sentiment | 1.000 | PASS | 698 |  |
| sent_sc_05 | sent_score | sentiment | 1.000 | PASS | 656 |  |
