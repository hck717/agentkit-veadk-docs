# brian\_assistant — local AgentKit Studio setup plan

## Summary

Stand up a personal-assistant VeADK agent at
`/Users/brianho/agentkit-veadk-docs/projects/brian_assistant` (currently **empty**), modelled on
the proven `fin_mate` layout, with:

1. **Local Viking DB** — an *isolated* OpenViking container (`brian-assistant-openviking`) on
   host port **1934** with its own volume, used as the KnowledgeBase (RAG) backend.
2. **SQLite** — short-term memory at `data/stores/brian_assistant.db`.
3. **Long-term memory** — the same OpenViking instance as LTM.
4. **Ark model connection** — BytePlus AP-Southeast-1 Ark, provider `openai`,
   `seed-1-6-flash-250715` (backup `seed-1-6-flash-250615`).
5. **AgentKit Studio / Web** — `veadk studio --dev` for add/manage and `veadk web` for chat,
   served from this project at port **8002** (8001 is taken by fin\_mate's running Studio).

Deliverable is **local-first**: runnable, locally validated, and still deployable later (an
`agentkit.yaml` is kept). Actual cloud build/deploy is **out of scope** for this change.

***

## Current State Analysis

Facts verified during exploration (not assumed):

| Fact                                    | Evidence                                                                                                                                                                                                                                                                                                                     |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Target dir is empty                     | [brian\_assistant](file:///Users/brianho/agentkit-veadk-docs/projects/brian_assistant) contains nothing                                                                                                                                                                                                                      |
| Reference project exists and works      | [fin\_mate](file:///Users/brianho/agentkit-veadk-docs/projects/fin_mate) — `agent.py`, `agent_build.py`, `agentkit.yaml`, `docker-compose.yml`, `tools/`                                                                                                                                                                     |
| Shell python has no veadk               | `python3 -c "import veadk"` → ModuleNotFoundError                                                                                                                                                                                                                                                                            |
| Python 3.11.15 available                | `/opt/homebrew/bin/python3.11`; `uv 0.12.10` also present                                                                                                                                                                                                                                                                    |
| veadk version pinned by reference       | `veadk_python-1.1.9.dist-info`, `openviking_sdk-0.1.8.dist-info`, `openviking-0.4.17.1.dist-info`                                                                                                                                                                                                                            |
| Docker + compose work                   | Docker Compose v5.0.1; `fin-mate-openviking` is Up (healthy)                                                                                                                                                                                                                                                                 |
| Ollama has the embedding model          | `nomic-embed-text:latest` present on `:11434`                                                                                                                                                                                                                                                                                |
| OpenViking container config shape known | `~/.openviking/ov.conf` = server(port/storage) + `storage.vectordb.local` (dim 768) + `embedding.dense` → ollama `host.docker.internal:11434/v1`, `nomic-embed-text`                                                                                                                                                         |
| Port 1934 free; **8001 busy**           | PID 62416 = fin\_mate's `veadk studio … --port 8001`                                                                                                                                                                                                                                                                         |
| AgentKit CLI location                   | `~/Agent-skills-POC/.venv/bin/agentkit` v0.8.5 (not on PATH) — only needed for cloud deploy, so unused here                                                                                                                                                                                                                  |
| KB/LTM env contract                     | `veadk/knowledgebase/backends/openviking_backend.py` reads `DATABASE_OPENVIKING_{URL,API_KEY,ACCOUNT,USER,USER_ID,TARGET_URI,WAIT,IMPORT_TIMEOUT,HYDRATE_RESULTS,READ_LIMIT}`; LTM uses `veadk.configs.database_configs.OpenVikingConfig` (`env_prefix="DATABASE_OPENVIKING_"`, requires URL + API\_KEY, `user_id` optional) |
| Hydration bug in veadk 1.1.9            | `OpenVikingKnowledgeBackend._hydrate` uses `overview()` whenever `is_leaf` is unset → returns "Directory overview is not ready". fin\_mate monkey-patches this in [agent\_build.py](file:///Users/brianho/agentkit-veadk-docs/projects/fin_mate/agent_build.py#L44-L83)                                                      |
| Model env contract                      | `veadk/configs/model_configs.py`: `MODEL_AGENT_API_KEY`, `MODEL_AGENT_NAME`, `MODEL_AGENT_PROVIDER`, `MODEL_AGENT_API_BASE`                                                                                                                                                                                                  |
| `web_search` needs its own credential   | `veadk/tools/builtin_tools/web_search.py`: if `CLOUD_PROVIDER=byteplus` it requires `BYTEPLUS_WEB_SEARCH_API_KEY`; otherwise it signs with `VOLCENGINE_ACCESS_KEY`/`_SECRET_KEY`. With neither it returns `"Web search failed: …"` (graceful, not a crash)                                                                   |
| Root `.env` is git-ignored              | `/Users/brianho/agentkit-veadk-docs/.gitignore` line 1                                                                                                                                                                                                                                                                       |

### What the reference does that we keep / drop

Keep: `agent.py` + `agent_build.py` split, HITL `before_tool_callback` gate, OpenViking
hydration patch, `calc` AST-whitelist tool, OpenViking auto-seed-on-boot, `agentkit.yaml`.

Drop (not needed for a personal assistant): `eval/`, `experiments/`, `observability/`, Jaeger /
otel-collector, `news_tools`, `yfinance/pandas/feedparser/pymupdf` deps, the `web` container in
compose (we run Studio on the host), and `studio_local_patch.py` (kept optional, see below).

***

## Proposed Changes

Final file tree for `projects/brian_assistant/`:

```
agent.py                 # veadk studio/web entry — exposes root_agent
brian-assistant.py       # AgentKit HTTP entry (/invoke + /ping) for future deploy
agent_build.py           # shared builder: KB + STM + LTM + tools + HITL + model
agentkit.yaml            # AgentKit project config (local + hybrid, for later deploy)
docker-compose.yml       # OpenViking only, port 1934, isolated volume
requirements.txt         # veadk-python[extensions]==1.1.9, openviking-sdk==0.1.8
.env.example             # template, no secrets
.env                     # generated skeleton; Ark key = TODO for the user
tools/__init__.py
tools/calc.py            # safe AST calc tool (port of fin_mate's)
data/kb/.gitkeep         # drop personal docs here; KB auto-seeds from this dir
data/kb/sample_note.md   # tiny placeholder so the RAG path is locally verifiable
data/stores/             # sqlite lives here (created at runtime)
```

### 1. `docker-compose.yml` — isolated OpenViking on :1934

Single service, mirroring fin\_mate's openviking block but fully isolated:

```yaml
services:
  openviking:
    container_name: brian-assistant-openviking
    image: ghcr.io/volcengine/openviking:latest
    ports: ["1934:1934"]
    volumes:
      - ~/.openviking-brian-assistant:/app/.openviking
    environment:
      OPENVIKING_SERVER_PORT: "1934"
      OPENVIKING_WITH_BOT: "0"
    extra_hosts: ["host.docker.internal:host-gateway"]
    healthcheck:
      test: ["CMD", "openviking-entrypoint", "--healthcheck"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    restart: unless-stopped
```

No `web` service → port 8000 stays free for fin\_mate's container.

**Why a pre-seeded config:** a brand-new volume has no `ov.conf`, so before `docker compose up`
I write `~/.openviking-brian-assistant/ov.conf` (outside the repo, so it is never committed)
with the same proven structure as `~/.openviking/ov.conf`, changed to:

* `server.port` = `1934`

* `server.root_api_key` = a freshly generated local key (written to `ov.conf` **and** to `.env`
  without being printed anywhere)

* `storage.workspace` = `/app/.openviking/data`, `storage.agfs.backend` = `local`,
  `storage.vectordb` = `{name: context, backend: local, distance_metric: cosine, dimension: 768}`

* `embedding.dense` = `{provider: ollama, api_base: http://host.docker.internal:11434/v1, model: nomic-embed-text, dimension: 768}`

Fallback if the hand-written config is rejected: start once, read the container log, and align
the generated default config to the port/embedding values above.

### 2. `requirements.txt`

```
veadk-python[extensions]==1.1.9
openviking-sdk==0.1.8
```

Pinned to the exact versions already proven in the reference venv (the OpenViking hydration
patch and the SDK kwargs API are version-sensitive). No finance/news deps.

Venv: `.venv` created with `uv venv --python 3.11` (matching the reference's 3.11.15), then
`uv pip install -r requirements.txt`.

### 3. `tools/calc.py` + `tools/__init__.py`

Direct port of [fin\_mate/tools/calc.py](file:///Users/brianho/agentkit-veadk-docs/projects/fin_mate/tools/calc.py)
(AST whitelist over `+ - * / **` and parentheses, returns `{"expr","result"}` or an `error`
field). `tools/__init__.py` stays empty. This gives a deterministic tool that needs no
credential, so the tool-calling path can be validated independently of `web_search`.

### 4. `agent_build.py` — shared agent construction

Structure copied from [fin\_mate/agent\_build.py](file:///Users/brianho/agentkit-veadk-docs/projects/fin_mate/agent_build.py)
with these specifics:

* `AGENT_NAME = "brian_assistant"`.

* `_patch_openviking_hydrate()` — **kept verbatim** (same guard flag, same logic). Required,
  otherwise KB search returns "Directory overview is not ready" instead of content.

* `human_gate(tool, args, tool_context)` — HITL gate over the side-effecting tools
  `{"run_code", "coding"}` only (no `read_news_file` here), bypassed when
  `BRIAN_ASSISTANT_AUTOAPPROVE` is truthy. Read-only tools always pass.

* `build_knowledgebase()` — `KnowledgeBase(backend="openviking", index="brian_kb", top_k=5)`;
  seeds `data/kb/` (and its subdirs) only when `_openviking_has_data("brian_kb")` is False,
  so restarts don't duplicate inserts. Returns `None` and logs a warning if the backend is
  unreachable, so a dead container degrades instead of blocking startup.

* `build_agent()` —

  * `ShortTermMemory(backend="sqlite", local_database_path=data/stores/brian_assistant.db)`

  * `LongTermMemory(backend="openviking")`

  * tools: `web_search, web_fetch, link_reader, run_code, coding, calc`

  * `model_name=["seed-1-6-flash-250715", "seed-1-6-flash-250615"]` (primary + backup)

  * `auto_save_session=True`, `before_tool_callback=human_gate`

  * `instruction`: a personal-assistant system prompt (concise, tool-first, cites sources,
    uses the knowledge base and memory before asking the user to repeat themselves).

  * No OTLP tracer block (observability is out of scope).

* Public helper `_openviking_has_data(index)` kept with the same SDK `list_tasks` check, used
  both by the seeder and by the verification step.

### 5. `agent.py` and `brian-assistant.py`

* [agent.py](file:///Users/brianho/agentkit-veadk-docs/projects/fin_mate/agent.py) equivalent:
  inserts its own dir on `sys.path`, imports `build_agent`, sets `root_agent = build_agent()`.
  This is what `--dev` `/list-apps` discovers.

* `brian-assistant.py`: `AgentkitSimpleApp` + `Runner`, `@app.entrypoint` reading
  `prompt`/`user_id`/`session_id`, `@app.ping` returning `"pong!"`, `app.run(host="0.0.0.0",
  port=8000)`. Kept for the future deploy path; not exercised in local validation.

### 6. `.env.example` / `.env`

Non-secret values are written by me; secret values are left as `<TODO>` for the user.

```
# --- cloud provider ---
CLOUD_PROVIDER=byteplus

# --- Ark model (BytePlus AP-Southeast-1) ---
MODEL_AGENT_PROVIDER=openai
MODEL_AGENT_API_BASE=https://ark.ap-southeast.bytepluses.com/api/v3
MODEL_AGENT_NAME=seed-1-6-flash-250715
MODEL_AGENT_API_KEY=<TODO: paste your Ark API key>

# --- local OpenViking (isolated instance, port 1934) ---
DATABASE_OPENVIKING_URL=http://localhost:1934
DATABASE_OPENVIKING_ACCOUNT=brian_assistant
DATABASE_OPENVIKING_USER=brian_assistant_user
DATABASE_OPENVIKING_USER_ID=brian_assistant_user
DATABASE_OPENVIKING_API_KEY=<generated locally, written by me — do not change>
DATABASE_OPENVIKING_WAIT=true
DATABASE_OPENVIKING_IMPORT_TIMEOUT=300
DATABASE_OPENVIKING_HYDRATE_RESULTS=true
DATABASE_OPENVIKING_READ_LIMIT=200

# --- optional ---
# BYTEPLUS_WEB_SEARCH_API_KEY=   # only needed for the builtin web_search
BRIAN_ASSISTANT_AUTOAPPROVE=    # set to 1 to skip the HITL prompt for run_code/coding
```

`.env` is written with mode `600`. It is already covered by the repo-root `.gitignore`.

**How the user supplies the Ark key:** I stop after writing `.env`, tell the user exactly which
single line to fill (`MODEL_AGENT_API_KEY`), and resume validation once they confirm. No secret
is ever read, echoed, or copied by me.

### 7. `agentkit.yaml`

Copy of [fin\_mate/agentkit.yaml](file:///Users/brianho/agentkit-veadk-docs/projects/fin_mate/agentkit.yaml)
with `agent_name: brian-assistant`, `entry_point: brian-assistant.py`, `cr_repo_name:
brian-assistant`, and the same `runtime_envs` (provider/openai, the AP-Southeast base, the
model name) and `docker_build.base_image`. Retained so a later `agentkit build/deploy` does not
require re-scaffolding; not used in this change.

***

## Assumptions & Decisions

| # | Decision                                                                     | Rationale                                                                                                                                                                                                                    |
| - | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | Isolated OpenViking on **:1934** with volume `~/.openviking-brian-assistant` | User choice; avoids sharing fin\_mate's store and avoids the port-1933 collision                                                                                                                                             |
| 2 | Studio/web on port **8002**                                                  | 8001 is occupied by the running fin\_mate Studio (PID 62416); 8000 is fin\_mate's container                                                                                                                                  |
| 3 | `--agents-dir ..` (parent `projects/`)                                       | Matches the reference; makes both `fin_mate` and `brian_assistant` selectable in the picker                                                                                                                                  |
| 4 | Reuse BytePlus AP-Southeast-1 Ark endpoint + `seed-1-6-flash-250715`         | User choice; identical to the working reference                                                                                                                                                                              |
| 5 | `web_search` stays wired but uncredentialed                                  | User has no web-search key; it degrades to a readable error string. Web research is validated via `web_fetch` + `link_reader` instead                                                                                        |
| 6 | Keep the `run_code`/`coding` tools behind HITL                               | User asked for code/calc capability; these have side effects, so they need approval by default                                                                                                                               |
| 7 | No cloud deploy in this change                                               | User asked for setup + local DBs + model connection; `agentkit.yaml` preserves the deploy path                                                                                                                               |
| 8 | One placeholder file in `data/kb/`                                           | Without any document, KB seeding and search cannot be distinguished from "broken". The placeholder is tiny and meant to be deleted/replaced                                                                                  |
| 9 | `studio_local_patch.py` **not** copied                                       | Optional; if wanted, the reference script can be pointed at this venv: `python3 fin_mate/studio_local_patch.py apply <brian_assistant>/.../veadk/cli/cli_frontend.py`. Listed as optional post-step, not part of this change |

***

## Verification

Local evidence is collected in this order; nothing is reported as passing unless it actually ran.

1. **Config sanity** — `docker compose config` parses; `ov.conf` is valid JSON and its port
   matches `1934`.
2. **Viking DB up** — `docker compose up -d`, then poll
   `docker inspect --format '{{.State.Health.Status}}' brian-assistant-openviking` until
   `healthy` (bounded wait).
3. **Isolation** — confirm `:1934` is served by the new container while fin\_mate's `:1933`
   is untouched, and that fin\_mate's containers are still Up.
4. **Imports / compile** — `.venv/bin/python -m compileall` on the project, then import
   `agent_build` and assert `build_agent()` returns an `Agent`.
5. **Tool-level checks (before agent integration)**

   * `calc("100 * (1 + 0.05) ** 3")` → numeric result, no error.

   * `_openviking_has_data("brian_kb")` → `True` after the first seed (proves index write).
6. **Retrieval check** — call the KB backend's `search()` directly with a phrase from
   `data/kb/sample_note.md` and confirm non-empty hydrated content (this is the check the
   hydration patch exists for).
7. **SQLite STM** — assert `data/stores/brian_assistant.db` is created and has tables after a
   short `Runner` session, proving the STM backend is wired.
8. **Model connection** — a minimal direct Ark call with `MODEL_AGENT_*` from `.env` must
   return a completion. Requires the user to have filled `MODEL_AGENT_API_KEY` first; this is
   the one step gated on user input.
9. **Representative agent run** — one `Runner.run()` through `build_agent()` with a prompt that
   forces a `calc` call, plus one prompt that should trigger memory/KB use; assert a non-empty
   final response.
10. **Service check** — launch the real Studio entry point
    (`veadk studio --agents-dir .. --dev --host 127.0.0.1 --port 8002`) as a background
    process, confirm it stays alive, then `curl /web/ui-config` (expect
    `"agentsSource": "local"`) and `curl /list-apps` (expect `brian_assistant` to appear).
    Stop the process afterwards.
11. **Walkthrough** — open the UI, select `brian_assistant`, and confirm the agent card shows
    the OpenViking KB, sqlite STM, and LTM components.

### Risks and how they are handled

* **Fresh** **`ov.conf`** **rejected by the image** → align with the entrypoint's generated defaults
  (step 2 fallback), then re-run steps 2–6.

* **Account/user auto-provisioning on a brand-new instance** → if `initialize()` fails, create
  the account/user through the OpenViking admin API/CLI, then re-run steps 5–6.

* **`run_code`** **/** **`coding`** **may need a cloud sandbox** → if they fail at runtime, keep them
  registered but report the dependency; `calc` already covers deterministic math.

* **`web_search`** **uncredentialed** → expected, documented, not treated as a failure.

***

## Out of Scope

* Cloud `agentkit build` / `deploy` / runtime creation (the CLI is available at
  `~/Agent-skills-POC/.venv/bin/agentkit` when wanted).

* Evaluation harness, observability/Jaeger, news tools, and the Studio local-management patch.

* Populating the knowledge base with real personal documents (user-supplied).

