# ITRI626 Portfolio

My portfolio for **ITRI626**: one folder per study unit, plus a folder for the models I tried.
This page maps every item on the module's portfolio checklist to where it lives.

Legend: ✅ done · 🟡 partly done · ❌ not yet · ➖ optional

## Layout
```
~/Projects/
├── summary-all.html          every learning outcome on one page (study summary)
├── su1-machine-learning/     SU1  Machine learning (summary only; no deliverable)
├── su2-neural-networks/      SU2  Neural networks – introduction
├── su3-learning-models/      SU3  Learning models – basic applications (Trask notebooks)
├── su4-cnn/                  SU4  Convolutional neural networks (group project)
├── su5-7-llm-agents/         SU5–7  Transfer learning, LLMs, agents
│   ├── environment/          the agentic coding environment on Linux
│   ├── local-llm/            local LLM (Ollama on the RTX 5070) driven by Codex
│   └── mission-control/      terminal dashboard for containers, projects and agents
├── models/                   every model downloaded or tried, and what I learned from it
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
No deliverable. The outcomes are covered in the [SU1 study summary](su1-machine-learning/SU1-summary.html).

### SU2 – Neural networks: introduction → [`su2-neural-networks/`](su2-neural-networks/)
| Item | Status | Where |
|---|---|---|
| Assignment submitted on eFundi: simple FF networks explained with creative scenarios | ✅ | [SISO, MISO, SIMO, MIMO notebooks](su2-neural-networks/README.md) |
| ➖ Other Jupyter notebooks tried or learned from | 🟡 | [TreasureSweeper-simple-neural-network](https://github.com/Cavey03/TreasureSweeper-simple-neural-network) |

### SU3 – Learning models: basic applications → [`su3-learning-models/`](su3-learning-models/)
| Item | Status | Where |
|---|---|---|
| Chapter 3 – Forward Propagation (original + with my comments) | ✅ | [`su3-learning-models/`](su3-learning-models/README.md) |
| Chapter 4 – Gradient Descent (original + with my comments) | ✅ | [`su3-learning-models/`](su3-learning-models/README.md) |
| ➖ Chapters 5, 6, 8, 9 and other notebooks | 🟡 Ch 5, 6, 8 originals added, comments to do | [`su3-learning-models/`](su3-learning-models/README.md) |

### SU4 – Convolutional neural networks → [`su4-cnn/`](su4-cnn/)
| Item | Status | Where |
|---|---|---|
| Group project report | ❌ | |
| Group project presentation slides | ❌ | |
| All experiments in the report (scripts, notebooks, results, comments) | 🟡 | [`su4-cnn/group-repo/`](su4-cnn/README.md) (submodule of [Gravity-Spy-Glitch-Spectrogram-Classification](https://github.com/Cavey03/Gravity-Spy-Glitch-Spectrogram-Classification)) |
| Dataset(s) in different stages of cleanup | ✅ | [`su4-cnn/group-repo/`](su4-cnn/README.md): `splits/` (train, validation, test, blank-image list) and the `data/` loading and inspection code |
| ➖ More experiments, Trask Chapters 10 and 11 | ❌ | |

### SU5–7 – Transfer learning, LLMs, agents → [`su5-7-llm-agents/`](su5-7-llm-agents/)
| Item | Status | Where |
|---|---|---|
| Document outlining my learning process (from the "Starting points", each model tried and what I learned) | 🟡 | template: [`learning-process.md`](su5-7-llm-agents/learning-process.md); facts recorded in [`local-llm`](su5-7-llm-agents/local-llm/README.md) and [`models/`](models/) |
| My system that uses a local LLM for agentic workflow(s) (suggested: Unsloth) | 🟡 | Ollama + Codex works ([`local-llm`](su5-7-llm-agents/local-llm/README.md)); Mission Control shows and launches the local model; the local model built part of it ([agentic run](su5-7-llm-agents/local-llm/agentic-runs/2026-11-18-localllm/README.md)); Dispatch and fine-tune to do |
| System documentation: design and development | 🟡 | decisions and install log exist; no design section yet |
| System documentation: intro video | ❌ | |
| System documentation: usage instructions | 🟡 | commands exist, spread through the log |

## Learning outcomes still to cover (SU5–7)
All of these are explained in the [SU5–7 study summary](su5-7-llm-agents/SU5-7-summary.html). What's still
missing is hands-on evidence:
- Fine-tuning an LLM to a specific domain (Unsloth). Transfer learning is shown by the SU4 group project's
  ImageNet-pretrained EfficientNetV2-S.
- Running clustering and a semi-supervised tool on real data (the summary has ready-to-run Scikit-Learn code)
- Building blocks of LLMs (partly covered: context window, speculative decoding, sliding-window attention)

## Who built what
Each folder's README has its own "Who built what" table. The portfolio restructure (one repo, one folder per
study unit, history of the old repos kept) was done by Claude Code at the owner's request on 2026-11-18.
The study summaries and their generator (`tools/summaries/`) were written by Claude Code on 2026-11-18,
from the owner's copy of Trask's book and an example page the owner supplied for the theme.
