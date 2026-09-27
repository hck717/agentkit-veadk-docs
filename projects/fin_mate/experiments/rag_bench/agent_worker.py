"""agentic 每題一個 fresh subprocess：veadk Agent + ADK Runner 喺同一進程連續跑會
hang / litellm threadpool 死；subprocess + timeout 令單題出事唔會拖冧成個 run。

用法：python -m experiments.rag_bench.agent_worker <eid> <out.json>
（run.py 喺 agentic pipe 每個 item spawn 佢。）

注意：
- Runner 嘅 sync generator 要喺**冇 active event loop** 先行到，唔好外層 asyncio.run 包住成段（except create_session）。
- 呢度直接 inline 實證可行嘅流程（唔走 strategies.run_agentic_sync 間接層）：似得咁先穩定。
- hang/超時由 run.py 嘅 subprocess 硬 timeout 管。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments import _lib  # noqa: E402


def main() -> int:
    eid, out_path = sys.argv[1], sys.argv[2]
    import asyncio
    import time as _tm
    from experiments.rag_bench import strategies as S
    from experiments.rag_bench.eval_set import ITEMS, all_doc_uris
    from google.adk.runners import Runner
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.genai import types

    _lib.load_env()
    doc_uris = all_doc_uris()
    item = next(i for i in ITEMS if i["eid"] == eid)
    strat, q, cat = "agentic", item["q"], item["cat"]

    kb = S._kb(S.STRATS[strat]["read_limit"])
    before = S._ov_snapshot()
    agent = S._build_agent(kb)
    events = []
    t0 = _tm.perf_counter()
    session_service = InMemorySessionService()
    new_message = types.Content(role="user", parts=[types.Part(text=q)])
    session_id = f"rag-{eid}"
    asyncio.run(session_service.create_session(app_name="rag_bench", user_id="bench", session_id=session_id))
    runner = Runner(agent=agent, app_name="rag_bench", session_service=session_service)
    transcript = []
    n_tool_rounds = 0
    for ev in runner.run(user_id="bench", session_id=session_id, new_message=new_message):
        kind = "final" if ev.is_final_response() else "function_call" if ev.get_function_calls() else \
            "function_response" if ev.get_function_responses() else "llm"
        payload = {"kind": kind, "ts": str(getattr(ev, "timestamp", ""))}
        if ev.content is not None and ev.content.parts:
            payload["parts"] = []
            for _x in ev.content.parts:
                _txt = getattr(_x, "text", None)
                if _txt is None:
                    continue
                payload["parts"] += [str(_y) for _y in (_txt if isinstance(_txt, list) else [_txt])]
        for fc in ev.get_function_calls() or []:
            payload.setdefault("calls", []).append({"name": getattr(fc, "name", ""), "args": getattr(fc, "args", {})})
        for fr in ev.get_function_responses() or []:
            payload.setdefault("responses", []).append({"name": getattr(fr, "name", ""), "response": getattr(fr, "response", "")})
        if ev.usage_metadata is not None:
            um = ev.usage_metadata
            payload["usage"] = {"prompt": getattr(um, "prompt_token_count", 0) or 0,
                                "completion": getattr(um, "response_token_count", 0) or 0,
                                "cached": getattr(um, "cached_content_token_count", 0) or 0}
        transcript.append(payload)
    ms = (_tm.perf_counter() - t0) * 1000
    _final = []
    for _ev in transcript:
        if _ev["kind"] == "final":
            _final += _ev.get("parts") or []
    answer = "\n".join(str(_p) for _p in _final)
    usage = {"prompt": sum(e.get("usage", {}).get("prompt", 0) for e in transcript),
             "completion": sum(e.get("usage", {}).get("completion", 0) for e in transcript),
             "cached": sum(e.get("usage", {}).get("cached", 0) for e in transcript)}
    tools_called = [c.get("name") for e in transcript for c in e.get("calls", [])]
    cite = S._cite(transcript, answer)
    after = S._ov_snapshot()
    S._emit(events, strat, eid, cat, "agent", ms=ms, tokens=usage, detail={"tool_calls": tools_called,
            "citation": cite, "observer_delta": {"vectors": after.get("vectors")}})
    res = dict(strategy=strat, eid=eid, category=cat, uris=cite["retrieved"], answer=answer, events=events,
               extra={"transcript": transcript, "usage": usage, "citation": cite, "tools": tools_called})
    Path(out_path).write_text(json.dumps(res, ensure_ascii=False, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())