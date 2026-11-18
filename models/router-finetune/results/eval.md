Held-out test tasks: 76

| Model | Prompt | Accuracy | Balanced accuracy | Recall local | Recall codex | Recall claude | Median time |
|---|---|---|---|---|---|---|---|
| gemma4:e2b | guidelines | 75% | **52%** | 80% | 75% | 0% | 0.08 s |
| router-rtx5070 | short | 82% | **63%** | 90% | 50% | 50% | 0.05 s |
| always local (baseline) | – | 79% | **33%** | 100% | 0% | 0% | – |
| ornith-1.5:9b (no thinking) | guidelines | 78% | **41%** | 97% | 0% | 25% | – |
| ornith-1.5:9b (thinking) | guidelines | 51% | **62%** | 52% | 33% | 100% | – |
