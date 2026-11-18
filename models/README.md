# Models

Every model I downloaded or tried for SU5–7, and what I learned from it. This feeds the "learning process"
document on the ITRI626 checklist.

**Weights are not stored here.** Ollama keeps them in `~/.ollama/models` (5–15 GB each, far over GitHub's
100 MB file limit). This folder holds notes, Modelfiles (Ollama's recipe files) and fine-tuning scripts.

| Model | Source / tag | Date | Status | What I learned |
|---|---|---|---|---|
| Gemma 4 12B | Ollama `gemma4:12b` (Q4_K_M, 8.0 GB) | 2026-11-05 | installed, fast option | Fastest (172 tokens/s) thanks to a built-in draft model (speculative decoding); fits 64K context on 12 GB; loops at temperature 0 with thinking on; `ollama ps` under-reports its memory. [Details](../su5-7-llm-agents/local-llm/README.md#first-test-2026-11-05) |
| Ornith 1.5 9B | Ollama `ornith-1.5:9b` (6.6 GB) | 2026-11-05 | installed, provisional default | Built for agentic coding; 103 tokens/s; 5/5 on the coding test with thinking on; more VRAM headroom at 64K. [Details](../su5-7-llm-agents/local-llm/README.md#default-model-provisional-2026-11-05) |
| gpt-oss 20B | Ollama `gpt-oss:20b` | – | considered, not pulled | Codex's default for `--oss`, but a 14 GB download won't fit fully in 12 GB of VRAM |
