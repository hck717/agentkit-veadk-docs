# Security Eval · 2026-09-10 09:21:41

- overall: **42/42** (100%)
- engine: deterministic（唔經 model，直接打 filters＋gate）
- block policy：所有 golden 越權 call 全 block（injection triggered＋authz denied）

## 攔截率（per set）

| set | n | pass | 攔截率 |
|---|---|---|---|
| injection | 15 | 15 | 100% |
| pii | 10 | 10 | 100% |
| secrets | 7 | 7 | 100% |
| authz | 10 | 10 | 100% |

## block policy

- status: **OK**

→ eval/reports/security_run.json（逐條 golden record）
