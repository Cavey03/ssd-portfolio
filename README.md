# ITRI626 Portfolio

My portfolio for **ITRI626**: one folder per study unit, plus a folder for the models I tried.
This page maps the module's portfolio checklist to where each item lives.

## Highlights
- **Mission Control**: a terminal dashboard that is the hub for all my coding agents (Claude Code, Codex and
  a local model): projects, containers, agents, the local LLM and plan usage on one screen
  ([`mission-control/`](su5-7-llm-agents/mission-control/README.md)).
- **An orchestrator for coding agents (Dispatch)**: Opus plans each task and picks a worker (the local model,
  Codex or Claude), the worker runs in its own git worktree, Opus reviews, and I decide what gets merged
  ([design](su5-7-llm-agents/DESIGN.md)).
- **A local LLM on my own GPU**: Ollama on the RTX 5070, driven by Codex as a coding agent
  ([`local-llm/`](su5-7-llm-agents/local-llm/README.md)).
- **Two fine-tuned models (Unsloth)**: a Gemma 4 router trained on my RTX 5070 and the same training on a free
  Colab T4; 63% balanced accuracy against 52% untrained, now suggesting a worker inside Dispatch
  ([write-up](models/router-finetune/README.md)).
- **Text-to-speech**: the intro video is narrated by Kokoro, an open voice model running on the same GPU
  ([video](su5-7-llm-agents/video/out/mission-control-intro.mp4)).

## Layout
```
~/Projects/
├── summary-all.html          every learning outcome on one page (study summary)
├── su1-machine-learning/     SU1  Machine learning (study summary)
├── su2-neural-networks/      SU2  Neural networks – introduction
├── su3-learning-models/      SU3  Learning models – basic applications (Trask notebooks)
├── su4-cnn/                  SU4  Convolutional neural networks (group project)
├── su5-7-llm-agents/         SU5–7  Transfer learning, LLMs, agents
│   ├── environment/          the agentic coding environment on Linux
│   ├── local-llm/            local LLM (Ollama on the RTX 5070) driven by Codex
│   ├── mission-control/      the dashboard and Dispatch (orchestrator and workers)
│   └── video/                the intro video and how it was made
├── models/                   every model downloaded or tried, and the router fine-tune
└── tools/summaries/          generator for the study-summary pages
```

## Study summaries
One page per study unit covers its learning outcomes, summarised from Trask's *Grokking Deep Learning*
with chapter and page references. Anything not in the book (Scikit-Learn, clustering, semi-supervised
learning, LLMs, fine-tuning) is filled in from other sources and hatched as **Not in Trask**. GitHub shows
HTML files as code, so download a page (or clone the repo) and open it in a browser.

| Unit | Page |
|---|---|
| All units | [`summary-all.html`](summary-all.html): every outcome, with search and a unit filter |
| SU1 | [`su1-machine-learning/SU1-summary.html`](su1-machine-learning/SU1-summary.html) |
| SU2 | [`su2-neural-networks/SU2-summary.html`](su2-neural-networks/SU2-summary.html) |
| SU3 | [`su3-learning-models/SU3-summary.html`](su3-learning-models/SU3-summary.html) |
| SU4 | [`su4-cnn/SU4-summary.html`](su4-cnn/SU4-summary.html) |
| SU5–7 | [`su5-7-llm-agents/SU5-7-summary.html`](su5-7-llm-agents/SU5-7-summary.html) |

To change a page, edit `tools/summaries/content.py`, then run `python3 tools/summaries/build.py`.

## Checklist

### SU1 – Machine learning → [`su1-machine-learning/`](su1-machine-learning/)
The outcomes are covered in the [SU1 study summary](su1-machine-learning/SU1-summary.html).

### SU2 – Neural networks: introduction → [`su2-neural-networks/`](su2-neural-networks/)
| Item | Where |
|---|---|
| Assignment submitted on eFundi: simple FF networks explained with creative scenarios | [SISO, MISO, SIMO, MIMO notebooks](su2-neural-networks/README.md) |
| Other Jupyter notebooks tried or learned from | [TreasureSweeper-simple-neural-network](https://github.com/Cavey03/TreasureSweeper-simple-neural-network) |

### SU3 – Learning models: basic applications → [`su3-learning-models/`](su3-learning-models/)
| Item | Where |
|---|---|
| Chapter 3 – Forward Propagation (original + with my comments) | [`su3-learning-models/`](su3-learning-models/README.md) |
| Chapter 4 – Gradient Descent (original + with my comments) | [`su3-learning-models/`](su3-learning-models/README.md) |
| Chapters 5, 6 and 8 (original notebooks) | [`su3-learning-models/`](su3-learning-models/README.md) |

### SU4 – Convolutional neural networks → [`su4-cnn/`](su4-cnn/)
| Item | Where |
|---|---|
| Group project report | [`su4-cnn/ITRI626-Report-GravitySpy.docx`](su4-cnn/ITRI626-Report-GravitySpy.docx) |
| Group project presentation slides | [`su4-cnn/ITRI626-Presentation-GravitySpy.pptx`](su4-cnn/ITRI626-Presentation-GravitySpy.pptx) |
| Experiments (scripts, notebooks, results) | [`su4-cnn/group-repo/`](su4-cnn/README.md) (submodule of [Gravity-Spy-Glitch-Spectrogram-Classification](https://github.com/Cavey03/Gravity-Spy-Glitch-Spectrogram-Classification)) |
| Dataset(s) in different stages of cleanup | [`su4-cnn/group-repo/`](su4-cnn/README.md): `splits/` (train, validation, test, blank-image list) and the `data/` loading and inspection code |

### SU5–7 – Transfer learning, LLMs, agents → [`su5-7-llm-agents/`](su5-7-llm-agents/)
| Item | Where |
|---|---|
| Document outlining my learning process (starting points, each model tried and what I learned) | [`learning-process.md`](su5-7-llm-agents/learning-process.md) (also as [PDF](su5-7-llm-agents/export/learning-process.pdf) and [Word](su5-7-llm-agents/export/learning-process.docx)): starting points, goal, a 17-step learning log, every model tried, concepts, what went wrong, sources |
| My system that uses a local LLM for agentic workflow(s) (suggested: Unsloth) | **Mission Control** with **Dispatch**: Opus routes each task to the local model, Codex or Claude, the worker runs in its own git worktree, Opus reviews, I merge ([how it works](su5-7-llm-agents/mission-control/README.md#dispatch-orchestrator-and-workers), [end-to-end test](su5-7-llm-agents/local-llm/agentic-runs/2026-11-18-dispatch-e2e/README.md)); the local model on Ollama + Codex ([`local-llm`](su5-7-llm-agents/local-llm/README.md)), which also built part of the system ([agentic run](su5-7-llm-agents/local-llm/agentic-runs/2026-11-18-localllm/README.md)); the **Unsloth fine-tune**: a Gemma 4 E2B router trained on my GPU and on a free Colab T4, 63% balanced accuracy vs 52% untrained, shown in Dispatch ([write-up](models/router-finetune/README.md)) |
| System documentation: design and development | [`su5-7-llm-agents/DESIGN.md`](su5-7-llm-agents/DESIGN.md) |
| System documentation: intro video | [`mission-control-intro.mp4`](su5-7-llm-agents/video/out/mission-control-intro.mp4) (3 min: Mission Control, the local model, a real Dispatch run, the fine-tune results; narrated with Kokoro text-to-speech); how it was made: [`VIDEO.md`](su5-7-llm-agents/video/VIDEO.md) |
| System documentation: usage instructions | [`su5-7-llm-agents/USAGE.md`](su5-7-llm-agents/USAGE.md) |

Transfer learning is shown twice: the router fine-tune (a pre-trained language model adapted to routing) and
the SU4 group project's ImageNet-pretrained EfficientNetV2-S.

## Who built what
Each folder's README has its own "Who built what" table. The portfolio restructure (one repo, one folder per
study unit, history of the old repos kept) was done by Claude Code at the owner's request on 2026-11-18.
The study summaries and their generator (`tools/summaries/`) were written by Claude Code on 2026-11-18,
from the owner's copy of Trask's book and an example page the owner supplied for the theme.
