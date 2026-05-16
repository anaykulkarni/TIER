#!/usr/bin/env bash
# DAPO objective variant of the full TIER reward (Appendix F).

source "$(dirname "$0")/_common.sh"

RUN_NAME="tier_dapo"

accelerate launch --config_file "${ACCELERATE_CONFIG}" -m tier.cli.train \
    --model "${TIER_MODEL}" \
    --run-name "${RUN_NAME}" \
    --reward-type finegrained \
    --objective GRPO_DAPO \
    --output-style json \
    --split-dataset \
    --full-finetuning \
    2>&1 | tee "$(log_path "${RUN_NAME}" train.log)"
