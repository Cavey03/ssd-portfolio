"""Measure every router on the held-out test tasks, through Ollama (how it would really be used).

Models compared on data/test.jsonl:
  * gemma4:e2b                 the base model, NOT fine-tuned, given the full routing guidelines (fair chance)
  * router-colab, router-rtx5070  the fine-tuned models, given only the short instruction they were trained with
  * ornith-1.5:9b              the pre-labeller, thinking off and on (taken from its pre-label files)

All models use structured output (the answer must be {"agent": ...}) and temperature 0, so every answer is
valid and the run is repeatable. Reports accuracy, recall per class, a confusion table and speed.

Usage: python3 eval_router.py [model ...]     -> results/eval.json, results/eval.md
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from prelabel import GUIDELINES, LABELS, SCHEMA
from train_router import SYSTEM_PROMPT

HERE = Path(__file__).parent
URL = "http://127.0.0.1:11434/api/chat"
BASE = "gemma4:e2b"
DEFAULT_MODELS = [BASE, "router-colab", "router-rtx5070"]


def ask(model: str, system: str, task: str) -> tuple[str, float]:
    """One routing answer and how long it took."""
    body = json.dumps({
        "model": model, "stream": False, "think": False, "format": SCHEMA, "options": {"temperature": 0},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": f"Task: {task}"}],
    }).encode()
    request = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    started = time.time()
    with urllib.request.urlopen(request, timeout=300) as response:
        content = json.loads(response.read())["message"]["content"]
    try:
        agent = json.loads(content).get("agent")
    except json.JSONDecodeError:
        agent = None
    return (agent if agent in LABELS else "invalid"), time.time() - started


def score(truth: list[str], predicted: list[str]) -> dict:
    """Accuracy, recall per class, balanced accuracy and the confusion table (rows: truth, columns: predicted).

    Balanced accuracy is the mean of the per-class recalls: with ~79% "local" tasks, always answering
    "local" gets 79% accuracy but only 33% balanced accuracy, so it shows whether a model really routes.
    """
    accuracy = sum(t == p for t, p in zip(truth, predicted)) / len(truth)
    recall = {}
    for label in LABELS:
        idx = [i for i, t in enumerate(truth) if t == label]
        recall[label] = round(sum(predicted[i] == label for i in idx) / len(idx), 3) if idx else None
    confusion = {t: {p: sum(1 for a, b in zip(truth, predicted) if a == t and b == p)
                     for p in (*LABELS, "invalid")} for t in LABELS}
    present = [v for v in recall.values() if v is not None]
    return {"accuracy": round(accuracy, 3), "balanced_accuracy": round(sum(present) / len(present), 3),
            "recall": recall, "confusion": confusion}


def main() -> None:
    test = [json.loads(line) for line in (HERE / "data" / "test.jsonl").read_text().splitlines()]
    truth = [r["label"] for r in test]
    results: dict[str, dict] = {}

    for model in sys.argv[1:] or DEFAULT_MODELS:
        system = GUIDELINES if model == BASE or not model.startswith("router") else SYSTEM_PROMPT
        try:
            answers = [ask(model, system, r["text"]) for r in test]
        except urllib.error.URLError as exc:
            print(f"{model}: skipped ({exc})")
            continue
        predicted = [a for a, _ in answers]
        seconds = [s for _, s in answers]
        results[model] = {**score(truth, predicted), "prompt": "guidelines" if system == GUIDELINES else "short",
                          "median_seconds": round(sorted(seconds)[len(seconds) // 2], 3),
                          "predictions": dict(zip((r["id"] for r in test), predicted))}
        print(f"{model:<16} accuracy {results[model]['accuracy']:.0%}  balanced {results[model]['balanced_accuracy']:.0%}"
              f"  recall {results[model]['recall']}")

    # Baseline: always answer "local", the most common label.
    results["always local (baseline)"] = {**score(truth, ["local"] * len(truth)), "prompt": "–"}

    # The pre-labeller's suggestions on the same tasks (already computed, no need to ask again).
    for name, file in (("ornith-1.5:9b (no thinking)", "prelabels-nothink.jsonl"),
                       ("ornith-1.5:9b (thinking)", "prelabels.jsonl")):
        path = HERE / "data" / file
        if path.exists():
            suggested = {r["id"]: r["suggested"] for r in map(json.loads, path.read_text().splitlines())}
            predicted = [suggested.get(r["id"], "invalid") for r in test]
            results[name] = {**score(truth, predicted), "prompt": "guidelines"}
            print(f"{name:<28} accuracy {results[name]['accuracy']:.0%}")

    out = HERE / "results"
    out.mkdir(exist_ok=True)
    (out / "eval.json").write_text(json.dumps({"test_tasks": len(test), "results": results}, indent=2))
    lines = [f"Held-out test tasks: {len(test)}\n", "| Model | Prompt | Accuracy | Balanced accuracy | Recall local | "
             "Recall codex | Recall claude | Median time |", "|---|---|---|---|---|---|---|---|"]
    for name, r in results.items():
        rec = r["recall"]
        fmt = lambda v: "–" if v is None else f"{v:.0%}"
        speed = f"{r['median_seconds']:.2f} s" if "median_seconds" in r else "–"
        lines.append(f"| {name} | {r['prompt']} | {r['accuracy']:.0%} | **{r['balanced_accuracy']:.0%}** | {fmt(rec['local'])} | "
                     f"{fmt(rec['codex'])} | {fmt(rec['claude'])} | {speed} |")
    (out / "eval.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
