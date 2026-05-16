"""Bridge between our pipeline's data format and ToolRL's reward primitives.

ToolRL (Qian et al., 2025) is the trajectory-supervised baseline used in
the paper's Table 1 / Table 3 comparisons.  The primitives live in
:mod:`tier.rewards._toolrl_external` (adapted from the official ToolRL
release); this module reshapes our generations and ground-truth ASTs into
the layout those primitives expect, then aggregates per-sample rewards.
"""

from __future__ import annotations

import json
import os
import re

from tier.rewards._toolrl_external import (
    customize_correctness_reward_tool as tool_rl_correctness_reward,
    customize_format_reward_func as tool_rl_format_reward,
    customize_length_reward_func as tool_rl_length_reward,
)


def _build_tool_rl_ground_truth(api_calls_entry):
    """Convert our numbered AST into the ``<tool_call>`` ToolRL expects."""
    calls = json.loads(api_calls_entry) if isinstance(api_calls_entry, str) else api_calls_entry

    tool_lines = []
    for idx in sorted(calls.keys(), key=lambda k: int(k)):
        entry = calls[idx]
        for func_name, params in entry.items():
            tool_lines.append(json.dumps({"name": func_name, "parameters": params}))

    return "<tool_call>\n" + "\n".join(tool_lines) + "\n</tool_call>"


def _translate_generation_to_tool_rl_format(gen, tag, parser, style="json"):
    """Re-serialise a model generation into the ToolRL layout."""
    try:
        is_valid, _ = parser.check_format(gen, style=style)
        if not is_valid:
            return gen

        think_match = re.search(r"<think\b[^>]*>([\s\S]*?)</think>", gen, re.S)
        think_content = think_match.group(1).strip() if think_match else ""

        calls, _ = parser.extract_tool_calls(gen, tag=tag, style=style)
        if not calls:
            return gen

        tool_lines = []
        for idx in sorted(calls.keys(), key=lambda k: int(k)):
            entry = calls[idx]
            for func_name, params in entry.items():
                clean_params = {k: v for k, v in params.items() if k != "tag"}
                tool_lines.append(json.dumps({"name": func_name, "parameters": clean_params}))

        return (
            f"<think>{think_content}</think>\n"
            f"<tool_call>\n"
            + "\n".join(tool_lines)
            + "\n</tool_call>"
        )
    except Exception:
        return gen


def calculate_tool_rl_reward(generations, answer, tag, api_calls, parser, style='xml'):
    """Compute rewards using the ToolRL scoring pipeline."""
    ground_truths = [_build_tool_rl_ground_truth(ac) for ac in api_calls]

    translated = [
        _translate_generation_to_tool_rl_format(gen, t, parser, style)
        for gen, t in zip(generations, tag)
    ]
    completions = [[{"role": "assistant", "content": g}] for g in translated]

    format_max, format_min = 1.0, 0.0
    if str(os.getenv("CORRECTMAX1", 0)) == "1":
        tool_max, tool_min = 1.0, -1.0
    else:
        tool_max, tool_min = 3.0, -3.0
    length_max, length_min = 1.0, 0.0

    rewards = []
    for comp, gt in zip(completions, ground_truths):
        batch_comp = [comp]
        batch_gt = [gt]

        fmt = tool_rl_format_reward(batch_comp, batch_gt, 0, format_max, format_min)[0]
        cor = tool_rl_correctness_reward(batch_comp, batch_gt, 0, tool_max, tool_min)[0]

        if str(os.getenv("WITHLENGTH", 0)) == "1":
            lng = tool_rl_length_reward(batch_comp, batch_gt, 0, length_max, length_min)[0]
        else:
            lng = 0.0

        rewards.append(fmt + cor + lng)

    return rewards
