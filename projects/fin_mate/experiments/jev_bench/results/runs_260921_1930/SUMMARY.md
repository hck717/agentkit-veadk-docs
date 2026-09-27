# JEV bench（phase-2）SUMMARY：5 任務 × 3 agents

- tag: runs_260921_1930   runs: 2026-09-21 14:22:59
- design: original（全 chat）vs JEV 介面（System One + chat args） vs JEV 完整（真 JEV：args 確定式 + 零 generation）

## 正確率（pass / recall@5 / F1 / stop-exact）

| task | original | jev | jev2 |
|---|---|---|---|
| 工具路由 | 3/3 | 3/3 | 3/3 |
| RAG 檢索 gating | 1.000/r5  F1=0.049  trap=1/1 | 1.000/r5  F1=0.033  trap=0/1 | 1.000/r5  F1=0.053  trap=0/1 |
| 記憶篩選 | F1=0.125 | F1=0.601 | F1=0.487 |
| 情緒分類 | 3/3 | 1/3 | 1/3 |
| 多步 workflow＋noUL | stop 1/2 | stop 1/2 | stop 1/2 |

## 延時/成本（per-item median ms；total + $ + μ$）

| task | original | jev | jev2 |
|---|---|---|---|
| 工具路由 | 595 | 1008 | 471 |
| RAG 檢索 gating | 1244 | 4649 | 5157 |
| 記憶篩選 | 1271 | 2816 | 2605 |
| 情緒分類 | 562 | 429 | 730 |
| 多步 workflow＋noUL | 2095 | 4860 | 4891 |
| 總計 | 16.5s $0.0006 (598μ$) | 41.1s $0.0008 (762μ$) | 41.8s $0.0007 (705μ$) |

## Jev telemetry

| 項目 | original | jev | jev2 |
|--|---|---|---|
| decisions | 0 | 57 | 54 |
| median ms | n/a | 464 | 526 |
| mean confidence | n/a | 0.740 | 0.742 |
| noul Y/N | — | 2/3 | 2/3 |
| thresholds | tool/sent/cont conf 0.5/0.4/0.5 · rag gate floor 0.5 / ratio 0.6 · mem 2.0 |

> decision model = seed-1-6-flash-250715（seed-1.6-mini 喺本 account 唔存在 → fallback flash，即「決策層 = interface + 1-3 token + probabilities/confidence」嘅純對照）。
