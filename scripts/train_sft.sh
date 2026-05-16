#!/usr/bin/env bash
# Supervised fine-tuning baseline (paper Table 3).

source "$(dirname "$0")/_common.sh"

RUN_NAME="sft"

accelerate launch --config_file "${ACCELERATE_CONFIG}" -m tier.cli.train \
    --model "${TIER_MODEL}" \
    --run-name "${RUN_NAME}" \
    --objective SFT \
    --output-style json \
    --split-dataset \
    --full-finetuning \
    2>&1 | tee "$(log_path "${RUN_NAME}" train.log)"
