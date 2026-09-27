# FIN-MATE Eval Report · run_full_260909_2212

- generated: 2026-09-09 22:14:04
- records: 34   judged: 2

## per-set

| set | n | score | pass | exact_mean | judge_rate | tokens | usd | ms |
|---|---|---|---|---|---|---|---|---|
| fact_single | 11 | 0.145 | 2/11 | 0.145 | n/a | 52189 | $0.0013 | 39781 |
| fact_multi | 4 | 1.000 | 4/4 | 1.000 | 1.000 | 24398 | $0.0007 | 13778 |
| calc_expr | 5 | 1.000 | 5/5 | 1.000 | n/a | 773 | $0.0000 | 3511 |
| news_extract | 3 | 1.000 | 3/3 | 1.000 | n/a | 437 | $0.0000 | 2276 |
| sent_3way | 6 | 1.000 | 6/6 | 1.000 | n/a | 777 | $0.0001 | 5627 |
| sent_score | 5 | 1.000 | 5/5 | 1.000 | n/a | 694 | $0.0001 | 3646 |
| **overall** | 34 | 0.723 | 25/34 | 0.706 | 1.000 | 79268 | $0.0022 | 68619 |

## per-record

| id | set | evaluator | score | pass | ms | note |
|---|---|---|---|---|---|---|
| qa_fs_01 | fact_single | f1 | 0.100 | FAIL | 26078 | f1=0.100 |
| qa_fs_02 | fact_single | f1 | 0.038 | FAIL | 2653 | f1=0.038 |
| qa_fs_03 | fact_single | f1 | 0.000 | FAIL | 982 | f1=0.000 |
| qa_fs_04 | fact_single | f1 | 0.000 | FAIL | 931 | f1=0.000 |
| qa_fs_05 | fact_single | f1 | 0.000 | FAIL | 849 | f1=0.000 |
| qa_fs_06 | fact_single | f1 | 0.083 | FAIL | 1060 | f1=0.083 |
| qa_fs_07 | fact_single | f1 | 0.286 | PASS | 1358 | f1=0.286 |
| qa_fs_08 | fact_single | f1 | 0.200 | FAIL | 1977 | f1=0.200 |
| qa_fs_09 | fact_single | f1 | 0.565 | PASS | 1083 | f1=0.565 |
| qa_fs_10 | fact_single | f1 | 0.231 | FAIL | 1290 | f1=0.231 |
| qa_fs_11 | fact_single | f1 | 0.093 | FAIL | 1520 | f1=0.093 |
| qa_fm_01 | fact_multi | llm_judge | 1.000 | PASS | 5871 | verdict='PASS' ms=4694 |
| qa_fm_02 | fact_multi | llm_judge | 1.000 | PASS | 5599 | verdict='PASS' ms=2014 |
| qa_fm_03 | fact_multi | trap | 1.000 | PASS | 1246 | hit=['無資料'] |
| qa_fm_04 | fact_multi | trap | 1.000 | PASS | 1063 | hit=['無資料'] |
| tc_calc_01 | calc_expr | tool_call | 1.000 | PASS | 801 | computed 37.0 vs want 37.0 |
| tc_calc_02 | calc_expr | tool_call | 1.000 | PASS | 685 | computed 1.0 vs want 1.0 |
| tc_calc_03 | calc_expr | tool_call | 1.000 | PASS | 732 | computed 17.064000000000004 vs want 17.064 |
| tc_calc_04 | calc_expr | tool_call | 1.000 | PASS | 668 | computed 65.0 vs want 65.0 |
| tc_calc_05 | calc_expr | tool_call | 1.000 | PASS | 625 | computed 39.682539682539684 vs want 39.6825396825 |
| tc_news_01 | news_extract | tool_call | 1.000 | PASS | 738 | row 0: MSFT/positive |
| tc_news_02 | news_extract | tool_call | 1.000 | PASS | 706 | row 1: 005930/negative |
| tc_news_03 | news_extract | tool_call | 1.000 | PASS | 833 | row 2: TSM/neutral |
| sent_3w_01 | sent_3way | sentiment | 1.000 | PASS | 835 |  |
| sent_3w_02 | sent_3way | sentiment | 1.000 | PASS | 1220 |  |
| sent_3w_03 | sent_3way | sentiment | 1.000 | PASS | 733 |  |
| sent_3w_04 | sent_3way | sentiment | 1.000 | PASS | 1034 |  |
| sent_3w_05 | sent_3way | sentiment | 1.000 | PASS | 1106 |  |
| sent_3w_06 | sent_3way | sentiment | 1.000 | PASS | 700 |  |
| sent_sc_01 | sent_score | sentiment | 1.000 | PASS | 582 |  |
| sent_sc_02 | sent_score | sentiment | 1.000 | PASS | 502 |  |
| sent_sc_03 | sent_score | sentiment | 1.000 | PASS | 739 |  |
| sent_sc_04 | sent_score | sentiment | 1.000 | PASS | 682 |  |
| sent_sc_05 | sent_score | sentiment | 1.000 | PASS | 1141 |  |
