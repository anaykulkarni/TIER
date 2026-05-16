import json
import os
import random

from tier.prompts import FEWSHOT_EXAMPLES, FUNCTION_DEFINITIONS, instructions


class Preprocessor:
    def __init__(self, instructions_fp=None, function_definitions_fp=None, fewshot_fp=None):

        self.instructions_fp = instructions_fp or str(instructions("xml"))
        self.function_definitions_fp = function_definitions_fp or str(FUNCTION_DEFINITIONS)
        self.fewshot_fp = fewshot_fp or str(FEWSHOT_EXAMPLES)
        
        self.instructions = self._load_instructions(self.instructions_fp)
        self.function_definitions = self._load_all_function_definitions(self.function_definitions_fp)
        self.fewshot_examples = self._load_fewshot_examples(self.fewshot_fp)

        self.all_functions = self.get_all_functions()

    def set_tokenizer(self, tokenizer):
        self.tokenizer = tokenizer
        
    def _load_instructions(self, instructions_fp) -> str:
        if not instructions_fp:
            raise ValueError("Instructions file path is not set")
        with open(instructions_fp, "r") as f:
            instructions = f.read()
        return instructions
    
    def _load_fewshot_examples(self, fewshot_fp) -> str:
        if not fewshot_fp:
            raise ValueError("Fewshot file path is not set")
        with open(fewshot_fp, "r") as f:
            fewshot_examples = f.read()
        return fewshot_examples

    def _load_all_function_definitions(self, function_definitions_fp) -> str:
        if not function_definitions_fp:
            raise ValueError("Function definitions file path is not set")
        with open(function_definitions_fp, 'r') as file:
            functions = json.load(file)
        return functions
    
    def get_all_functions(self):
        if not self.function_definitions:
            self.function_definitions = self._load_all_function_definitions(self.function_definitions_fp)
        return list(self.function_definitions.keys())

    def _filter_function_definitions(self, keep=[]):
        if not self.function_definitions:
            self.function_definitions = self._load_all_function_definitions(self.function_definitions_fp)
        if keep:
            keep = set(keep)
            return [self.function_definitions[f] for f in self.function_definitions if f in keep]
        return self.function_definitions

    def _convert_functions_format(self, functions):
        # Function definitions are always in JSON format
        if isinstance(functions, dict):
            return json.dumps(functions, indent=4)
        elif isinstance(functions, list):
            return "\n".join([json.dumps(f, indent=4) for f in functions])
        else:
            return str(functions)

    def prepare_system_prompt(self, keep=[]):
        if not self.instructions:
            self.instructions = self._load_instructions()

        # Always use json format for function definitions in system prompt

        functions = self._filter_function_definitions(keep=keep)
        system_prompt = self.instructions + "\n\n"
        system_prompt += "# Available APIs:\n\n"
        system_prompt += self._convert_functions_format(functions) + "\n"
        # system_prompt += "# Examples for reference:\n\n"
        # system_prompt += self.fewshot_examples + "\n"
        return system_prompt
    
    def _apply_chat_template(self, prompt, add_generation_prompt):
        return self.tokenizer.apply_chat_template(
            prompt,
            tokenize=False,
            add_generation_prompt=add_generation_prompt,
        )

    def prepare_prompts(self, dataset, k_extra_functions=0):
        if not self.all_functions:
            self.all_functions = self.get_all_functions()
        
        prompts = []
        for q in dataset:
            required_functions = q['apis']
            if k_extra_functions > 0:
                other_functions = list(set(self.all_functions) - set(required_functions))
                k = min(k_extra_functions, max(0, len(other_functions)))
                required_functions = required_functions + random.sample(other_functions, k=k)
            
            prompts.append([
                {
                    "role": "system",
                    "content": self.prepare_system_prompt(keep=required_functions)
                },
                {
                    "role": "user",
                    "content": q['question']
                }
            ])
        dataset = dataset.add_column('prompt', prompts)
        return dataset
    
    def prepare_prompts_for_sft(self, dataset, k_extra_functions=0):
        """Prepare SFT prompts by adding system prompt to existing messages.
        
        This method takes a dataset with 'messages' field containing user/assistant conversations
        and adds the appropriate system prompt at index 0.
        
        Args:
            dataset: Dataset with 'messages' field containing conversation turns.
            k_extra_functions: Number of extra functions to include (default: 0).
            
        Returns:
            Dataset: Updated dataset with system prompts added to messages.
        """
        if not self.all_functions:
            self.all_functions = self.get_all_functions()
        
        updated_messages = []
        for q in dataset:
            required_functions = q['apis']
            if k_extra_functions > 0:
                other_functions = list(set(self.all_functions) - set(required_functions))
                k = min(k_extra_functions, max(0, len(other_functions)))
                required_functions = required_functions + random.sample(other_functions, k=k)
            
            # Create system prompt
            system_prompt = self.prepare_system_prompt(keep=required_functions)
            system_message = {
                "role": "system",
                "content": system_prompt
            }
            
            # Get existing messages (user/assistant only)
            existing_messages = q['messages']
            
            # Add system prompt at index 0
            new_messages = [system_message] + existing_messages
            updated_messages.append(new_messages)
        
        # Replace the messages column with updated messages
        dataset = dataset.remove_columns(['messages'])
        dataset = dataset.add_column('messages', updated_messages)
        return dataset

    def prepare_prompts_for_toolace(self, dataset, k_extra_functions=0):
        if not self.all_functions or not isinstance(self.all_functions, set):
            self.all_functions = set(self.get_all_functions())
        
        prompts = []
        for q in dataset:
            # Safely get APIs list
            required_functions = q.get('apis', [])
            if not isinstance(required_functions, list):
                required_functions = []
            
            if k_extra_functions > 0:
                other_functions = list(self.all_functions - set(required_functions))
                k = min(k_extra_functions, max(0, len(other_functions)))
                required_functions = required_functions + random.sample(other_functions, k=k)
            
            system_content = self.prepare_system_prompt(keep=required_functions)
            
            # Safely append time if it exists and is not empty
            time_info = q.get('time', '').strip()
            if time_info:
                system_content += f"\n{time_info}"
            
            prompts.append([
                {
                    "role": "system",
                    "content": system_content
                },
                {
                    "role": "user",
                    "content": q['question']
                }
            ])
        dataset = dataset.add_column('prompt', prompts)
        return dataset
    
    def prepare_prompts_for_xlam(self, dataset, k_extra_functions=0):
        """Prepare prompts for XLAM dataset.
        
        Similar to prepare_prompts_for_toolace but adapted for XLAM's specific format.
        XLAM datasets don't use time information like ToolACE does.
        
        Args:
            dataset: Dataset with XLAM format.
            k_extra_functions: Number of extra functions to include (default: 0).
            
        Returns:
            Dataset: Dataset with prompt column added.
        """
        if not self.all_functions or not isinstance(self.all_functions, set):
            self.all_functions = set(self.get_all_functions())
        
        prompts = []
        for q in dataset:
            # Safely get APIs list
            required_functions = q.get('apis', [])
            if not isinstance(required_functions, list):
                required_functions = []
            
            if k_extra_functions > 0:
                other_functions = list(self.all_functions - set(required_functions))
                k = min(k_extra_functions, max(0, len(other_functions)))
                required_functions = required_functions + random.sample(other_functions, k=k)
            
            system_content = self.prepare_system_prompt(keep=required_functions)
            
            # XLAM doesn't use time information, so we skip the time append step
            # that ToolACE uses
            
            prompts.append([
                {
                    "role": "system",
                    "content": system_content
                },
                {
                    "role": "user",
                    "content": q['question']
                }
            ])
        dataset = dataset.add_column('prompt', prompts)
        return dataset