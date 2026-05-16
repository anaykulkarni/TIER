"""``tier-train`` entry point.

Reproduces the GRPO / SFT training loops from the paper.  See
``scripts/train_*.sh`` for canonical invocations and the README for a
mapping from each script to the corresponding paper table.

Usage::

    tier-train --model Qwen/Qwen3-8B --run-name my_run --reward-type finegrained ...

Or, equivalently::

    python -m tier.cli.train --model Qwen/Qwen3-8B --run-name my_run ...
"""

from __future__ import annotations

import os

import torch

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("VLLM_USE_V1", "0")
# Default to Blackwell-class compute capability used in the paper experiments.
# Override externally for older architectures (e.g. ``TORCH_CUDA_ARCH_LIST=9.0``).
os.environ.setdefault("TORCH_CUDA_ARCH_LIST", "12.0")

from tier.data import DatasetManager  # noqa: E402
from tier.parsing import Parser  # noqa: E402
from tier.prompts import FUNCTION_DEFINITIONS  # noqa: E402
from tier.training import TrainArgParser, get_trainer, setup_model_and_tokenizer  # noqa: E402


def _setup_environment(args, tokenizer) -> Parser:
    """Build a :class:`Parser` and bind it to the training tokenizer."""
    function_definitions_fp = args.function_definitions_fp or str(FUNCTION_DEFINITIONS)
    parser = Parser(args.seed, args.instructions_fp, function_definitions_fp)
    parser.preprocessor.set_tokenizer(tokenizer)
    return parser


def main() -> None:
    args = TrainArgParser().parse_args()

    dataset_for_next_run = [] if args.multiturn else None

    print(f"Starting {'multi-turn' if args.multiturn else 'single-turn'} training...")
    torch.cuda.init()

    model, tokenizer = setup_model_and_tokenizer(args)
    parser = _setup_environment(args, tokenizer)

    dataset_manager = DatasetManager(
        seed=args.seed,
        dataset_path=args.dataset_path,
        objective=args.objective,
    )
    train_dataset, _ = dataset_manager.setup_dataset(parser, args)

    trainer = get_trainer(
        model,
        tokenizer,
        train_dataset,
        parser,
        args,
        trainer_type=args.objective,
        dataset_for_next_run=dataset_for_next_run,
    )

    trainer.train(resume_from_checkpoint=args.resume_training)

    if args.multiturn:
        if not dataset_for_next_run:
            print("No more incorrect samples, training is completed!")
        else:
            print(
                f"Storing {len(dataset_for_next_run)} incorrect samples for next training iteration..."
            )
            dataset_manager.store_dataset_for_next_run(dataset_for_next_run, args=args)
            print("To continue training, run this script again with the same arguments.")


if __name__ == "__main__":
    main()
