"""Parsing-only ablation (format + parse + answer, no execution signal).

Used in paper Table 2 row "+Parsing (no Execution)".  The final reward is
renormalised to ``[0, 1]`` to keep magnitudes comparable with the full TIER
reward and other ablations.
"""

from __future__ import annotations


def calculate_reward_with_parsing(generations, answer, tag, parser, style='xml', order_aware=True):
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
            scores, _ = parser.validate_ast_against_function_definitions(calls)
            name_error, param_error, type_error = scores
            r_name = 0.1 if not name_error else 0.0
            r_param = 0.1 if param_error == 0 else max(0.0, 0.1 - 0.025 * param_error)
            r_type = 0.1 if type_error == 0 else max(0.0, 0.1 - 0.025 * type_error)
            reward += r_name + r_param + r_type
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
        reward += 0.5

        # Renormalise to [0, 1] for scale parity with TIER.
        reward = reward / 0.9
        rewards.append(reward)

    return rewards
