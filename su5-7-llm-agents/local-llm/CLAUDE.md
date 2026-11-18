# CLAUDE.md – local-llm

Workspace-wide rules are in `~/Projects/CLAUDE.md`. Claude loads that file too.

## What this is
Setting up and documenting a **local LLM for agentic coding** (Ollama on the RTX 5070, driven by
`codex --oss`), as a team member and fallback next to Claude Code and Codex (GPT).
This is an infrastructure/documentation project: **README.md is the main deliverable.** Record every
command, decision, problem and measurement there as it happens.

## Decided (see README "Decisions")
Role: team member + fallback · Agent: Codex CLI `--oss` · Server: Ollama · Show it in Mission Control.

## Constraints
- Bazzite is immutable: never install into `/usr`. Prefer user-level installs (`~/.local`, `systemctl --user`).
- The `dev` container has no NVIDIA libraries, so run the model server on the **host**. Codex in `dev`
  reaches it at `http://localhost:11434` (shared network).
- 12 GB VRAM: prefer models that fit fully on the GPU, including context.
- Verify model tags and versions against the official Ollama library and docs before using them; web
  guides disagree and go out of date quickly.
- Ask the owner before downloading large models (several GB) or adding services that start automatically.

## Progress
The checklist lives in README.md ("Plan"). Keep it current.
