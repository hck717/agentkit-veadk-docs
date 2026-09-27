# JEV bench SUMMARY：System One 決策層 vs 原裝 fin-mate pipeline

- tag: jbv_full2   runs: 2026-09-21 13:05:29

| variant | QA r5 | QA f1 | gate-r5 | trap | tool | sent | memF1 | memSelF1 | jev# | jev med ms | usd |
|---|---|---|---|---|---|---|---|---|---|---|---|
| original | 0.808 | 0.087 | 0.808 | 2/2 | 8/8 | 6/6 | 0.409 | n/a | 0 | n/a | $0.0017 |
| original_mini | 0.808 | 0.085 | 0.808 | 2/2 | 8/8 | 6/6 | 0.420 | n/a | 0 | n/a | $0.0017 |
| jev_tool | 0.808 | 0.076 | 0.808 | 2/2 | 8/8 | 6/6 | 0.442 | n/a | 30 | 435 | $0.0017 |
| jev_rag | 0.808 | 0.102 | 0.308 | 1/2 | 8/8 | 6/6 | 0.389 | n/a | 94 | 480 | $0.0020 |
| jev_mem | 0.808 | 0.080 | 0.808 | 2/2 | 8/8 | 6/6 | 0.446 | 1.000 | 26 | 443 | $0.0019 |
| jev_full | 0.808 | 0.082 | 0.308 | 1/2 | 8/8 | 6/6 | 0.493 | 1.000 | 150 | 437 | $0.0020 |

> decision model = seed-1-6-flash-250715（seed-1.6-mini 喺本 account 唔存在 → fallback flash，即「決策層 = interface + 1-3 token + probabilities/confidence」嘅純對照）。
