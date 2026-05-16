"""TIER: Trajectory-Invariant Execution Rewards for multi-step tool composition.

Public surface:
    - :mod:`tier.environment` – the DepthBench simulator and individual API classes.
    - :mod:`tier.rewards` – the TIER reward and its component / baseline variants.
    - :mod:`tier.parsing` – AST parser and schema validator.
    - :mod:`tier.data` – dataset loading and prompt construction.
    - :mod:`tier.training` – trainer factory and CLI argument parsing.
    - :mod:`tier.evaluation` – batched evaluator for trained checkpoints.
    - :mod:`tier.cli` – command-line entry points ``tier-train`` / ``tier-eval``.
"""

__version__ = "0.1.0"
