# JEV bench SUMMARY：5 任務 × 4 agents

- tag: runs_260921_1508   runs: 2026-09-21 15:10:10
- design: original（全 chat）vs JEV 介面（System One + chat args） vs JEV 完整（真 JEV：args 確定式 + 零 generation） vs JEV tier-0（確定式規則：RRF gate / 規則路由 / marker rule / noUL asymmetric）

## 正確率（pass / recall@5 / F1 / stop-exact）

| task | original | jev | jev2 | jev3 |
|---|---|---|---|---|
| 工具路由 | 3/3 | 3/3 | 3/3 | 3/3 |
| RAG 檢索 gating | 1.000/r5  F1=0.062  trap=1/1 | 1.000/r5  F1=0.027  trap=0/1 | 1.000/r5  F1=0.037  trap=0/1 | 1.000/r5  F1=0.049  trap=1/1 |
| 記憶篩選 | F1=0.477 | F1=0.500 | F1=0.667 | F1=0.857 |
| 情緒分類 | 3/3 | 1/3 | 1/3 | 3/3 |
| 多步 workflow＋noUL | stop 1/2 | stop 1/2 | stop 1/2 | stop 2/2 |

## 延時/成本（per-item median ms；total + $ + μ$）

| task | original | jev | jev2 | jev3 |
|---|---|---|---|---|
| 工具路由 | 608 | 1009 | 524 | 0 |
| RAG 檢索 gating | 1173 | 4911 | 5045 | 1178 |
| 記憶篩選 | 1250 | 3627 | 3215 | 1509 |
| 情緒分類 | 613 | 553 | 520 | 589 |
| 多步 workflow＋noUL | 3225 | 5622 | 5607 | 1741 |
| 總計 | 18.6s $0.0006 (593μ$) | 46.5s $0.0007 (721μ$) | 44.2s $0.0007 (737μ$) | 14.5s $0.0006 (564μ$) |

## Jev telemetry

| 項目 | original | jev | jev2 | jev3 |
|--|---|---|---|---|
| decisions | 0 | 57 | 53 | 14 |
| median ms | n/a | 546 | 529 | 546 |
| mean confidence | n/a | 0.734 | 0.746 | 0.640 |
| noul YES flags | — | 2/3 | 2/3 | 2/3 |
| tier-0 (確定式) | 0 | 0 | 0 | 35 |
| thresholds | tool/sent/cont conf 0.5/0.4/0.5 · rag gate floor 0.5 / ratio 0.6 · mem 2.0 |

> decision model = seed-1-6-flash-250715（seed-1.6-mini 喺本 account 唔存在 → fallback flash，即「決策層 = interface + 1-3 token + probabilities/confidence」嘅純對照）。
