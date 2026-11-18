# CLAUDE.md – mission-control

Workspace-wide rules are in `~/Projects/CLAUDE.md`. Claude loads that file too.

## What this is
A terminal "mission control" dashboard (TUI) for the dev setup, built with Python + Textual.

### Version 1 scope
| Panel | Shows | Keys |
|---|---|---|
| Containers | Distrobox containers and their status | `s` start / stop |
| Projects | Folders in `~/Projects` with git status (branch, uncommitted changes, unpushed commits) | `↑↓` select |
| Agents | Which of claude, codex and agy are running, and in which project | – |
| Launch | Open the selected project with an agent in a new Konsole tab | `1` Claude, `2` Codex, `3` Agy |

## Dev setup
- Run everything inside `dev`: `distrobox enter dev`, then `cd ~/Projects/su5-7-llm-agents/mission-control && source .venv/bin/activate`.
- Run tests with `.venv/bin/python -m unittest -v` (in dev) and `.venv-host/bin/python -m unittest -v` (on the host).
- Dependencies are in `requirements.txt`. After adding a package, run `pip freeze > requirements.txt`.
- The app runs on the host or inside `dev`, and must work in both. `mc` prefers the host (avoids orphaned processes when a window closes). Inside `dev`, use `distrobox-host-exec <cmd>` for host things (podman, Konsole).
- Start the app with `mc` (scripts/mc). Install the command and menu entry with `scripts/install.sh`.

## Progress
- [x] Project folder, git repo, private GitHub repo
- [x] Python venv with Textual
- [x] App skeleton (layout + keybindings)
- [x] Containers panel (live podman status via host, start/stop with self-protection, tests)
- [x] Projects panel (live git status, auto-refresh every 10s, unit tests)
- [x] Agents panel (host processes, folder per session, helper filtering, tests)
- [x] Usage panel (real 5h/weekly plan limits: Codex from session logs, Claude from ~/.claude.json cache, tests)
- [x] Launch actions (1/2/3 open the agent in a new Konsole window inside dev)
- [x] Stop agent (k, with confirmation; for orphaned sessions)
- [x] Themes (t cycles; colours only from theme variables, never hard-code colours)
- [x] `mc` launcher + KDE menu entry (runs on host with fallback to dev)

Update this checklist as work is done.

## Version 2: the hub for cloud and local agents (decided 2026-11-18)
Mission Control is the main point of the SU5–7 system: it tracks containers, projects, agents (cloud and
local) and usage, and dispatches tasks. Design: **orchestrator–workers**. Opus 5.5 (`claude -p`) plans,
picks the agent/model, starts workers in git worktrees, reviews their results; the owner approves merges.
Later, a fine-tuned local model takes over the routing step (free, offline, private); Opus keeps planning
and reviewing. **Training data:** Anthropic's and OpenAI's terms restrict using their output to build products
or models that compete with theirs. Default: labels come from the owner, an open-weight teacher whose licence
allows it, or rules. The router fine-tune (2026-11-18) is a documented exception: the owner asked Claude to
review the labels, judged as non-competing coursework (see models/router-finetune/README.md). Ask the owner
before using Claude/GPT output in training data again.

- [x] Phase 0: Projects panel lists real projects only (folders with their own CLAUDE.md/AGENTS.md, or own
      repo: mission-control, local-llm, tools/summaries, particle-sim) plus one row for the portfolio repo
- [x] Phase 1: Local LLM panel: server/version, installed models, loaded model + context, VRAM (nvidia-smi);
      `o` starts/stops the Ollama user service (no load/unload from the panel)
- [x] Phase 2: Agents panel tags local Codex sessions (`codex · local (<model>)`); `4` launches `codex -p local`
- [x] Phase 3: Usage panel "Local" row (tokens from Codex session logs with `model_provider: ollama`)
- [x] Phase 4: Dispatch (`d`): orchestrator, `mc task start/status/diff/merge`, Tasks panel, decision log
- [x] Phase 5a: design + usage docs with architecture diagrams (`../DESIGN.md`, `../USAGE.md`), screenshots
- [x] Phase 5b: intro video (demo: d → Opus plan → local worker → review → merge)
- [x] Later (after phases 0–4 work): routing fine-tune in Colab (Unsloth) and on the RTX 5070, GGUF → Ollama,
      evaluation on held-out tasks; label source to be chosen (see above)
