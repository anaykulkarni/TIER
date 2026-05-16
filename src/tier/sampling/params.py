"""Per-model sampling parameter loader.

The sampling JSON ships inside :mod:`tier.prompts` so the resolved values
follow the package wherever it is installed.
"""

import json

from vllm import SamplingParams

from tier.prompts import SAMPLING_PARAMS


class GenerationConfig:
    """Load sampling defaults keyed by model identifier."""

    def __init__(self):
        with open(SAMPLING_PARAMS, "r") as f:
            self.sampling_params_config = json.load(f)

    def get_sampling_params(self, model: str, max_tokens: int) -> SamplingParams:
        if model not in self.sampling_params_config:
            model = "default"
        config = dict(self.sampling_params_config[model])
        config["max_tokens"] = max_tokens
        return SamplingParams(**config)
