# JEV bench（phase-2）SUMMARY：5 任務 × 2 agents

- tag: runs_260921_1354   runs: 2026-09-21 13:55:07
- design: original agent（全 chat）vs JEV agent（全決策點 System One）

## 正確率（pass / recall@5 / F1 / stop-exact）

| task | original | jev |
|---|---|---|
| 工具路由 | 3/3 | 3/3 |
| RAG 檢索 gating | 1.000/r5  F1=0.150  trap=1/1 | 1.000/r5  F1=0.029  trap=0/1 |
| 記憶篩選 | F1=0.481 | F1=0.706 |
| 情緒分類 | 3/3 | 1/3 |
| 多步 workflow＋noUL | stop 1/2 | stop 1/2 |

## 延時/成本（per-item median ms；total + $ + μ$）

| task | original | jev |
|---|---|---|
| 工具路由 | 579 | 1051 |
| RAG 檢索 gating | 1049 | 4834 |
| 記憶篩選 | 1293 | 2638 |
| 情緒分類 | 534 | 506 |
| 多步 workflow＋noUL | 3052 | 5173 |
| 總計 | 17.5s $0.0006 (611μ$) | 42.3s $0.0007 (724μ$) |

## Jev telemetry（jev arm）

| 項目 | 值 |
|---|---|
| decisions | 57 |
| median ms | 489 |
| mean confidence | 0.737 |
| noul flags | 2/3 |
| thresholds | tool/sent/cont conf 0.5/0.4/0.5 · rag gate floor 0.5 / ratio 0.6 · mem 2.0 |

> decision model = seed-1-6-flash-250715（seed-1.6-mini 喺本 account 唔存在 → fallback flash，即「決策層 = interface + 1-3 token + probabilities/confidence」嘅純對照）。
