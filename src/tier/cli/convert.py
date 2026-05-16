"""``tier-convert`` entry point.

Converts a DeepSpeed ZeRO-3 checkpoint (as written by the training scripts
under ``scripts/train_*.sh``) into a HuggingFace ``from_pretrained``-loadable
directory.

Usage::

    # Convert outputs/tier/checkpoint-500 -> outputs/tier/checkpoint-500-hf
    tier-convert --run-name tier --checkpoint-step 500

    # Or supply explicit paths
    tier-convert --checkpoint-path /path/to/ckpt --output-path /path/to/out

Both forms produce a directory containing ``model.safetensors``,
``config.json``, the tokenizer files, etc. — ready to be passed back to
``tier-eval`` as ``--model``.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import torch
from deepspeed.utils.zero_to_fp32 import load_state_dict_from_zero_checkpoint
from transformers import AutoModelForCausalLM, AutoTokenizer

from tier.constants import OUTPUTS_DIR


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Materialise a DeepSpeed ZeRO-3 checkpoint into a HuggingFace folder.",
    )
    p.add_argument(
        "--model", default="Qwen/Qwen3-8B",
        help="Base model id (default: %(default)s).",
    )
    p.add_argument(
        "--max-seq-length", type=int, default=8192,
        help="Tokenizer max-model-length (default: %(default)s).",
    )

    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--checkpoint-path", type=Path,
        help="Explicit path to the DeepSpeed checkpoint directory.",
    )
    src.add_argument(
        "--run-name",
        help="Run name under outputs/.  Combined with --checkpoint-step.",
    )
    p.add_argument(
        "--checkpoint-step", type=int,
        help="Step number to convert when --run-name is given.",
    )

    p.add_argument(
        "--output-path", type=Path,
        help="Destination directory; defaults to <checkpoint>-hf next to the source.",
    )
    p.add_argument(
        "--cuda-device", default=os.environ.get("CUDA_VISIBLE_DEVICES", "0"),
        help="CUDA_VISIBLE_DEVICES override (default: %(default)s).",
    )
    return p.parse_args()


def _resolve_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.checkpoint_path is not None:
        checkpoint_path = args.checkpoint_path
    else:
        if args.checkpoint_step is None:
            raise SystemExit("--run-name requires --checkpoint-step")
        checkpoint_path = OUTPUTS_DIR / args.run_name / f"checkpoint-{args.checkpoint_step}"

    if not checkpoint_path.is_dir():
        raise SystemExit(f"Checkpoint directory does not exist: {checkpoint_path}")

    output_path = args.output_path or checkpoint_path.with_name(checkpoint_path.name + "-hf")
    return checkpoint_path, output_path


def main() -> None:
    args = _parse_args()

    os.environ["CUDA_VISIBLE_DEVICES"] = args.cuda_device
    torch.cuda.init()

    checkpoint_path, output_path = _resolve_paths(args)
    print(f"Converting {checkpoint_path}  ->  {output_path}")

    base_model = AutoModelForCausalLM.from_pretrained(
        args.model, dtype=torch.bfloat16, device_map="cpu",
    )
    tokenizer = AutoTokenizer.from_pretrained(
        args.model, max_model_length=args.max_seq_length, padding_side="left",
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print("Materializing full state dict from DeepSpeed checkpoint")
    model = load_state_dict_from_zero_checkpoint(base_model, str(checkpoint_path))

    output_path.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(output_path), safe_serialization=True)
    tokenizer.save_pretrained(str(output_path))
    print(f"Saved HF-loadable checkpoint to: {output_path}")


if __name__ == "__main__":
    main()
