"""Split the reviewed labels into training and test data.

Input:  data/labels.jsonl   one line per task: id, text, suggested (Ornith), label (final), changed
Output: data/train.jsonl    what the model learns from
        data/test.jsonl     held out: never trained on, only used to measure the models

The split is stratified (each label keeps its share in both parts) and seeded, so it can be reproduced.

The labels are very unbalanced (real commits are mostly small: ~79% local). So the TRAINING file repeats the
rare classes (OVERSAMPLE: codex x2, claude x5), otherwise the model can score well by always answering
"local". The test file is left natural, and is never trained on.
"""

from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path

DATA = Path(__file__).parent / "data"
TEST_SHARE = 0.2
SEED = 626
OVERSAMPLE = {"local": 1, "codex": 2, "claude": 5}


def main() -> None:
    rows = [json.loads(line) for line in (DATA / "labels.jsonl").read_text().splitlines()]
    rng = random.Random(SEED)
    train: list[dict] = []
    test: list[dict] = []
    for label in sorted({r["label"] for r in rows}):
        group = [r for r in rows if r["label"] == label]
        rng.shuffle(group)
        cut = round(len(group) * TEST_SHARE)
        test += group[:cut]
        train += group[cut:] * OVERSAMPLE.get(label, 1)
    rng.shuffle(train)
    rng.shuffle(test)
    for name, part in (("train", train), ("test", test)):
        with (DATA / f"{name}.jsonl").open("w") as f:
            for r in part:
                f.write(json.dumps({"id": r["id"], "text": r["text"], "label": r["label"]}) + "\n")
        print(f"{name}: {len(part)}  {dict(Counter(r['label'] for r in part))}")


if __name__ == "__main__":
    main()
