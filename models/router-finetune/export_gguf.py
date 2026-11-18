"""Turn a trained LoRA adapter into a GGUF model file that Ollama can run.

Both adapters (the one trained in Colab and the one trained on my GPU) go through this same step, so the
two models differ only in where they were trained.

  distrobox enter gpu -- ~/.venvs/unsloth-gpu/bin/python export_gguf.py runs/rtx5070
  ollama create router-rtx5070 -f runs/rtx5070/gguf/Modelfile        (on the host)

Unsloth merges the adapter into the base model and converts it with llama.cpp to GGUF, quantised to
Q4_K_M (4-bit, the same kind of quantisation as my other Ollama models). Weights stay out of git.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    run = Path(sys.argv[1])
    adapter, target = run / "lora", run / "gguf"
    from unsloth import FastModel
    from unsloth.chat_templates import get_chat_template

    from train_router import MAX_SEQ_LENGTH

    # Loading the adapter folder loads its base model (named in adapter_config.json) with it.
    model, tokenizer = FastModel.from_pretrained(model_name=str(adapter), max_seq_length=MAX_SEQ_LENGTH,
                                                 load_in_4bit=False)
    tokenizer = get_chat_template(tokenizer, chat_template="gemma-4")
    model.save_pretrained_gguf(str(target), tokenizer, quantization_method="q4_k_m")
    ggufs = sorted(target.glob("*.gguf"), key=lambda p: p.stat().st_size, reverse=True)
    print("GGUF files:", [f"{p.name} ({p.stat().st_size / 1e9:.1f} GB)" for p in ggufs])
    if not (target / "Modelfile").exists() and ggufs:
        # Unsloth usually writes a Modelfile; if not, a minimal one (Ollama reads the chat template from the GGUF).
        (target / "Modelfile").write_text(f"FROM ./{ggufs[0].name}\n")
    print("Next, on the host:  ollama create router-<name> -f", target / "Modelfile")


if __name__ == "__main__":
    main()
