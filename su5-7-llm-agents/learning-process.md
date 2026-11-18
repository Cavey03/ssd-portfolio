# My learning process – SU5–7 (transfer learning, LLMs, agents)

How I went from the theory of SU1–6 to a working system with local models, agents and a fine-tuned model:
where I started, what I tried in order, what each model taught me, and what I would do differently. Each
step links to the folder with the evidence instead of repeating it.

## 1. Starting points
What I knew before SU5–7, and what was new.

| Area | What I already knew | What was new to me |
|---|---|---|
| Machine learning basics (SU1) | Supervised vs unsupervised learning, training/test data, overfitting, evaluation | Evaluating a model whose classes are very unbalanced (balanced accuracy) |
| Neural networks (SU2–SU3) | Feed-forward networks, weights, gradient descent and backpropagation, from Trask's notebooks and the SU2 assignment | How the same ideas scale to models with billions of weights |
| Classification and CNNs (SU4) | Image classification with a CNN in the group project (Gravity Spy glitches), including a pre-trained EfficientNetV2-S (transfer learning on images) | Transfer learning on **language** models, and text classification with an LLM |
| LLMs (SU5–6 theory) | What an LLM is at the level of the study content: tokens, transformers, attention, pre-training | Running one myself: model files, quantisation, context length, GPU memory, chat templates, special tokens |
| Fine-tuning | **Nothing hands-on.** I had only trained models from scratch (small networks) or used a pre-trained CNN | LoRA/QLoRA fine-tuning with Unsloth, preparing a dataset, exporting a model to GGUF and Ollama |
| Open-source / local models | **Nothing.** I had only used cloud chat assistants | Choosing models that fit 12 GB of VRAM, running them with Ollama, comparing them with cloud models |
| Agents and orchestration | I had used AI coding assistants, but never built anything around them | Agents as an LLM in a loop with tools; the **orchestrator–workers** pattern: one strong model plans, routes and reviews while cheaper models do the work, each in an isolated copy of the code (git worktree), with time limits and a human approving every merge |

## 2. Goal: what the models are for
**Use case: coding and my own projects.** Mission Control is the hub: from one screen I track containers,
projects, agents (cloud and local) and usage, and send work to an agent. The local models run on my
RTX 5070 as a team member and fallback next to Claude Code and Codex.

**Why this goal:** AI coding agents (Claude Code, Codex, Copilot) are already part of how many developers
work, so this is a realistic use of LLMs, and a system I can actually keep using for my own projects. Adding
local models shows the real trade-offs (cost, privacy, working offline, but weaker results), and it gave the
fine-tune a concrete, measurable job: deciding which agent should do a task.

## 3. Learning log
One entry per step, in the order I did them.

| # | What I tried | What happened | What I learned | Next |
|---|---|---|---|---|
| 1 | Installed Ollama on an immutable Linux (Bazzite) as a user service, without touching the read-only system ([local-llm](local-llm/README.md)) | Works on the GPU; Ollama brings its own CUDA libraries | On an immutable system, tools go in the home folder or in containers | Choose models that fit 12 GB |
| 2 | Pulled `gemma4:12b` and `ornith-1.5:9b` and measured them | Both fit fully on the GPU; Gemma was faster (172 vs 103 tokens/s) because it uses speculative decoding | Model size alone doesn't decide speed; a small "draft" model can make a big one faster | Check the context length |
| 3 | Looked at how much text the models could take in | Ollama loads models with only **4096 tokens** of context by default; coding agents need 64K. Both models still fit on the GPU at 64K | The context window costs GPU memory; defaults are often too small for agents | Test the models on code |
| 4 | Coding sanity test: 5 small tasks, thinking on and off | Both 5/5 with thinking on. At temperature 0 Gemma **looped** ("Wait, I'm repeating myself") and never wrote code | Don't force temperature 0 on thinking models | Connect Codex |
| 5 | Connected Codex CLI to the local model (`codex -p local`) | A full coding agent running offline on my own GPU | Agent tools can run on open models if the server speaks the right API | Build the hub |
| 6 | Turned Mission Control into the hub: projects, containers, agents, local LLM panel, usage of cloud plans and local tokens ([mission-control](mission-control/README.md)) | One screen shows and starts everything | – | Let the local model do real work |
| 7 | Let the local model build part of Mission Control by itself ([write-up](local-llm/agentic-runs/2026-11-18-localllm/README.md)) | Full task: thought in circles for 6 min, wrote nothing. A third of the task: working code in 2½ min, but stuck on a stray bracket in its own tests | Small models need small tasks, a time limit and a reviewer; overthinking, not bad code, is what stops them | Compare with a cloud model |
| 8 | Gave the same kind of task to Codex with a cloud model (GPT) ([write-up](local-llm/agentic-runs/2026-11-18-worktrees-gpt/README.md)) | Finished in 3 min with 27 passing tests; nothing to fix | On multi-step agentic work the gap between a 9B local model and a frontier model is large | Route only small tasks locally |
| 9 | Built Dispatch: Opus routes each task, a worker runs in its own git worktree, Opus reviews, I merge ([end-to-end test](local-llm/agentic-runs/2026-11-18-dispatch-e2e/README.md)) | The local model did two one-function tasks in ~1 min each; Opus's review caught `.pyc` files that would have been merged | Orchestrator–workers: a strong model plans and checks, cheap models do small steps; a review catches what workers can't see | Let a small local model do the routing |
| 10 | Built a dataset for a router: 380 real coding tasks (commit messages from CommitPackFT), pre-labelled by Ornith ([data](../models/router-finetune/README.md#1-the-data)) | Without thinking Ornith said "local" 368 times and never "codex"; with thinking it sent half to "claude". The two runs agreed on only 185 of 380 | A 9B model is an unreliable judge; labels must be reviewed | Review every label, then train |
| 11 | Fine-tuned Gemma 4 E2B with Unsloth (QLoRA) on my RTX 5070 ([write-up](../models/router-finetune/README.md)) | Training loss fell, but the model answered "local" for everything, worse than before training | A falling loss doesn't prove the model learned the right thing | Find out why |
| 12 | Diagnosed it: overfitted 24 examples on purpose, then compared the training text with the real prompt token by token | Learned perfectly (loss 0.000016) but still wrong when asked; the training text had **no `<bos>` start token**, which every real prompt has. Without it in the prompt: 24/24 | Test a model the way it will be used; overfit a tiny set first to check the whole pipeline | Retrain with the fix |
| 13 | Retrained with the fix, exported to GGUF and Ollama, evaluated on 76 unseen tasks | 63% balanced accuracy vs 52% untrained, as good as the 9B model that thinks first (62%) and ~100× faster | Fine-tuning moves the instructions into the weights: the model now needs a one-line prompt | Check it reproduces |
| 14 | Ran the same notebook on a free Google Colab T4 | 58%, agreeing with the RTX 5070 model on 72 of 76 tasks; 299 s vs 247 s | The method reproduces, and a free cloud GPU is enough for this | Put the router into Dispatch |
| 15 | Added the router to Dispatch, next to Opus's plan | It answers in 0.05 s; in the demo it suggested "codex" where Opus chose "local" | A small router gives an instant, free first opinion; the strong model still decides | Record the demo |
| 16 | Recorded a real Dispatch run for the intro video ([video](video/VIDEO.md)) | The local model wrote the change but hit its 10-minute limit before running the tests; Opus asked for changes. The 190 tests were run before merging (all passed), then I merged | The review step works as designed: it flagged unverified work instead of approving it | Narrate the video |
| 17 | Narrated the video with Kokoro-82M, an open text-to-speech model, on the same GPU | 11 lines in ~15 s, three voices | Open models now cover speech too; spelling numbers as words fixes pronunciation | – |

## 4. Models tried
Full notes per model: [`../models/`](../models/README.md). Here only the verdict.

| Model | Why I tried it | Result | Verdict |
|---|---|---|---|
| `ornith-1.5:9b` | Agentic coding on 12 GB | 5/5 on small coding tests; looped on a large agentic task; did one-function tasks in ~1 min; unreliable as a labeller | Good worker for small tasks only |
| `gemma4:12b` | Fast option (speculative decoding) | 172 tokens/s; looped at temperature 0 | Kept as the fast option |
| GPT (cloud, through Codex) | Comparison with a frontier model | Same kind of task in 3 min, 27 tests, nothing to fix | Much stronger on multi-step work |
| `gemma4:e2b` | Base model for the router fine-tune | 52% balanced accuracy untrained | Small and fast, but needs training for this job |
| `router-rtx5070` (my fine-tune) | Route tasks locally | 63% balanced accuracy, 0.05 s per answer | Best router I tested; used in Dispatch |
| `router-colab` (my fine-tune) | Same training on a free GPU | 58%, agrees with the RTX 5070 router on 72/76 | The method reproduces |
| Kokoro-82M | Voice-over for the video | Natural voices, runs in seconds on the GPU | Good enough for narration |

## 5. Concepts I understand now
| Learning outcome | My explanation | Where I saw it in practice |
|---|---|---|
| Transfer learning | A model pre-trained on a huge general dataset already knows useful features (shapes for images, language for text). Instead of training from scratch, I adapt it to my task with little data and compute. | SU4: EfficientNetV2-S pre-trained on ImageNet, adapted to Gravity Spy glitches. SU5–7: Gemma 4 E2B, pre-trained on general text, adapted to routing coding tasks with 409 examples. |
| Building blocks of LLMs | Text is split into **tokens** (with special tokens such as `<bos>` and chat-turn markers), turned into vectors, and passed through **transformer** layers whose **attention** relates every token to the others; the model predicts the next token. The **context window** is how many tokens it can see, and it costs GPU memory (the KV cache). **Quantisation** stores the weights in fewer bits so big models fit on a small GPU. | Context had to go from 4096 to 64K for Codex; 4-bit (Q4_K_M) models of 3–8 GB on a 12 GB GPU; Gemma's sliding-window attention keeps its memory low; speculative decoding made the 12B model faster than the 9B one; a missing `<bos>` token broke my first fine-tune. |
| Fine-tuning an LLM to a domain | Full fine-tuning changes all the weights, which needs far too much memory. **LoRA** freezes the model and trains small extra matrices (an "adapter"); **QLoRA** also keeps the frozen model in 4-bit. The training data must look exactly like the prompts the model will see, and the result must be tested on unseen data. | Unsloth QLoRA on Gemma 4 E2B: a 97 MB adapter trained in 4 minutes on my GPU (8 GB of VRAM) and on a free Colab T4; 52% → 63% balanced accuracy on 76 unseen tasks. |
| Agentic workflows | An agent is an LLM in a loop with tools (read files, run commands, run tests) working towards a goal. In an **orchestrator–workers** workflow a strong model splits and routes the work, cheaper or specialised workers do it, and the result is reviewed before it is accepted; a human stays in control. | Dispatch in Mission Control: Opus plans and picks the worker (local model, Codex or Claude), the worker runs in its own git worktree with a time limit, Opus reviews, I merge. |
| Evaluating a model fairly | When one class dominates (79% of my tasks are "local"), accuracy is misleading: always answering "local" scores 79%. **Balanced accuracy** (the mean recall per class) shows that this scores only 33%. | Every router was compared on balanced accuracy against the "always local" baseline. |
| Clustering / semi-supervised learning | Clustering groups data without labels by similarity (for example k-means). Semi-supervised learning uses a few labelled examples together with many unlabelled ones, for example by letting a model label the rest and keeping its confident guesses. | Not done hands-on yet. The closest I came: Ornith pre-labelling 380 tasks for me to review, which showed why machine-made labels need checking. |

## 6. What went wrong, and what I would do differently
| What went wrong | What I learned | What I would do differently |
|---|---|---|
| My first fine-tune learned nothing useful: the training data had no `<bos>` token (I followed Unsloth's guide, which assumes the tokenizer adds it; Gemma 4's doesn't) | Training loss can look perfect while the model is useless | Overfit a tiny set first and test it **the way it will be used** before the full training run |
| Gemma looped forever at temperature 0 | Thinking models need some randomness | Start from the model's recommended settings |
| Ollama's default context (4096 tokens) was far too small for an agent | Defaults are not made for agents | Check context length and memory first when setting up a model |
| The local model overthought a big task and wrote nothing; in the video run it hit its time limit before testing | Small models need small, concrete tasks | Split work into smaller tasks, and give the local model lower reasoning effort and a longer limit for tasks with tests |
| Ornith's pre-labels were inconsistent (its two runs agreed on 185 of 380) | A small model is a weak judge | Write clear labelling rules first, and label a sample myself before letting a model help |
| 79% of the tasks were "local"; the test set had only 4 "claude" tasks | Unbalanced data makes accuracy misleading and per-class results noisy | Collect more examples of the rare classes; use balanced accuracy from the start |
| A power cut corrupted a 5 GB model download | Large downloads can fail silently | Always verify checksums before using a download |
| I only settled late how the labels could be made under the AI providers' terms | Training data has licensing and terms-of-use questions | Decide the label source before collecting data |

## 7. Sources
- Study content of ITRI626 SU1–SU7 (eFundi) and my [study summaries](SU5-7-summary.html).
- Trask, A. (2019). *Grokking Deep Learning*. Manning.
- Hu, E. et al. (2021). *LoRA: Low-Rank Adaptation of Large Language Models*. arXiv:2106.09685.
- Dettmers, T. et al. (2023). *QLoRA: Efficient Finetuning of Quantized LLMs*. arXiv:2305.14314.
- Muennighoff, N. et al. (2023). *OctoPack: Instruction Tuning Code Large Language Models* (the CommitPackFT dataset). arXiv:2308.07124.
- Anthropic (2024). *Building effective agents* (the orchestrator–workers pattern). https://www.anthropic.com/research/building-effective-agents
- Unsloth documentation: fine-tuning Gemma models, saving to GGUF. https://docs.unsloth.ai
- Ollama documentation: running models, context length, using it with Codex. https://docs.ollama.com
- OpenAI Codex CLI documentation: using open-source models (`--oss`). https://developers.openai.com/codex
- Google: Gemma 4 model card. https://ai.google.dev/gemma
- hexgrad: Kokoro-82M text-to-speech model (Apache 2.0). https://huggingface.co/hexgrad/Kokoro-82M
- llama.cpp and the GGUF format. https://github.com/ggml-org/llama.cpp
