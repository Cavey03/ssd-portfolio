# Comparison run: a cloud model on a similar task (2026-11-18)

The same afternoon as the [local model's runs](../2026-11-18-localllm/README.md), Codex with its normal cloud
model built another Mission Control module from a brief of the same kind. This gives a direct comparison
between my local 9B model and a frontier cloud model doing agentic coding in the same setup.

**Task:** `mission_control/worktrees.py`, the git layer of Dispatch: create a private git worktree per task,
summarise its changes (including new untracked files), commit, merge into the main checkout (aborting cleanly
on conflicts), and clean up. With unit tests on temporary repos. Brief: [`brief.txt`](brief.txt) (about the
same length and detail as the local model's first brief). Log: [`codex.log`](codex.log).

**Setup:** identical to the local runs except the model: Codex CLI 0.166.0, `codex exec -s workspace-write`,
own git worktree, unattended, 25-minute limit. Model `gpt-6.1-sol`, `reasoning effort: high`.

| | Local `ornith-1.5:9b`, run 1 | Local, run 2 (⅓ of the task) | Cloud `gpt-6.1-sol` |
|---|---|---|---|
| Task size | 4 classes, 9 functions | 3 classes, 4 functions | 2 classes, 7 functions (harder: real git, merges, conflicts) |
| Time | stopped after 6 min | stopped by limit, 10 min | **3 min 14 s**, finished itself |
| Commands | 5 (reading only) | 54 | **5** |
| Result | no files | 13/15 tests, 1 bug | **182-line module, 27 tests, all passing** |
| Review findings | – | missing `self.` (crash), 2 broken test samples | **none**; accepted unchanged |

**What the review noticed** (commit `6452c58`, merged as `f53fcd1`): it went beyond the brief in sensible
ways. It resolves paths before comparing them (on Fedora Atomic `/home` is really `/var/home`), uses NUL-separated
git output so odd filenames can't break parsing, refuses to abort a merge that was already in progress, and
added tests for binary files, renames, unusual filenames and an existing empty folder. Its tests only touch
temporary repos, as the brief required.

**What this shows:** for a multi-step agentic task, the gap between a 9B local model and a frontier model is not
small: the cloud model needed 5 commands for what the local model couldn't start. The local model is still
useful, but only for small, single-step jobs, which is exactly how Dispatch's routing rules use it.

| Part | By |
|---|---|
| Brief, worktree, review, merge, this write-up | Claude Code (owner allowed using GPT for Phases 3–4) |
| `worktrees.py` and `test_worktrees.py` | Codex, `gpt-6.1-sol` |
