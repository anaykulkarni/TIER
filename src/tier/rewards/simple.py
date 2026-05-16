"""Outcome-only baseline reward (paper Table 1 row "Simple")."""

from __future__ import annotations


def calculate_simple_reward(generations, answer, tag, parser, style='xml', order_aware=True):
    """Format validity + binary answer correctness, no intermediate signal."""
    rewards = []
    for gen, ans, t in zip(generations, answer, tag):
        reward = 0.0
        try:
            is_valid_format, _ = parser.check_format(gen, style=style)
            if not is_valid_format:
                rewards.append(reward)
                continue
        except Exception:
            rewards.append(reward)
            continue

        reward += 0.1

        try:
            calls, return_all = parser.extract_tool_calls(gen, tag=t, style=style)
        except Exception:
            rewards.append(reward)
            continue

        try:
            result = parser.execute_syntax_tree(calls, return_all)
            result = parser.serialize_response(result)
        except Exception:
            rewards.append(reward)
            continue

        if not parser.check_response_equivalence(result, ans, order_aware=order_aware):
            rewards.append(reward)
            continue

        reward += 0.9
        rewards.append(reward)

    return rewards
