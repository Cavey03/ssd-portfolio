# AGENTS.md – mission-control (for Codex / Antigravity)

Workspace rules: no AI attribution in commits; keep README.md updated; Claude may review your changes.

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
- Run everything inside `dev`: `distrobox enter dev`, then `cd ~/Projects/mission-control && source .venv/bin/activate`.
- Run tests with `.venv/bin/python -m unittest -v`.
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
