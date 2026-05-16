"""Multi-turn variants of the TIER reward.

These produce both a scalar reward and a tool-response string that is fed
back to the model on the next turn.  Used by the multi-turn training loop
discussed in the future-work section of the paper.
"""

from __future__ import annotations

import json


def calculate_reward_multiturn(
    generations, answer, tag, parser, style="xml", order_aware=True
):
    rewards = []
    tool_responses = []
    for gen, ans, t in zip(generations, answer, tag):
        reward = 0.0
        try:
            is_valid_format, errors = parser.check_format(gen, style=style)
            if not is_valid_format:
                rewards.append(reward)
                tool_responses.append(f'{style} Format is incorrect: ' + ', '.join(errors))
                continue
        except Exception as e:
            rewards.append(reward)
            tool_responses.append(f'{style} Format is incorrect. Encountered exception: ' + str(e))
            continue

        reward += 0.1

        try:
            calls, return_all = parser.extract_tool_calls(gen, tag=t, style=style)
        except Exception as e:
            rewards.append(reward)
            tool_responses.append('Failed to parse XML. Encountered exception: ' + str(e))
            continue

        try:
            scores, validation_results = parser.validate_ast_against_function_definitions(calls)
            name_error, param_error, type_error = scores
            r_name = 0.1 if not name_error else 0.0
            r_param = 0.1 if param_error == 0 else max(0.0, 0.1 - 0.025 * param_error)
            r_type = 0.1 if type_error == 0 else max(0.0, 0.1 - 0.025 * type_error)
            reward += r_name + r_param + r_type

            parsing_response = parser.format_validation_results(validation_results)
            if not parsing_response or parsing_response.strip() == "":
                parsing_response = ""
        except Exception as e:
            rewards.append(reward)
            tool_responses.append('Failed to validate API calls. Encountered exception: ' + str(e))
            continue

        try:
            result = parser.execute_syntax_tree(calls, return_all)
            result = parser.serialize_response(result)

            if not result or result.strip() == "":
                api_response = "(empty response)"
            else:
                try:
                    api_response = json.dumps(json.loads(result), indent=4)
                except json.JSONDecodeError:
                    api_response = str(result)
        except Exception as e:
            rewards.append(reward)
            tool_responses.append(
                parsing_response + '\nFailed to execute API. Encountered exception: ' + str(e)
            )
            continue

        reward += 0.1

        if not parser.check_response_equivalence(result, ans, order_aware=order_aware):
            rewards.append(reward)
            tool_responses.append(f"{parsing_response}\n{api_response}\n")
            continue
        reward += 0.5

        rewards.append(reward)
        tool_responses.append(f"\n{api_response}\n")

    return rewards, tool_responses


def calculate_reward_with_env_response(
    generations, answer, tag, solved, parser, style="xml", order_aware=True
):
    """Variant that also returns whether each sample should be retried."""
    rewards = []
    tool_responses = []
    include = []
    for gen, ans, t, s in zip(generations, answer, tag, solved):
        reward = 0.0
        try:
            is_valid_format, errors = parser.check_format(gen, style=style)
            if not is_valid_format:
                rewards.append(reward)
                tool_responses.append(f'{style} Format is incorrect: ' + ', '.join(errors))
                include.append(True)
                continue
        except Exception as e:
            rewards.append(reward)
            tool_responses.append(f'{style} Format is incorrect. Encountered exception: ' + str(e))
            include.append(True)
            continue

        reward += 0.1

        try:
            calls, return_all = parser.extract_tool_calls(gen, tag=t, style=style)
        except Exception as e:
            rewards.append(reward)
            tool_responses.append('Failed to parse XML. Encountered exception: ' + str(e))
            include.append(True)
            continue

        try:
            scores, validation_results = parser.validate_ast_against_function_definitions(calls)
            name_error, param_error, type_error = scores
            r_name = 0.1 if not name_error else 0.0
            r_param = 0.1 if param_error == 0 else max(0.0, 0.1 - 0.025 * param_error)
            r_type = 0.1 if type_error == 0 else max(0.0, 0.1 - 0.025 * type_error)
            reward += r_name + r_param + r_type

            parsing_response = parser.format_validation_results(validation_results)
            if not parsing_response or parsing_response.strip() == "":
                parsing_response = ""
        except Exception as e:
            rewards.append(reward)
            tool_responses.append('Failed to validate API calls. Encountered exception: ' + str(e))
            include.append(True)
            continue

        try:
            result = parser.execute_syntax_tree(calls, return_all)
            result = parser.serialize_response(result)

            if not result or result.strip() == "":
                api_response = "(empty response)"
            else:
                try:
                    api_response = json.dumps(json.loads(result), indent=4)
                    api_response = api_response[:1500] + '...' if len(api_response) > 1500 else api_response
                except json.JSONDecodeError:
                    api_response = str(result)
                    api_response = api_response[:1500] + '...' if len(api_response) > 1500 else api_response
        except Exception as e:
            rewards.append(reward)
            tool_responses.append(
                parsing_response + '\nFailed to execute API. Encountered exception: ' + str(e)
            )
            include.append(True)
            continue

        reward += 0.1

        if not parser.check_response_equivalence(result, ans, order_aware=order_aware):
            rewards.append(reward)
            tool_responses.append(
                f"{parsing_response}\nAPI Response:\n{api_response}\n"
                "Problem not solved: Response does not match final answer."
            )
            if s and result == "":
                include.append(False)
                rewards[-1] = 1.0
            else:
                include.append(True)
            continue

        reward += 0.5
        rewards.append(reward)
        tool_responses.append(
            f"{parsing_response}\nAPI Response:\n{api_response}\nProblem solved: Response matches final answer."
        )
        include.append(not s)

    return rewards, tool_responses, include
