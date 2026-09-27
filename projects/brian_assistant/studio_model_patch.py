"""veadk-studio-model patch (idempotent, reversible).

Points the Studio natural-language agent wizard at models the BytePlus
account has actually activated, and makes those models selectable inside the
wizard's output schema.

Upstream pins three things to `seed-2-0-lite-260228`, which account
3003699972 has not opened (Ark returns `ModelNotOpen`):

    1. veadk/cli/generated_agent_planner.py  PLANNER_MODEL_NAME
       the model Studio calls to turn a requirement into an AgentDraft.
    2. veadk/cli/generated_agent_planner.py  GeneratedAgentPlan.modelName
       a `Literal` enum of the only model names the planner may emit.
    3. veadk/consts.py  DEFAULT_MODEL_AGENT_NAME
       the modelName stamped into every generated llm Agent.

(2) is the subtle one: the schema validator requires
`modelName == DEFAULT_GENERATED_MODEL_NAME`, so changing (1)/(3) without
extending the enum makes every plan fail validation:

    Value error, web_search_handler must use <model>

The two roles get different models on purpose:

    planner          a single short structured-planning call. It must emit a
                     schema-valid recursive plan, which the cheapest tier does
                     not do reliably (it produced a non-leaf llm root).
    generated agent  runs on every user turn, so it uses the cheapest tier:
                     seed-2-0-mini-260428 at $0.10 in / $0.40 out per 1M
                     tokens (seed-2-0-lite is $0.25 / $2.00).

Apply:    python3 studio_model_patch.py apply  [<cli_frontend.py path>]
Revert:   python3 studio_model_patch.py revert [<cli_frontend.py path>]
Override: STUDIO_PLANNER_MODEL / STUDIO_AGENT_MODEL env vars.
Default target is this project's venv. Backups: *.studiomodel.bak
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

MARKER = "veadk-studio-model"

DEFAULT_PLANNER_MODEL = os.getenv("STUDIO_PLANNER_MODEL", "seed-1-8-251228")
DEFAULT_AGENT_MODEL = os.getenv("STUDIO_AGENT_MODEL", "seed-2-0-mini-260428")

DEFAULT_TARGET = Path(
    "/Users/brianho/agentkit-veadk-docs/projects/brian_assistant/.venv"
    "/lib/python3.11/site-packages/veadk/cli/cli_frontend.py"
)

PLANNER_ANCHOR = '''\
PLANNER_MODEL_NAME = (
    "seed-2-0-lite-260228"
    if cloud_provider_from_env() == "byteplus"
    else "doubao-seed-2-0-lite-260428"
)
'''

MODEL_ENUM_ANCHOR = '''\
    modelName: Literal[
        "",
        "doubao-seed-2-1-pro-260628",
        "seed-2-0-lite-260228",
    ] = Field(description="Fixed model for an llm Agent; empty for an orchestrator.")
'''

CONSTS_ANCHOR = '''\
if provider and provider.lower() == "byteplus":
    DEFAULT_MODEL_AGENT_NAME = "seed-2-0-lite-260228"
'''


def _planner_replacement(planner_model: str) -> str:
    return f'''\
# === {MARKER}: prefer an activated model; see studio_model_patch.py ===
PLANNER_MODEL_NAME = (
    "{planner_model}"
    if cloud_provider_from_env() == "byteplus"
    else "doubao-seed-2-0-lite-260428"
)
'''


def _model_enum_replacement(agent_model: str) -> str:
    return f'''\
    # === {MARKER}: add the activated model to the allowed enum ===
    modelName: Literal[
        "",
        "doubao-seed-2-1-pro-260628",
        "seed-2-0-lite-260228",
        "{agent_model}",
    ] = Field(description="Fixed model for an llm Agent; empty for an orchestrator.")
'''


def _consts_replacement(agent_model: str) -> str:
    return f'''\
if provider and provider.lower() == "byteplus":
    # === {MARKER}: prefer an activated model; see studio_model_patch.py ===
    DEFAULT_MODEL_AGENT_NAME = "{agent_model}"
'''


def _site_packages(cli_frontend: Path) -> Path:
    return cli_frontend.parents[2]


def _apply_once(src: str, old: str, new: str, label: str) -> str:
    count = src.count(old)
    if count != 1:
        raise SystemExit(
            f"{label}: anchor matched {count} times (expected 1); aborting.\n{old[:160]!r}"
        )
    return src.replace(old, new, 1)


def _edits(planner_model: str, agent_model: str) -> list[tuple[str, str, str]]:
    planner = "veadk/cli/generated_agent_planner.py"
    return [
        (planner, PLANNER_ANCHOR, _planner_replacement(planner_model)),
        (planner, MODEL_ENUM_ANCHOR, _model_enum_replacement(agent_model)),
        ("veadk/consts.py", CONSTS_ANCHOR, _consts_replacement(agent_model)),
    ]


def _recover_models(planner_source: str, consts_source: str) -> tuple[str, str]:
    """Read the models back out of the patched sources so revert is exact."""

    planner_match = re.search(
        r'PLANNER_MODEL_NAME = \(\n\s*"([^"]+)"', planner_source
    )
    agent_match = re.search(
        rf'# === {MARKER}: prefer an activated model; see studio_model_patch\.py ===\n'
        r'    DEFAULT_MODEL_AGENT_NAME = "([^"]+)"',
        consts_source,
    )
    if not planner_match or not agent_match:
        raise SystemExit("could not recover patched model names; aborting.")
    return planner_match.group(1), agent_match.group(1)


def main() -> None:
    action = sys.argv[1] if len(sys.argv) > 1 else "apply"
    if action not in {"apply", "revert"}:
        raise SystemExit("usage: studio_model_patch.py [apply|revert] [target]")
    target = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_TARGET
    if not target.exists():
        raise SystemExit(f"target not found: {target}")

    site_packages = _site_packages(target)
    origin = target.with_suffix(target.suffix + ".studiomodel.bak")
    planner_path = site_packages / "veadk/cli/generated_agent_planner.py"
    consts_path = site_packages / "veadk/consts.py"
    applied = MARKER in planner_path.read_text(encoding="utf-8")

    if action == "apply" and applied:
        print("already applied -> nothing to do")
        return
    if action == "revert" and not applied:
        print("not applied -> nothing to revert")
        return

    if action == "apply":
        planner_model, agent_model = DEFAULT_PLANNER_MODEL, DEFAULT_AGENT_MODEL
        if not origin.exists():
            shutil.copy2(target, origin)
            print(f"backup: {origin}")
    else:
        planner_model, agent_model = _recover_models(
            planner_path.read_text(encoding="utf-8"),
            consts_path.read_text(encoding="utf-8"),
        )

    revisions = _edits(planner_model, agent_model)
    if action == "revert":
        revisions = list(reversed(revisions))

    for relative, anchor, replacement in revisions:
        path = site_packages / relative
        source = path.read_text(encoding="utf-8")
        if action == "revert":
            anchor, replacement = replacement, anchor
        path.write_text(
            _apply_once(source, anchor, replacement, relative), encoding="utf-8"
        )
        print(f"[{action}] {relative}")

    if action == "revert":
        origin.unlink(missing_ok=True)

    print(
        f"{action} done (planner={planner_model}, agent={agent_model}) -> {site_packages}"
    )


if __name__ == "__main__":
    main()
