"""
Model and tokenizer loading utilities.
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import get_kbit_device_map
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training


def setup_model_and_tokenizer(args):
    """Load and configure the model and tokenizer.
    
    Args:
        args: Parsed command line arguments containing model configuration.
        
    Returns:
        tuple: (model, tokenizer) - Loaded model and tokenizer.
    """
    quantization_config = None
    if args.use_4bit_quantization:
        print("Using 4-bit quantization")
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,                  
            bnb_4bit_quant_type="nf4",          
            bnb_4bit_compute_dtype=torch.bfloat16, 
            bnb_4bit_use_double_quant=True
        )

    tokenizer = AutoTokenizer.from_pretrained(
        args.model, 
        model_max_length=args.max_seq_length, 
        padding_side="right"
    )
    
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.model, 
        attn_implementation="flash_attention_2",
        quantization_config=quantization_config,
        device_map=get_kbit_device_map() if quantization_config else None,
        dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
    )

    if not args.full_finetuning:
        model = setup_lora(model, quantization_config, args)
    
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": True})
    return model, tokenizer


def setup_lora(model, quantization_config, args):
    """Configure LoRA for the model.
    
    Args:
        model: The model to configure LoRA for.
        quantization_config: Quantization configuration (if any).
        args: Parsed command line arguments containing LoRA configuration.
        
    Returns:
        model: Model with LoRA configuration applied.
    """
    if quantization_config:
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=False)
    
    peft_config = LoraConfig(
        r=args.lora_rank,
        lora_alpha=args.lora_rank,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        lora_dropout=0.1,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model.enable_input_require_grads()
    return get_peft_model(model, peft_config)

