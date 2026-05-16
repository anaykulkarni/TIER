"""Execution-only ablation (format + execution + answer, no parsing signal).

Paper Table 2 row "+Execution (no Parsing)".  This is the configuration that
exhibits the reward-hacking behaviour discussed in §4.3: the model learns to
route queries to a small set of "safe" tools that reliably execute without
producing the correct answer.  The final reward is renormalised to ``[0, 1]``.
"""

from __future__ import annotations


def calculate_reward_with_execution(generations, answer, tag, parser, style='xml', order_aware=True):
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

        reward += 0.1

        if not parser.check_response_equivalence(result, ans, order_aware=order_aware):
            rewards.append(reward)
            continue
        reward += 0.5

        # Renormalise to [0, 1] for scale parity with TIER.
        reward = reward / 0.7
        rewards.append(reward)

    return rewards
