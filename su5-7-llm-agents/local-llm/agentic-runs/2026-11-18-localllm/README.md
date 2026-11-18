# Agentic run: the local model builds part of Mission Control (2026-11-18)

**Question:** can my local model (`ornith-1.5:9b`, 9B parameters, on the RTX 5070) do a real agentic coding
task inside my own system, not just answer single prompts?

**Task:** write `mission_control/localllm.py` for Mission Control's new Local LLM panel. The module parses the
Ollama server's API replies and `nvidia-smi` output into Python data, and comes with unit tests.

**Setup:**
- Agent: Codex CLI 0.166.0, `codex exec -p local` (the `local` profile points Codex at Ollama).
- Model: `ornith-1.5:9b` (Q4_K_M), 64K context, 100% on the GPU.
- Isolation: run in its own git worktree (`.worktrees/mc-localllm`, branch `mc-localllm`) with
  `-s workspace-write`, so it could only write inside that folder. Approval: never (runs unattended).
- Brief written by Claude Code. It included the real API samples and the exact function names, so the model
  didn't need to guess anything.
- What Codex reported at startup (from the log): `reasoning effort: high`, and
  `Model metadata for ornith-1.5:9b not found. Defaulting to fallback metadata; this can degrade performance`.

## Run 1: the full task. Result: stopped after 6 minutes, nothing written
Brief: [`run1-brief.txt`](run1-brief.txt) (132 lines: 4 data classes, 9 functions, HTTP + subprocess + tests).
Log: [`run1-codex.log`](run1-codex.log).

| Measure | Value |
|---|---|
| Time | 13:12:45 → stopped by Claude at ~13:18:40 (6 min) |
| Commands run | 5, all reading (the brief, two example modules, a test file, a folder listing) |
| Files written | **0** |
| Log length | 2,235 lines, almost all of it the model's own reasoning |
| "Let me write / create …" | **42 times** |
| "Let me reconsider …" | **40 times** |
| GPU | 95% busy the whole time |

**What happened:** after reading the files, the model planned the whole module in its head, decided to write
it ("Now let me write the files with apply_patch"), then reconsidered a detail (which exceptions to catch,
how `fromisoformat` handles nanoseconds), and planned again, over and over. It never called a tool to write.
This is the same failure I saw in the first coding test, where `gemma4:12b` at temperature 0 filled its whole
context with thinking (`Wait, I'm repeating myself again.`). Here it happened at the default temperature, on
a bigger task.

## Run 2: a third of the task. Result: working code with one bug, tests stuck at 13/15
Changed **one thing**: the task size. Only the 3 data classes and 4 parse functions plus their tests
(HTTP, commands and the service control were left to Claude). The brief also said: "do not plan at length;
write the file first, then fix it." 10-minute time limit (`timeout 600`).
Brief: [`run2-brief.txt`](run2-brief.txt). Log: [`run2-codex.log`](run2-codex.log).
Its files exactly as it left them: [`run2-output/`](run2-output/).

| Measure | Value |
|---|---|
| Time | 13:21:51 → stopped by the 10-minute limit at 13:31:52 |
| First file written | `localllm.py` at **13:24** (2½ min), then `test_localllm.py` |
| Commands run | 54 (writing files, running tests, inspecting its test file) |
| Test runs | 8. First: 3 failures + 2 errors. It fixed the 3 failures, then the next **7 runs** all ended with the same 2 errors |
| "Let me write / create …" / "reconsider" | 15 / 14 (vs 42 / 40 in run 1) |
| Final state | 13 of 15 tests pass |

**What happened:** it wrote both files quickly and fixed its first real mistakes. The last 2 errors came from
broken JSON in its *own* test samples: one sample was missing a `}` and had an extra `]`, another had an extra
`}`. It then spent the rest of the time looking at those 6 lines in every way it could think of (`sed`, `awk`,
`cat -A`, `od -c`, `hexdump`; 26 inspection commands) without seeing the stray brackets.

**Claude Code's review** (commit `f782df9` = its output unchanged, `10d47b6` = the fixes):
| Problem | Severity |
|---|---|
| `gpu_percent` used `size_bytes` / `vram_bytes` without `self.`: a `NameError` the first time a loaded model is shown. Its own test would have caught it, but that test never got past the broken sample | **Bug** (would crash the panel) |
| `parse_tags`/`parse_ps` crashed with `AttributeError` on JSON that isn't an object (`[]`), instead of the `ValueError` the brief asked for | Minor |
| Error messages pasted the whole server reply; no docstrings | Style |
| The 2 malformed JSON samples in the tests | Test bug |

Everything else (the 3 data classes, timestamp handling with nanoseconds, `nvidia-smi` parsing with `[N/A]`,
the sorting, skipping bad entries) was correct, and its 15 tests covered every case in the brief. After the
fixes it was merged into Mission Control (merge `98c9ce4`) and now runs the Local LLM panel.

## What this shows about small local models as agents
1. **Task size matters more than difficulty.** Each function was easy: the model knew how to write all of
   them. With 9 functions at once it never started. With 4 it started within 2½ minutes. Small models need
   small, single-step tasks; the orchestrator (a stronger model or me) should split the work.
2. **Overthinking is the main failure, not wrong code.** The reasoning ("thinking") mode makes small models
   better at single answers (5/5 vs 3/5 in the coding test) but in an agent loop it can stop them acting.
   Codex ran it at `reasoning effort: high` by default. Worth testing: `-c model_reasoning_effort=low`.
3. **They get stuck on small bugs they made themselves.** The code was mostly right, but a stray bracket in
   its own test data held it up for 7 minutes. A small model is weak at *finding* an error: it looks at the
   same text again and again. A reviewer (a stronger model or me) found both brackets at a glance. So a
   local worker's output always needs review, and its time limit should end the run, not the model.
4. **Unattended runs need a time limit.** Without `timeout`, run 1 would have kept the GPU at 95%
   indefinitely. Mission Control's Dispatch (Phase 4) should give every local worker a time limit and show
   when it stalls.
5. **Side effect found:** each local Codex run writes an all-empty `rate_limits` entry to its session log.
   Mission Control's Usage panel read the newest entry, so after the runs it showed my ChatGPT limits as
   "unknown". Fixed: entries without any limits are skipped.
6. **Sandboxing worked.** In both runs the model only touched its worktree; the main checkout was never at
   risk, and stopping it lost nothing.

## Who did what
| Part | By |
|---|---|
| Briefs, worktree, running and stopping the model, measurements, this write-up | Claude Code (owner approved each delegation and asked for the evidence to be saved) |
| `localllm.py` parse functions and `test_localllm.py` (run 2) | `ornith-1.5:9b` via Codex, reviewed by Claude Code |
