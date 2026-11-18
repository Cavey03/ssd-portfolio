"""Build the Google Colab notebook from train_router.py, so Colab runs exactly the same training code.

Usage: python3 make_notebook.py   -> colab/router_finetune_colab.ipynb
Re-run it after changing train_router.py.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(keepends=True)}


def code(text: str) -> dict:
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": text.strip("\n").splitlines(keepends=True)}


def main() -> None:
    script = (HERE / "train_router.py").read_text()
    cells = [
        md("""
# Router fine-tune: Gemma 4 E2B with Unsloth (free Colab T4)
ITRI626 SU5–7. Teaches a small model to route coding tasks to `local`, `codex` or `claude`, from ~300 labelled
tasks. The **same** `train_router.py` also runs on my RTX 5070, so the two runs can be compared.

**Before you start:** *Runtime → Change runtime type → T4 GPU*. Then run the cells in order
(*Runtime → Run all* works too; the upload cell waits for you to choose the file).
"""),
        md("## 1. Install Unsloth (2–4 minutes)"),
        code("!pip install -q unsloth\n!nvidia-smi --query-gpu=name,memory.total --format=csv"),
        md("## 2. Upload the training data\nChoose `train.jsonl` from `models/router-finetune/data/` in the portfolio."),
        code("""
import os, shutil
from google.colab import files
uploaded = files.upload()
os.makedirs("data", exist_ok=True)
shutil.move(next(iter(uploaded)), "data/train.jsonl")
print(sum(1 for _ in open("data/train.jsonl")), "examples")
"""),
        md("## 3. The training script (identical to `train_router.py` in the repo)"),
        code("%%writefile train_router.py\n" + script),
        md("## 4. Train (about 5–15 minutes on a T4)"),
        code("!python train_router.py --data data/train.jsonl --out runs/colab"),
        md("## 5. Download the result\nThe adapter is small (tens of MB). Put the zip in `models/router-finetune/runs/` "
           "and unzip it there; `export_gguf.py` turns it into an Ollama model on my PC."),
        code("""
!cd runs && zip -qr colab-lora.zip colab/lora colab/metrics.json && ls -lh colab-lora.zip
from google.colab import files
files.download("runs/colab-lora.zip")
"""),
    ]
    notebook = {
        "cells": cells,
        "metadata": {
            "accelerator": "GPU",
            "colab": {"gpuType": "T4", "provenance": []},
            "kernelspec": {"display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4, "nbformat_minor": 0,
    }
    out = HERE / "colab" / "router_finetune_colab.ipynb"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(notebook, indent=1))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
