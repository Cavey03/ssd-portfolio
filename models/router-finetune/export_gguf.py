"""Turn a trained LoRA adapter into a GGUF model file that Ollama can run.

Both adapters (the one trained in Colab and the one trained on my GPU) go through this same step, so the
two models differ only in where they were trained.

  distrobox enter gpu -- ~/.venvs/unsloth-gpu/bin/python export_gguf.py runs/rtx5070
  ollama create router-rtx5070 -f runs/rtx5070/gguf_gguf/Modelfile   (on the host)

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
    # Unsloth saves the merged 16-bit model in `target` and the GGUF files in `target`_gguf.
    gguf_dir = target.parent / f"{target.name}_gguf"
    quantised = next(gguf_dir.glob("*Q4_K_M.gguf"))
    print("GGUF files:", [f"{p.name} ({p.stat().st_size / 1e9:.1f} GB)" for p in sorted(gguf_dir.glob("*.gguf"))])
    write_modelfile(gguf_dir, quantised.name)
    print("Next, on the host:  ollama create router-<name> -f", gguf_dir / "Modelfile")


# Gemma 4's chat format, exactly as in training: system, user, then the model's turn.
# (Unsloth's own Modelfile says `FROM .`, which also picks up the vision file, so it is replaced.)
TEMPLATE = """{{- range $i, $_ := .Messages }}
{{- $last := eq (len (slice $.Messages $i)) 1 }}
<|turn>{{ if eq .Role "assistant" }}model{{ else }}{{ .Role }}{{ end }}
{{ .Content }}{{ if not $last }}<turn|>
{{ end }}
{{- end }}<turn|>
<|turn>model
"""


def write_modelfile(gguf_dir: Path, gguf_name: str) -> None:
    """An explicit Modelfile: only the text model, the training chat format, stop at the end of the turn."""
    (gguf_dir / "Modelfile").write_text(
        f"FROM ./{gguf_name}\nTEMPLATE \"\"\"{TEMPLATE}\"\"\"\nPARAMETER stop \"<turn|>\"\n"
        "PARAMETER temperature 0\n")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--modelfile-only"]:  # rewrite the Modelfile of an existing export
        d = Path(sys.argv[2])
        write_modelfile(d, next(d.glob("*Q4_K_M.gguf")).name)
    else:
        main()
