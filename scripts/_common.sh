#!/usr/bin/env bash
# Shared environment + paths for every training / evaluation script.  Source
# this from the top of a run script with ``source "$(dirname "$0")/_common.sh"``.

set -euo pipefail

# Resolve the repo root regardless of the user's current working directory.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

export TIER_REPO_ROOT="${REPO_ROOT}"
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"
export VLLM_USE_V1="${VLLM_USE_V1:-0}"
# Default to Blackwell-class compute (paper experiments).  Override for
# other generations by exporting ``TORCH_CUDA_ARCH_LIST`` before launch.
export TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST:-12.0}"

# Default model.  Override by exporting ``TIER_MODEL`` in your shell.
TIER_MODEL="${TIER_MODEL:-Qwen/Qwen3-8B}"

ACCELERATE_CONFIG="${REPO_ROOT}/configs/accelerate.yaml"

OUTPUTS_ROOT="${REPO_ROOT}/outputs"
mkdir -p "${OUTPUTS_ROOT}"

log_path() {
    local run_name="$1"
    mkdir -p "${OUTPUTS_ROOT}/${run_name}"
    echo "${OUTPUTS_ROOT}/${run_name}/$2"
}
