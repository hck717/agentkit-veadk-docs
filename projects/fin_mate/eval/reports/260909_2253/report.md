# FIN-MATE Eval Report · 260909_2253

- generated: 2026-09-09 22:53:52
- records: 34   judged: 2

## per-set

| set | n | score | pass | exact_mean | judge_rate | tokens | usd | ms |
|---|---|---|---|---|---|---|---|---|
| fact_single | 11 | 0.130 | 2/11 | 0.130 | n/a | 52588 | $0.0014 | 18741 |
| fact_multi | 4 | 0.500 | 2/4 | 0.000 | 1.000 | 14537 | $0.0006 | 16170 |
| calc_expr | 5 | 1.000 | 5/5 | 1.000 | n/a | 774 | $0.0000 | 2100 |
| news_extract | 3 | 1.000 | 3/3 | 1.000 | n/a | 443 | $0.0000 | 1678 |
| sent_3way | 6 | 1.000 | 6/6 | 1.000 | n/a | 693 | $0.0001 | 3826 |
| sent_score | 5 | 1.000 | 5/5 | 1.000 | n/a | 697 | $0.0001 | 2981 |
| **overall** | 34 | 0.660 | 23/34 | 0.638 | 1.000 | 69732 | $0.0022 | 45497 |

## per-record

| id | set | evaluator | score | pass | ms | note |
|---|---|---|---|---|---|---|
| qa_fs_01 | fact_single | f1 | 0.071 | FAIL | 3318 | f1=0.071 |
| qa_fs_02 | fact_single | f1 | 0.020 | FAIL | 4185 | f1=0.020 |
| qa_fs_03 | fact_single | f1 | 0.000 | FAIL | 721 | f1=0.000 |
| qa_fs_04 | fact_single | f1 | 0.000 | FAIL | 551 | f1=0.000 |
| qa_fs_05 | fact_single | f1 | 0.000 | FAIL | 631 | f1=0.000 |
| qa_fs_06 | fact_single | f1 | 0.211 | FAIL | 1851 | f1=0.211 |
| qa_fs_07 | fact_single | f1 | 0.279 | PASS | 1443 | f1=0.279 |
| qa_fs_08 | fact_single | f1 | 0.167 | FAIL | 2102 | f1=0.167 |
| qa_fs_09 | fact_single | f1 | 0.391 | PASS | 1255 | f1=0.391 |
| qa_fs_10 | fact_single | f1 | 0.214 | FAIL | 1182 | f1=0.214 |
| qa_fs_11 | fact_single | f1 | 0.077 | FAIL | 1502 | f1=0.077 |
| qa_fm_01 | fact_multi | llm_judge | 1.000 | PASS | 5157 | verdict='PASS' ms=2044 |
| qa_fm_02 | fact_multi | llm_judge | 1.000 | PASS | 4392 | verdict='PASS' ms=1929 |
| qa_fm_03 | fact_multi | trap | 0.000 | FAIL | 4180 | pred='要查詢Microsoft（微軟）的股息殖利率和歷年派息紀錄，通常需要訪問其官方財報、投資者關係網站，或權威的金融數據平台' |
| qa_fm_04 | fact_multi | trap | 0.000 | FAIL | 2443 | pred='關於Microsoft在日本搜尋市場的份額及與Yahoo Japan的合作詳情，以下是已知信息：\n\n### 市場份額\n-' |
| tc_calc_01 | calc_expr | tool_call | 1.000 | PASS | 426 | computed 37.0 vs want 37.0 |
| tc_calc_02 | calc_expr | tool_call | 1.000 | PASS | 417 | computed 1.0 vs want 1.0 |
| tc_calc_03 | calc_expr | tool_call | 1.000 | PASS | 431 | computed 17.064000000000004 vs want 17.064 |
| tc_calc_04 | calc_expr | tool_call | 1.000 | PASS | 452 | computed 65.0 vs want 65.0 |
| tc_calc_05 | calc_expr | tool_call | 1.000 | PASS | 374 | computed 39.682539682539684 vs want 39.6825396825 |
| tc_news_01 | news_extract | tool_call | 1.000 | PASS | 436 | row 0: MSFT/positive |
| tc_news_02 | news_extract | tool_call | 1.000 | PASS | 708 | row 1: 005930/negative |
| tc_news_03 | news_extract | tool_call | 1.000 | PASS | 534 | row 2: TSM/neutral |
| sent_3w_01 | sent_3way | sentiment | 1.000 | PASS | 503 |  |
| sent_3w_02 | sent_3way | sentiment | 1.000 | PASS | 533 |  |
| sent_3w_03 | sent_3way | sentiment | 1.000 | PASS | 572 |  |
| sent_3w_04 | sent_3way | sentiment | 1.000 | PASS | 601 |  |
| sent_3w_05 | sent_3way | sentiment | 1.000 | PASS | 738 |  |
| sent_3w_06 | sent_3way | sentiment | 1.000 | PASS | 881 |  |
| sent_sc_01 | sent_score | sentiment | 1.000 | PASS | 470 |  |
| sent_sc_02 | sent_score | sentiment | 1.000 | PASS | 504 |  |
| sent_sc_03 | sent_score | sentiment | 1.000 | PASS | 712 |  |
| sent_sc_04 | sent_score | sentiment | 1.000 | PASS | 731 |  |
| sent_sc_05 | sent_score | sentiment | 1.000 | PASS | 565 |  |
