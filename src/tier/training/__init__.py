"""Training entry points: argument parsing, model loading, and trainer setup."""

from tier.training.argparser import EvalArgParser, TrainArgParser
from tier.training.model_loader import setup_model_and_tokenizer
from tier.training.trainer import get_trainer

__all__ = [
    "EvalArgParser",
    "TrainArgParser",
    "get_trainer",
    "setup_model_and_tokenizer",
]
