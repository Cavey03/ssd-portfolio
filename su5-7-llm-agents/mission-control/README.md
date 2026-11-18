# Mission Control

A terminal dashboard (TUI) for my Linux agentic coding setup. From one screen I can:

- see and start/stop my Distrobox containers
- see the git status of every project in `~/Projects`
- see which AI coding agents (Claude Code, Codex, Antigravity) are running
- launch any agent in any project with one keypress

Built with **Python 3.14** and **[Textual](https://textual.textualize.io/)**.
Part of my SSD portfolio: [ssd-portfolio](https://github.com/Cavey03/ssd-portfolio).

## Status
🚧 In development. See the progress checklist in `CLAUDE.md`.

## Run
Type `mc` in any terminal, or open **Mission Control** from the KDE app menu (Development).

Install the command and menu entry once with `./scripts/install.sh` (`--uninstall` removes both).
It links `~/.local/bin/mc` to `scripts/mc` and writes `~/.local/share/applications/mission-control.desktop`.

**Where it runs:** started from the host, `mc` runs the app **on the host**. A Python venv only works with
the Python version it was built with, and the host and `dev` can differ (since November 2026 the host has
Python 3.15 and `dev` 3.14). So there are two venvs: `.venv` (built in `dev`) and `.venv-host` (built on the
host). `mc` tries `.venv-host`, then `.venv`, and if neither works it falls back to running inside `dev`
with a warning.

**Why the host:** a program started through `distrobox enter` keeps running invisibly when you close its
window, because podman's `conmon` keeps the container side of the terminal open. A test with a
pseudo-terminal proved it: closing the window left Mission Control running inside `dev`, but on the host it
stopped normally. On the host the app also gets Podman directly and can see every process's folder, with
no `distrobox-host-exec` workarounds needed.

## Tests
```bash
.venv/bin/python -m unittest -v        # inside dev
.venv-host/bin/python -m unittest -v   # on the host: the app must work in both
```

## How the Projects panel works
- **What counts as a project.** `~/Projects` is one git repo (the portfolio), so the panel lists:
  1. the portfolio repo itself (`Projects`), with its branch, changes and sync state;
  2. indented under it, each folder inside it that has its own `CLAUDE.md` or `AGENTS.md`, such as
     `su5-7-llm-agents/mission-control`. Each shows only the changes inside that folder
     (`git status -- <folder>`), and shares the repo's branch;
  3. every separate git repo below `~/Projects`, such as `particle-sim` or the `su4-cnn/group-repo` submodule.
  The search goes 4 folder levels deep, skips hidden folders, `.venv` and `node_modules`, and doesn't look
  inside separate repos. Plain folders such as `su3-learning-models/` aren't projects, so they aren't listed.
- The launch keys open the agent in exactly the selected folder, and the Agents panel names each agent by
  the project it works in (`mission-control`, not `su5-7-llm-agents`).
- `gitinfo.py` runs `git status --porcelain=v2 --branch` in each folder in `~/Projects`. The
  "porcelain" format is git's stable, machine-readable output. One command gives the branch,
  the changed files and how many commits are ahead of or behind the remote.
- It sets `GIT_OPTIONAL_LOCKS=0`, so polling never locks a repo that git or an AI agent is using.
- Scanning runs in a **background thread** (Textual `@work(thread=True)`), so the UI never freezes.
  It refreshes every 10 seconds, or when you press `r`.
- Set `MISSION_CONTROL_PROJECTS` to scan a different folder.

## How the Containers panel works
- The app runs **inside** the `dev` container, but podman lives on the **host**. Commands go through
  `distrobox-host-exec podman ...`. If the app is run directly on the host, it calls `podman` itself.
- It lists only Distrobox containers (`--filter label=manager=distrobox`) as JSON, parsed by a pure,
  unit-tested function.
- `s` starts or stops the selected container in a background thread. **Self-protection:** it refuses to
  stop the container Mission Control is running in, detected from `$CONTAINER_ID` or `/run/.containerenv`.
- All podman calls have timeouts and never crash the UI. Errors are shown in the panel instead.

## How the Agents and Usage panels work
- **Agents:** Distrobox shares the host's process list, so the app reads `/proc` to find `claude`, `codex`
  and `agy` sessions, the folder each works in, and when each started. Two complications:
  - The kernel hides host processes' working folders from a rootless container. For those, the app asks
    the host in one `distrobox-host-exec` call.
  - Codex runs helper processes (a sandbox runner and a background daemon). These are filtered out, so
    each session appears once.
- **Usage:** both providers show the **real 5-hour and weekly plan limits**:
  - **Codex** writes them to its session logs (`~/.codex/sessions`) after every request.
  - **Claude Code** caches the numbers behind its `/usage` command in `~/.claude.json`. The app only reads
    it. Run `/usage` in Claude Code for the freshest numbers. This is an internal format, so the parser
    treats every field as optional.

## Launching agents
Select a project and press `1` (Claude), `2` (Codex) or `3` (Antigravity). A **new Konsole window** opens in
that project, inside the `dev` container. It is started detached, so it stays open when Mission Control closes.
(A new tab isn't used, because Konsole adds tabs to whichever window was used last, which can be hard to find.)

## Stopping agents (and the "orphan" problem)
Select a session in the Agents panel and press `k`. A confirmation dialog asks first; "No" has focus, so Enter
never confirms by accident. The agent gets `SIGTERM`, the polite "please exit" signal.

**Why this exists:** if you close a terminal window while an agent runs **inside a container**, the agent does
**not** quit. Normally closing a terminal sends the program a hang-up signal, but podman's `conmon` process
keeps the container side of the terminal open. The agent keeps running invisibly ("orphaned") until reboot.
Mission Control showed three of these, and the fix was to find them and stop them. The habit to learn: quit
agents with `/quit` (Codex) or `/exit` (Claude) before closing the window.

Safety checks in `stop_agent()`: it re-checks that the process ID still belongs to the same program with the
same start time (process IDs get reused), never stops Mission Control itself, and falls back to sending the
signal from the host if the container isn't allowed to.

## Themes
Press `t` to cycle through the built-in looks. Your choice is saved in `~/.config/mission-control/settings.json`.

| Theme | Look |
|---|---|
| **Neon City** (default) | Cyberpunk: deep purple-black, glowing cyan and electric yellow, hot-pink alerts |
| **CRT Green** | Retro mainframe: green phosphor on black |
| **CRT Amber** | The same retro feel, in amber phosphor |
| **Mission Teal** | The original look |

Textual's own themes (Nord, Dracula, Gruvbox, Tokyo Night, Catppuccin, …) also work via the command
palette (`Ctrl+P` → "Change theme").

**How it works:** the stylesheet only uses theme variables (`$primary`, `$secondary`, `$background`,
`$text-muted`, …), so the layout recolours itself. The coloured text inside the tables is drawn with Rich,
which needs plain `#rrggbb` colours, so `themes.py` turns the active theme into a small `Palette` (muted
text is the foreground blended into the background, because Textual's `auto 60%` isn't a real colour).
Each panel remembers its last data and redraws instantly when the theme changes.

## Known issues
- **Containers panel at startup:** about one start in three, the Containers table first draws its columns
  at header width (`dev   ● run  fedor`). The data is right; the next refresh (within 10 s) draws it
  correctly. Present before the version 2 work; not yet investigated.

## Setup
```bash
# 1. The dev venv (for tests and for running inside dev)
distrobox enter dev
cd ~/Projects/su5-7-llm-agents/mission-control
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
exit

# 2. The host venv (so mc runs on the host). Run on the host, not in dev.
#    Only this project folder changes; nothing is installed into the system.
cd ~/Projects/su5-7-llm-agents/mission-control
python3 -m venv .venv-host
.venv-host/bin/pip install -r requirements.txt
```
Rebuild `.venv-host` (delete it and repeat step 2) when a Bazzite update changes the host's Python;
`mc` warns when it has to fall back to `dev`.

## Who built what
| Part | Built by |
|---|---|
| Project setup | Claude Code |
| App skeleton (layout, panels, keybindings, styling) | Codex (GPT), reviewed by Claude Code |
| Review fixes: Tab shown in footer, cleaner panel backgrounds, header clock | Claude Code |
| Projects panel: live git status, background refresh, unit tests | Claude Code |
| Containers panel: podman via host, start/stop, self-protection, 20 tests | Codex (**GPT-6 Astra**), reviewed by Claude Code |
| Review fixes: panel fit (uptime merged into State), equal column widths, grammar | Claude Code |
| Agents panel + Usage panel, 13 tests | Claude Code (in parallel with the launch actions) |
| Launch actions: Konsole tab via host, safe quoting, 13 tests | Codex (**GPT-6.1 Sol**) in a git worktree, reviewed and merged by Claude Code |
| Orphan investigation, stop-agent key + confirm dialog, launches in new window, 7 tests | Claude Code |
| Theme system: Neon City / CRT Green / CRT Amber / Mission Teal, `t` to cycle, saved choice, 10 tests | Claude Code |
| `mc` launcher, KDE menu entry, install script, script tests | Codex (**GPT-6.1 Sol**), reviewed by Claude Code |
| Review: found that closing the window orphaned the app inside `dev` (pty test); `mc` now runs on the host with a fallback; menu category fix | Claude Code |
| Found that a host update (Python 3.15) broke `mc` on the host; `.venv-host` and launcher order, 3 tests | Claude Code |
| Projects panel for the one-repo portfolio (projects = marked folders + separate repos, changes per folder), agents named by project, fixed a date-dependent usage test, 6 tests | Claude Code (owner chose "real projects only") |

### Agent review notes
- **Codex skeleton:** clean, typed, well-structured code that worked on the first run. It ignored one
  instruction ("don't edit AGENTS.md") and ticked the progress checklist itself. That's harmless, but it
  shows that agent output always needs reviewing.
- **Claude's Projects panel:** the first version added table columns twice in the placeholder panels.
  Textual runs `on_mount` for every class in the inheritance chain itself, so calling `super().on_mount()`
  duplicated the setup. The screenshot check caught it. Fixed with a `populate()` hook.
- **Astra's Containers panel:** followed every rule in the brief (no doc edits, no commits, no real
  container actions). It wrote strong defensive code and 20 tests with all podman calls mocked, and
  kept the safety check in two places (UI and module). The one flaw was layout: 4 columns overflowed
  the narrow side panel. Unit tests can't catch that, only the screenshot check did. Compared with the
  skeleton task, Astra was slower but noticeably more careful than the default model.
- **Parallel work (Sol + Claude):** Codex built the launch actions in a separate **git worktree** on its own
  branch while Claude built two panels on `main`. Codex ran with `-a never -s workspace-write`, so it never
  stopped to ask permission but could only write inside its worktree. Its code was small, correct and
  stayed inside its allowed files. Merging gave one expected conflict (both sides edited the imports in
  `app.py`), resolved by keeping both. Unit tests mock `Popen`, so a final real end-to-end launch with a
  harmless command (`true`) checked the actual path from container to host to Konsole.
