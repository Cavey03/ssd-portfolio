# Local LLM – agentic coding on my own GPU

A local large language model (LLM) running on my RTX 5070, used as a coding agent next to Claude Code and
Codex (GPT). Part of my SSD portfolio: [ssd-portfolio](https://github.com/Cavey03/ssd-portfolio).

## Status
🧪 **Planning, nothing installed yet.** This README records every decision and step as the setup happens.

## Why a local model?
- **Fallback:** works offline and when cloud usage limits run out.
- **Team member:** small, routine tasks can go to the local model to save Claude/ChatGPT limits.
- **Privacy:** code never leaves the machine.
- **Portfolio:** a measured comparison of local vs cloud agents on the same tasks.

Honest expectation: a ~12B model on a 12 GB GPU is clearly weaker than Claude or GPT-6 at multi-step
agentic coding. It is good at small, well-defined tasks, explanations and simple scripts.

## Decisions (2026-11-05)
| Question | Decision | Why |
|---|---|---|
| Role | **Team member + fallback** | Saves cloud limits and keeps working offline |
| Agent tool | **Codex CLI with `--oss`** | Already installed and familiar; supports local models through Ollama |
| Model server | **Ollama** | Standard local runner; Codex `--oss` talks to it directly |
| Dashboard | **Show it in Mission Control** | Server running?, loaded model, GPU memory use |

## Hardware (checked 2026-11-05)
| Part | Value | What it means |
|---|---|---|
| GPU | NVIDIA RTX 5070, **12 GB VRAM**, driver 615.78 | The main limit: models of ~9–14B parameters fit fully on the GPU |
| RAM | 31 GB | Bigger models can spill into RAM, but then run much slower |
| Disk | 125 GB free on `/var/home` | Enough for several models (5–15 GB each) |
| Container `dev` | No NVIDIA libraries (created without `--nvidia`) | The model server should run on the host, not in `dev` |

## Model candidates for 12 GB
To be tested; tags must be checked against the Ollama library before pulling.
- **Gemma 4 12B**: the most common recommendation for 12 GB cards (about 8 GB download, leaves room for context).
- **Ornith 9B**: smaller and aimed at agentic coding; more room for a long context.
- **gpt-oss:20b**: Codex `--oss`'s default model, but a 14 GB download, so it won't fully fit in 12 GB of VRAM.
- **Context length matters**: agents send long prompts, so a smaller model that stays fully on the GPU
  often works better than a bigger one that spills into RAM.

## How to install Ollama on Bazzite (options)
Bazzite is an immutable system, so Ollama's official installer, which writes into `/usr` and creates a
system service, does not fit. Bazzite's `ujust` has no Ollama helper.

1. **Ollama release unpacked into `~/.local`, run as a user service** (`systemctl --user`).
   Uses the GPU directly on the host (Ollama ships its own CUDA libraries), changes nothing in the system,
   and is easy to update or remove. Needs a small hand-written systemd unit.
2. **Ollama in a Podman container with GPU access**, managed as a user Quadlet service. This is the approach
   from the Universal Blue forum guide. More isolated, but GPU passthrough on an atomic system is more fiddly.

Codex in `dev` can reach either option at `http://localhost:11434`, because distrobox shares the host's
network.

## Plan
- [ ] Choose the install option and install Ollama
- [ ] Verify Ollama uses the GPU (`ollama ps`, `nvidia-smi`)
- [ ] Pull 2–3 candidate models
- [ ] Connect Codex: `codex --oss -m <model>` (and set `oss_provider` in `~/.codex/config.toml`)
- [ ] Benchmark: the same small coding tasks on each local model vs Sol/Claude (speed, success, quality)
- [ ] Pick a default local model
- [ ] Add rules for delegating to the local model in `~/Projects/CLAUDE.md`
- [ ] Mission Control: show Ollama status, loaded model and GPU memory

## Sources
- [Ollama Linux docs](https://docs.ollama.com/linux.md)
- [Ollama on Bazzite with NVIDIA GPU (Universal Blue forum)](https://universal-blue.discourse.group/t/ollama-on-bazzite-with-nvidia-gpu-support/7042)
- [Non-root Ollama install (GitHub issue #7421)](https://github.com/ollama/ollama/issues/7421)
- [OpenAI Codex with Ollama (Ollama blog)](https://registry.ollama.ai/blog/codex)
- [Best Ollama coding models by VRAM (haimaker)](https://haimaker.ai/blog/ollama-coding-models-by-nvidia-rtx-vram/)
- [Best coding model for 12 GB VRAM (promptquorum)](https://www.promptquorum.com/prompt-bites/best-local-llm-coding-12gb-vram)
- [Best local LLMs for 12 GB VRAM (atomic.chat)](https://atomic.chat/blog/guides/best-local-llm-12gb)

## Who built what
| Part | Built by |
|---|---|
| Research, decisions, this plan | Claude Code (with the owner choosing role, tool and dashboard) |
