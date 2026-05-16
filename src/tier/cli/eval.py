"""``tier-eval`` entry point.

Evaluates one or more checkpoints from a training run, mirroring the
protocol used to produce DepthBench / BFCL / NestFUL numbers in the paper.

Usage::

    tier-eval --model Qwen/Qwen3-8B --run-name my_run --full-finetuned \\
              --is-deepspeed --reward-type finegrained --split-dataset
"""

from __future__ import annotations

import gc
import os
import shutil
import sys

import torch

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("VLLM_USE_V1", "0")
os.environ.setdefault("TORCH_CUDA_ARCH_LIST", "12.0")

from deepspeed.utils.zero_to_fp32 import load_state_dict_from_zero_checkpoint  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

from tier.data import DatasetManager  # noqa: E402
from tier.evaluation import Evaluator  # noqa: E402
from tier.parsing import Parser  # noqa: E402
from tier.prompts import FUNCTION_DEFINITIONS  # noqa: E402
from tier.training import EvalArgParser  # noqa: E402


def _get_checkpoint_paths(args):
    """Resolve the list of ``(name, path)`` tuples to evaluate."""
    if args.checkpoint_dir:
        root = args.checkpoint_dir
        dirs = [d for d in os.listdir(root) if d.startswith('checkpoint-')]
        if not dirs:
            print(f"No checkpoints found in {root}. Please check the path.")
            sys.exit(1)
        dirs.sort(key=lambda x: int(x.split('-')[1]))

        if not args.skip_base:
            dirs = ['base'] + dirs

        return [(name, os.path.join(root, name) if name != 'base' else None) for name in dirs]

    if args.checkpoint:
        path = args.checkpoint
        if not os.path.exists(path):
            print(f"Checkpoint not found: {path}")
            sys.exit(1)
        name = os.path.basename(path)
        if args.skip_base:
            return [(name, path)]
        return [('base', None), (name, path)]

    if args.skip_base:
        print("Error: --skip-base cannot be used when evaluating only the base model.")
        sys.exit(1)
    return [('base', None)]


def _build_parser(args) -> Parser:
    function_definitions_fp = args.function_definitions_fp or str(FUNCTION_DEFINITIONS)
    return Parser(
        seed=args.seed,
        instructions_fp=args.instructions_fp,
        function_definitions_fp=function_definitions_fp,
    )


def _build_dataset(args, parser):
    manager = DatasetManager(seed=args.seed, dataset_path=args.dataset_path, objective=args.objective)
    train_dataset, test_dataset = manager.setup_dataset(parser, args)

    if test_dataset is not None:
        print(f"Using test split for evaluation: {len(test_dataset)} samples")
        return test_dataset
    print(f"Using full dataset for evaluation: {len(train_dataset)} samples")
    return train_dataset


def _build_evaluator(args) -> Evaluator:
    evaluator = Evaluator(seed=args.seed)
    evaluator.set_sampling_params(model=args.model, max_tokens=args.max_tokens)
    return evaluator


def _load_base_model(args, evaluator):
    """Load the base model (and tokenizer) once; reused for LoRA adapters."""
    model_path = args.model
    use_vllm = not args.no_vllm

    if args.checkpoint_dir:
        print(
            f"Loading base model {model_path} for checkpoints from {args.checkpoint_dir}"
            + (" (skipping base evaluation)" if args.skip_base else "")
        )
    elif args.checkpoint:
        print(
            f"Loading base model {model_path} for single checkpoint {args.checkpoint}"
            + (" (skipping base evaluation)" if args.skip_base else "")
        )
    else:
        print(f"Loading base model {model_path} for base model evaluation only")

    base_model, tokenizer = evaluator.load_model_and_tokenizer_from_checkpoint(
        model_path=model_path,
        max_seq_length=args.max_seq_length,
        max_lora_rank=None if args.full_finetuned else args.lora_rank,
        use_vllm=use_vllm,
        vllm_gpu_memory_utilization=args.gpu_memory_utilization,
    )
    return base_model, tokenizer, use_vllm


def _load_checkpoint_model(args, evaluator, base_model, name, path, use_vllm):
    """Materialise a checkpoint into a vLLM-loadable model."""
    lora_request = None
    temp_path = None

    if name == 'base':
        return base_model, None, lora_request, temp_path

    if args.full_finetuned:
        if args.is_deepspeed:
            base = AutoModelForCausalLM.from_pretrained(
                args.model, torch_dtype=torch.bfloat16, device_map="cpu",
            )
            tokenizer = AutoTokenizer.from_pretrained(
                args.model, max_model_length=args.max_seq_length, padding_side="left",
            )
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            gc.collect()
            print("Materializing full state dict from DeepSpeed checkpoint")
            model = load_state_dict_from_zero_checkpoint(base, path)
            temp_path = os.path.join(path, "temp")
            os.makedirs(temp_path, exist_ok=True)
            model.save_pretrained(temp_path, safe_serialization=True)
            tokenizer.save_pretrained(temp_path)
            path = temp_path

        print(f"Loading full finetuned model from {path}")
        model, tokenizer = evaluator.load_model_and_tokenizer_from_checkpoint(
            model_path=path,
            max_seq_length=args.max_seq_length,
            max_lora_rank=None,
            use_vllm=use_vllm,
            vllm_gpu_memory_utilization=args.gpu_memory_utilization,
        )
        return model, tokenizer, lora_request, temp_path

    model, lora_request = evaluator.load_adapters(
        model=base_model, adapter_path=path, use_vllm=use_vllm,
    )
    return model, None, lora_request, temp_path


def _evaluate_checkpoint(args, evaluator, name, path, base_model, tokenizer, test_dataset, parser, use_vllm):
    if path:
        print(f"Evaluating model from checkpoint: {path}")
    else:
        print("Evaluating base model")

    model, ckpt_tokenizer, lora_request, temp_path = _load_checkpoint_model(
        args, evaluator, base_model, name, path, use_vllm,
    )

    gc.collect()

    if ckpt_tokenizer is not None:
        tokenizer = ckpt_tokenizer

    out_dir = None
    if args.output_dir:
        out_dir = os.path.join(args.output_dir, name)

    evaluator.evaluate_model(
        model=model,
        tokenizer=tokenizer,
        lora_request=lora_request,
        test_dataset=test_dataset,
        parser=parser,
        batch_size=args.batch_size,
        oversample_factor=args.oversample_factor,
        log_responses=True,
        use_vllm=use_vllm,
        output_dir=out_dir,
        output_style=args.output_style,
    )

    del model
    if temp_path and os.path.exists(temp_path):
        print(f"Cleaning up temporary directory: {temp_path}")
        shutil.rmtree(temp_path)

    torch.cuda.empty_cache()
    gc.collect()


def main() -> None:
    args = EvalArgParser().parse_args()

    print("Starting evaluation...")
    torch.cuda.init()

    checkpoint_paths = _get_checkpoint_paths(args)
    parser = _build_parser(args)
    test_dataset = _build_dataset(args, parser)
    evaluator = _build_evaluator(args)

    if not args.full_finetuned or not args.skip_base:
        base_model, tokenizer, use_vllm = _load_base_model(args, evaluator)
    else:
        base_model, tokenizer, use_vllm = None, None, not args.no_vllm

    for name, path in checkpoint_paths:
        _evaluate_checkpoint(
            args, evaluator, name, path, base_model, tokenizer, test_dataset, parser, use_vllm,
        )

        if args.full_finetuned:
            base_model = None
            torch.cuda.empty_cache()
            gc.collect()


if __name__ == "__main__":
    main()
