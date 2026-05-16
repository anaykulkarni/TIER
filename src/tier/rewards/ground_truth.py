"""Ground-truth-anchored reward variants.

These rewards bypass execution and score generations against a reference
``api_calls`` AST.  Useful for sanity checks but not trajectory-invariant —
they will penalise valid alternative solution paths and are included here
mostly for parity with prior work.
"""

from __future__ import annotations

import json


def calculate_simple_reward_with_gt(
    generations, answer, tag, api_calls, parser, style='xml', order_aware=True
):
    """Binary equivalence against the ground-truth AST."""
    rewards = []
    for gen, _ans, t, calls_gt in zip(generations, answer, tag, api_calls):
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
            calls, _return_all = parser.extract_tool_calls(gen, tag=t, style=style)
            calls_gt = json.loads(calls_gt) if isinstance(calls_gt, str) else calls_gt
        except Exception:
            rewards.append(reward)
            continue

        if not parser.check_response_equivalence(calls, calls_gt, order_aware=order_aware):
            rewards.append(reward)
            continue

        reward += 0.9
        rewards.append(reward)

    return rewards


def calculate_reward_with_gt(
    generations, answer, tag, api_calls, parser, style='xml', order_aware=True
):
    """Fine-grained reward but compared against the ground-truth AST."""
    rewards = []
    for gen, _ans, t, calls_gt in zip(generations, answer, tag, api_calls):
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
            calls_gt = json.loads(calls_gt) if isinstance(calls_gt, str) else calls_gt
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

        reward += 0.1

        if not parser.check_response_equivalence(calls, calls_gt, order_aware=order_aware):
            rewards.append(reward)
            continue
        reward += 0.5
        rewards.append(reward)

    return rewards
