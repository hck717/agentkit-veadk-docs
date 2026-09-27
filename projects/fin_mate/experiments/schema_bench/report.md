# Schema Bench · 2026-09-10 09:23:07
- model: seed-1-6-flash-250715  iter: 3×2  live: True
- RISK_SCHEMA fields: company, risk_level, score, reasons, sources

## aggregate（valid = 過到 schema 檢查）

| variant | n | valid | parse | field_rate | tokens(p/c) | usd |
|---|---|---|---|---|---|---|
| plain | 24 | 100% | 100% | 100% | 4161/3530 | $0.0008 |
| schema | 24 | 100% | 100% | 100% | 9129/2510 | $0.0007 |

## per prompt

| prompt | ticker | plain (valid\|parse\|field) | schema (valid\|parse\|field) |
|---|---|---|---|
| p1 | MSFT | 100%| 100% | 100% | 100%| 100% | 100% |
| p2 | NVDA | 100%| 100% | 100% | 100%| 100% | 100% |
| p3 | AAPL | 100%| 100% | 100% | 100%| 100% | 100% |
| p4 | TSM | 100%| 100% | 100% | 100%| 100% | 100% |
| p5 | TSLA | 100%| 100% | 100% | 100%| 100% | 100% |
| p6 | AMZN | 100%| 100% | 100% | 100%| 100% | 100% |
| p7 | GOOGL | 100%| 100% | 100% | 100%| 100% | 100% |
| p8 | META | 100%| 100% | 100% | 100%| 100% | 100% |

## p8 example output

```json
{"company": "META", "risk_level": "high", "score": 4, "reasons": [""], "sources": [""]}
```
