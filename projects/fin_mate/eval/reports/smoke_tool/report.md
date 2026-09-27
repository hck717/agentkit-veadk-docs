# FIN-MATE Eval Report · smoke_tool

- generated: 2026-09-09 22:12:17
- records: 8   judged: 0

## per-set

| set | n | score | pass | exact_mean | judge_rate | tokens | usd | ms |
|---|---|---|---|---|---|---|---|---|
| calc_expr | 5 | 1.000 | 5/5 | 1.000 | n/a | 774 | $0.0000 | 3030 |
| news_extract | 3 | 1.000 | 3/3 | 1.000 | n/a | 443 | $0.0000 | 1435 |
| **overall** | 8 | 1.000 | 8/8 | 1.000 | n/a | 1217 | $0.0001 | 4465 |

## per-record

| id | set | evaluator | score | pass | ms | note |
|---|---|---|---|---|---|---|
| tc_calc_01 | calc_expr | tool_call | 1.000 | PASS | 431 | computed 37.0 vs want 37.0 |
| tc_calc_02 | calc_expr | tool_call | 1.000 | PASS | 451 | computed 1.0 vs want 1.0 |
| tc_calc_03 | calc_expr | tool_call | 1.000 | PASS | 762 | computed 17.064000000000004 vs want 17.064 |
| tc_calc_04 | calc_expr | tool_call | 1.000 | PASS | 605 | computed 65.0 vs want 65.0 |
| tc_calc_05 | calc_expr | tool_call | 1.000 | PASS | 781 | computed 39.682539682539684 vs want 39.6825396825 |
| tc_news_01 | news_extract | tool_call | 1.000 | PASS | 426 | row 0: MSFT/positive |
| tc_news_02 | news_extract | tool_call | 1.000 | PASS | 509 | row 1: 005930/negative |
| tc_news_03 | news_extract | tool_call | 1.000 | PASS | 501 | row 2: TSM/neutral |
