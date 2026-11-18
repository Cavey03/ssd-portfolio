#!/usr/bin/env bash
# Create the `gpu` Distrobox container for fine-tuning with Unsloth, and its Python environment.
# Run on the host. Safe to re-run: existing parts are kept.
#
# Why a separate container: `dev` has no NVIDIA access and Python 3.14, while Unsloth needs CUDA and
# Python 3.11-3.13. Ubuntu 24.04 ships Python 3.12, the version ML packages support best.
# `--nvidia` gives the container the host's NVIDIA driver; PyTorch brings its own CUDA libraries.
set -euo pipefail

VENV="$HOME/.venvs/unsloth-gpu"   # big (several GB), so outside the git repo

if ! podman container exists gpu; then
    distrobox create --name gpu --image quay.io/toolbx/ubuntu-toolbox:24.04 --nvidia --yes
fi

distrobox enter gpu -- bash -lc "
    set -euo pipefail
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
    # venv: isolated Python; dev headers + compiler: some packages build small extensions (Triton);
    # cmake/git/curl: needed by llama.cpp to export the model to GGUF for Ollama.
    sudo apt-get update -qq
    sudo apt-get install -y -qq python3-venv python3-dev build-essential cmake git curl libcurl4-openssl-dev
    [ -d '$VENV' ] || python3 -m venv '$VENV'
    '$VENV/bin/pip' install -q --upgrade pip
    '$VENV/bin/pip' install -q unsloth
    '$VENV/bin/python' -c 'import torch; print(\"torch\", torch.__version__, \"CUDA\", torch.version.cuda, \"GPU ok:\", torch.cuda.is_available(), torch.cuda.get_device_name(0))'
    '$VENV/bin/python' -c 'import unsloth; print(\"unsloth\", unsloth.__version__)'
"
