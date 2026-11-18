# ITRI626 Portfolio

My portfolio for **ITRI626**: one folder per study unit, plus a folder for the models I tried.
This page maps every item on the module's portfolio checklist to where it lives.

Legend: ✅ done · 🟡 partly done · ❌ not yet · ➖ optional

## Layout
```
~/Projects/
├── su2-neural-networks/      SU2  Neural networks – introduction
├── su3-learning-models/      SU3  Learning models – basic applications (Trask notebooks)
├── su4-cnn/                  SU4  Convolutional neural networks (group project)
├── su5-7-llm-agents/         SU5–7  Transfer learning, LLMs, agents
│   ├── environment/          the agentic coding environment on Linux
│   ├── local-llm/            local LLM (Ollama on the RTX 5070) driven by Codex
│   └── mission-control/      terminal dashboard for containers, projects and agents
└── models/                   every model downloaded or tried, and what I learned from it
```

## Checklist

### SU2 – Neural networks: introduction → [`su2-neural-networks/`](su2-neural-networks/)
| Item | Status | Where |
|---|---|---|
| Assignment submitted on eFundi: simple FF networks explained with creative scenarios | ✅ | [SISO, MISO, SIMO, MIMO notebooks](su2-neural-networks/README.md) |
| ➖ Other Jupyter notebooks tried or learned from | 🟡 | [TreasureSweeper-simple-neural-network](https://github.com/Cavey03/TreasureSweeper-simple-neural-network) |

### SU3 – Learning models: basic applications → [`su3-learning-models/`](su3-learning-models/)
| Item | Status | Where |
|---|---|---|
| Chapter 3 – Forward Propagation (original + with my comments) | 🟡 original added, comments to do | [`su3-learning-models/`](su3-learning-models/README.md) |
| Chapter 4 – Gradient Descent (original + with my comments) | 🟡 original added, comments to do | [`su3-learning-models/`](su3-learning-models/README.md) |
| ➖ Chapters 5, 6, 8, 9 and other notebooks | ❌ | |

### SU4 – Convolutional neural networks → [`su4-cnn/`](su4-cnn/)
| Item | Status | Where |
|---|---|---|
| Group project report | ❌ | |
| Group project presentation slides | ❌ | |
| All experiments in the report (scripts, notebooks, results, comments) | 🟡 | [`su4-cnn/group-repo/`](su4-cnn/README.md) (submodule of [Gravity-Spy-Glitch-Spectrogram-Classification](https://github.com/Cavey03/Gravity-Spy-Glitch-Spectrogram-Classification)) |
| Dataset(s) in different stages of cleanup | ❌ | |
| ➖ More experiments, Trask Chapters 10 and 11 | ❌ | |

### SU5–7 – Transfer learning, LLMs, agents → [`su5-7-llm-agents/`](su5-7-llm-agents/)
| Item | Status | Where |
|---|---|---|
| Document outlining my learning process (from the "Starting points", each model tried and what I learned) | 🟡 | facts recorded in [`local-llm`](su5-7-llm-agents/local-llm/README.md) and [`models/`](models/); still to be written up as a learning story |
| My system that uses a local LLM for agentic workflow(s) (suggested: Unsloth) | 🟡 | Ollama + Codex works ([`local-llm`](su5-7-llm-agents/local-llm/README.md)); no fine-tuned model or own workflow yet |
| System documentation: design and development | 🟡 | decisions and install log exist; no design section yet |
| System documentation: intro video | ❌ | |
| System documentation: usage instructions | 🟡 | commands exist, spread through the log |

## Learning outcomes still to cover (SU5–7)
- Fine-tuning an LLM to a specific domain, and transfer learning (the reason Unsloth is suggested)
- Labelled vs unlabelled data, clustering, semi-supervised tools
- Building blocks of LLMs (partly covered: context window, speculative decoding, sliding-window attention)

## Who built what
Each folder's README has its own "Who built what" table. The portfolio restructure (one repo, one folder per
study unit, history of the old repos kept) was done by Claude Code at the owner's request on 2026-11-18.
