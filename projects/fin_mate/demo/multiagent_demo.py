"""FIN-MATE D7 demo：research → risk SequentialAgent（veadk 原生），連安全層。

一條龍：
  1. 定咗 role（預設 admin；可用 --role/token 模擬）
  2. 用 `veadk.agents.SequentialAgent` 行 research_agent（新聞＋calc＋KB）→
     risk_agent（output_schema 迫出 `{company, risk_level, score, reasons, sources}`）
  3. 途中安全層 hook 全部開：injection/PII input filter、PII/sensitive output
     redact、role×tool allowlist gate
  4. 同時演示 A2A 概念：唔起 service，但 2 個 sub-agents 係「遠端可註冊」嘅
     RemoteVeAgent 形態（要轉 A2A 只需換 veadk RemoteVeAgent + agent card）。

用法：`./.venv/bin/python -m demo.multiagent_demo --ticker MSFT [--role viewer|analyst|admin]`
       `./.venv/bin/python -m demo.multiagent_demo --self-test`
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# scripted demo：唔逐個 tool 撳 y（HITL 自動放行），focus 係睇 D7 安全層同委派
os.environ.setdefault("FIN_MATE_AUTOAPPROVE", "1")

from security.auth import authenticate  # noqa: E402
from security.hooks import role  # noqa: E402
from security.gate import role_tools  # noqa: E402

import multi_agent  # noqa: E402


async def _demo(ticker: str, current_role: str) -> int:
    print(f"[demo] role={current_role}  token auth 跑咗先，然後 compose "
          f"{multi_agent.build_research_agent().name} → {multi_agent.build_risk_agent().name}")
    allowed = role_tools(current_role)
    print(f"[demo] role='{current_role}' 可用 tools: {', '.join(allowed) or '(只 read/查唔到)'}\n")
    with role(current_role):
        q = (f"幫我研究 {ticker}：睇 sample_news.csv 有冇 {ticker} 新聞、用 calc 計情緒比例，"
             "然後俾一個風險結論。")
        trace = await multi_agent.run_sequential(q)
        for t in trace:
            if t.get("stage") == "final":
                print(f"── {t['author']} ──")
                print(t["text"][:900])
                print()
    risk_text = next((t["text"] for t in reversed(trace) if t.get("author") == "risk_agent"), "")
    obj = multi_agent._extract_json_obj(risk_text)
    if obj:
        print("risk_agent 結構化 JSON（output_schema 驗證）:")
        print(json.dumps(obj, ensure_ascii=False, indent=2))
        ok = all(k in obj for k in ("company", "risk_level", "score", "reasons"))
        return 0 if ok else 1
    print("冇抽出 risk JSON——睇上面 trace。")
    return 0


def _self_test() -> int:
    seq = multi_agent.build_sequential_agent()
    print(f"SequentialAgent '{seq.name}' sub_agents = {[s.name for s in seq.sub_agents]}")
    return 0


def main() -> int:
    from experiments import _lib
    _lib.load_env()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ticker", default="MSFT")
    p.add_argument("--role", default="admin", choices=["viewer", "analyst", "admin"])
    p.add_argument("--token", default=None, help="用 token 模擬認證（預設走 --role）")
    p.add_argument("--self-test", action="store_true")
    a = p.parse_args()

    role_name = a.role
    if a.token:  # 正路：token → authenticate() → 個 gate 用嘅 role
        role_name = authenticate(a.token) or "viewer"
        print(f"[demo] authenticate(token) → role='{role_name}'")

    if a.self_test:
        return _self_test()
    return asyncio.run(_demo(a.ticker, role_name))


if __name__ == "__main__":
    sys.exit(main())