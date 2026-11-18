# End-to-end test of Dispatch with the local model (2026-11-18)

The first real runs of Mission Control's Dispatch pipeline: a task goes to a worker in its own git worktree,
the supervisor collects the changes, Opus reviews them, and the owner merges or discards. Done in a
throwaway repo (`~/.cache/mc-e2e/repo`: `mathutils.py` with an `add` function and one test), so nothing in
the portfolio could be touched. The worker was the local model, chosen by hand (`--agent local`) with a
5-minute limit.

| Task | Worker | Time | Changes | Opus review | Owner |
|---|---|---|---|---|---|
| [`20261118-1344-9b2f`](20261118-1344-9b2f/) add `is_even` + tests (even, odd, zero, negative) | `ornith-1.5:9b` | ~1 min | 4 files | **changes**: code and tests right, but 2 `__pycache__/*.pyc` files would be committed | merged (to test the merge path) |
| [`20261118-1346-52d4`](20261118-1346-52d4/) add `is_odd` + a test | `ornith-1.5:9b` | ~1 min | 2 files | **approve** | discarded (to test the discard path) |

Each folder has the task record (`task.json`, including the review), the worker's log and the diff.
[`decisions.jsonl`](decisions.jsonl) is the routing log.

## What it showed
- **Small tasks suit the local model.** Both one-function tasks were done correctly in about a minute,
  tests included. Compare its first agentic run, where a 9-function task never got started
  ([../2026-11-18-localllm](../2026-11-18-localllm/README.md)).
- **The review step pays off.** On the first task, Opus found a real problem that the worker and its tests
  could not see: running the tests created `__pycache__/*.pyc` files, and the throwaway repo had no
  `.gitignore`, so they would have been merged. **Fix:** workers now run with `PYTHONDONTWRITEBYTECODE=1`,
  so no bytecode files are written. The second task, after the fix, changed exactly the 2 files it should.
- **Review limit (by design):** Opus reviews the diff and the worker's log, without running anything. It said
  so in its review ("I only had the diff to review and didn't rerun the tests myself"). The worker's own test
  run is in its log.
- **Merge and discard both clean:** merge made a proper merge commit and removed the worktree and branch;
  discard removed them and left the main checkout unchanged.
- **Found while testing:** the first merge commit contained the full task title and the worker's model name.
  Commit messages are now `Task <id>: <short title>`, because the portfolio has no AI attribution in
  commit messages; who did the work stays in the task record.

## The routing adapts
Asked to plan the same task (add `--version` to `mc`) twice, Opus chose:
- **Codex** while the local server was stopped ("the local model would normally be the cheapest choice, but
  its server is not running"), with a detailed multi-step brief;
- **the local model** once it was running ("a small, well-specified change in two or three files… the local
  model can handle it for free"), with a brief written for a small model: exact files, exact code to add.
