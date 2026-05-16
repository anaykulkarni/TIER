#!/usr/bin/env bash
# +Execution ablation: format + exec + answer (no parsing signal).  Paper
# Table 2 row "+Execution (no Parsing)" — this is the configuration that
# exhibits reward-hacking in §4.3.

source "$(dirname "$0")/_common.sh"

RUN_NAME="execution"

accelerate launch --config_file "${ACCELERATE_CONFIG}" -m tier.cli.train \
    --model "${TIER_MODEL}" \
    --run-name "${RUN_NAME}" \
    --reward-type finegrained_with_execution \
    --objective GRPO_BNPO \
    --output-style json \
    --split-dataset \
    --full-finetuning \
    2>&1 | tee "$(log_path "${RUN_NAME}" train.log)"
