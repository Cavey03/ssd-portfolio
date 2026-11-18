"""Let the local model (ornith-1.5:9b, MIT licence) suggest a worker for every task.

These are only suggestions: every label is reviewed afterwards (review.py). The guidelines below are the
same routing rules Mission Control's orchestrator uses, reduced to what can be judged from the task text.

Usage: python3 prelabel.py [--think] [model]     (Ollama must be running)  -> data/prelabels.jsonl
  --think   let the model reason first: much slower (~6 s per task) but less one-sided suggestions.
            Without it, ornith-1.5:9b suggested "local" for 368 of 380 tasks and "codex" for none.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

URL = "http://127.0.0.1:11434/api/chat"
DATA = Path(__file__).parent / "data"
LABELS = ("local", "codex", "claude")

GUIDELINES = """\
You route coding tasks to one of three AI coding workers. Judge only from the task description.
- local: a small 9B model on my GPU. SMALL, single-step, clear tasks in one or two files: typos, wording or
  docs changes, renaming, a config value, a simple function or test, a small bug with an obvious fix,
  a style tweak.
- codex: GPT in the cloud. Clear, well-specified work that spans several files or needs some building:
  a new feature, component, endpoint, command or option, an integration, a port, tests for a module.
- claude: Claude in the cloud. Large, vague or cross-cutting work that needs judgement: redesigns and
  refactors of a whole part, architecture, performance or security investigations, unclear bugs,
  migrations across a codebase.
Answer with JSON: {"agent": "local" | "codex" | "claude"}."""

SCHEMA = {"type": "object", "properties": {"agent": {"type": "string", "enum": list(LABELS)}},
          "required": ["agent"]}


def suggest(model: str, task: str, think: bool = False) -> str:
    """Ask the model for one label; structured output guarantees one of LABELS."""
    body = json.dumps({
        "model": model, "stream": False, "think": think, "format": SCHEMA,
        "messages": [{"role": "system", "content": GUIDELINES}, {"role": "user", "content": f"Task: {task}"}],
    }).encode()
    request = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=600) as response:
        reply = json.loads(response.read())["message"]["content"]
    agent = json.loads(reply).get("agent")
    if agent not in LABELS:
        raise ValueError(f"unexpected label {agent!r}")
    return agent


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--think"]
    think = "--think" in sys.argv
    model = args[0] if args else "ornith-1.5:9b"
    tasks = [json.loads(line) for line in (DATA / "tasks.jsonl").read_text().splitlines()]
    start = time.time()
    counts = {label: 0 for label in LABELS}
    with (DATA / "prelabels.jsonl").open("w") as out:
        for i, task in enumerate(tasks, 1):
            label = suggest(model, task["text"], think)
            counts[label] += 1
            out.write(json.dumps({"id": task["id"], "text": task["text"], "suggested": label,
                                  "suggested_by": model + (" (thinking)" if think else "")}) + "\n")
            if i % 50 == 0:
                print(f"{i}/{len(tasks)}  {time.time() - start:.0f} s  {counts}", flush=True)
    print(f"done: {len(tasks)} tasks in {time.time() - start:.0f} s  {counts}")


if __name__ == "__main__":
    main()
