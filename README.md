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
```bash
distrobox enter dev
cd ~/Projects/mission-control
.venv/bin/python -m mission_control
```

## Tests
```bash
.venv/bin/python -m unittest -v
```

## How the Projects panel works
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

## Setup
```bash
distrobox enter dev
cd ~/Projects/mission-control
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

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
