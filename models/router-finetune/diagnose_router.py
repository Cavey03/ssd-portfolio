"""Look inside a trained adapter: how likely does it find each label, before any export or Ollama?

For each task the prompt is built exactly as in training, followed by the start of the answer
`{"agent": "`. The next token decides the label, so we read the model's probability for the first token
of "local", "codex" and "claude". This separates "the model didn't learn" from "the export broke it".

  distrobox enter gpu -- ~/.venvs/unsloth-gpu/bin/python diagnose_router.py runs/rtx5070 [data/test.jsonl]
"""

from __future__ import annotations

import json
import sys
from collections import Counter
import os
from pathlib import Path

NO_CACHE = os.environ.get("DIAG_NO_CACHE") == "1"
NO_BOS = os.environ.get("DIAG_NO_BOS") == "1"


def main() -> None:
    run = Path(sys.argv[1])
    data = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/train.jsonl")
    from unsloth import FastModel
    from unsloth.chat_templates import get_chat_template
    import torch

    from train_router import MAX_SEQ_LENGTH, to_messages

    model, tokenizer = FastModel.from_pretrained(model_name=str(run / "lora"), max_seq_length=MAX_SEQ_LENGTH,
                                                 load_in_4bit=True)
    tokenizer = get_chat_template(tokenizer, chat_template="gemma-4")
    FastModel.for_inference(model)
    text_tok = getattr(tokenizer, "tokenizer", tokenizer)  # Gemma 4 returns a processor; its text tokenizer
    label_ids = {lab: text_tok.encode(lab, add_special_tokens=False)[0] for lab in ("local", "codex", "claude")}
    print("first token per label:", {k: text_tok.decode([v]) for k, v in label_ids.items()})

    rows, seen = [], set()
    for r in map(json.loads, data.read_text().splitlines()):
        if r["id"] not in seen:
            seen.add(r["id"])
            rows.append(r)
    rows = [r for r in rows if r["label"] != "local"][:40] + [r for r in rows if r["label"] == "local"][:20]

    correct, confusion = 0, Counter()
    for r in rows:
        prompt = text_tok.apply_chat_template(to_messages(r["text"]), tokenize=False, add_generation_prompt=True)
        prompt += '{"agent": "'
        if NO_BOS:  # DIAG_NO_BOS=1: drop <bos>, as the (buggy) training data did
            prompt = prompt.removeprefix("<bos>")
        ids = text_tok(prompt, return_tensors="pt", add_special_tokens=False).to(model.device)
        with torch.no_grad():
            # DIAG_NO_CACHE=1: compute the way training does (no KV cache), to compare with normal inference.
            logits = model(**ids, use_cache=not NO_CACHE).logits[0, -1]
        probs = torch.softmax(logits[list(label_ids.values())].float(), dim=0).tolist()
        best = max(zip(label_ids, probs), key=lambda x: x[1])[0]
        correct += best == r["label"]
        confusion[(r["label"], best)] += 1
        print(f"{r['label']:<6} -> {best:<6}  " + "  ".join(f"{k} {p:.2f}" for k, p in zip(label_ids, probs))
              + f"   {r['text'][:60]}")
    print(f"\n{correct}/{len(rows)} correct on {data.name}; confusion (truth, predicted): {dict(confusion)}")
    print("Generation prompt ends with:", repr(prompt[-80:]))


if __name__ == "__main__":
    main()
