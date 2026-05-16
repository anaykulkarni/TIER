#!/usr/bin/env bash
# Evaluate checkpoints from the +Execution ablation run.

source "$(dirname "$0")/_common.sh"

RUN_NAME="execution"

python -m tier.cli.eval \
    --model "${TIER_MODEL}" \
    --run-name "${RUN_NAME}" \
    --output-style json \
    --split-dataset \
    --full-finetuned \
    --is-deepspeed \
    2>&1 | tee "$(log_path "${RUN_NAME}" eval.log)"
