# JEV bench（refined）SUMMARY：5 任務 × 2 arms

- tag: runs_260921_1324   runs: 2026-09-21 13:25:46
- design: original（全 chat）vs jev_tools（淨係 tool-calling 用 Jev）

## 正確率（pass 率 / recall@5 / answer-F1）

| task | original | jev_tools |
|---|---|---|
| 工具調用 | 10/10 | 10/10 |
| RAG 單源事實 | 0.818 / 0.085 | 0.818 / 0.069 |
| RAG 跨源推理 | 0.750 / 0.121 | 0.750 / 0.179 |
| 情緒分類 | 6/6 | 6/6 |
| 記憶召回 | 0.360 | 0.436 |

## 延時（per-item median ms；total ms + $）

| task | original | jev_tools |
|---|---|---|
| 工具調用 | 555 | 1570 |
| RAG 單源事實 | 1333 | 1141 |
| RAG 跨源推理 | 2770 | 4212 |
| 情緒分類 | 552 | 684 |
| 記憶召回 | 1160 | 929 |
| 總計 | 41.0s $0.0017 | 50.5s $0.0017 |

## Jev telemetry（jev_tools arm）

| 項目 | 值 |
|---|---|
| decisions | 30 |
| median ms | 515 |
| mean confidence | 0.579 |
| noul flags | 5/10 |

> decision model = seed-1-6-flash-250715（seed-1.6-mini 喺本 account 唔存在 → fallback flash，即「決策層 = interface + 1-3 token + probabilities/confidence」嘅純對照）。
