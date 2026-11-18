# SU5–7 – Transfer learning, large language models, agents

The main deliverable is **my system that uses a local LLM for agentic workflows**, fully documented.

**Start here:** [`DESIGN.md`](DESIGN.md) (how the system is designed and was built) ·
[`USAGE.md`](USAGE.md) (how to use it) · [`learning-process.md`](learning-process.md) (what I learned).

| Part | What it is |
|---|---|
| [`environment/`](environment/README.md) | The agentic coding environment: Bazzite host, the `dev` container, Claude Code, Codex and Antigravity |
| [`local-llm/`](local-llm/README.md) | Ollama on the RTX 5070, driven by `codex --oss`: install, models, context/GPU tests, coding test |
| [`mission-control/`](mission-control/README.md) | The hub: dashboard for containers, projects, agents, the local LLM and usage, plus Dispatch (Opus routes tasks to the local model, Codex or Claude) |
| [`../models/`](../models/README.md) | Every model downloaded or tried, and what I learned from it |
| [`SU5-7-summary.html`](SU5-7-summary.html) | Study summary of the SU5–7 outcomes (download it and open it in a browser) |

## Checklist
| Item | Status | Notes |
|---|---|---|
| Document outlining my learning process (starting points, each model tried and what I learned) | ✅ | [`learning-process.md`](learning-process.md): starting points, goal, a 17-step learning log, models tried, concepts, what went wrong, sources |
| My system which uses a local LLM for agentic workflow(s) (suggested platform: Unsloth) | ✅ | Built: Mission Control + Dispatch with the local model as a worker ([DESIGN](DESIGN.md)); a router fine-tuned with Unsloth on my GPU, suggesting a worker in Dispatch, and reproduced on a free Colab T4 ([write-up](../models/router-finetune/README.md)) |
| Documentation: design and development | ✅ | [`DESIGN.md`](DESIGN.md): requirements, architecture, Dispatch, decisions, how it was built and tested, limitations |
| Documentation: intro video | ✅ | [`video/out/mission-control-intro.mp4`](video/out/mission-control-intro.mp4); how it was made: [`video/VIDEO.md`](video/VIDEO.md) |
| Documentation: usage instructions | ✅ | [`USAGE.md`](USAGE.md): setup, keys, local model, Dispatch, command line, troubleshooting |

## Learning outcomes
| Outcome | Covered? |
|---|---|
| Labelled vs unlabelled data; techniques for unlabelled data | ❌ |
| Clustering on unlabelled data | ❌ |
| Tools that use semi-supervised learning | ❌ |
| Transfer learning to a different domain | ✅ [router fine-tune](../models/router-finetune/README.md): a pre-trained Gemma 4 E2B adapted to routing coding tasks with ~300 examples (also SU4's ImageNet-pretrained CNN) |
| Building blocks and operation of LLMs | 🟡 context window, speculative decoding, sliding-window attention, thinking tokens |
| Using LLMs effectively as they exist | ✅ Codex with a local model, context sizing, temperature lesson, orchestrator–workers routing, measured local vs cloud agents ([runs](local-llm/agentic-runs/)) |
| Fine-tuning an LLM to a specific domain | ✅ QLoRA with Unsloth: 52% → 63% balanced accuracy on unseen tasks ([write-up](../models/router-finetune/README.md)) |
