#!/usr/bin/env python3
"""FIN-MATE 本地 observability 打包：一次過收返所有 trace / log / 透明度資料。

用法（cwd = projects/fin_mate）：
    ./.venv/bin/python scripts/trace_all.py [out_dir]

行咩嘢：
  1. OpenViking 透明度（REST /api/v1/*，用 .env 個 API key）：
       observer/system, observer/queue, observer/models, observer/retrieval,
       observer/filesystem, stats/memories, tasks, debug/vector/count
  2. 容器 log：docker compose logs web / openviking / otel-collector / jaeger
  3. CLI 自身 log：.agentkit/logs/
  4. Session / STM 檔案摘要：data/stores/fin_mate.db、.adk/session.db（只列大小+時間）
  5. Jaeger 提示（邊度開 UI 睇完整 span trace）

輸出：<out_dir>/observability-<timestamp>/  一個資料夾，JSON + 人類可讀 summary。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
ENDPOINTS = [
    ("observer/system", "/api/v1/observer/system"),
    ("observer/queue", "/api/v1/observer/queue"),
    ("observer/models", "/api/v1/observer/models"),
    ("observer/retrieval", "/api/v1/observer/retrieval"),
    ("observer/filesystem", "/api/v1/observer/filesystem"),
    ("stats/memories", "/api/v1/stats/memories"),
    ("tasks", "/api/v1/tasks?limit=100"),
    ("debug/vector/count", "/api/v1/debug/vector/count"),
]
LOG_SERVICES = ["web", "openviking", "otel-collector", "jaeger"]


def _load_env() -> dict:
    env = {}
    envf = PROJECT / ".env"
    if envf.exists():
        for line in envf.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"')
    return env


def _api_key(env: dict) -> str:
    # 實際費 key 喺 .env 嘅 DATABASE_OPENVIKING_API_KEY；root key 做 fallback
    return os.getenv("DATABASE_OPENVIKING_API_KEY") or env.get(
        "DATABASE_OPENVIKING_API_KEY", ""
    )


def _openviking_base(env: dict) -> str:
    return os.getenv("DATABASE_OPENVIKING_URL") or env.get(
        "DATABASE_OPENVIKING_URL", "http://localhost:1933"
    )


def _get_json(url: str, api_key: str) -> dict | str:
    import urllib.request

    req = urllib.request.Request(url)
    if api_key:
        req.add_header("X-API-Key", api_key)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode()
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": str(exc)})


def _run(cmd: list[str]) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        return (r.stdout or "") + (r.stderr or "")
    except Exception as exc:  # noqa: BLE001
        return f"(error running: {cmd[0]} -> {exc})"


def _dump_files(out_dir: Path) -> None:
    for label, paths in [
        ("stores_db", [PROJECT / "data" / "stores" / "fin_mate.db"]),
        ("adk_session_db", [PROJECT / ".adk" / "session.db"]),
    ]:
        lines = []
        for p in paths:
            if p.exists():
                st = p.stat()
                lines.append(f"{p} size={st.st_size} mtime={datetime.fromtimestamp(st.st_mtime)}")
            else:
                lines.append(f"{p} (missing)")
        (out_dir / f"{label}.txt").write_text("\n".join(lines) + "\n")


def main() -> int:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT / "observability"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bundle = out_dir / f"observability-{stamp}"
    bundle.mkdir(parents=True, exist_ok=True)

    env = _load_env()
    base = _openviking_base(env)
    key = _api_key(env)

    # 1. OpenViking REST 透明度
    for name, path in ENDPOINTS:
        raw = _get_json(f"{base}{path}", key)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = raw
        fname = f"openviking_{name.replace('/', '_')}.json"
        (bundle / fname).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        )

    # 2. 容器 logs
    logs_dir = bundle / "logs"
    logs_dir.mkdir()
    for svc in LOG_SERVICES:
        (logs_dir / f"{svc}.log").write_text(_run(["docker", "compose", "logs", "--no-log-prefix", svc]))

    # 3. CLI 自身 log
    cli_logs = PROJECT / ".agentkit" / "logs"
    if cli_logs.exists():
        shutil.copytree(cli_logs, bundle / "agentkit_logs", dirs_exist_ok=True)

    # 4. session / STM 檔案摘要
    _dump_files(bundle)

    # 5. Jaeger 提示
    (bundle / "JAEGER.txt").write_text(
        "Open Jaeger UI: http://localhost:16686\n"
        'Select service (e.g. "veadk" / agent service) -> Find Traces.\n'
        "OpenViking internals: use the openviking_*.json files in this folder.\n"
    )

    # 人類可讀 summary
    summary = ["# FIN-MATE Observability Bundle", f"time: {stamp}", "", "## OpenViking observer/system"]
    summary.append(_get_json(f"{base}/api/v1/observer/system", key))
    (bundle / "SUMMARY.txt").write_text("\n".join(summary) + "\n")

    print(f"Done -> {bundle}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
