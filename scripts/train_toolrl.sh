#!/usr/bin/env bash
# ToolRL trajectory-supervised baseline (paper Table 1, row "ToolRL").

source "$(dirname "$0")/_common.sh"

RUN_NAME="toolrl"

accelerate launch --config_file "${ACCELERATE_CONFIG}" -m tier.cli.train \
    --model "${TIER_MODEL}" \
    --run-name "${RUN_NAME}" \
    --reward-type tool_rl \
    --objective GRPO_BNPO \
    --output-style json \
    --split-dataset \
    --full-finetuning \
    2>&1 | tee "$(log_path "${RUN_NAME}" train.log)"
