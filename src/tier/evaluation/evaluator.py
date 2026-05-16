from typing import Any
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel, PeftConfig
from collections import defaultdict
from torch.utils.data import DataLoader
from vllm import LLM, SamplingParams
from vllm.lora.request import LoRARequest
import random
import os
import json
from tier.parsing import Parser
from tier.rewards.tier import calculate_reward
from tier.rewards.simple import calculate_simple_reward
from tier.sampling import GenerationConfig

class Evaluator:
    def __init__(self, seed=42):
        self.lora_adapter_counter = 0
        self._set_seed(seed)
        self.generation_config = GenerationConfig()
        self.responses_file = None
        self.errors_file = None
        
    def _set_seed(self, seed=42):
        random.seed(seed)
        import numpy as np
        np.random.seed(seed)
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

    def _prepare_dataset(self, test_dataset, batch_size, oversample_factor=10):
        # Convert Hugging Face dataset to PyTorch-compatible format
        test_data = test_dataset.to_dict()
        test_data = list(
            zip(
                test_data['question'], 
                test_data['answer'], 
                test_data['num_calls'], 
                test_data['tag'], 
                test_data['prompt'],
                test_data['api_calls']
            )
        )
        test_data_oversampled = test_data * oversample_factor

        # Create a DataLoader for batching
        dataloader = DataLoader(test_data_oversampled, batch_size=batch_size, shuffle=False, num_workers=16, pin_memory=True)
        return dataloader

    def set_sampling_params(self, model, max_tokens):
        self.sampling_params = self.generation_config.get_sampling_params(model, max_tokens)
        print(f"Sampling params: {self.sampling_params}")

    def _log_to_responses(self, message):
        """Helper method to log correct responses"""
        print(message)
        if self.responses_file:
            self.responses_file.write(message + '\n')
            self.responses_file.flush()

    def _log_to_errors(self, message):
        """Helper method to log errors and mismatches"""
        print(message)
        if self.errors_file:
            self.errors_file.write(message + '\n')
            self.errors_file.flush()

    def _log_evaluation_result(self, entry_counter, prompt, question, tag, num_calls, generated_text, 
                            expected_api_calls, generated_api_calls, return_all, 
                            expected_answer, generated_answer, is_correct, is_exception, 
                            error_message=None, reward=None, log_responses=True):
        """Helper method to log evaluation results to appropriate files"""
        if not log_responses:
            return
            
        if is_exception:
            # Log to errors file
            self._log_to_errors('\n' + '='*60 + '\n')
            self._log_to_errors(f"Prompt: \n{prompt}")
            self._log_to_errors(f"Question {entry_counter}: \n{question}")
            self._log_to_errors(f"Tag: {tag}; # Calls: {num_calls}")
            self._log_to_errors(f"Generated Output: \n{generated_text}")
            self._log_to_errors(f"Expected API calls: \n{expected_api_calls}")
            self._log_to_errors(f"Generated API Calls: \n{generated_api_calls}")
            self._log_to_errors(f"Return All: {return_all}")
            self._log_to_errors(f"Expected Answer: \n{expected_answer}")
            self._log_to_errors(f"Generated Answer: \n{generated_answer}")
            if reward is not None:
                self._log_to_errors(f"Reward: {reward:.4f}")
            self._log_to_errors(f"Encountered exception! {error_message}")
        elif is_correct:
            # Log to responses file
            self._log_to_responses('\n' + '='*60 + '\n')
            self._log_to_responses(f"Prompt: \n{prompt}")
            self._log_to_responses(f"Question {entry_counter}: \n{question}")
            self._log_to_responses(f"Tag: {tag}; # Calls: {num_calls}")
            self._log_to_responses(f"Generated Output: \n{generated_text}")
            self._log_to_responses(f"Expected API calls: \n{expected_api_calls}")
            self._log_to_responses(f"Generated API Calls: \n{generated_api_calls}")
            self._log_to_responses(f"Return All: {return_all}")
            self._log_to_responses(f"Expected Answer: \n{expected_answer}")
            self._log_to_responses(f"Generated Answer: \n{generated_answer}")
            if reward is not None:
                self._log_to_responses(f"Reward: {reward:.4f}")
            self._log_to_responses("Answers match!")
        else:
            # Log to errors file (answers don't match)
            self._log_to_errors('\n' + '='*60 + '\n')
            self._log_to_errors(f"Prompt: \n{prompt}")
            self._log_to_errors(f"Question {entry_counter}: \n{question}")
            self._log_to_errors(f"Tag: {tag}; # Calls: {num_calls}")
            self._log_to_errors(f"Generated Output: \n{generated_text}")
            self._log_to_errors(f"Expected API calls: \n{expected_api_calls}")
            self._log_to_errors(f"Generated API Calls: \n{generated_api_calls}")
            self._log_to_errors(f"Return All: {return_all}")
            self._log_to_errors(f"Expected Answer: \n{expected_answer}")
            self._log_to_errors(f"Generated Answer: \n{generated_answer}")
            if reward is not None:
                self._log_to_errors(f"Reward: {reward:.4f}")
            self._log_to_errors("Answers don't match")

    def _print_results(self, total_samples, correct, exceptions, total, rewards=None, errors=None, run_name=None, output_dir=None):
        results_text = []
        results_text.append("=" * 60)
        results_text.append("Evaluation Results")
        results_text.append("=" * 60)

        results_text.append(f"Total Samples Tested: {total_samples}\n")

        total_correct = 0
        total_exceptions = 0
        total_reward = 0.0
        total_reward_count = 0

        for c in sorted(total.keys()):
            correct_count = correct[c]
            exception_count = exceptions[c]
            total_count = total[c]

            total_correct += correct_count
            total_exceptions += exception_count

            accuracy = 100 * correct_count / total_count
            exception_rate = 100 * exception_count / total_count

            results_text.append(f"{c}-Step Prompts:")
            results_text.append(f"  Accuracy         : {accuracy:.2f}%")
            results_text.append(f"  Exception Rate   : {exception_rate:.2f}%")
            
            # Add reward statistics if available
            if rewards and c in rewards and rewards[c]:
                category_rewards = rewards[c]
                avg_reward = sum(category_rewards) / len(category_rewards)
                max_reward = max(category_rewards)
                min_reward = min(category_rewards)
                results_text.append(f"  Avg Reward       : {avg_reward:.4f}")
                results_text.append(f"  Max Reward       : {max_reward:.4f}")
                results_text.append(f"  Min Reward       : {min_reward:.4f}")
                total_reward += sum(category_rewards)
                total_reward_count += len(category_rewards)
            
            results_text.append("")

        results_text.append("=" * 60)
        overall_accuracy = 100 * total_correct / total_samples
        overall_exception_rate = 100 * total_exceptions / total_samples

        results_text.append(f"Overall Accuracy      : {overall_accuracy:.2f}%")
        results_text.append(f"Overall Exception Rate: {overall_exception_rate:.2f}%")
        
        # Add overall reward statistics if available
        if total_reward_count > 0:
            overall_avg_reward = total_reward / total_reward_count
            results_text.append(f"Overall Avg Reward    : {overall_avg_reward:.4f}")
        
        results_text.append("=" * 60)

        # Print to console
        for line in results_text:
            print(line)
        
        # Write to file if output_dir is provided
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            results_file = os.path.join(output_dir, "eval_results.txt")
            with open(results_file, 'w') as f:
                for line in results_text:
                    f.write(line + '\n')
            print(f"Results saved to: {results_file}")

    def load_model_and_tokenizer_from_checkpoint(self, model_path, max_seq_length, max_lora_rank, use_vllm=False, vllm_gpu_memory_utilization=0.9):
        # Load model and tokenizer using vLLM if specified
        if use_vllm:
            # For full finetuned models (max_lora_rank=None), don't enable LoRA
            if max_lora_rank is None:
                model = LLM(
                    model=model_path,
                    max_model_len=max_seq_length,
                    dtype="bfloat16",
                    gpu_memory_utilization=vllm_gpu_memory_utilization
                )
            else:
                model = LLM(
                    model=model_path, 
                    max_model_len=max_seq_length,
                    enable_lora=True,
                    dtype="bfloat16",
                    gpu_memory_utilization=vllm_gpu_memory_utilization,
                    max_lora_rank=max_lora_rank
                )
            tokenizer = model.get_tokenizer()
        else:
            model = AutoModelForCausalLM.from_pretrained(model_path, device_map="auto")
            tokenizer = AutoTokenizer.from_pretrained(model_path, max_model_length=max_seq_length)

        return model, tokenizer

    def load_adapters(self, model, adapter_path, use_vllm=False):
        try:
            # returns vllm base model that supports lora and a lora request
            if use_vllm:
                self.lora_adapter_counter += 1
                lora_request = LoRARequest(f"lora_adapter_{self.lora_adapter_counter}", self.lora_adapter_counter, adapter_path)
                print(f"Successfully created LoRA request for adapter: {adapter_path}")
                return model, lora_request
            
            # Validate adapter path exists
            if not os.path.exists(adapter_path):
                raise FileNotFoundError(f"Adapter path not found: {adapter_path}")
                
            # Returns model with LoRA adapter loaded
            peft_config = PeftConfig.from_pretrained(adapter_path)  # This reads adapter_config.json
            model = PeftModel.from_pretrained(model, adapter_path, config=peft_config)
            print(f"Successfully loaded LoRA adapter from: {adapter_path}")
            return model, None
        except Exception as e:
            print(f"Error loading adapter from {adapter_path}: {str(e)}")
            print(f"Continuing evaluation with base model (no adapter loaded)")
            return model, None

    def _run_inference(self, model, tokenizer, prompts, lora_request=None, use_vllm=False):

        # Build prompt text using chat template
        text = [
            tokenizer.apply_chat_template([
                {"role": "system", "content": prompts[0]['content'][i]},
                {"role": "user", "content": prompts[1]['content'][i]},
            ], tokenize=False, add_generation_prompt=True)
            for i in range(len(prompts[0]['content']))
        ]
        
        if use_vllm:
            # vLLM inference
            outputs = model.generate(
                text,
                sampling_params=self.sampling_params,
                lora_request=lora_request
            )
            return text, [out.outputs[0].text for out in outputs]
        
        # Standard transformers inference
        # Tokenize prompts
        inputs = tokenizer(
            text,
            padding=True, # padding is required for transformers
            padding_side="left", # padding side should be left for inference
            truncation=True,
            return_tensors="pt",
            max_length=self.sampling_params.max_tokens,
        ).to(model.device)

        # Track input lengths
        input_lengths = inputs["input_ids"].shape[1]

        # Generate outputs
        out = model.generate(
            **inputs,
            temperature=self.sampling_params.temperature,
            top_p=self.sampling_params.top_p,
            top_k=self.sampling_params.top_k,
            min_p=self.sampling_params.min_p,
            max_new_tokens=self.sampling_params.max_tokens,
            do_sample=True,
        )

        # Extract only the generated continuation
        generated_tokens = out[:, input_lengths:]  # Strip prompt tokens
        outputs = tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)
        return text, outputs

    def evaluate_model(self, model, tokenizer, lora_request, test_dataset, parser: Parser, batch_size=32, oversample_factor=10, log_responses=True, use_vllm=False, output_dir=None, output_style='xml', reward_type='finegrained'):
        # Prepare the dataset and dataloader
        test_loader = self._prepare_dataset(test_dataset, batch_size, oversample_factor)

        total_samples = len(test_loader.dataset)
        correct = defaultdict(int)
        total = defaultdict(int)
        exceptions = defaultdict(int)
        errors = {}
        rewards = defaultdict(list)  # Track rewards per category

        # Setup output files for responses if output_dir is provided
        if output_dir and log_responses:
            os.makedirs(output_dir, exist_ok=True)
            self.responses_file = open(os.path.join(output_dir, "eval_responses.txt"), 'w')
            self.errors_file = open(os.path.join(output_dir, "eval_errors.txt"), 'w')

        entry_counter = 1
        # Iterate through batches
        for batch in test_loader:
            questions, answers, num_calls, tags, prompts, api_calls = batch

            input_messages, outputs = self._run_inference(model, tokenizer, prompts, lora_request=lora_request, use_vllm=use_vllm)

            # Process outputs for the batch
            for i, output in enumerate(outputs):
                generated_text = output  # Extract the generated text for each input
                c = num_calls[i].item()
                total[c] += 1

                calls, result = None, None
                return_all = None
                calls_gt = json.loads(api_calls[i])
                is_correct = False
                is_exception = False
                error_message = None
                
                try:
                    valid, format_errors = parser.check_format(generated_text, style=output_style)
                    if not valid:
                        raise ValueError(f"Error: {output_style} Format is incorrect. errors: {format_errors}")
                    
                    calls, return_all = parser.extract_tool_calls(generated_text, tag=tags[i], style=output_style)

                    if calls:
                        # Validate function calls
                        err_scores, validation_results = parser.validate_ast_against_function_definitions(calls)
                        if any(err_scores):
                            # Only format validation reports for functions that failed
                            failed_reports = [
                                f"{fn_name}:\n{parser.validator.format_validation_report(result)}"
                                for fn_name, result in validation_results.items()
                                if not result.get('success', False)
                            ]
                            report = "\n\n".join(failed_reports) if failed_reports else "Validation failed"
                            raise ValueError(f"Error: AST validation failed.\n{report}")
                        
                    result = parser.execute_syntax_tree(calls, return_all)
                    result = parser.serialize_response(result)
                    if result == answers[i]:
                        is_correct = True
                        correct[c] += 1
                    else:
                        is_correct = False
                                        
                except Exception as e:
                    is_exception = True
                    error_message = str(e)
                    exceptions[c] += 1
                    errors[questions[i]] = {
                        "output": generated_text,
                        "answer": answers[i],
                        "api_call": calls,
                        "result": result,
                        "error": error_message
                    }

                try:
                    if reward_type == 'finegrained':
                        reward_values = calculate_reward([generated_text], [answers[i]], [tags[i]], parser, style=output_style)
                    elif reward_type == 'simple':
                        reward_values = calculate_simple_reward([generated_text], [answers[i]], [tags[i]], parser, style=output_style)
                except Exception as e:
                    reward_values = [0.0]

                # Track reward for this sample
                reward = reward_values[0] if reward_values else 0.0
                rewards[c].append(reward)

                # Log based on outcome
                self._log_evaluation_result(
                    entry_counter=entry_counter,
                    prompt=input_messages[i],
                    question=questions[i],
                    tag=tags[i],
                    num_calls=num_calls[i],
                    generated_text=generated_text,
                    expected_api_calls=calls_gt,
                    generated_api_calls=calls,
                    return_all=return_all,
                    expected_answer=answers[i],
                    generated_answer=result,
                    is_correct=is_correct,
                    is_exception=is_exception,
                    error_message=error_message,
                    reward=reward,
                    log_responses=log_responses
                )
                
                entry_counter += 1
            
        # Close the files if they were opened
        if self.responses_file:
            self.responses_file.close()
            print(f"Correct responses saved to: {os.path.join(output_dir, 'eval_responses.txt')}")
        
        if self.errors_file:
            self.errors_file.close()
            print(f"Errors and mismatches saved to: {os.path.join(output_dir, 'eval_errors.txt')}")
            
        # Print final results
        self._print_results(total_samples, correct, exceptions, total, rewards, errors, output_dir=output_dir)