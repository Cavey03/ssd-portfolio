"""Collect realistic coding-task descriptions from human-written commit messages.

Source: CommitPackFT (bigcode/commitpackft on Hugging Face, MIT licence): commits from permissively
licensed GitHub repos whose messages read like instructions ("Add retry to upload", "Fix typo in docs").
A commit subject is a good stand-in for a task someone would hand to a coding agent.

Only the first part of each language's file is streamed (the files are large: they also hold the code
before and after each commit). For each task we keep its source (language, repo, licence).

Usage: python3 fetch_tasks.py            -> data/tasks.jsonl
"""

from __future__ import annotations

import json
import random
import re
import urllib.request
from pathlib import Path

URL = "https://huggingface.co/datasets/bigcode/commitpackft/resolve/main/data/{lang}/data.jsonl"
# How many tasks per language: mostly the kinds of projects I work on (Python, web, docs, config).
PER_LANGUAGE = {
    "python": 110, "javascript": 45, "typescript": 40, "markdown": 30, "shell": 25, "go": 25,
    "rust": 25, "java": 20, "yaml": 20, "css": 15, "html": 15, "toml": 10,
}
LINES_TO_READ = 2500
SEED = 626  # ITRI626: a fixed seed so the sample can be reproduced
OUT = Path(__file__).parent / "data" / "tasks.jsonl"

BORING = re.compile(
    r"^(merge|initial commit|wip|bump|version|release|update [\w./-]+$|changelog|typo$|cleanup$|fix$|"
    r"minor|small|tweak|oops|revert|test commit)", re.I)


def good_subject(text: str) -> bool:
    """A subject that reads like a task: an instruction of sensible length, in plain ASCII English."""
    return (
        20 <= len(text) <= 110
        and text.isascii()
        and text[0].isalpha()
        and len(text.split()) >= 4
        and not BORING.match(text)
        and "http" not in text
    )


def stream_subjects(lang: str) -> list[dict[str, str]]:
    """Read the first LINES_TO_READ commits of one language and keep the usable subjects."""
    found: list[dict[str, str]] = []
    request = urllib.request.Request(URL.format(lang=lang), headers={"User-Agent": "router-finetune"})
    with urllib.request.urlopen(request, timeout=60) as response:
        for i, raw in enumerate(response):
            if i >= LINES_TO_READ:
                break
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            subject = (row.get("subject") or row.get("message") or "").strip().splitlines()[0].strip().rstrip(".")
            if good_subject(subject):
                found.append({"text": subject, "lang": lang, "repo": str(row.get("repos", "")).split(",")[0],
                              "license": str(row.get("license", ""))})
    return found


def main() -> None:
    rng = random.Random(SEED)
    tasks: list[dict[str, str]] = []
    seen: set[str] = set()
    for lang, count in PER_LANGUAGE.items():
        for attempt in range(3):  # the CDN sometimes drops long downloads: try again
            try:
                subjects = stream_subjects(lang)
                break
            except OSError as exc:
                print(f"{lang}: {exc}, retrying")
        else:
            raise SystemExit(f"could not download {lang}")
        candidates = [c for c in subjects if c["text"].lower() not in seen]
        rng.shuffle(candidates)
        picked = []
        for c in candidates:
            if c["text"].lower() in seen:
                continue
            seen.add(c["text"].lower())
            picked.append(c)
            if len(picked) == count:
                break
        print(f"{lang:<11} {len(candidates):>4} usable, {len(picked)} taken")
        tasks.extend(picked)
    rng.shuffle(tasks)
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w") as f:
        for i, task in enumerate(tasks):
            f.write(json.dumps({"id": f"t{i:03d}", **task}) + "\n")
    print(f"{len(tasks)} tasks -> {OUT}")


if __name__ == "__main__":
    main()
