"""FIN-MATE：`veadk web` app 入口。

每個子目錄含 `agent.py` 並暴露 `root_agent` 就成為 veadk web 嘅一個 app。
執行（cwd = 本目錄 projects/fin_mate）：
    veadk web .. --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_build import build_agent

root_agent = build_agent()