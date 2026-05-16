#!/usr/bin/env bash
# +Parsing ablation: format + parse + answer (no execution signal).  Paper
# Table 2 row "+Parsing (no Execution)".

source "$(dirname "$0")/_common.sh"

RUN_NAME="parsing"

accelerate launch --config_file "${ACCELERATE_CONFIG}" -m tier.cli.train \
    --model "${TIER_MODEL}" \
    --run-name "${RUN_NAME}" \
    --reward-type finegrained_with_parsing \
    --objective GRPO_BNPO \
    --output-style json \
    --split-dataset \
    --full-finetuning \
    2>&1 | tee "$(log_path "${RUN_NAME}" train.log)"
