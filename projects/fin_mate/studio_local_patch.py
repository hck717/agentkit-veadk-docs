"""veadk-studio-local-mgmt patch (idempotent, reversible).

Patches the installed veadk Studio server (cli_frontend.py in the fin_mate
venv) so that, when running with `--dev`, the cloud-only management tabs
serve the LOCAL agents/knowledge bases/memory instead of calling the BytePlus/
Volcengine control plane (which is NXDOMAIN from this machine):

  - /web/my-runtimes, /web/runtimes  -> lists local agents as "local:" pseudo-runtimes
  - /web/runtime-detail              -> local agent config (env values masked)
  - /web/viking-knowledgebases       -> local openviking KB components (e.g. fin_kb)
  - /web/viking-memories             -> local openviking LTM components
  - /web/cronjobs                    -> mount an empty stub when TOS storage is absent
                                       (otherwise the SPA fallback returns HTML and the
                                       page crashes parsing JSON)

Apply:    python3 studio_local_patch.py apply   [<cli_frontend.py path>]
Revert:   python3 studio_local_patch.py revert  [<cli_frontend.py path>]
Default path is the fin_mate venv copy. A .bak is written on first apply.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

MARKER = "veadk-studio-local-mgmt"

DEFAULT_TARGET = Path(
    "/Users/brianho/agentkit-veadk-docs/projects/fin_mate/.venv"
    "/lib/python3.11/site-packages/veadk/cli/cli_frontend.py"
)

HELPERS = '''\
    _agent_loader = AgentLoader(agents_dir)

    # === veadk-studio-local-mgmt: local management helpers ===
    def _local_mgmt_components() -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        try:
            names = _agent_loader.list_agents()
        except Exception:
            return out
        for name in sorted(names):
            try:
                agent = _agent_loader.load_agent(name)
            except Exception:
                continue
            for comp in (agent_component_summaries(agent) or []):
                comp = dict(comp or {})
                out.append({
                    "agent": name,
                    "kind": comp.get("kind", ""),
                    "name": comp.get("name", ""),
                    "source": comp.get("source", ""),
                    "backend": comp.get("backend", ""),
                    "description": str(comp.get("description", "") or ""),
                })
        return out

    def _local_mgmt_runtimes() -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        try:
            names = _agent_loader.list_agents()
        except Exception:
            return out
        for name in sorted(names):
            try:
                agent = _agent_loader.load_agent(name)
            except Exception as e:
                out.append({
                    "name": name,
                    "runtimeId": f"local:{name}",
                    "status": "UNKNOWN",
                    "region": "local",
                    "description": f"未能載入本地 agent: {e}",
                    "isMine": True,
                    "canDelete": False,
                    "author": "local",
                    "createdAt": "",
                    "currentVersion": None,
                })
                continue
            out.append({
                "name": name,
                "runtimeId": f"local:{name}",
                "status": "RUNNING",
                "region": "local",
                "description": str(getattr(agent, "description", "") or ""),
                "cpuMilli": None,
                "memoryMb": None,
                "currentVersion": None,
                "author": "local",
                "isMine": True,
                "canDelete": False,
                "createdAt": "",
            })
        return out
'''

# Ordered list of (anchor_old, replacement_new). Revert reverses the list.
EDITS = [
    (
        '    _agent_loader = AgentLoader(agents_dir)\n',
        HELPERS,
    ),
    (
        '    `region=all` queries every supported region and merges results."""\n'
        '        principal = _current_principal(request)\n',
        '    `region=all` queries every supported region and merges results."""\n'
        '        # === ' + MARKER + ': serve LOCAL agents when running --dev ===\n'
        '        if dev:\n'
        '            return {"runtimes": _local_mgmt_runtimes()}\n'
        '        principal = _current_principal(request)\n',
    ),
    (
        '        region=all merges runtimes across all supported regions."""\n'
        '        principal = _current_principal(request)\n',
        '        region=all merges runtimes across all supported regions."""\n'
        '        # === ' + MARKER + ': serve LOCAL agents when running --dev ===\n'
        '        if dev:\n'
        '            return {"runtimes": _local_mgmt_runtimes(), "nextToken": ""}\n'
        '        principal = _current_principal(request)\n',
    ),
    (
        '        if not runtimeId:\n'
        '            raise HTTPException(status_code=400, detail="runtimeId is required")\n'
        '        region = _coerce_cloud_region(region)\n',
        '        if not runtimeId:\n'
        '            raise HTTPException(status_code=400, detail="runtimeId is required")\n'
        '        # === ' + MARKER + ': local agent as pseudo-runtime detail (--dev) ===\n'
        '        if dev and runtimeId.startswith("local:"):\n'
        '            local_name = runtimeId[len("local:"):]\n'
        '            try:\n'
        '                agent = _agent_loader.load_agent(local_name)\n'
        '            except Exception:\n'
        '                raise HTTPException(status_code=404, detail=f"unknown local agent: {local_name}")\n'
        '            envs: list[dict[str, str]] = []\n'
        '            for key in sorted(os.environ):\n'
        '                upper = key.upper()\n'
        '                if any(tok in upper for tok in ("SECRET", "PASSWORD", "ACCESS", "TOKEN", "API_KEY", "KEY")):\n'
        '                    envs.append({"key": key, "value": "[masked]"})\n'
        '                    continue\n'
        '                envs.append({"key": key, "value": os.environ[key][:200]})\n'
        '            return {\n'
        '                "runtimeId": runtimeId,\n'
        '                "name": local_name,\n'
        '                "description": str(getattr(agent, "description", "") or ""),\n'
        '                "status": "RUNNING",\n'
        '                "statusMessage": "本地 agent（--dev），由 veadk studio 直接提供",\n'
        '                "model": str(_model_name(getattr(agent, "model", "")) or ""),\n'
        '                "project": "",\n'
        '                "region": "local",\n'
        '                "createdAt": "",\n'
        '                "updatedAt": "",\n'
        '                "currentVersion": None,\n'
        '                "resources": {"cpuMilli": None, "memoryMb": None, "minInstance": None, "maxInstance": None, "maxConcurrency": None},\n'
        '                "envs": envs,\n'
        '                "memoryId": "",\n'
        '                "toolId": "",\n'
        '                "knowledgeId": "",\n'
        '                "mcpToolsetId": "",\n'
        '                "artifactUrl": "",\n'
        '                "artifactType": "",\n'
        '                "networkTypes": [],\n'
        '                "endpoint": "http://127.0.0.1:8001",\n'
        '                "authType": "local",\n'
        '            }\n'
        '        region = _coerce_cloud_region(region)\n',
    ),
    (
        '    @app.get("/web/viking-knowledgebases")\n'
        '    async def _web_list_viking_knowledgebases(\n'
        '        request: Request,\n'
        '        region: str = "",\n'
        '        project: str = "",\n'
        '    ):\n'
        '        """List VikingDB KnowledgeBase collections visible to server creds."""\n'
        '        _require_agent_management(request)\n',
        '    @app.get("/web/viking-knowledgebases")\n'
        '    async def _web_list_viking_knowledgebases(\n'
        '        request: Request,\n'
        '        region: str = "",\n'
        '        project: str = "",\n'
        '    ):\n'
        '        """List VikingDB KnowledgeBase collections visible to server creds."""\n'
        '        # === ' + MARKER + ': serve LOCAL KBs when running --dev ===\n'
        '        if dev:\n'
        '            items = []\n'
        '            for comp in _local_mgmt_components():\n'
        '                if comp.get("kind") != "knowledgebase":\n'
        '                    continue\n'
        '                items.append({\n'
        '                    "id": comp["name"],\n'
        '                    "name": comp["name"],\n'
        '                    "description": comp["description"],\n'
        '                    "projectName": "local",\n'
        '                    "region": "local",\n'
        '                    "docCount": None,\n'
        '                    "updatedAt": "",\n'
        '                    "resourceId": f"local:{comp[\'agent\']}:{comp[\'name\']}",\n'
        '                    "sourceKind": "knowledge",\n'
        '                    "sourceLabel": "Local OpenViking",\n'
        '                })\n'
        '            if not items:\n'
        '                raise HTTPException(status_code=502, detail="暫時無法載入本地知識庫（未偵測到 knowledgebase component）。")\n'
        '            return {"items": items, "totalCount": len(items)}\n'
        '        _require_agent_management(request)\n',
    ),
    (
        '    @app.get("/web/viking-memories")\n'
        '    async def _web_list_viking_memories(\n'
        '        region: str = "",\n'
        '        project: str = "",\n'
        '    ):\n'
        '        """List VikingDB Memory collections visible to server creds."""\n'
        '        region = _coerce_cloud_region(region)\n',
        '    @app.get("/web/viking-memories")\n'
        '    async def _web_list_viking_memories(\n'
        '        region: str = "",\n'
        '        project: str = "",\n'
        '    ):\n'
        '        """List VikingDB Memory collections visible to server creds."""\n'
        '        # === ' + MARKER + ': serve LOCAL LTM when running --dev ===\n'
        '        if dev:\n'
        '            items = []\n'
        '            for comp in _local_mgmt_components():\n'
        '                if comp.get("kind") != "memory" or comp.get("source") != "long_term_memory":\n'
        '                    continue\n'
        '                items.append({\n'
        '                    "projectName": "local",\n'
        '                    "name": comp["name"],\n'
        '                    "id": comp["name"],\n'
        '                    "description": comp["description"],\n'
        '                    "region": "local",\n'
        '                    "sourceLabel": "Local OpenViking LTM",\n'
        '                })\n'
        '            return {"items": items, "totalCount": len(items)}\n'
        '        region = _coerce_cloud_region(region)\n',
    ),
    (
        '                replica_id=f"studio-local-{os.getpid()}",\n'
        '            )\n\n'
        '    @app.get("/web/my-runtimes")\n',
        '                replica_id=f"studio-local-{os.getpid()}",\n'
        '            )\n'
        '    else:\n'
        '        # === ' + MARKER + ': mount empty stub when no TOS storage ===\n'
        '        @app.get("/web/cronjobs")\n'
        '        async def _web_cronjobs_stub():\n'
        '            return {"items": [], "totalCount": 0}\n\n'
        '    @app.get("/web/my-runtimes")\n',
    ),
]


def _apply_once(src: str, old: str, new: str) -> str:
    count = src.count(old)
    if count != 1:
        raise SystemExit(
            f"anchor matched {count} times (expected 1); aborting — file changed?\n{old[:120]!r}"
        )
    if MARKER not in old and MARKER in new and MARKER not in src:
        pass  # first application
    return src.replace(old, new, 1)


def main() -> None:
    target = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_TARGET
    action = sys.argv[1] if len(sys.argv) > 1 else "apply"
    if not target.exists():
        raise SystemExit(f"target not found: {target}")

    src = target.read_text(encoding="utf-8")
    revisions = EDITS if action == "apply" else list(reversed(EDITS))

    marker_present = MARKER in src
    if action == "apply" and marker_present:
        print("already applied -> nothing to do")
        return
    if action == "revert" and not marker_present:
        print("not applied -> nothing to revert")
        return

    bak = target.with_suffix(target.suffix + ".lokalmgmt.bak")
    if action == "apply" and not bak.exists():
        shutil.copy2(target, bak)
        print(f"backup: {bak}")

    for i, (old, new) in enumerate(revisions, 1):
        before = old if action == "apply" else new
        after = new if action == "apply" else old
        src = _apply_once(src, before, after)
        print(f"[{i}/{len(revisions)}] {'patched' if action == 'apply' else 'reverted'} ({len(after)} chars)")

    target.write_text(src, encoding="utf-8")
    print(f"{action} done -> {target}")


if __name__ == "__main__":
    main()