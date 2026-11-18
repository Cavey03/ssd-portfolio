"""Fine-tune Gemma 4 E2B with Unsloth to route coding tasks (local / codex / claude).

The same file runs in both places, so the two runs are directly comparable:
  * Google Colab, free T4 GPU   (the notebook writes this file and runs it)
  * my RTX 5070, in the `gpu` Distrobox container
      distrobox enter gpu -- ~/.venvs/unsloth-gpu/bin/python train_router.py --out runs/rtx5070

Method: QLoRA. The base model is loaded in 4-bit and frozen; small LoRA adapter matrices are added to the
attention and MLP layers and only those are trained. The loss is computed on the answer only
(train_on_responses_only), so the model learns to produce the label, not to repeat the task text.

Output (in --out): the LoRA adapter, and metrics.json (GPU, time, peak memory, losses).
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

BASE_MODEL = "unsloth/gemma-4-E2B-it"
SYSTEM_PROMPT = "Route the coding task to one worker: local, codex or claude. Answer with JSON."
MAX_SEQ_LENGTH = 512  # a task plus its answer is under 100 tokens


def to_messages(task: str, label: str | None = None) -> list[dict[str, str]]:
    """One example in chat form. Without a label: the prompt for inference."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": f"Task: {task}"}]
    if label is not None:
        messages.append({"role": "assistant", "content": json.dumps({"agent": label})})
    return messages


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/train.jsonl")
    parser.add_argument("--out", default="runs/colab")
    parser.add_argument("--epochs", type=float, default=3)
    parser.add_argument("--rank", type=int, default=16)
    args = parser.parse_args()

    # Imported here so the helpers above can be used without a GPU (evaluation, tests).
    # Unsloth must come first: it patches transformers/trl for speed and memory when imported.
    from unsloth import FastModel
    from unsloth.chat_templates import get_chat_template, train_on_responses_only
    import torch
    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    started = time.time()

    # 1. The base model in 4-bit (QLoRA): ~2B effective parameters, fits a free T4 and a 12 GB card.
    model, tokenizer = FastModel.from_pretrained(
        model_name=BASE_MODEL, dtype=None, max_seq_length=MAX_SEQ_LENGTH,
        load_in_4bit=True, full_finetuning=False,
    )
    # 2. LoRA adapters on the language layers only (the vision and audio parts aren't needed).
    model = FastModel.get_peft_model(
        model, finetune_vision_layers=False, finetune_language_layers=True,
        finetune_attention_modules=True, finetune_mlp_modules=True,
        r=args.rank, lora_alpha=args.rank, lora_dropout=0, bias="none", random_state=3407,
    )
    # 3. Gemma 4's chat format ("gemma-4" = without thinking, recommended for the small models).
    tokenizer = get_chat_template(tokenizer, chat_template="gemma-4")
    rows = [json.loads(line) for line in Path(args.data).read_text().splitlines()]
    texts = [
        tokenizer.apply_chat_template(to_messages(r["text"], r["label"]), tokenize=False,
                                      add_generation_prompt=False).removeprefix("<bos>")
        for r in rows
    ]
    dataset = Dataset.from_dict({"text": texts})
    print(f"{len(texts)} training examples. First one:\n{texts[0]}")

    # 4. Training: small batches, 3 passes over the data, the usual QLoRA learning rate.
    trainer = SFTTrainer(
        model=model, tokenizer=tokenizer, train_dataset=dataset,
        args=SFTConfig(
            dataset_text_field="text", per_device_train_batch_size=4, gradient_accumulation_steps=2,
            num_train_epochs=args.epochs, warmup_steps=5, learning_rate=2e-4, logging_steps=5,
            optim="adamw_8bit", weight_decay=0.001, lr_scheduler_type="linear", seed=3407,
            max_length=MAX_SEQ_LENGTH, output_dir=str(out / "checkpoints"), save_strategy="no",
            report_to="none",
        ),
    )
    # Learn only the answer: everything before Gemma 4's model turn marker is masked out of the loss.
    trainer = train_on_responses_only(trainer, instruction_part="<|turn>user\n", response_part="<|turn>model\n")
    torch.cuda.reset_peak_memory_stats()
    train_started = time.time()
    stats = trainer.train()
    train_seconds = time.time() - train_started

    # 5. Save the adapter (tens of MB). export_gguf.py turns it into a model for Ollama.
    model.save_pretrained(str(out / "lora"))
    tokenizer.save_pretrained(str(out / "lora"))
    metrics = {
        "gpu": torch.cuda.get_device_name(0),
        "base_model": BASE_MODEL,
        "examples": len(texts), "epochs": args.epochs, "lora_rank": args.rank,
        "train_seconds": round(train_seconds, 1),
        "total_seconds": round(time.time() - started, 1),
        "peak_vram_gb": round(torch.cuda.max_memory_reserved() / 1024**3, 2),
        "final_loss": round(stats.training_loss, 4),
        "loss_log": [{"step": h["step"], "loss": h["loss"]} for h in trainer.state.log_history if "loss" in h],
    }
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps({k: v for k, v in metrics.items() if k != "loss_log"}, indent=2))


if __name__ == "__main__":
    main()
