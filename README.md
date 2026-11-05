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

## First test (2026-11-05)

### Context length vs GPU fit
Each model was loaded with growing `num_ctx` and the server log was checked for how many layers landed on
the GPU (`load_tensors: offloaded X/Y layers to GPU`). VRAM numbers from `nvidia-smi` include ~1 GB used by
the desktop.

| Context (tokens) | `gemma4:12b` layers on GPU | VRAM | `ornith-1.5:9b` layers on GPU | VRAM |
|---|---|---|---|---|
| 8K | 49/49 | 10.1 GB | 33/33 | 7.6 GB |
| 16K | 49/49 | 10.3 GB | 33/33 | 7.9 GB |
| 32K | 49/49 | 10.2 GB | 33/33 | 8.3 GB |
| 64K | 49/49 | 10.7 GB | 33/33 | 9.3 GB |
| 128K | **47/49** (spills to RAM) | 11.6 GB | **30/33** (spills to RAM) | 11.0 GB |

**Both models stay fully on the GPU up to 64K context.** That is the ceiling to use for Codex.

What the log showed along the way:
- `gemma4:12b` is really **two models**: the 12B main model (49 layers, 7.0 GB) plus a small "Assistant"
  draft model (5 layers, 0.4 GB) for speculative decoding: the draft guesses tokens ahead and the big model
  checks them. That is why the 12B model is *faster* than the 9B one (172 vs 103 tokens/s).
- `ollama ps` (and `/api/ps`) shows gemma as only ~1.2–1.5 GB: it appears to report the draft model only.
  **Trust `nvidia-smi` and the server log for gemma, not `ollama ps`.** (Matters for Mission Control.)
- Gemma uses sliding-window attention: only 8 of its layers keep the full context, so its memory grows very
  little with context. Ornith's grows faster (+1 GB from 32K to 64K).

### Coding test
`bench/coding_test.py`: 5 small Python tasks (Roman numerals, merge intervals, parse a duration string with
error handling, fix a buggy binary search, top-k word count). The model's code is run against hidden
asserts in a separate process. Thinking off and on, 32K context, each model's default temperature.

```bash
NUM_CTX=32768 python3 -I bench/coding_test.py            # both models, thinking off and on
```

| Model | Thinking off | Thinking on |
|---|---|---|
| `gemma4:12b` | 4/5 passed, 12 s total | **5/5 passed**, 91 s total |
| `ornith-1.5:9b` | 3/5 passed, 11 s total | **5/5 passed**, 83 s total |

- Without thinking, both are near-instant (~1–6 s per task) but make careless mistakes (gemma: Roman
  numerals; ornith: duration parsing and the word counter).
- With thinking, both solve everything, at the cost of 2–50 s per task (up to ~6,600 thinking tokens).
- **Problem found: temperature 0 makes gemma loop.** My first run used `temperature 0` (always pick the most
  likely word, for repeatable results). Gemma then failed 2 tasks with thinking on: it filled the *entire*
  context (8K, and again 32K) with thinking and never wrote code. Its thinking ended in
  `Wait, I'm repeating myself again.`, repeated. With the model's default temperature it finished normally.
  **Lesson: don't force temperature 0 on thinking models.**
- Only 5 tasks, one run each, with non-zero temperature, so results vary between runs. This is a first
  sanity check, not the benchmark; that comes after connecting Codex.

## Plan
- [x] Choose the install option and install Ollama (option 1, v0.40.14)
- [x] Verify Ollama uses the GPU (`ollama ps`, `nvidia-smi`): both models 100% GPU
- [x] Pull 2–3 candidate models (`gemma4:12b`, `ornith-1.5:9b`; a third later if needed)
- [x] Raise the context length and check the models still fit fully on the GPU: both fit up to 64K
- [x] First coding sanity test (`bench/coding_test.py`): both 5/5 with thinking on
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
| Context/GPU-fit test, `bench/coding_test.py` and first coding test | Claude Code (owner asked to test the models) |
