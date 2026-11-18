# SU5–7 – Transfer learning, large language models, agents

The main deliverable is **my system that uses a local LLM for agentic workflows**, fully documented.

| Part | What it is |
|---|---|
| [`environment/`](environment/README.md) | The agentic coding environment: Bazzite host, the `dev` container, Claude Code, Codex and Antigravity |
| [`local-llm/`](local-llm/README.md) | Ollama on the RTX 5070, driven by `codex --oss`: install, models, context/GPU tests, coding test |
| [`mission-control/`](mission-control/README.md) | Terminal dashboard for containers, projects and agents (will also show the local LLM) |
| [`../models/`](../models/README.md) | Every model downloaded or tried, and what I learned from it |

## Checklist
| Item | Status | Notes |
|---|---|---|
| Document outlining my learning process (from the "Starting points" in *Update for Study Units 5,6,7.pdf*; each model tried and what I learned) | 🟡 | The facts are in `local-llm` and `models/`; needs writing as a learning story |
| My system which uses a local LLM for agentic workflow(s) (suggested platform: Unsloth) | 🟡 | Ollama + Codex works; still to add a fine-tuned model (Unsloth) and a clear workflow of my own |
| Documentation: design and development | 🟡 | Decisions and install log exist; needs an architecture/design section |
| Documentation: intro video | ❌ | |
| Documentation: usage instructions | 🟡 | Needs one "How to use" section |

## Learning outcomes
| Outcome | Covered? |
|---|---|
| Labelled vs unlabelled data; techniques for unlabelled data | ❌ |
| Clustering on unlabelled data | ❌ |
| Tools that use semi-supervised learning | ❌ |
| Transfer learning to a different domain | ❌ (fine-tuning would cover it) |
| Building blocks and operation of LLMs | 🟡 context window, speculative decoding, sliding-window attention, thinking tokens |
| Using LLMs effectively as they exist | 🟡 Codex with a local model, context sizing, temperature lesson |
| Fine-tuning an LLM to a specific domain | ❌ (Unsloth) |
