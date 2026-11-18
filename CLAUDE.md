# CLAUDE.md – portfolio root (applies to everything in ~/Projects)

The owner is new to Linux and agentic coding, so explain commands briefly as you go.

## What this is
`~/Projects` is **one git repo**: the owner's portfolio for module **ITRI626** (private GitHub repo
`Cavey03/ssd-portfolio`; "SSD portfolio" and "ITRI626 portfolio" mean the same thing).
It has one folder per study unit plus a `models/` folder. The root `README.md` maps every item on the
ITRI626 checklist to where it lives. Keep that mapping current: it is how the portfolio gets marked.

## Layout
| Folder | What it holds |
|---|---|
| `su2-neural-networks/` | SU2: simple feed-forward networks (eFundi assignment) |
| `su3-learning-models/` | SU3: Trask notebooks, original and with the owner's comments |
| `su4-cnn/` | SU4: CNN group project (report, slides, experiments, datasets) |
| `su5-7-llm-agents/` | SU5–7: the local-LLM agentic system and everything around it |
| `su5-7-llm-agents/environment/` | Write-up of the agentic coding environment (Bazzite, `dev`, the agents) |
| `su5-7-llm-agents/local-llm/` | Ollama + `codex --oss` on the RTX 5070: setup, tests, benchmark |
| `su5-7-llm-agents/mission-control/` | Terminal dashboard (Python + Textual) for containers, projects and agents |
| `models/` | One note per model downloaded or tried; Modelfiles and fine-tuning scripts. **No weights in git.** |
| `particle-sim/` | GPU particle simulator. **Still its own repo** (gitignored here) until its Codex worktree work is done; then it moves into `su5-7-llm-agents/` with its history. |

Each subproject keeps its own `CLAUDE.md` / `AGENTS.md`, which apply on top of this file.
Project ideas are in `~/Desktop/project-ideas.txt`.

## Environment
- Host: Bazzite 44, an immutable Fedora with KDE. The system is read-only, so don't install tools on the host.
- Tools live in the Distrobox container `dev`. Enter it with `distrobox enter dev`.
- `claude` and `agy` are in `~/.local/bin` and work both on the host and in `dev`. `codex`, `node`, `npm`, `gh` and `python3` (3.14) are in `dev`.
- GitHub (account `Cavey03`) is authenticated inside `dev`, so run `git push` and `gh` from there.
- Python projects use a `.venv` in their own folder, created inside `dev` (gitignored).

## Rules
- Do NOT add `Co-Authored-By: Claude` or any other AI attribution to commit messages.
- Keep the root `README.md` checklist and each folder's `README.md` up to date. The READMEs are the portfolio evidence.
- Never commit model weights (`.gguf`, `.safetensors`, Ollama blobs) or datasets bigger than a few MB; GitHub
  rejects files over 100 MB. Document where they live instead.
- The old separate GitHub repos (`local-llm`, `mission-control`) are left untouched; don't archive or delete
  them without asking.

## Delegating to other agents (Codex / Antigravity)
Claude may hand tasks to the other agents, but **ask the owner first, every time**. Say which agent, what
task, and which folder, and wait for a yes.
- **Prefer Codex (GPT).** Use Antigravity only when asked or for a second opinion.
- Codex: `distrobox enter dev -- bash -c 'cd <folder> && codex exec "<task>"'`
- Antigravity: `agy -p "<task>"`, run from the folder.
- Review their changes with `git diff` before committing, and log in the folder's README which agent built what.
