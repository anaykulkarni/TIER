"""
Argument parser for training and evaluation scripts.

COMMON ARGUMENTS (shared by both train.py and eval.py):

Required:
    --run-name                  Name for the run (required for both train and eval)
                                Creates: <repo>/outputs/[run-name] for training
                                        <repo>/outputs/[run-name] for checkpoints (eval auto-finds them)
                                        <repo>/outputs/[run-name]/evaluation_results/ for eval outputs

Model Options:
    --model                      Path to the base model (required)
    --max-seq-length            Maximum sequence length (default: 4096)
    --lora-rank                 LoRA rank (default: 256)
    --max-prompt-length         Maximum prompt length (default: 2048)
    --max-completion-length     Maximum completion length (default: 2048)

Dataset Options:
    --toolace                   Use ToolACE dataset for training
    --xlam                      Use XLAM dataset for training
    --dataset-path              Custom path to dataset JSON file (overrides default dataset selection)
    --seed                      Random seed (default: 1337)
    --test-size                 Fraction for testing (default: 0.2, mutually exclusive with --full-dataset and --split-dataset)
    --full-dataset              Use full dataset without splitting (mutually exclusive with --test-size and --split-dataset)
    --split-dataset             Split so test tools not seen in training (mutually exclusive with --test-size and --full-dataset)
    --filter-dataset-by-tools   Filter by comma-separated tool names (default: "")
    --filter-dataset-by-num-calls Filter by number of function calls (default: "")
    --no-chaining               Disable chaining in dataset creation (default: chain=True)
    --instructions-fp           Path to instructions file (default: None)
    --function-definitions-fp   Path to function definitions file (default: None)
    
Hyperparameters:
    --batch-size                Batch size (default: 8)
    --k-extra-functions         Number of extra functions to include (default: 3)
    --reward-type               Reward type (default: finegrained)
    --disable-order-aware       Disable order awareness in reward calculation (default: False)
    --objective                 Training/evaluation objective: GRPO_DAPO, GRPO_BNPO or SFT (default: GRPO_BNPO)
    --output-style              Output style format (default: xml)

VLLM Options:
    --no-vllm                   Disable VLLM usage (default: False, VLLM enabled by default)
    --gpu-memory-utilization    GPU memory usage (default: 0.7)
    --vllm-tensor-parallel-size Tensor parallel size for vLLM (default: 1)

TRAINING-SPECIFIC ARGUMENTS (train.py only):

Training Parameters:
    --max-steps                 Maximum training steps (default: 1000)
    --num-train-epochs          Number of training epochs (default: 1)
    --save-steps                Save checkpoint every N steps (default: 250)
    --gradient-accumulation-steps Gradient accumulation steps (default: 4)
    --num-generations           Number of generations (default: 8)
    --learning-rate             Learning rate (default: 5e-6)
    --max-grad-norm             Maximum gradient norm (default: 0.1)
    --warmup-ratio              Warmup ratio (default: 0.1)
    --weight-decay              Weight decay (default: 0.1)

Training Options:
    --output-dir                Output directory (optional override, default: <repo>/outputs/[run-name])
    --resume-training           Resume from latest checkpoint (default: False)
    --multiturn                 Enable multi-turn iterative training (default: False)
    --use-4bit-quantization     Use 4-bit quantization (qLoRA) (mutually exclusive with --full-finetuning)
    --full-finetuning           Use full fine-tuning instead of LoRA (mutually exclusive with --use-4bit-quantization)

EVALUATION-SPECIFIC ARGUMENTS (eval.py only):

Checkpoint Options:
    --checkpoint-dir            Path to directory containing checkpoints (mutually exclusive with --checkpoint)
                                (default: <repo>/outputs/[run-name])
    --checkpoint                Path to single checkpoint to evaluate (mutually exclusive with --checkpoint-dir)
    --skip-base                 Skip evaluation of base model (default: False)
    --output-dir                Output directory (optional override, default: <repo>/outputs/[run-name]/evaluation_results)

Model Options:
    --full-finetuned            Use full finetuned checkpoints instead of LoRA (default: False)
    --is-deepspeed              Checkpoints are from DeepSpeed (may need conversion) (default: False)

Sampling Parameters:
    --max-tokens                Maximum tokens for sampling (default: 2048)

Evaluation Settings:
    --oversample-factor         Oversample factor (default: 1)
"""

import argparse

from tier.constants import OUTPUTS_DIR


class BaseArgParser:
    """Base argument parser with common arguments for training and evaluation."""
    
    def __init__(self, description, epilog=''):
        """Initialize the base argument parser.
        
        Args:
            description: Description of the parser.
            epilog: Epilog text with examples.
        """
        self.parser = argparse.ArgumentParser(
            description=description,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=epilog
        )
    
    def _add_common_arguments(self):
        """Add all common arguments for training and evaluation."""
        # Required Arguments
        required_group = self.parser.add_argument_group('Required Arguments')
        required_group.add_argument('--run-name', type=str, required=True,
                                   help='Name for the run (used to create output directories)')
        
        # Model Options
        model_group = self.parser.add_argument_group('Model Options')
        model_group.add_argument('--model', type=str, required=True,
                                help='Path to the base model')
        model_group.add_argument('--max-seq-length', type=int, default=4096,
                                help='Maximum sequence length (default: 4096)')
        model_group.add_argument('--lora-rank', type=int, default=256,
                                help='LoRA rank (default: 256)')
        model_group.add_argument('--max-prompt-length', type=int, default=2048,
                                help='Maximum prompt length (default: 2048)')
        model_group.add_argument('--max-completion-length', type=int, default=2048,
                                help='Maximum completion length (default: 2048)')
        
        # Dataset Options
        dataset_group = self.parser.add_argument_group('Dataset Options')
        dataset_group.add_argument('--toolace', action='store_true',
                                   help='Use ToolACE dataset for training')
        dataset_group.add_argument('--xlam', action='store_true',
                                   help='Use XLAM dataset for training')
        dataset_group.add_argument('--dataset-path', type=str, default=None,
                                   help='Custom path to dataset JSON file (overrides default dataset selection)')
        dataset_group.add_argument('--seed', type=int, default=1337,
                                   help='Random seed (default: 1337)')
        
        # Mutually exclusive dataset split options
        split_group = self.parser.add_mutually_exclusive_group()
        split_group.add_argument('--test-size', type=float, default=0.2,
                                 help='Fraction of dataset for testing (default: 0.2)')
        split_group.add_argument('--full-dataset', action='store_true',
                                 help='Use full dataset without splitting')
        split_group.add_argument('--split-dataset', action='store_true',
                                 help='Split dataset so tools in test set are not seen in training')
        
        dataset_group.add_argument('--filter-dataset-by-tools', type=str, default='',
                                   help='Filter samples by comma-separated list of tools (default: "")')
        dataset_group.add_argument('--filter-dataset-by-num-calls', type=str, default='',
                                   help='Filter samples by number of function calls (default: "")')
        dataset_group.add_argument('--no-chaining', action='store_false', dest='chain',
                                   help='Disable chaining in dataset creation (default: chain=True)')
        dataset_group.add_argument('--instructions-fp', type=str, default=None,
                                   help='Path to instructions file (default: None)')
        dataset_group.add_argument('--function-definitions-fp', type=str, default=None,
                                   help='Path to function definitions file (default: None)')
        
        # Common hyperparameters
        hyperparam_group = self.parser.add_argument_group('Hyperparameters')
        hyperparam_group.add_argument('--batch-size', type=int, default=8,
                                      help='Batch size (default: 8)')
        hyperparam_group.add_argument('--k-extra-functions', type=int, default=3,
                                      help='Number of extra functions to include (default: 3)')
        hyperparam_group.add_argument('--reward-type', type=str, default='finegrained',
                                      choices=['finegrained', 'finegrained_with_execution', 'finegrained_with_parsing', 'simple', 'simple_with_gt', 'fgr_with_gt', 'tool_rl'],
                                      help='Reward type (default: finegrained)')
        hyperparam_group.add_argument('--disable-order-aware', action='store_true', default=False,
                                      help='Order of tool calls is not considered in reward calculation (default: False)')
        hyperparam_group.add_argument('--objective', type=str, choices=['GRPO_DAPO', 'GRPO_BNPO', 'SFT'], default='GRPO_BNPO',
                                      help='Training/evaluation objective (default: GRPO_BNPO)')
        hyperparam_group.add_argument('--output-style', type=str, default='xml',
                                      help='Output style format (default: xml)')
        
        # VLLM Options
        vllm_group = self.parser.add_argument_group('VLLM Options')
        vllm_group.add_argument('--no-vllm', action='store_true',
                               help='Disable VLLM usage (VLLM is enabled by default)')
        vllm_group.add_argument('--gpu-memory-utilization', type=float, default=0.7,
                               help='GPU memory usage (default: 0.7)')
        vllm_group.add_argument('--vllm-tensor-parallel-size', type=int, default=1,
                               help='Tensor parallel size for vLLM (default: 1)')
        
        return dataset_group, model_group
    
    def parse_args(self):
        """Parse and return command line arguments.
        
        This method should be overridden by subclasses for custom post-processing.
        """
        return self.parser.parse_args()


class TrainArgParser(BaseArgParser):
    """Argument parser for GRPO training."""
    
    def __init__(self):
        """Initialize and configure the argument parser."""
        epilog = """
Note: VLLM is always enabled for training.
Full fine-tuning and quantization are mutually exclusive options.

Examples:
    # Train with default settings
    python train.py --model Qwen/Qwen3-8B --run-name my_experiment

    # Train with ToolACE dataset
    python train.py --model Qwen/Qwen3-8B --run-name toolace_experiment --toolace

    # Train with XLAM dataset
    python train.py --model Qwen/Qwen3-8B --run-name xlam_experiment --xlam

    # Train with custom settings
    python train.py \\
        --model Qwen/Qwen2.5-7B-Instruct \\
        --run-name custom_experiment \\
        --max-steps 2000 \\
        --save-steps 500 \\
        --batch-size 16 \\
        --gradient-accumulation-steps 2 \\
        --lora-rank 512 \\
        --learning-rate 1e-5
"""
        super().__init__('Train model with GRPO', epilog)
        
        self._add_train_specific_options()
        self._add_training_parameters()
        self._add_training_options()
    
    def _add_train_specific_options(self):
        """Add training-specific arguments."""
        # Add all common arguments
        _ = self._add_common_arguments()
    
    def _add_training_parameters(self):
        """Add training hyperparameter arguments."""
        group = self.parser.add_argument_group('Training Parameters')
        
        group.add_argument('--max-steps', type=int, default=None,
                          help='Maximum training steps (default: 1000)')
        group.add_argument('--num-train-epochs', type=int, default=None,
                          help='Number of training epochs (default: 1)')
        group.add_argument('--save-steps', type=int, default=None,
                          help='Save checkpoint every N steps (default: 250)')
        group.add_argument('--gradient-accumulation-steps', type=int, default=4,
                          help='Gradient accumulation steps (default: 4)')
        group.add_argument('--num-generations', type=int, default=8,
                          help='Number of generations (default: 8)')
        group.add_argument('--learning-rate', type=float, default=5e-6,
                          help='Learning rate (default: 5e-6)')
        group.add_argument('--max-grad-norm', type=float, default=0.1,
                          help='Maximum gradient norm (default: 0.1)')
        group.add_argument('--warmup-ratio', type=float, default=0.1,
                          help='Warmup ratio (default: 0.1)')
        group.add_argument('--weight-decay', type=float, default=0.1,
                          help='Weight decay (default: 0.1)')
    
    def _add_training_options(self):
        """Add training mode and option arguments."""
        group = self.parser.add_argument_group('Training Options')
        
        group.add_argument('--output-dir', type=str, default=None,
                          help='Output directory (default: <repo>/outputs/[run-name])')
        group.add_argument('--resume-training', action='store_true',
                          help='Resume training from the latest checkpoint (default: False)')
        group.add_argument('--multiturn', action='store_true',
                          help='Enable multi-turn iterative training mode (default: False)')
        
        # Mutually exclusive training modes
        training_mode_group = self.parser.add_mutually_exclusive_group()
        training_mode_group.add_argument('--use-4bit-quantization', action='store_true',
                                        help='Use 4-bit quantization (qLoRA)')
        training_mode_group.add_argument('--full-finetuning', action='store_true',
                                        help='Use full fine-tuning instead of LoRA')
    
    def parse_args(self):
        """Parse and return command line arguments."""
        args = self.parser.parse_args()
        
        # Post-processing: Set output_dir from run_name
        if args.output_dir is None:
            args.output_dir = str(OUTPUTS_DIR / args.run_name)

        return args


class EvalArgParser(BaseArgParser):
    """Argument parser for model evaluation."""
    
    def __init__(self):
        """Initialize and configure the argument parser."""
        epilog = """
Examples:
    # Evaluate base model only
    python eval.py --model Qwen/Qwen2.5-7B-Instruct --run-name my_eval --full-dataset
    
    # Evaluate all checkpoints from a training run
    python eval.py --model Qwen/Qwen3-8B --run-name my_training_run --full-dataset
    
    # Evaluate specific checkpoint
    python eval.py --model Qwen/Qwen3-8B --run-name my_run --checkpoint path/to/checkpoint --full-dataset
    
    # Evaluate full finetuned checkpoints
    python eval.py --model Qwen/Qwen3-8B --run-name my_run --full-finetuned --full-dataset
"""
        super().__init__('Evaluate model checkpoints', epilog)
        
        self._add_eval_specific_options()
        self._add_sampling_parameters()
        self._add_evaluation_settings()
    
    def _add_eval_specific_options(self):
        """Add evaluation-specific arguments."""
        # Evaluation-specific options
        group = self.parser.add_argument_group('Evaluation-Specific Options')
        
        checkpoint_group = self.parser.add_mutually_exclusive_group(required=False)
        checkpoint_group.add_argument('--checkpoint-dir', type=str,
                                     help='Path to the directory containing checkpoints')
        checkpoint_group.add_argument('--checkpoint', type=str,
                                     help='Path to a single checkpoint to evaluate')
        
        group.add_argument('--skip-base', action='store_true',
                          help='Skip evaluation of the base model (only evaluate checkpoints)')
        group.add_argument('--output-dir', type=str, default=None,
                          help='Directory to save evaluation results and responses')
        
        # Add all common arguments
        _, model_group = self._add_common_arguments()
        
        # Evaluation-specific model parameters
        group.add_argument('--full-finetuned', action='store_true',
                          help='Use full finetuned checkpoints instead of LoRA adapters')
        model_group.add_argument('--is-deepspeed', action='store_true',
                                help='Indicates checkpoints are from DeepSpeed (may need conversion)')
    
    def _add_sampling_parameters(self):
        """Add sampling parameter arguments."""
        group = self.parser.add_argument_group('Sampling Parameters')
        group.add_argument('--max-tokens', type=int, default=2048,
                          help='Maximum tokens for sampling (default: 2048)')
    
    def _add_evaluation_settings(self):
        """Add evaluation configuration arguments."""
        group = self.parser.add_argument_group('Evaluation Settings')
        
        group.add_argument('--oversample-factor', type=int, default=1,
                          help='Oversample factor (default: 1)')
    
    def parse_args(self):
        """Parse and return command line arguments."""
        args = self.parser.parse_args()
        
        # Post-processing: Set checkpoint_dir and output_dir from run_name if not provided
        if not hasattr(args, 'checkpoint_dir') or args.checkpoint_dir is None:
            if not args.checkpoint:  # Only set if no specific checkpoint provided
                args.checkpoint_dir = str(OUTPUTS_DIR / args.run_name)

        if args.output_dir is None:
            args.output_dir = str(OUTPUTS_DIR / args.run_name / "evaluation_results")
        
        # For evaluation, multiturn is not used, but DatasetManager.setup_dataset expects it
        args.multiturn = False
        
        return args
