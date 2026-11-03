# CLAUDE.md

SSD portfolio assignment: setting up and documenting an agentic coding environment on Linux.
The owner is new to Linux and agentic coding, so explain commands briefly as you go.

## Environment
- Host: Bazzite 44, an immutable Fedora with KDE. The system is read-only, so don't install tools on the host.
- Tools live in the Distrobox container `dev`. Enter it with `distrobox enter dev`.
- `claude` and `agy` are in `~/.local/bin` and work both on the host and in `dev`. `codex`, `node`, `npm` and `gh` are only in `dev`.
- GitHub auth is set up inside `dev`, so run `git push` and `gh` from there.
- Remote: private repo `Cavey03/ssd-portfolio`.

## Rules
- Do NOT add `Co-Authored-By: Claude` or any other AI attribution to commit messages.
- Keep `README.md` up to date with every setup change and every problem solved. It is the portfolio write-up.
