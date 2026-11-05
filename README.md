# Local LLM – agentic coding on my own GPU

A local large language model (LLM) running on my RTX 5070, used as a coding agent next to Claude Code and
Codex (GPT). Part of my SSD portfolio: [ssd-portfolio](https://github.com/Cavey03/ssd-portfolio).

## Status
🔧 **Ollama v0.40.14 running on the GPU with two models (`gemma4:12b`, `ornith-1.5:9b`).** This README records every
decision and step as the setup happens.

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

**Chosen: option 1** (2026-11-05). Simplest, no GPU passthrough, nothing touches the system.

## Install log (2026-11-05)
Ollama **v0.40.14** (released 2026-11-03), file `ollama-linux-amd64.tar.zst` (1.45 GB download, 2.3 GB
unpacked; it bundles its own CUDA 12 and 13 libraries, so nothing NVIDIA-related needs installing).

```bash
# 1. Download from the official GitHub release, plus the checksum list
B=https://github.com/ollama/ollama/releases/download/v0.40.14
curl -fL -o ollama-linux-amd64.tar.zst $B/ollama-linux-amd64.tar.zst
curl -fsSL -o sha256sum.txt $B/sha256sum.txt

# 2. Verify the download is intact (prints "OK"). Entries are written as "./name".
grep ' ./ollama-linux-amd64.tar.zst$' sha256sum.txt | sha256sum -c -

# 3. Unpack into ~/.local instead of /usr (no sudo): gives ~/.local/bin/ollama + ~/.local/lib/ollama
tar --zstd -xf ollama-linux-amd64.tar.zst -C ~/.local
```

The official docs unpack into `/usr` with `sudo`, which is read-only on Bazzite. Ollama finds its
libraries relative to its own binary (`../lib/ollama`), so the same layout under `~/.local` just works,
and `~/.local/bin` is already on `PATH`.

**User service** `~/.config/systemd/user/ollama.service` (instead of the docs' system service and
dedicated `ollama` user):

```ini
[Unit]
Description=Ollama model server (user)
After=network-online.target

[Service]
ExecStart=%h/.local/bin/ollama serve
Environment="OLLAMA_HOST=127.0.0.1:11434"
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
```

- `OLLAMA_HOST=127.0.0.1` keeps the server private to this machine (the `dev` container shares the host
  network, so it still reaches it).
- Models are stored in `~/.ollama/models` (the default when Ollama runs as my user).
- **Not started automatically** (decision): it is started by hand, so the GPU stays free for other work.

```bash
systemctl --user daemon-reload       # make systemd read the new unit file
systemctl --user start ollama        # start the server (stop: systemctl --user stop ollama)
systemctl --user status ollama       # is it running?
journalctl --user -u ollama -f       # follow the server log
# Autostart at login, if wanted later: systemctl --user enable ollama
```

**Verified:**
| Check | Result |
|---|---|
| `curl http://127.0.0.1:11434/api/version` (host) | `{"version":"0.40.14"}` |
| Same from inside `dev` (`localhost:11434`) | `{"version":"0.40.14"}` |
| Server log, GPU discovery | `inference compute ... library=CUDA compute=12.0 description="NVIDIA GeForce RTX 5070" libdirs=ollama,cuda_v13 driver=13.4` |

**Problem hit:** my first checksum check failed with `no properly formatted checksum lines found`. The
download was fine; `sha256sum.txt` lists files as `./name`, and my `grep` pattern missed the `./`.

**Update:** stop the service, `rm -rf ~/.local/lib/ollama` (old libraries must not mix with new ones),
unpack the new release the same way, start again.
**Uninstall:** `systemctl --user stop ollama`, then
`rm -rf ~/.local/bin/ollama ~/.local/lib/ollama ~/.config/systemd/user/ollama.service` and
`systemctl --user daemon-reload`. Models are in `~/.ollama` (delete separately if wanted).

## Models pulled (2026-11-05)
Tags checked against the official Ollama library first. Started with two, as decided with the owner.

| Tag | Download | Why this tag |
|---|---|---|
| `gemma4:12b` | 8.0 GB | Plain `12b` tag; its ID `6114515d63c1` is the same as `gemma4:12b-it-q4_K_M`, so it is **Q4_K_M**. (`gemma4:latest` is the smaller E4B model, not the 12B.) |
| `ornith-1.5:9b` | 6.6 GB | Ornith has two official lines: `ornith:9b` (1.0, 4 months old) and `ornith-1.5` (updated 2 weeks ago, adds image input). Chose the newer 1.5. |

```bash
ollama pull gemma4:12b
ollama pull ornith-1.5:9b
ollama list
```

**First check (one short prompt each, thinking off, via `/api/generate`):**

| Model | `ollama ps` | VRAM in use (`nvidia-smi`, incl. ~1 GB desktop) | Load time | Output speed |
|---|---|---|---|---|
| `gemma4:12b` | 100% GPU | 9.7 GB / 12 GB | 3.9 s | 172 tokens/s |
| `ornith-1.5:9b` | 100% GPU | 7.4 GB / 12 GB | 2.9 s | 103 tokens/s |

One run each, only a sanity check; the real comparison is the benchmark step.

**Found:** Ollama loads models with a **4096-token context** by default (the `CONTEXT` column of
`ollama ps`). That is far too small for an agent like Codex, which sends long prompts. It has to be raised
(for example `OLLAMA_CONTEXT_LENGTH` in the service, or per model) when connecting Codex, while watching that
the model still fits 100% on the GPU. Gemma 4 12B has only ~2.5 GB of VRAM headroom left for that.

## Plan
- [x] Choose the install option and install Ollama (option 1, v0.40.14)
- [x] Verify Ollama uses the GPU (`ollama ps`, `nvidia-smi`): both models 100% GPU
- [x] Pull 2–3 candidate models (`gemma4:12b`, `ornith-1.5:9b`; a third later if needed)
- [ ] Raise the context length and check the models still fit fully on the GPU
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
| Ollama install (option 1), user service, install log | Claude Code (owner approved download and manual start) |
| Model tag check, pulls, first GPU/speed check | Claude Code (owner approved pulling two models) |
