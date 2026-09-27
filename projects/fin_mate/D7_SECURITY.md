# D7 · Agent Security + Multi-Agent (research → risk)

FIN-MATE D7：喺 agentkit + veadk 上面，砌「薄」嘅安全層（規則式、deterministic、
零 LLM），再做 multi-agent 委派 demo（`SequentialAgent`），同埋用 Ark Responses 原生
`text.format.json_schema` 量度「有／無 output_schema」嘅結構化輸出正確率。

| 部件 | 技術 | 文件 |
|---|---|---|
| 安全層（filter + auth + gate + hooks） | `security/`（純 function + ADK callback） | `security/self_test.py` |
| Multi-agent demo | `veadk.agents.SequentialAgent` + `google.adk.runners.Runner` | `demo/multiagent_demo.py` |
| Structured output bench | Ark `responses.create(text={format: json_schema})` | `experiments/schema_bench/` |
| Red-team eval | deterministic golden sets × four families | `eval/golden_datasets/security/` |

---

## 1. 安全層（rules-only）

三層 role：`viewer < analyst < admin`。

| 層 | 權限 |
|---|---|
| viewer | 只讀：`web_search / web_fetch / link_reader / calc` + KB/read 類 builtin |
| analyst | viewer + `fetch_news / read_news_file` |
| admin | 全部（含 `run_code / coding`） |

原則：
- **default-deny**：任何唔喺矩陣嘅 tool 只准 admin（`security/gate.py:32`）。
- **input filter**（`before_model_callback`）：`input_injection_filter` 掃 prompt
  injection（6 families：ignore_instructions / system_override / data_exfil /
  dev_mode / secrets_extract / role_jailbreak），命中即回「REFUSED」LlmResponse，
  唔入 model。同時掃 PII / sensitive，命中照常處理但標記。
- **output filter**（`after_model_callback`）：`output_pii_filter` redact PII 同
  secret 先出返俾用戶（■ masking）。
- **tool gate**（`before_tool_callback`）：`role_tool_gate` 按 `current_role`
  contextvar 檢查 tool allowlist；block 時回
  `{"result":"ROLE_BLOCKED", "reason", "tool", "role"}`，tool 唔執行。
- **auth**：`security/auth.py` token→role（`.env` `FINMATE_TOKENS`），`_safe_eq`
  constant-time compare；demo 用 `authenticate()` 攞 role 再餵俾 `role()` contextvar。

接線（`agent_build.py`）：三條 callback 全部掛入 `build_agent()`，
`tools.py` 原有 HITL `human_gate` 照行（blocked 嘅唔會入 HITL）。

## 2. Multi-agent（research → risk）

```python
seq = veadk.agents.SequentialAgent(
    name="fin_mate_seq",
    sub_agents=[research_agent, risk_agent],
)
runner = google.adk.runners.Runner(agent=seq, auto_create_session=True, ...)
async for ev in runner.run_async(user_id=..., new_message=types.Content(...)):
    ...
```

- `research_agent`：tools `read_news_file / fetch_news / calc`（＋KB）→ 產出
  「已查證嘅研究發現」文字。
- `risk_agent`：`output_schema=RISK_SCHEMA`（`{company, risk_level, score,
  reasons[], sources[]}`），喺同一 session 睇到 research 產出，出結構化風險結論。
- sub-agents 共享 session → 委派效果；要變真 A2A 只需將 sub-agents 換做
  `veadk.a2a.RemoteVeAgent` + `remote_ve_a2a_server`（呢度「點到即止」）。

## 3. output_schema vs 無 schema（schema_bench）

`experiments/schema_bench/run.py`：8 條中文風險分析 prompt × 3 iter × 2 variant
（`plain`＝淨靠 prompt 出 JSON；`schema`＝Ark `text.format.json_schema` strict），
量 parse / schema_valid / field_rate / usd。最新 run 見
`experiments/schema_bench/report.md`。

## 4. Red-team eval（interception-rate 表）

`eval/run_security_eval.py` 全 deterministic，唔經 model，直接打 `security.filters`
＋`security.gate`：

| set | 內容 |
|---|---|
| `injection.jsonl` | 15 條 × injection 6 families |
| `pii.jsonl` | 10 條（email / HK 電話 / HKID / credit card / passport＋真負例） |
| `secrets.jsonl` | 7 條（ark/sk / aws / gcp / gh / bearer / password＋負例） |
| `authz.jsonl` | 10 條 role×tool 越權矩陣（viewer 撞 `run_code` 等） |

最後有 assertion：**所有 golden 越權 call 全數 block**（injection triggered 全攔、
authz denied 全拒），有走漏即 `make sec-eval` exit 1。

## Commands

```
make sec-eval       # security self-test + deterministic red-team eval（42/42 PASS 先綠）
make schema-bench   # plain vs output_schema 對比 → report.md
make demo           # SequentialAgent research→risk demo（admin role）
.venv/bin/python -m demo.multiagent_demo --role analyst   # 睇 role gate 攔 read_news_file
```