#!/usr/bin/env bash
# Install TIER in editable mode along with the CUDA-specific accelerators
# (vLLM, FlashAttention, FlashInfer).  Re-run this whenever requirements.txt
# or pyproject.toml change.
#
# Usage:
#   bash install.sh              # CPU + CUDA stack (default)
#   bash install.sh --no-cuda    # CPU-only (skip vllm/flash-attn/flashinfer)

set -euo pipefail

SKIP_CUDA=0
for arg in "$@"; do
    case "$arg" in
        --no-cuda) SKIP_CUDA=1 ;;
        *) echo "Unknown argument: $arg" >&2; exit 1 ;;
    esac
done

# 1. Bootstrap build tooling.
pip install --upgrade pip setuptools wheel
pip install uv ninja packaging psutil

# 2. Core dependencies and editable install of the package itself.
pip install -r requirements.txt
pip install -e .

# 3. CUDA accelerators (matched to the cu128 / Blackwell setup used in the paper).
if [[ "${SKIP_CUDA}" -eq 0 ]]; then
    uv pip install vllm==0.10.2 --torch-backend=cu128
    pip install flash-attn --no-build-isolation
    pip install flashinfer-python flashinfer-cubin
    pip install flashinfer-jit-cache --index-url https://flashinfer.ai/whl/cu128/

    # Sanity check.
    python -c "import torch; print('CUDA:', torch.version.cuda)"
    python -c "import flash_attn; print('flash-attn OK')"
    flashinfer show-config || true
fi

echo "Installation complete."
