#!/usr/bin/env bash
# Outcome-only reward baseline (paper Table 1, row "Simple").

source "$(dirname "$0")/_common.sh"

RUN_NAME="simple"

accelerate launch --config_file "${ACCELERATE_CONFIG}" -m tier.cli.train \
    --model "${TIER_MODEL}" \
    --run-name "${RUN_NAME}" \
    --reward-type simple \
    --objective GRPO_BNPO \
    --output-style json \
    --split-dataset \
    --full-finetuning \
    2>&1 | tee "$(log_path "${RUN_NAME}" train.log)"
