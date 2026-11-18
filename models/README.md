# Models

Every model I downloaded or tried for SU5–7, and what I learned from it. This feeds the "learning process"
document on the ITRI626 checklist.

**Weights are not stored here.** Ollama keeps them in `~/.ollama/models` (5–15 GB each, far over GitHub's
100 MB file limit). This folder holds notes, Modelfiles (Ollama's recipe files) and fine-tuning scripts.

| Model | Source / tag | Date | Status | What I learned |
|---|---|---|---|---|
| Gemma 4 12B | Ollama `gemma4:12b` (Q4_K_M, 8.0 GB) | 2026-11-05 | installed, fast option | Fastest (172 tokens/s) thanks to a built-in draft model (speculative decoding); fits 64K context on 12 GB; loops at temperature 0 with thinking on; `ollama ps` under-reports its memory. [Details](../su5-7-llm-agents/local-llm/README.md#first-test-2026-11-05) |
| Ornith 1.5 9B | Ollama `ornith-1.5:9b` (6.6 GB) | 2026-11-05 | installed, provisional default | Built for agentic coding; 103 tokens/s; 5/5 on the coding test with thinking on; more VRAM headroom at 64K. **As an agent (2026-11-18):** looped without acting on a 9-function task; on a 4-function task wrote working code in 2½ min (one bug) but couldn't find a stray bracket in its own tests. [Details](../su5-7-llm-agents/local-llm/README.md#default-model-provisional-2026-11-05), [agentic run](../su5-7-llm-agents/local-llm/agentic-runs/2026-11-18-localllm/README.md) |
| gpt-oss 20B | Ollama `gpt-oss:20b` | – | considered, not pulled | Codex's default for `--oss`, but a 14 GB download won't fit fully in 12 GB of VRAM |
| Gemma 4 E2B | Ollama `gemma4:e2b` (4.6 GB); for training `unsloth/gemma-4-E2B-it` (4-bit 8.2 GB, 16-bit 10.3 GB, in `~/.cache/huggingface`) | 2026-11-18 | base model of the router fine-tune | Untrained, with the full routing rules in its prompt: 52% balanced accuracy. Its "per-layer embeddings" stay 16-bit, so even the 4-bit download is 8 GB. Its tokenizer doesn't add `<bos>`, which broke my first fine-tune. [Fine-tune](router-finetune/README.md) |
| **router-rtx5070** (my fine-tune) | Ollama `router-rtx5070` (3.4 GB, Q4_K_M), built from `router-finetune/runs/rtx5070` | 2026-11-18 | used by Dispatch | Gemma 4 E2B + LoRA trained with Unsloth on 409 rows in 4 min on the RTX 5070: 63% balanced accuracy (best of all models tried), 0.05 s per answer. Trained again on a free Colab T4 (`router-colab`): 58%, agreeing on 72 of 76 tasks. [Details](router-finetune/README.md) |
