# JEV bench SUMMARY：System One 決策層 vs 原裝 fin-mate pipeline

- tag: jbv_full   runs: 2026-09-21 12:57:32

| variant | QA r5 | QA f1 | gate-r5 | trap | tool | sent | memF1 | memSelF1 | jev# | jev med ms | usd |
|---|---|---|---|---|---|---|---|---|---|---|---|
| original | 0.808 | 0.085 | 0.808 | 2/2 | 8/8 | 6/6 | 0.412 | n/a | 0 | n/a | $0.0017 |
| original_mini | 0.808 | 0.087 | 0.808 | 2/2 | 8/8 | 6/6 | 0.457 | n/a | 0 | n/a | $0.0018 |
| jev_tool | 0.808 | 0.090 | 0.808 | 2/2 | 8/8 | 6/6 | 0.329 | n/a | 30 | 502 | $0.0018 |
| jev_rag | 0.875 | 0.090 | 0.333 | 1/2 | 8/8 | 6/6 | 0.394 | n/a | 87 | 564 | $0.0018 |
| jev_mem | 0.808 | 0.069 | 0.808 | 2/2 | 8/8 | 6/6 | 0.448 | 1.000 | 26 | 391 | $0.0018 |
| jev_full | 0.808 | 0.072 | 0.308 | 0/2 | 8/8 | 6/6 | 0.470 | 1.000 | 150 | 413 | $0.0021 |

> decision model = seed-1-6-flash-250715（seed-1.6-mini 喺本 account 唔存在 → fallback flash，即「決策層 = interface + 1-3 token + probabilities/confidence」嘅純對照）。
