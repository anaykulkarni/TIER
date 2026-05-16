"""
Trainer setup utilities for different training methods.
"""

import torch
from trl import GRPOConfig, GRPOTrainer, SFTConfig, SFTTrainer

from tier.constants import OUTPUTS_DIR
from tier.rewards import create_reward_function


def get_trainer(
    model,
    tokenizer,
    train_dataset,
    parser,
    args,
    trainer_type="GRPO",
    dataset_for_next_run=None
):
    """Create and configure a trainer based on the specified type.
    
    Args:
        model: The model to train.
        tokenizer: Tokenizer for the model.
        train_dataset: Dataset for training.
        parser: Parser instance for validation and execution.
        args: Parsed command line arguments containing training configuration.
        trainer_type: Type of trainer to create ('GRPO' or 'SFT'). Default: 'GRPO'.
        dataset_for_next_run: List to store incorrect samples for next training iteration (multiturn only).
        
    Returns:
        Configured trainer instance.
        
    Raises:
        ValueError: If an unsupported trainer_type is provided.
    """
    if trainer_type == "GRPO_DAPO":
        return _setup_grpo_dapo_trainer(
            model, 
            tokenizer, 
            train_dataset, 
            parser, 
            args, 
            dataset_for_next_run
        )
    elif trainer_type == "GRPO_BNPO":
        return _setup_grpo_bnpo_trainer(
            model, 
            tokenizer, 
            train_dataset, 
            parser, 
            args, 
            dataset_for_next_run
        )
    elif trainer_type == "SFT":
        return _setup_sft_trainer(
            model, 
            tokenizer, 
            train_dataset, 
            parser, 
            args
        )
    else:
        raise ValueError(f"Unsupported trainer type: {trainer_type}. Supported types: 'GRPO', 'SFT'")

def _setup_grpo_dapo_trainer(model, tokenizer, train_dataset, parser, args, dataset_for_next_run=None):
    """Set up the GRPO (Generalized Reinforcement Learning from Policy Optimization) DAPO trainer.
    
    Args:
        model: The model to train.
        tokenizer: Tokenizer for the model.
        train_dataset: Dataset for training.
        parser: Parser instance for validation and execution.
        args: Parsed command line arguments containing training configuration.
        dataset_for_next_run: List to store incorrect samples for next training iteration (multiturn only).
        
    Returns:
        Configured GRPOTrainer instance.
    """
    training_args = GRPOConfig(
        scale_rewards=True,
        beta=0.0,
        loss_type="dapo",
        use_vllm=True,
        vllm_tensor_parallel_size=args.vllm_tensor_parallel_size,
        vllm_gpu_memory_utilization=args.gpu_memory_utilization,
        vllm_max_model_length=args.max_seq_length,
        vllm_mode="colocate",
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": True},
        learning_rate=args.learning_rate,
        adam_beta1=0.9,
        adam_beta2=0.99,
        weight_decay=args.weight_decay,
        warmup_ratio=args.warmup_ratio,
        lr_scheduler_type="cosine",
        bf16=torch.cuda.is_bf16_supported(),
        fp16=not torch.cuda.is_bf16_supported(),
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        num_generations=args.num_generations,
        # max_prompt_length=args.max_prompt_length,
        max_completion_length=args.max_completion_length,
        max_grad_norm=args.max_grad_norm,
        report_to=["tensorboard"],
        output_dir=args.output_dir,
        logging_dir=str(OUTPUTS_DIR / "runs" / args.run_name),
        logging_steps=1,
        logging_first_step=True,
        log_completions=True,
        # use_liger_kernel=True,
    )

    if args.max_steps is not None:
        training_args.max_steps = args.max_steps
        training_args.save_steps = args.save_steps
        training_args.save_strategy = "steps"
    elif args.num_train_epochs is not None:
        training_args.num_train_epochs = args.num_train_epochs
        training_args.save_strategy = "epoch"

    # Create reward function based on training mode
    if args.multiturn:
        reward_func = create_reward_function(args, parser, dataset_for_next_run)
    else:
        reward_func = create_reward_function(args, parser)

    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        reward_funcs=[reward_func],
        args=training_args,
        train_dataset=train_dataset,
    )

    return trainer

def _setup_grpo_bnpo_trainer(model, tokenizer, train_dataset, parser, args, dataset_for_next_run=None):
    """Set up the GRPO (Generalized Reinforcement Learning from Policy Optimization) BNPO trainer.
    
    Args:
        model: The model to train.
        tokenizer: Tokenizer for the model.
        train_dataset: Dataset for training.
        parser: Parser instance for validation and execution.
        args: Parsed command line arguments containing training configuration.
        dataset_for_next_run: List to store incorrect samples for next training iteration (multiturn only).
        
    Returns:
        Configured GRPOTrainer instance.
    """
    training_args = GRPOConfig(
        scale_rewards=True,
        beta=0.0,
        loss_type="bnpo",
        use_vllm=True,
        vllm_tensor_parallel_size=args.vllm_tensor_parallel_size,
        vllm_gpu_memory_utilization=args.gpu_memory_utilization,
        vllm_max_model_length=args.max_seq_length,
        vllm_mode="colocate",
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": True},
        learning_rate=args.learning_rate,
        adam_beta1=0.9,
        adam_beta2=0.99,
        weight_decay=args.weight_decay,
        warmup_ratio=args.warmup_ratio,
        lr_scheduler_type="cosine",
        bf16=torch.cuda.is_bf16_supported(),
        fp16=not torch.cuda.is_bf16_supported(),
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        num_generations=args.num_generations,
        # max_prompt_length=args.max_prompt_length,
        max_completion_length=args.max_completion_length,
        max_grad_norm=args.max_grad_norm,
        report_to=["tensorboard"],
        output_dir=args.output_dir,
        logging_dir=str(OUTPUTS_DIR / "runs" / args.run_name),
        logging_steps=1,
        logging_first_step=True,
        log_completions=True,
        # use_liger_kernel=True,
    )

    if args.max_steps is not None:
        training_args.max_steps = args.max_steps
        training_args.save_steps = args.save_steps
        training_args.save_strategy = "steps"
    elif args.num_train_epochs is not None:
        training_args.num_train_epochs = args.num_train_epochs
        training_args.save_strategy = "epoch"

    # Create reward function based on training mode
    if args.multiturn:
        reward_func = create_reward_function(args, parser, dataset_for_next_run)
    else:
        reward_func = create_reward_function(args, parser)

    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        reward_funcs=[reward_func],
        args=training_args,
        train_dataset=train_dataset,
    )

    return trainer


def _setup_sft_trainer(model, tokenizer, train_dataset, parser, args):
    """Set up the SFT (Supervised Fine-Tuning) trainer.
    
    Args:
        model: The model to train.
        tokenizer: Tokenizer for the model.
        train_dataset: Dataset for training.
        parser: Parser instance for validation and execution.
        args: Parsed command line arguments containing training configuration.
        
    Returns:
        Configured SFTTrainer instance.
    """
    training_args = SFTConfig(
        gradient_checkpointing=True,
        learning_rate=args.learning_rate,
        adam_beta1=0.9,
        adam_beta2=0.99,
        weight_decay=args.weight_decay,
        warmup_ratio=args.warmup_ratio,
        lr_scheduler_type="cosine",
        bf16=torch.cuda.is_bf16_supported(),
        fp16=not torch.cuda.is_bf16_supported(),
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        max_length=args.max_seq_length,
        num_train_epochs=args.num_train_epochs,
        save_strategy="epoch",
        max_grad_norm=args.max_grad_norm,
        report_to=["tensorboard"],
        output_dir=args.output_dir,
        logging_dir=str(OUTPUTS_DIR / "runs" / args.run_name),
        logging_steps=1,
        logging_first_step=True,
        packing=False,  # Important: disable packing for conversational data
        # use_liger_kernel=True,
    )

    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        args=training_args,
        train_dataset=train_dataset,
    )

    return trainer

