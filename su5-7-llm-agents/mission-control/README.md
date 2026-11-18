# Mission Control

A terminal dashboard (TUI) for my Linux agentic coding setup. From one screen I can:

- see and start/stop my Distrobox containers
- see the git status of every project in `~/Projects`
- see which AI coding agents (Claude Code, Codex, Antigravity) are running, and which run on my **local model**
- see the **local LLM** (Ollama on my RTX 5070): server, models, what's loaded, GPU memory; start/stop it
- launch any agent, including Codex on a local model, in any project with one keypress
- **dispatch** a task: Opus picks the right worker (local model, Codex or Claude) and writes its brief, the
  worker runs unattended in its own git worktree, Opus reviews the result, and I merge or discard it
- see my plan limits (ChatGPT, Claude) and how many tokens my local model processed

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

## How the Local LLM panel works
The local model server is **Ollama**, running on the host as a user service (see
[`../local-llm`](../local-llm/README.md)). `localllm.py` reads it every 10 seconds:

| Line | Source |
|---|---|
| `● Ollama 0.40.14 running` / `○ Ollama stopped` | `GET /api/version` on `127.0.0.1:11434`. No answer = stopped (normal, not an error) |
| GPU bar, used / total GB, % busy | `nvidia-smi --query-gpu=...`. Not Ollama's own numbers: `ollama ps` under-reports `gemma4:12b`, and other programs use the GPU too |
| One row per installed model, with its size | `GET /api/tags` |
| `● loaded · 64K ctx · 100% GPU` | `GET /api/ps`. Below 100% means part of the model spilled into normal RAM (it works, but much slower) |

- **★** marks the default model of the Codex `local` profile (`~/.codex/local.config.toml`).
- **`o`** starts the server (`systemctl --user start ollama`). Stopping asks first, and warns when agent
  sessions are using the local model. The server is never started automatically, so the GPU stays free.
- Inside `dev`, `systemctl --user` and `nvidia-smi` belong to the host, so they go through `distrobox-host-exec`.

## Local agents
- **Detection:** a Codex session runs on the local model when its command line uses the `local` profile
  (`-p local`) or `--oss`. The Agents panel then shows `● codex · ornith-1.5:9b` (the model from `-m`, or the
  profile's default), and the panel label counts them (`codex 2 (1 local)`).
- **Key `4`** opens Codex on the model selected in the Local LLM panel (`codex -p local -m <model>`) in the
  project selected in the Projects panel. If Ollama isn't running, it says so instead.

## Usage panel: the Local row
The local model has no plan limits, so the panel shows how much work it did instead: tokens processed today
and in the last 7 days, and in how many sessions. It reads the Codex session logs whose first line says
`model_provider: "ollama"` and takes the last running total (`total_token_usage`) of each. A log is only read
again when it changes, so the 60-second refresh stays instant. These are tokens that didn't use cloud limits.

Local sessions also write an *empty* plan-limit entry to their logs. The ChatGPT row skips those, otherwise a
local run would hide the real ChatGPT limits ("unknown").

## Dispatch: orchestrator and workers
```
 you ──d──▶ Dispatch dialog ── task text ──▶ Opus (claude -p, no tools, JSON schema)
                 ▲                              │ plan: worker, model, why, brief, time limit
                 └──── confirm or change ◀──────┘                           │
                                                                            ▼ logged in decisions.jsonl
 Tasks panel ◀── task.json ◀── supervisor (detached process) ──────────────────┐
   v view                         1. git worktree + branch task/<id>          │
   m merge (asks first)           2. worker in dev, with a time limit:        │
   x discard (asks first)            local: codex exec -p local -m <model>    │
                                     codex: codex exec                        │
                                     claude: claude -p --permission-mode acceptEdits
                                  3. changes (files, diff) from the worktree  │
                                  4. review by Opus: approve / changes / reject
```
**Life of a task:** `planned → running → done | timeout | failed → merged | discarded`. Each task is a folder
in `~/.local/state/mission-control/tasks/<id>/` with `task.json`, `worker.log`, `diff.patch` and the worker's
last message. The supervisor is a separate process, so tasks keep running when Mission Control is closed,
and the Tasks panel picks them up again on the next start.

**How Opus chooses** (`orchestrator.py`, `ROUTING_RULES`): the cheapest worker that will very likely succeed.
- **local**: only small, single-step, well-specified tasks (1–2 files), only when Ollama is running,
  10-minute limit, and a short concrete brief ending in "write the change first, then test, then fix".
  These rules come from measurements: the local 9B model looped on a large task but did small ones in about
  a minute ([agentic runs](../local-llm/agentic-runs/)).
- **codex** (GPT): well-specified multi-file work. **claude**: ambiguous or design-heavy work.
- The plan is checked before use: the local model can't be chosen while Ollama is off, and an unknown model
  falls back to the default.

**The local router:** next to Opus's plan, the Dispatch dialog shows the suggestion of `router-rtx5070`, a small
model I fine-tuned with Unsloth to route tasks ([write-up](../../models/router-finetune/README.md)). It answers in
about 0.05 s, for free and offline. If Opus can't be reached, its choice is preselected, and every decision log
entry records it, so its agreement with Opus can be measured over time. Set `MISSION_CONTROL_ROUTER` to use
another router model.

**You stay in control:** nothing starts until you press Start (you can change the worker; Opus's brief is
kept), and nothing is merged until you confirm `m`. If Opus can't be reached, choose a worker yourself and
the task text becomes the brief.

**Safety:**
- Every worker works in its own git worktree under `~/Projects/.worktrees/`, never in the main checkout.
  Codex workers run with `-s workspace-write` (they can only write inside it); Claude workers may edit files
  and run only the unit tests and `git status`/`git diff`.
- Every worker has a time limit (`timeout`), and the supervisor kills it 60 s after that if needed.
- Workers run with `PYTHONDONTWRITEBYTECODE=1`, so running tests leaves no `.pyc` files in the diff.
- A worktree starts from the last **commit**: uncommitted changes in the main checkout aren't in it.
- Merging commits the worktree as `Task <id>: <title>` (no AI names in commit messages, see the portfolio
  rules) and merges with `--no-ff`. On a conflict the merge is aborted and the main checkout is left as it was.
- `decisions.jsonl` records every plan, whether I changed it, and the local router's suggestion. It's for
  transparency and for measuring the router against Opus, not training data: the providers' terms restrict using their output to build competing models.

**Limits:** Opus reviews the diff and the worker's log; it doesn't run the tests itself. A worktree has no
`.venv` (it's gitignored), so the brief tells the worker to use the main checkout's `.venv`.

### From the command line
`mc task` does the same without the dashboard (for scripts, or for another agent acting as orchestrator):
```bash
mc task start "add a --version option to mc"          # Opus plans, you confirm, it runs
mc task start "fix the typo in README" --agent local  # skip planning, choose the worker yourself
mc task list                                          # recent tasks with status and review
mc task show <id>       mc task diff <id>
mc task merge <id>      mc task discard <id>
```
The project is the folder you run `mc task` in (or `--project`).

## Launching agents
Select a project and press `1` (Claude), `2` (Codex), `3` (Antigravity) or `4` (Codex on the local model). A **new Konsole window** opens in
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
| `localllm.py` parse functions + 15 tests | **Local model `ornith-1.5:9b`** via `codex exec -p local` in a worktree (2nd attempt; 1st looped), reviewed by Claude Code: fixed one bug (`self.` missing) and two broken test samples. [Write-up](../local-llm/agentic-runs/2026-11-18-localllm/README.md) |
| Local LLM panel, `localllm.py` server/GPU/service functions, local-agent detection, keys `4` and `o`, Usage fix for local sessions, 24 tests | Claude Code |
| `worktrees.py` (git layer of Dispatch) + 27 tests | **Codex (`gpt-6.1-sol`)** in a worktree, 3 min, accepted unchanged after review. [Comparison with the local model](../local-llm/agentic-runs/2026-11-18-worktrees-gpt/README.md) |
| Dispatch: orchestrator (Opus planning + review), task store and supervisor, `mc task` CLI, Dispatch dialog, Tasks panel, task view, 25 tests; Usage panel Local row, 4 tests | Claude Code (owner allowed GPT for Phases 3–4) |
| Local router in Dispatch (`router.py`: suggestion, fallback, logging), 4 tests | Claude Code |
| End-to-end test of Dispatch with the local model; fixes it found (`.pyc` files, commit messages) | Claude Code. [Evidence](../local-llm/agentic-runs/2026-11-18-dispatch-e2e/README.md) |
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
