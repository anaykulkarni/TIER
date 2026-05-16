#!/usr/bin/env bash
# Evaluate every checkpoint of the TIER training run on the held-out
# DepthBench split.

source "$(dirname "$0")/_common.sh"

RUN_NAME="tier"

python -m tier.cli.eval \
    --model "${TIER_MODEL}" \
    --run-name "${RUN_NAME}" \
    --output-style json \
    --split-dataset \
    --full-finetuned \
    --is-deepspeed \
    2>&1 | tee "$(log_path "${RUN_NAME}" eval.log)"
