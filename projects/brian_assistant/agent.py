"""brian_assistant：`veadk studio` / `veadk web` app 入口。

每個含 `agent.py` 並暴露 `root_agent` 嘅目錄，就係 veadk studio/web 嘅一個 app。
執行（cwd = 本目錄 projects/brian_assistant）：
    .venv/bin/veadk studio --agents-dir . --dev --host 127.0.0.1 --port 8002

`--agents-dir .` 會令 ADK AgentLoader 進入 single-agent 模式，只載入本 project。
若改成 `--agents-dir ..`，Studio 會在同一個 process 內載入 `projects/` 下所有
project（包括 fin_mate），屆時 fin_mate 會用本 project 嘅 .env，把 fin_kb
寫入本 project 嘅 OpenViking。

由於 module 係以頂層名 import，此處的 wiring module 特意用 project 專屬名
（`brian_assistant_agent_build`），避免同其他 project 嘅 `agent_build` 互相覆蓋。
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brian_assistant_agent_build import build_agent

root_agent = build_agent()
