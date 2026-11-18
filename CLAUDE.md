# CLAUDE.md – workspace-wide (applies to every project in ~/Projects)

The owner is new to Linux and agentic coding, so explain commands briefly as you go.
These projects are part of an SSD portfolio.

## Environment
- Host: Bazzite 44, an immutable Fedora with KDE. The system is read-only, so don't install tools on the host.
- Tools live in the Distrobox container `dev`. Enter it with `distrobox enter dev`.
- `claude` and `agy` are in `~/.local/bin` and work both on the host and in `dev`. `codex`, `node`, `npm`, `gh` and `python3` (3.14) are in `dev`.
- GitHub (account `Cavey03`) is authenticated inside `dev`, so run `git push` and `gh` from there.
- Each project gets its own folder here, its own git repo, and its own **private** GitHub repo.
- Python projects use a `.venv` in the project folder, created inside `dev`.

## Projects
| Folder | What it is | GitHub |
|---|---|---|
| `ssd-portfolio/` | The portfolio write-up of the environment setup | Cavey03/ssd-portfolio |
| `mission-control/` | Terminal dashboard (Python + Textual) for containers, projects and agents | Cavey03/mission-control |
| `particle-sim/` | GPU particle simulator (WebGPU + TypeScript, galaxy mode first) | Cavey03/particle-sim |
| `local-llm/` | Local LLM for agentic coding (Ollama + `codex --oss`), setup documentation | Cavey03/local-llm |

Keep this table up to date when projects are added. Project ideas are in `~/Desktop/project-ideas.txt`.

## Rules
- Do NOT add `Co-Authored-By: Claude` or any other AI attribution to commit messages.
- Keep each project's `README.md` up to date. The READMEs are the portfolio evidence.

## Delegating to other agents (Codex / Antigravity)
Claude may hand tasks to the other agents, but **ask the owner first, every time**. Say which agent, what
task, and which folder, and wait for a yes.
- **Prefer Codex (GPT).** Use Antigravity only when asked or for a second opinion.
- Codex: `distrobox enter dev -- bash -c 'cd <project> && codex exec "<task>"'`
- Antigravity: `agy -p "<task>"`, run from the project folder.
- Review their changes with `git diff` before committing, and log in the project README which agent built what.
