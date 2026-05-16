"""Reward functions for TIER and its baselines.

The full reward decomposition introduced in the paper lives in
:mod:`tier.rewards.tier`.  Each ablation / baseline is exposed as its own
submodule so that they can be inspected and reused independently:

* :mod:`tier.rewards.tier` – full TIER reward (paper Table 1, last row).
* :mod:`tier.rewards.simple` – outcome-only baseline (paper Table 1, row 1).
* :mod:`tier.rewards.parsing` – format + parse + answer ablation.
* :mod:`tier.rewards.execution` – format + exec + answer ablation.
* :mod:`tier.rewards.ground_truth` – trajectory-supervised variants.
* :mod:`tier.rewards.multiturn` – multi-turn reward producing tool feedback.
* :mod:`tier.rewards.toolrl` – ToolRL trajectory-supervised baseline.

The factory :func:`create_reward_function` returns the right reward closure
based on the parsed CLI arguments.
"""

from __future__ import annotations

from typing import Callable, List

from tier.rewards.execution import calculate_reward_with_execution
from tier.rewards.ground_truth import (
    calculate_reward_with_gt,
    calculate_simple_reward_with_gt,
)
from tier.rewards.multiturn import (
    calculate_reward_multiturn,
    calculate_reward_with_env_response,
)
from tier.rewards.parsing import calculate_reward_with_parsing
from tier.rewards.simple import calculate_simple_reward
from tier.rewards.tier import calculate_reward
from tier.rewards.toolrl import calculate_tool_rl_reward

__all__ = [
    "calculate_reward",
    "calculate_reward_with_execution",
    "calculate_reward_with_parsing",
    "calculate_reward_with_gt",
    "calculate_simple_reward",
    "calculate_simple_reward_with_gt",
    "calculate_reward_multiturn",
    "calculate_reward_with_env_response",
    "calculate_tool_rl_reward",
    "pipeline_reward_func",
    "pipeline_reward_func_multiturn",
    "create_reward_function",
]


def pipeline_reward_func(prompts, completions, answer, tag, api_calls, **kwargs) -> List[float]:
    """Route a batch of generations to the requested reward variant."""
    generations = [completion[0]['content'] for completion in completions]

    parser = kwargs.get('parser')
    style = kwargs.get('style', 'xml')
    reward_type = kwargs.get('reward_type', 'finegrained')
    order_aware = kwargs.get('order_aware', True)

    assert parser is not None, "Parser must be provided"
    assert len(generations) == len(answer) == len(tag), (
        "Generations, answer, and tag must have the same length"
    )

    if reward_type == 'finegrained':
        return calculate_reward(generations, answer, tag, parser, style=style, order_aware=order_aware)
    if reward_type == 'finegrained_with_execution':
        return calculate_reward_with_execution(generations, answer, tag, parser, style=style, order_aware=order_aware)
    if reward_type == 'finegrained_with_parsing':
        return calculate_reward_with_parsing(generations, answer, tag, parser, style=style, order_aware=order_aware)
    if reward_type == 'simple':
        return calculate_simple_reward(generations, answer, tag, parser, style=style, order_aware=order_aware)
    if reward_type == 'simple_with_gt':
        return calculate_simple_reward_with_gt(generations, answer, tag, api_calls, parser, style=style, order_aware=order_aware)
    if reward_type == 'fgr_with_gt':
        return calculate_reward_with_gt(generations, answer, tag, api_calls, parser, style=style, order_aware=order_aware)
    if reward_type == 'tool_rl':
        return calculate_tool_rl_reward(generations, answer, tag, api_calls, parser, style=style)
    raise ValueError(f"Invalid reward type: {reward_type}")


def pipeline_reward_func_multiturn(
    prompts, completions, question, answer, num_calls, tag, api_calls, apis, solved, id, turn, **kwargs
) -> List[float]:
    """Multi-turn variant: appends each generation + tool response to the prompt."""
    generations = [completion[0]['content'] for completion in completions]

    parser = kwargs.get('parser')
    new_dataset = kwargs.get('new_dataset')
    style = kwargs.get('style', 'xml')
    reward_type = kwargs.get('reward_type', 'finegrained')
    order_aware = kwargs.get('order_aware', True)
    assert parser is not None, "Parser must be provided"
    assert new_dataset is not None, "New dataset must be provided"

    if reward_type != 'finegrained':
        raise ValueError(f"Invalid reward type for multiturn: {reward_type}")

    rewards, tool_responses = calculate_reward_multiturn(
        generations, answer, tag, parser, style=style, order_aware=order_aware
    )
    assert len(rewards) == len(tool_responses), (
        "rewards and tool_responses must have the same length"
    )

    for i in range(len(rewards)):
        prompts[i].extend([
            {"role": "assistant", "content": generations[i]},
            {"role": "user", "content": 'Tool response: ' + tool_responses[i]},
        ])
        new_dataset.append({
            "id": id[i],
            "turn": turn[i],
            "prompt": prompts[i],
            "question": question[i],
            "answer": answer[i],
            "num_calls": num_calls[i],
            "tag": tag[i],
            "api_calls": api_calls[i],
            "apis": apis[i],
            "solved": rewards[i] == 1.0,
        })

    return rewards


def create_reward_function(args, parser, dataset_for_next_run=None) -> Callable:
    """Return a closure consumable by ``GRPOTrainer``.

    Reads ``args.reward_type``, ``args.output_style``, ``args.disable_order_aware``,
    and ``args.multiturn`` to pick the appropriate variant.
    """
    order_aware = not getattr(args, 'disable_order_aware', False)

    if args.multiturn:
        assert dataset_for_next_run is not None, (
            "dataset_for_next_run must be provided for multiturn training"
        )

        def wrapped_reward_func(
            prompts, completions, question, answer, num_calls, tag, api_calls,
            apis, solved, id, turn, **kwargs,
        ):
            return pipeline_reward_func_multiturn(
                prompts, completions, question, answer, num_calls, tag, api_calls,
                apis, solved, id, turn,
                parser=parser,
                new_dataset=dataset_for_next_run,
                style=args.output_style,
                reward_type=args.reward_type,
                order_aware=order_aware,
                **kwargs,
            )

        return wrapped_reward_func

    def wrapped_reward_func(prompts, completions, answer, tag, api_calls, **kwargs):
        return pipeline_reward_func(
            prompts, completions, answer, tag, api_calls,
            parser=parser,
            reward_type=args.reward_type,
            style=args.output_style,
            order_aware=order_aware,
            **kwargs,
        )

    return wrapped_reward_func
