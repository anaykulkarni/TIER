#!/usr/bin/env bash
# TIER (full reward) on DepthBench.
#
# Reproduces the final row of Table 1 / Table 2 — the trajectory-invariant
# fine-grained reward decomposing into format + parse + exec + answer.

source "$(dirname "$0")/_common.sh"

RUN_NAME="tier"

accelerate launch --config_file "${ACCELERATE_CONFIG}" -m tier.cli.train \
    --model "${TIER_MODEL}" \
    --run-name "${RUN_NAME}" \
    --reward-type finegrained \
    --objective GRPO_BNPO \
    --output-style json \
    --split-dataset \
    --full-finetuning \
    2>&1 | tee "$(log_path "${RUN_NAME}" train.log)"
