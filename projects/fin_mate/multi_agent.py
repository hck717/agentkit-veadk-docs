"""FIN-MATE D7：SequentialAgent 委派 demo（research_agent → risk_agent）。

用 veadk 原生 `veadk.agents.SequentialAgent` 將兩個 sub-agents 串行執行：
  research_agent（數據＋新聞）：KB hybrid / 新聞 CSV / calc → 出「已查證嘅研究發現」文字
  risk_agent（風險結論）     ：消費 research 輸出，`output_schema` 迫出結構化 JSON
                               {company, risk_level, score, reasons[], sources[]}

執行用 `veadk.runner.Runner(agent=seq)`（in-memory session）；兩個 sub-agents 共享
同一 session，所以 risk 睇到 research 之前喺對話嘅產出。A2A 嘅遠程版 = veadk
`RemoteVeAgent`（agent card + A2A server，`veadk/a2a/`），呢度「點到即止」唔起 service。

用法：
  ./.venv/bin/python -m multi_agent --ticker MSFT     # 一條龍 demo
  ./.venv/bin/python -m multi_agent --self-test        # 唔撳 network 嘅結構 smoke
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions.in_memory_session_service import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

from agent_build import MODEL_PRIMARY, MODEL_BACKUP, human_gate, tool_security_gate  # noqa: E402
from security.hooks import input_injection_filter, output_pii_filter  # noqa: E402
from veadk import Agent  # noqa: E402
from veadk.agents.sequential_agent import SequentialAgent  # noqa: E402
from tools.calc import calc  # noqa: E402
from tools.news_tools import fetch_news, read_news_file  # noqa: E402

RESEARCH_INSTRUCTION = (
    "你是 FIN-MATE 研究 agent。任務：為用戶指定嘅股票做功課，產出一份「已查證嘅研究發現」。"
    "（1）用 read_news_file 讀 data/news/sample_news.csv / msft_news.csv 攞新聞同情緒；"
    "（2）要計數用 calc；（3）KB 有資料就查知識庫。"
    "結尾用「## 研究發現」列出幾點 factual claims（每點列數字或新聞標題＋情緒）。"
    "唔好作；查唔到就寫「冇資料」。"
)

RISK_INSTRUCTION = (
    "你是 FIN-MATE 風險 agent。睇返上面 research agent 嘅「研究發現」，"
    "對該股票出一個風險結論，嚴格跟輸出 JSON schema。"
)

RISK_SCHEMA = {
    "type": "object",
    "properties": {
        "company": {"type": "string", "description": "股票/公司名"},
        "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
        "score": {"type": "number", "minimum": 1, "maximum": 5, "description": "風險分 1–5（5 最高風險）"},
        "reasons": {"type": "array", "items": {"type": "string"}, "description": "唔超過 3 個理由"},
        "sources": {"type": "array", "items": {"type": "string"}, "description": "來源（新聞標題/KB 章節）"},
    },
    "required": ["company", "risk_level", "score", "reasons", "sources"],
}


def _kb_or_none():
    try:
        from agent_build import build_knowledgebase
        return build_knowledgebase()
    except Exception:  # noqa: BLE001 - demo 唔阻
        return None


def build_research_agent() -> Agent:
    kb = _kb_or_none()
    return Agent(
        name="research_agent",
        description="FIN-MATE 研究：攞數據＋新聞，產出已查證嘅研究發現",
        instruction=RESEARCH_INSTRUCTION,
        tools=[read_news_file, fetch_news, calc],
        knowledgebase=kb,
        model_name=[MODEL_PRIMARY, MODEL_BACKUP],
        before_model_callback=input_injection_filter,
        after_model_callback=output_pii_filter,
        before_tool_callback=[tool_security_gate, human_gate],
        auto_save_session=False,
    )


def build_risk_agent() -> Agent:
    return Agent(
        name="risk_agent",
        description="FIN-MATE 風險：基於研究發現出風險結論（structured JSON）",
        instruction=RISK_INSTRUCTION,
        model_name=[MODEL_PRIMARY, MODEL_BACKUP],
        output_schema=RISK_SCHEMA,
        before_model_callback=input_injection_filter,
        after_model_callback=output_pii_filter,
        auto_save_session=False,
    )


def build_sequential_agent() -> SequentialAgent:
    return SequentialAgent(
        name="fin_mate_seq",
        description="research → risk 兩段串行金融研究",
        instruction="順序執行 sub-agents：research_agent 做功課，risk_agent 出風險結論。",
        sub_agents=[build_research_agent(), build_risk_agent()],
    )


async def run_sequential(user_input: str) -> list[dict]:
    """用 veadk Runner 行 SequentialAgent，回傳 event 摘要（含每 sub-agent final）。"""
    seq = build_sequential_agent()
    app_name, user_id, session_id = "fin_mate_seq", "demo", f"seq-{getattr(seq, 'name', 'fm')}-{time.time_ns():x}"
    service = InMemorySessionService()
    service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
    runner = Runner(agent=seq, app_name=app_name, auto_create_session=True, session_service=service)
    msg = types.Content(role="user", parts=[types.Part(text=user_input)])
    trace: list[dict] = []
    finals: dict[str, str] = {}
    event_list = []
    async for ev in runner.run_async(user_id=user_id, session_id=session_id, new_message=msg):
        event_list.append(ev)
        if getattr(ev, "is_final_response", lambda: False)():
            author = getattr(ev, "author", "") or ""
            text = "".join(p.text for p in (ev.content.parts or []) if getattr(p, "text", None))
            finals[author] = text
            trace.append({"stage": "final", "author": author, "text": text[:2000]})
    return trace


def _extract_json_obj(text: str) -> dict:
    s = text.strip()
    # 由最後一個 "{" 開始向後 balance，揀最後一段完整 JSON object
    best: dict = {}
    for i, ch in enumerate(s):
        if ch != "{":
            continue
        depth, j = 0, i
        in_str, esc = False, False
        for j in range(i, len(s)):
            c = s[j]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        break
        if depth != 0:
            continue
        try:
            obj = json.loads(s[i:j + 1])
        except Exception:  # noqa: BLE001
            continue
        if isinstance(obj, dict):
            best = obj
    return best


def _fmt_final(trace: list[dict]) -> str:
    stages = []
    for t in trace:
        if t.get("stage") == "final":
            stages.append(f"── {t['author']} ──\n{t['text']}\n")
    return "\n".join(stages)


FS = "\033[2m"  # dim
RS = "\033[0m"


async def demo(ticker: str) -> int:
    print(f"{FS}D7 SequentialAgent demo · ticker={ticker} · model={MODEL_PRIMARY}{RS}")
    q = (
        f"幫我研究 {ticker}：睇 sample_news.csv 有冇 {ticker} 新聞、計一計新聞情緒比例，"
        "然後俾一個風險結論。"
    )
    trace = await run_sequential(q)
    print(_fmt_final(trace))
    risk_text = next((t["text"] for t in reversed(trace) if t.get("author") == "risk_agent"), "")
    obj = _extract_json_obj(risk_text)
    if obj:
        print("── risk_agent 結構化 JSON（提取）──")
        print(json.dumps(obj, ensure_ascii=False, indent=2))
        ok = all(k in obj for k in ("company", "risk_level", "score", "reasons"))
        print(f"\noutput_schema 驗證: {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    print("╔ 冇抽出 risk JSON；SequentialAgent 有無出到 structured output 要睇上面。")
    return 1


async def self_test() -> int:
    """唔撳網絡嘅 smoke：build 到 + schema 合法。"""
    a = build_sequential_agent()
    names = [s.name for s in a.sub_agents]
    print(f"SequentialAgent '{a.name}' sub_agents = {names}")
    return 0 if names == ["research_agent", "risk_agent"] else 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ticker", default="MSFT")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    from experiments import _lib
    _lib.load_env()
    if not os.environ.get("MODEL_AGENT_API_KEY"):
        print("[error] MODEL_AGENT_API_KEY 空；要行 model 先 set。--self-test 唔使。")
        if not args.self_test:
            return 2
    code = asyncio.run(self_test() if args.self_test else demo(args.ticker))
    sys.exit(code)


if __name__ == "__main__":
    main()