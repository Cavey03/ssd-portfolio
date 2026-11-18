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
    # The training data is built into the notebook (it is small), so nothing has to be uploaded to Colab.
    train_data = (HERE / "data" / "train.jsonl").read_text()
    cells = [
        md("""
# Router fine-tune: Gemma 4 E2B with Unsloth (free Colab T4)
ITRI626 SU5–7. Teaches a small model to route coding tasks to `local`, `codex` or `claude`, from ~300 labelled
tasks. The **same** `train_router.py` also runs on my RTX 5070, so the two runs can be compared.

**Before you start:** *Runtime → Change runtime type → T4 GPU*. Then *Runtime → Run all*.
Everything needed (the training data and the script) is inside this notebook. At the end the result
(`colab-lora.zip`, ~100 MB) downloads by itself; if the browser asks, allow the download.
"""),
        md("## 1. Install Unsloth (2–4 minutes)"),
        code("!pip install -q unsloth\n!nvidia-smi --query-gpu=name,memory.total --format=csv"),
        md("## 2. The training data (identical to `data/train.jsonl` in the repo: 409 rows)"),
        code("!mkdir -p data"),
        code("%%writefile data/train.jsonl\n" + train_data),
        md("## 3. The training script (identical to `train_router.py` in the repo)"),
        code("%%writefile train_router.py\n" + script),
        md("## 4. Train (about 5–15 minutes on a T4)"),
        code("!python train_router.py --data data/train.jsonl --out runs/colab"),
        md("## 5. Download the result\nThe adapter is about 100 MB. It downloads to your Downloads folder; "
           "on the PC, `export_gguf.py` turns it into an Ollama model."),
        code("""
!cat runs/colab/metrics.json | head -12
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
