# Router fine-tune: teaching a small local model to route coding tasks

ITRI626 SU5–7 · checklist: *"your system which uses a local LLM for agentic workflow(s) (suggested platform:
Unsloth)"* and the outcomes *transfer learning to a different domain* and *fine-tuning an LLM to a domain*.

**Goal:** Mission Control's Dispatch asks Opus (cloud) which worker should do a task: `local` (my 9B model),
`codex` (GPT) or `claude`. A small model that I fine-tune can make that routing decision itself: free,
offline, private, and in a fraction of a second. **Base model:** Gemma 4 E2B (about 2B effective parameters).
**Tool:** [Unsloth](https://unsloth.ai) (QLoRA). Trained twice with the same code and data: in **Google Colab on a
free T4** and on **my RTX 5070**, then both are measured against the untrained base model.

## Results (76 held-out test tasks, never trained on)
| Model | Prompt | Accuracy | **Balanced accuracy** | Recall local | Recall codex | Recall claude | Time per task |
|---|---|---|---|---|---|---|---|
| **router-rtx5070**: Gemma 4 E2B fine-tuned on my RTX 5070 | one line | **82%** | **63%** | 90% | 50% | 50% | 0.05 s |
| COLAB_ROW
| `gemma4:e2b`: the same model, **not** fine-tuned | full routing guidelines | 75% | 52% | 80% | 75% | 0% | 0.08 s |
| `ornith-1.5:9b`, thinking on | full routing guidelines | 51% | 62% | 52% | 33% | 100% | ~5 s |
| `ornith-1.5:9b`, thinking off | full routing guidelines | 78% | 41% | 97% | 0% | 25% | ~0.2 s |
| always "local" (baseline) | – | 79% | 33% | 100% | 0% | 0% | – |
| router v1 (training bug, see below) | one line | 75% | 32% | 95% | 0% | 0% | 0.05 s |

Balanced accuracy = the mean of the three recalls; it is the fair measure here because 79% of the tasks are
"local". Full numbers, including confusion tables and every prediction: [`results/eval.json`](results/eval.json).

**What it shows**
- **Fine-tuning taught the task.** The same 2B model went from 52% to 63% balanced accuracy, and needs only a
  one-line instruction instead of a page of rules: the rules are now in its weights. That is transfer learning:
  general language understanding from pre-training, adapted with ~300 examples to one narrow job.
- **A 2B fine-tune matches a 9B model that reasons first** (62%), about 100× faster and with no thinking step.
- **Caveats:** the test set is small, especially the rare classes (12 codex, 4 claude: "50% claude" is 2 of 4),
  so the per-class numbers would move a lot with another split. Many mistakes are on tasks a person could
  label either way ("Refactor to follow style guides", "Update for latest version of Rust"): a one-line commit
  message often doesn't say how big the job is. The labels are one reviewer's judgement.

**Training** (`runs/*/metrics.json`)
| | RTX 5070 (12 GB), `gpu` container | Colab free T4 (16 GB) |
|---|---|---|
| Training time (409 examples × 3 epochs) | 247 s | COLAB_TIME |
| Peak GPU memory | 7.98 GB | COLAB_VRAM |
| Loss at the end | 0.012 | COLAB_LOSS |
| LoRA adapter | 97 MB | |
| Exported model (GGUF Q4_K_M) | 3.4 GB | |

## What went wrong first, and how it was found
The first trained router (v1) answered "local" for nearly everything, **worse than the untrained model**.
Finding out why ([`diagnose_router.py`](diagnose_router.py), logs in [`logs/`](logs/)):

| Test | Result | Conclusion |
|---|---|---|
| Ask v1 about tasks it was **trained** on | 0% codex, 0% claude | Not a generalisation problem: training or export |
| Read the adapter's label probabilities directly (no export, no Ollama) | ≈ 0.6 / 0.15 / 0.25 for **every** task | The export is fine; the model only learned how common each label is |
| Train on 24 examples for 30 epochs, on purpose to overfit | training loss 0.000016, but only **11/24** right when asked | It learned perfectly but answered wrongly: training and inference saw different input |
| The same, with the KV cache off as in training | 11/24 | Not the cache (my first guess was wrong) |
| Compare the training text and the inference prompt token by token | training started with `<\|turn>`, inference with `<bos>` | **The training data had no `<bos>` token** |
| The same 24, with `<bos>` removed from the prompt | **24/24** | Proven |

**Cause:** Unsloth's Gemma guide removes `<bos>` from the training text because "the tokenizer adds it"; Gemma
4's tokenizer does not, so every training example lacked the start-of-sequence token that every real prompt
(Ollama's included) has. Gemma relies heavily on that first token, so the model learned the task in a setting it
never meets in use. **Fix:** keep `<bos>`, and `train_router.py` now refuses to train unless every example starts
with exactly one `<bos>`. **Lesson:** a falling training loss doesn't prove a model learned the right thing; test
the trained model the way it will be used, and overfit a tiny set first to check the pipeline.


## 1. The data
| Step | What | File |
|---|---|---|
| Task texts | 380 commit subjects written by people, from **CommitPackFT** (MIT licence; commits from permissively licensed GitHub repos), 12 languages, sampled with a fixed seed. A commit subject ("Add retry to upload", "Fix typo in docs") reads like a task handed to an agent | [`fetch_tasks.py`](fetch_tasks.py) → `data/tasks.jsonl` (source repo and licence kept per task) |
| Suggestions | My local model `ornith-1.5:9b` (MIT licence) suggests a worker for each task, using the same routing rules as Dispatch | [`prelabel.py`](prelabel.py) → `data/prelabels.jsonl` |
| Review | Every suggestion was confirmed or corrected against fixed rules (below). **176 of 380 were changed** | `data/review-changes.json` → `data/labels.jsonl` |
| Split | 80/20 stratified, seeded: **76 test tasks never trained on**. The training part repeats the rare classes (codex ×2, claude ×5) | [`build_dataset.py`](build_dataset.py) → `data/train.jsonl` (409 rows), `data/test.jsonl` (76) |

**Review rules** (the same as Dispatch's routing rules):
- `local`: typos, wording, docs and comments, renames, a config or version change, one small function or test, a bug
  with an obvious fix, style tweaks.
- `codex`: a clear new feature, component, endpoint, command, option or integration; support for something; a port;
  tests for a module.
- `claude`: a refactor or redesign of a whole part, architecture, performance, security, migrations across a
  codebase, vague work ("improve…", "rework…"), hard bugs (segfaults, races, async context).

**Final labels:** 301 local, 61 codex, 18 claude. Real commits are mostly small changes, so the data is
unbalanced: always answering "local" is right 79% of the time. That is why the results report **balanced
accuracy** (the mean of the three per-class recalls), where that trivial answer scores 33%.

### What the pre-labelling showed
| `ornith-1.5:9b` as a labeller | local | codex | claude | Time | Agrees with the reviewed labels |
|---|---|---|---|---|---|
| Thinking off | 368 | **0** | 12 | 66 s | 298 / 380 (mostly because it says "local") |
| Thinking on | 178 | 17 | **185** | 32 min | 204 / 380 |

Without thinking it sent almost everything to itself and never chose Codex. With thinking it swung the other
way and sent half of the tasks to Claude, including one-line jobs like "Add code comment". The two runs agreed
on only 185 tasks. **A 9B model is not a reliable judge for this**, which is why its suggestions were reviewed,
and a good reason to train a model on reviewed labels instead.

### Who labelled, and the terms of use
The task texts were written by people (CommitPackFT); the suggestions came from an open MIT-licensed model;
the review was done by **Claude Code (Opus)** at my request, because the project is presented tomorrow and
labelling 380 tasks by hand wasn't possible in time. Anthropic's consumer terms restrict using Claude to build
products or services that **compete** with Anthropic's, which includes training AI models for that. This is a
small router for my own coursework, presented once and not distributed or offered to anyone, so I judged it
outside that restriction. No GPT output was used. (Earlier in the project I wrote "never Claude output as
training data" into the design notes as a stricter rule; this fine-tune is the documented exception.)

## 2. The method
[`train_router.py`](train_router.py), the same file in both places (the Colab notebook embeds it):
- **QLoRA:** the base model `unsloth/gemma-4-E2B-it` is loaded in 4-bit and frozen; small LoRA matrices (rank 16)
  are added to the attention and MLP layers of the language model, and only those are trained. The vision and
  audio parts are left alone.
- **Format:** Gemma 4's chat format: a one-line system instruction, `Task: <text>` as the user turn, and
  `{"agent": "local"}` as the answer.
- **Loss on the answer only** (`train_on_responses_only` with Gemma 4's `<|turn>model` marker), so the model
  learns to produce the label, not to copy task texts.
- 3 epochs, batch 4 × gradient accumulation 2, learning rate 2e-4, AdamW 8-bit, seed 3407.

This is **transfer learning**: the model already understands language and code from its pre-training; the
fine-tune only adapts it to a new, narrow job, which is why ~300 examples are enough.

**Export:** [`export_gguf.py`](export_gguf.py) merges an adapter into the base model and writes a 4-bit GGUF
(Q4_K_M), which Ollama runs like my other models. Both adapters go through the same export.
**Evaluation:** [`eval_router.py`](eval_router.py) asks every model, through Ollama, about the 76 test tasks
(structured output, temperature 0).

## 3. How to run it
| Step | Where | Command |
|---|---|---|
| GPU container (once) | host | [`./setup-gpu-container.sh`](setup-gpu-container.sh): Ubuntu 24.04 container `gpu` with NVIDIA access, PyTorch + Unsloth in `~/.venvs/unsloth-gpu` |
| Data | host | `python3 fetch_tasks.py`, `python3 prelabel.py --think`, review, `python3 build_dataset.py` |
| Train on my GPU | `gpu` | `~/.venvs/unsloth-gpu/bin/python train_router.py --out runs/rtx5070` (stop Ollama first: `systemctl --user stop ollama`) |
| Train in Colab | browser | open [`colab/router_finetune_colab.ipynb`](colab/router_finetune_colab.ipynb) in Colab, T4 runtime, run all, upload `data/train.jsonl`, download `colab-lora.zip`, unzip into `runs/` |
| Export | `gpu` | `~/.venvs/unsloth-gpu/bin/python export_gguf.py runs/rtx5070` (and `runs/colab`) |
| Into Ollama | host | `ollama create router-rtx5070 -f runs/rtx5070/gguf/Modelfile` (and `router-colab`) |
| Evaluate | host | `ollama pull gemma4:e2b`, then `python3 eval_router.py` → `results/eval.md` |

`make_notebook.py` rebuilds the notebook from `train_router.py`. Weights, checkpoints and GGUF files are
gitignored; the `metrics.json` of each run is kept.
