# My learning process – SU5–7 (transfer learning, LLMs, agents)

> **Status: template.** Fill each section as the work happens. Keep entries short and dated; link to the
> folder that holds the evidence instead of repeating it.

## 1. Starting points
From the brief *Update for Study Units 5,6,7.pdf*: one row per starting point it lists.

| Starting point (from the brief) | What I did with it | What I learned | Evidence |
|---|---|---|---|
| _(to fill in from the brief)_ | | | |

## 2. Goal: what the models are for
**Use case: coding and my own projects.** Mission Control is the hub: from one screen I track containers,
projects, agents (cloud and local) and usage, and send work to an agent. The local models run on my
RTX 5070 as a team member and fallback next to Claude Code and Codex.

_Why this goal:_ …

## 3. Learning log
One entry per step, newest at the bottom.

| Date | What I tried | What happened | What I learned | Next |
|---|---|---|---|---|
| 2026-11-05 | Ran two local models with Codex (example row) | Both 5/5 on the coding test with thinking on; gemma looped at temperature 0 | Don't force temperature 0 on thinking models | Benchmark local vs cloud |
| 2026-11-18 | Let my local model (`ornith-1.5:9b`) build part of Mission Control by itself ([write-up](local-llm/agentic-runs/2026-11-18-localllm/README.md)) | Full task: thought in circles for 6 min, wrote nothing. A third of the task: working code in 2½ min, but stuck on a stray bracket in its own tests | Small models need small tasks, a time limit and a reviewer; overthinking, not bad code, is what stops them | Try lower reasoning effort; split work in Dispatch |
| 2026-11-18 | Same kind of task for Codex with a cloud model (GPT) ([write-up](local-llm/agentic-runs/2026-11-18-worktrees-gpt/README.md)) | Finished in 3 min with 5 commands and 27 passing tests; nothing to fix | On multi-step agentic work the gap between a 9B local model and a frontier model is large | Route only small tasks to the local model |
| 2026-11-18 | Built Dispatch: Opus routes each task, a worker runs in its own git worktree, Opus reviews, I merge ([end-to-end test](local-llm/agentic-runs/2026-11-18-dispatch-e2e/README.md)) | The local model did two one-function tasks in ~1 min each; Opus's review caught `.pyc` files that would have been merged | Orchestrator–workers: a strong model plans and checks, cheap models do small steps; a review step catches what workers can't see | Use Dispatch for real tasks; fine-tune the router later |
| 2026-11-18 | Let Ornith label 380 real commit-message tasks for the router, with and without thinking ([data](../models/router-finetune/README.md#1-the-data)) | Without thinking: "local" 368 times, never "codex". With thinking: half sent to "claude". The two runs agreed on 185 of 380 | A 9B model is an unreliable judge; reviewed labels are needed | Review every label |
| 2026-11-18 | Fine-tuned Gemma 4 E2B with Unsloth on my RTX 5070 ([write-up](../models/router-finetune/README.md)) | First run looked fine (loss fell) but routed everything to "local". An overfit test and token-by-token comparison found the cause: no `<bos>` token in the training data. Fixed: 63% balanced accuracy on unseen tasks vs 52% untrained, matching the 9B model with thinking at ~100× the speed | A falling loss proves nothing: test the model the way it is used; overfit a tiny set first to check the pipeline | Run the same training in Colab and compare |

## 4. Models tried
Full notes per model: [`../models/`](../models/README.md). Here only the verdict.

| Model | Why I tried it | Result | Verdict |
|---|---|---|---|
| `ornith-1.5:9b` | Agentic coding on 12 GB | 5/5 on small coding tests; looped on a large agentic task; did one-function tasks in ~1 min; unreliable as a labeller | Good worker for small tasks only |
| `gemma4:12b` | Fast option (speculative decoding) | 172 tokens/s; looped at temperature 0 | Kept as the fast option |
| `gemma4:e2b` | Base model for the router fine-tune | 52% balanced accuracy untrained, 63% fine-tuned | A small model can learn a narrow job well |

## 5. Concepts I understand now
| Learning outcome | My explanation (2–3 sentences) | Where I saw it in practice |
|---|---|---|
| Transfer learning | | |
| Building blocks of LLMs | | |
| Fine-tuning an LLM to a domain | | |
| Agentic workflows | | |
| Clustering / semi-supervised learning | | |

## 6. What went wrong, and what I would do differently
-

## 7. Sources
-
