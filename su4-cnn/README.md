# SU4 – Convolutional neural networks

Group project: **Gravity Spy glitch spectrogram classification** (LIGO spectrograms into 22 classes, PyTorch).
The code lives in the group's repo:
[Cavey03/Gravity-Spy-Glitch-Spectrogram-Classification](https://github.com/Cavey03/Gravity-Spy-Glitch-Spectrogram-Classification).
It is included here as a git **submodule** in [`group-repo/`](group-repo/): a pointer to one exact commit of
that repo. On GitHub, click the folder to open it. To get its files when cloning, use
`git clone --recurse-submodules`. To move the pointer to the group's latest work, run
`git submodule update --remote su4-cnn/group-repo` and commit.

**Study summary of the SU4 outcomes:** [`SU4-summary.html`](SU4-summary.html) (download it and open it in a browser;
GitHub shows HTML as code).

What `group-repo/` holds: training and evaluation scripts (`train.py`, `evaluate.py`, `compare.py`),
models, notebooks, outputs, data splits and a `RUNBOOK.md`.

## Checklist
| Item | Status | Where |
|---|---|---|
| Group project report | ✅ | [`ITRI626-Report-GravitySpy.docx`](ITRI626-Report-GravitySpy.docx) (Word; GitHub offers it as a download) |
| Group project presentation slides | ✅ | [`ITRI626-Presentation-GravitySpy.pptx`](ITRI626-Presentation-GravitySpy.pptx) (PowerPoint) |
| All experiments referred to in the report (scripts, programs, notebooks, results, comments) | 🟡 | [`group-repo/`](group-repo/) (submodule); still to map each report experiment to its file |
| Dataset(s) in different stages of cleanup | ✅ | `group-repo/splits/` (train, validation, test, and the blank images removed in cleanup) and `group-repo/data/` (loading, inspection and transforms). The full 3.1 GB Gravity Spy download stays out of git |
| Optional: more experiments not in the report | ❌ | |
| Optional: Trask Chapter 10 – Intro to CNNs | ❌ | |
| Optional: Trask Chapter 11 – Intro to Word Embeddings | ❌ | |

## Learning outcomes
- Application areas of CNNs
- The function of a convolutional layer and of a pooling layer
