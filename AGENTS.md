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
- Dependencies are in `requirements.txt`. After adding a package, run `pip freeze > requirements.txt`.
- The app runs inside the container but must see host things (distrobox/podman, Konsole). Use `distrobox-host-exec <cmd>` to run host commands.

## Progress
- [x] Project folder, git repo, private GitHub repo
- [x] Python venv with Textual
- [x] App skeleton (layout + keybindings)
- [ ] Containers panel
- [ ] Projects panel
- [ ] Agents panel
- [ ] Launch actions

Update this checklist as work is done.
