# FIN-MATE Eval Report · 260909_2249

- generated: 2026-09-09 22:50:38
- records: 34   judged: 2

## per-set

| set | n | score | pass | exact_mean | judge_rate | tokens | usd | ms |
|---|---|---|---|---|---|---|---|---|
| fact_single | 11 | 0.130 | 2/11 | 0.130 | n/a | 52370 | $0.0013 | 20314 |
| fact_multi | 4 | 0.750 | 3/4 | 0.500 | 1.000 | 24449 | $0.0007 | 13320 |
| calc_expr | 5 | 1.000 | 5/5 | 1.000 | n/a | 775 | $0.0000 | 2455 |
| news_extract | 3 | 1.000 | 3/3 | 1.000 | n/a | 455 | $0.0000 | 2021 |
| sent_3way | 6 | 1.000 | 6/6 | 1.000 | n/a | 713 | $0.0001 | 4738 |
| sent_score | 5 | 1.000 | 5/5 | 1.000 | n/a | 701 | $0.0001 | 3657 |
| **overall** | 34 | 0.689 | 24/34 | 0.670 | 1.000 | 79463 | $0.0023 | 46505 |

## per-record

| id | set | evaluator | score | pass | ms | note |
|---|---|---|---|---|---|---|
| qa_fs_01 | fact_single | f1 | 0.105 | FAIL | 4994 | f1=0.105 |
| qa_fs_02 | fact_single | f1 | 0.036 | FAIL | 3186 | f1=0.036 |
| qa_fs_03 | fact_single | f1 | 0.089 | FAIL | 1580 | f1=0.089 |
| qa_fs_04 | fact_single | f1 | 0.087 | FAIL | 1339 | f1=0.087 |
| qa_fs_05 | fact_single | f1 | 0.000 | FAIL | 827 | f1=0.000 |
| qa_fs_06 | fact_single | f1 | 0.083 | FAIL | 971 | f1=0.083 |
| qa_fs_07 | fact_single | f1 | 0.279 | PASS | 1274 | f1=0.279 |
| qa_fs_08 | fact_single | f1 | 0.188 | FAIL | 2201 | f1=0.188 |
| qa_fs_09 | fact_single | f1 | 0.154 | FAIL | 1164 | f1=0.154 |
| qa_fs_10 | fact_single | f1 | 0.412 | PASS | 1417 | f1=0.412 |
| qa_fs_11 | fact_single | f1 | 0.000 | FAIL | 1362 | f1=0.000 |
| qa_fm_01 | fact_multi | llm_judge | 1.000 | PASS | 4834 | verdict='PASS' ms=4503 |
| qa_fm_02 | fact_multi | llm_judge | 1.000 | PASS | 6576 | verdict='PASS' ms=1947 |
| qa_fm_03 | fact_multi | trap | 0.000 | FAIL | 1259 | pred='關於微軟（Microsoft，股票代號：MSFT）的股息殖利率及歷年派息紀錄，目前提供的資料中並未提及相關內容。因此，無' |
| qa_fm_04 | fact_multi | trap | 1.000 | PASS | 651 | hit=['無資料'] |
| tc_calc_01 | calc_expr | tool_call | 1.000 | PASS | 414 | computed 37.0 vs want 37.0 |
| tc_calc_02 | calc_expr | tool_call | 1.000 | PASS | 470 | computed 1.0 vs want 1.0 |
| tc_calc_03 | calc_expr | tool_call | 1.000 | PASS | 413 | computed 17.064000000000004 vs want 17.064 |
| tc_calc_04 | calc_expr | tool_call | 1.000 | PASS | 690 | computed 65.0 vs want 65.0 |
| tc_calc_05 | calc_expr | tool_call | 1.000 | PASS | 468 | computed 39.682539682539684 vs want 39.6825396825 |
| tc_news_01 | news_extract | tool_call | 1.000 | PASS | 540 | row 0: MSFT/positive |
| tc_news_02 | news_extract | tool_call | 1.000 | PASS | 548 | row 1: 005930/negative |
| tc_news_03 | news_extract | tool_call | 1.000 | PASS | 933 | row 2: TSM/neutral |
| sent_3w_01 | sent_3way | sentiment | 1.000 | PASS | 585 |  |
| sent_3w_02 | sent_3way | sentiment | 1.000 | PASS | 1047 |  |
| sent_3w_03 | sent_3way | sentiment | 1.000 | PASS | 859 |  |
| sent_3w_04 | sent_3way | sentiment | 1.000 | PASS | 665 |  |
| sent_3w_05 | sent_3way | sentiment | 1.000 | PASS | 817 |  |
| sent_3w_06 | sent_3way | sentiment | 1.000 | PASS | 766 |  |
| sent_sc_01 | sent_score | sentiment | 1.000 | PASS | 609 |  |
| sent_sc_02 | sent_score | sentiment | 1.000 | PASS | 475 |  |
| sent_sc_03 | sent_score | sentiment | 1.000 | PASS | 850 |  |
| sent_sc_04 | sent_score | sentiment | 1.000 | PASS | 1146 |  |
| sent_sc_05 | sent_score | sentiment | 1.000 | PASS | 577 |  |
