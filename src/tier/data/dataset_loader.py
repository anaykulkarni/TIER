"""
Dataset loading and management utilities.
"""

import glob
import json
import os
import random
import re

import pandas as pd
from datasets import Dataset

from tier.constants import DATA_DIR


def set_seed(seed=42):
    """Set random seed for reproducibility."""
    random.seed(seed)
    import numpy as np
    np.random.seed(seed)
    import torch
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class DatasetManager:
    """Manager for loading, filtering, and preparing datasets for training."""
    
    def __init__(self, seed=42, dataset_path=None, objective=None):
        """Initialize DatasetManager.
        
        Args:
            seed: Random seed for reproducibility.
            dataset_path: Path to the dataset file. If None, uses default path based on objective.
            objective: Training objective ('GRPO' or 'SFT'). Used to determine default dataset path.
        """
        self.seed = seed
        self.objective = objective or 'GRPO'
        
        if dataset_path is None:
            # Default dataset paths (DepthBench JSON dumps and the SFT corpus
            # live in the repo-root ``data/`` directory; see :mod:`tier.constants`).
            if self.objective == 'SFT':
                self.dataset_path = str(DATA_DIR / 'sft' / 'sft_dataset.json')
            else:
                self.dataset_path = str(DATA_DIR / 'depthbench' / 'full_dataset.json')
        else:
            self.dataset_path = dataset_path
            
        set_seed(seed)
    
    def _load_raw_dataset(self):
        """Load the raw dataset from JSON file.
        
        Returns:
            dict: Raw dataset loaded from JSON.
        """
        with open(self.dataset_path, 'r') as file:
            data = json.load(file)
        return data
    
    def _filter_by_tools(self, data, filter_dataset_by_tools):
        """Filter dataset by tool names.
        
        Args:
            data: Dataset dictionary.
            filter_dataset_by_tools: Comma-separated string of tool names.
            
        Returns:
            dict: Filtered dataset.
        """
        if not filter_dataset_by_tools:
            return data
        
        filter_set = set([f.strip() for f in filter_dataset_by_tools.split(',')])
        return {q: data[q] for q in data if any(f in filter_set for f in data[q]['apis'])}
    
    def _filter_by_num_calls(self, data, filter_dataset_by_num_calls):
        """Filter dataset by number of function calls.
        
        Args:
            data: Dataset dictionary.
            filter_dataset_by_num_calls: Comma-separated string of call counts.
            
        Returns:
            dict: Filtered dataset.
        """
        if not filter_dataset_by_num_calls:
            return data
        
        filter_set = set([int(f.strip()) for f in filter_dataset_by_num_calls.split(',')])
        return {q: data[q] for q in data if data[q]['num_calls'] in filter_set}
    
    def _filter_chaining_functions(self, data):
        """Remove functions that don't work without chaining enabled.
        
        Functions that require large inputs like DataFrames are difficult for
        models to write out in function calls.
        
        Args:
            data: Dataset dictionary.
            
        Returns:
            dict: Filtered dataset with chaining-required functions removed.
        """
        chaining_functions = set([
            'FilterByCarBuild',
            'FilterByCarBrand',
            'FilterByCarPrice',
            'FilterByCarMileage',
            'FilterByCarProductionYear',
            'FilterByCarTitle',
            'FilterByCuisine',   
            'FilterByRatings',
            'FilterByOpeningHours',
        ])
        return {q: data[q] for q in data if not any(f in chaining_functions for f in data[q]['apis'])}
    
    def create_dataset(self, filter_dataset_by_tools='', filter_dataset_by_num_calls=None, chain=True):
        """Create a single-turn dataset.
        
        Args:
            filter_dataset_by_tools: Comma-separated list of tools to filter by.
            filter_dataset_by_num_calls: Comma-separated list of call counts to filter by.
            chain: Whether chaining is enabled (affects filtering).
            
        Returns:
            Dataset: Hugging Face Dataset object.
        """
        data = self._load_raw_dataset()
        data = self._filter_by_tools(data, filter_dataset_by_tools)
        data = self._filter_by_num_calls(data, filter_dataset_by_num_calls)
        
        if not chain:
            data = self._filter_chaining_functions(data)
        
        # Helper function to ensure consistent data types
        def normalize_value(value):
            """Convert dictionaries to JSON strings for consistency."""
            if isinstance(value, dict):
                return json.dumps(value)
            return value
        
        dataset = Dataset.from_dict({
            'question': [data[q]['prompt'] for q in data],
            'answer': [normalize_value(data[q]['response']) for q in data],
            'num_calls': [data[q]['num_calls'] for q in data],
            'tag': [data[q]['tag'] for q in data],
            'apis': [data[q]['apis'] for q in data],
            'api_calls': [normalize_value(data[q]['api_calls']) for q in data],
            'return_all': [data[q]['return_all'] for q in data],
            'follow_up': [data[q]['follow_up'] for q in data],
        })
        
        print(f"Dataset size: {len(dataset)}")
        return dataset
    
    def create_dataset_multiturn(self, filter_dataset_by_tools='', filter_dataset_by_num_calls=None, chain=True):
        """Create a multi-turn dataset with 'solved' field.
        
        Args:
            filter_dataset_by_tools: Comma-separated list of tools to filter by.
            filter_dataset_by_num_calls: Comma-separated list of call counts to filter by.
            chain: Whether chaining is enabled (affects filtering).
            
        Returns:
            Dataset: Hugging Face Dataset object with 'solved' field.
        """
        data = self._load_raw_dataset()
        data = self._filter_by_tools(data, filter_dataset_by_tools)
        data = self._filter_by_num_calls(data, filter_dataset_by_num_calls)
        
        if not chain:
            data = self._filter_chaining_functions(data)
        
        dataset = Dataset.from_dict({
            'id': [q for q in data],
            'turn': [1 for q in data],
            'question': [data[q]['prompt'] for q in data],
            'answer': [data[q]['response'] for q in data],
            'num_calls': [data[q]['num_calls'] for q in data],
            'tag': [data[q]['tag'] for q in data],
            'apis': [data[q]['apis'] for q in data],
            'api_calls': [json.dumps(data[q]['api_calls']) if isinstance(data[q]['api_calls'], dict) else data[q]['api_calls'] for q in data],
            'solved': [False for q in data],
        })
        
        print(f"Dataset size: {len(dataset)}")
        return dataset
    
    def create_sft_dataset(self, filter_dataset_by_tools='', filter_dataset_by_num_calls=None, chain=True):
        """Create a single-turn SFT dataset.
        
        Args:
            filter_dataset_by_tools: Comma-separated list of tools to filter by.
            filter_dataset_by_num_calls: Comma-separated list of call counts to filter by.
            chain: Whether chaining is enabled (affects filtering).
            
        Returns:
            Dataset: Hugging Face Dataset object with messages field.
        """
        data = self._load_raw_dataset()
        data = self._filter_by_tools(data, filter_dataset_by_tools)
        data = self._filter_by_num_calls(data, filter_dataset_by_num_calls)
        
        if not chain:
            data = self._filter_chaining_functions(data)
        
        dataset = Dataset.from_dict({
            'messages': [data[q]['messages'] for q in data],
            'question': [data[q]['question'] for q in data],
            'answer': [data[q]['answer'] for q in data],
            'num_calls': [data[q]['num_calls'] for q in data],
            'tag': [data[q]['tag'] for q in data],
            'apis': [data[q]['apis'] for q in data],
            'api_calls': [data[q]['api_calls'] for q in data],
        })
        
        print(f"Dataset size: {len(dataset)}")
        return dataset
    
    def create_sft_dataset_multiturn(self, filter_dataset_by_tools='', filter_dataset_by_num_calls=None, chain=True):
        """Create a multi-turn SFT dataset with 'solved' field.
        
        Args:
            filter_dataset_by_tools: Comma-separated list of tools to filter by.
            filter_dataset_by_num_calls: Comma-separated list of call counts to filter by.
            chain: Whether chaining is enabled (affects filtering).
            
        Returns:
            Dataset: Hugging Face Dataset object with messages field and 'solved' field.
        """
        data = self._load_raw_dataset()
        data = self._filter_by_tools(data, filter_dataset_by_tools)
        data = self._filter_by_num_calls(data, filter_dataset_by_num_calls)
        
        if not chain:
            data = self._filter_chaining_functions(data)
        
        dataset = Dataset.from_dict({
            'id': [q for q in data],
            'turn': [1 for q in data],
            'messages': [data[q]['messages'] for q in data],
            'question': [data[q]['question'] for q in data],
            'answer': [data[q]['answer'] for q in data],
            'num_calls': [data[q]['num_calls'] for q in data],
            'tag': [data[q]['tag'] for q in data],
            'apis': [data[q]['apis'] for q in data],
            'api_calls': [data[q]['api_calls'] for q in data],
            'solved': [False for q in data],
        })
        
        print(f"Dataset size: {len(dataset)}")
        return dataset
    
    def create_sft_seen_unseen_dataset(self, chain=True):
        """Create SFT training and testing sets with disjoint functions.
        
        Args:
            chain: Whether chaining is enabled (affects filtering of chaining functions).
            
        Returns:
            tuple: (trainset, testset) - Two Dataset objects with disjoint function sets and messages field.
        """
        training_functions = set([
            'BookSearchAPI',
            'CryptoPriceAPI',
            'CurrencyExchangeAPI',
            'EnglishDictionaryAPI',
            'FlightStatusAPI',
            'MovieSearchAPI',
            'GetLocation',  
            'FindDealershipsByLocation',
            'GetCarListingByDealerships',
            'FilterByCarBuild',
            'FilterByCarBrand',
            'FilterByCarPrice',
            'FilterByCarMileage',
            'FilterByCarProductionYear',
            'FilterByCarTitle',
            'SearchFlight',
            'BookFlight',
            'CancelFlight',    
            'SearchSKU',
            'CreateCart',
            'CancelStoreOrder'
        ])
        
        testing_functions = set([
            'SongLyricsAPI',
            'SpanishDictionaryAPI',
            'StockPriceAPI',
            'TimeZoneConverterAPI',
            'UnitConversionAPI',
            'GetLocation',
            'GetDate',
            'GetTime',
            'GetWeather',
            'GetAirQuality',
            'FindRestaurantsByLocation',
            'FilterByCuisine',   
            'FilterByRatings',
            'FilterByOpeningHours',
            'SearchHotel',
            'BookHotel',
            'CancelHotel',
            'SearchProducts',
            'CheckoutCart'
        ])
        
        # Remove chaining functions if chaining is disabled
        if not chain:
            chaining_functions = set([
                'FilterByCarBuild',
                'FilterByCarBrand',
                'FilterByCarPrice',
                'FilterByCarMileage',
                'FilterByCarProductionYear',
                'FilterByCarTitle',
                'FilterByCuisine',   
                'FilterByRatings',
                'FilterByOpeningHours',
            ])
            training_functions -= chaining_functions
            testing_functions -= chaining_functions
        
        raw_dataset = self._load_raw_dataset()
        
        # Apply chaining function filtering if chain is disabled
        if not chain:
            raw_dataset = self._filter_chaining_functions(raw_dataset)
        
        # Irrelevance detection - use actual keys from filtered dataset
        no_call_idx = [idx for idx in raw_dataset.keys() if raw_dataset[idx]['num_calls'] == 0]
        
        # Populate training set and test set with equal number of no call indices
        training_set = {idx: raw_dataset[idx] for idx in no_call_idx[:50]}
        testing_set = {idx: raw_dataset[idx] for idx in no_call_idx[50:]}
        
        # Samples requiring tool calls - use actual keys from filtered dataset
        call_idx = [idx for idx in raw_dataset.keys() if raw_dataset[idx]['num_calls'] > 0]
        
        # Populate training set with call_idx
        for i in call_idx:
            apis = raw_dataset[i]['apis']
            if any(f not in training_functions for f in apis):
                # problem requires apis that are not available in training functions
                continue
            training_set[i] = raw_dataset[i]
        
        # Populate testing set with call_idx
        for i in call_idx:
            apis = raw_dataset[i]['apis']
            if any(f not in testing_functions for f in apis):
                # problem requires apis that are not available in testing functions
                continue
            testing_set[i] = raw_dataset[i]
        
        # Patch GetLocation to GetCurrentLocation to avoid function leakage in testing set
        for i in testing_set:
            for j in range(len(testing_set[i]['apis'])):
                if testing_set[i]['apis'][j] == 'GetLocation':
                    testing_set[i]['apis'][j] = 'GetCurrentLocation'
            testing_set[i]['api_calls'] = testing_set[i]['api_calls'].replace('GetLocation', 'GetCurrentLocation')
        
        print(f"{len(raw_dataset) - len(training_set) - len(testing_set)} samples remain unused")
        
        train_indices = list(training_set.keys())
        test_indices = list(testing_set.keys())
        
        random.shuffle(train_indices)
        random.shuffle(test_indices)
        
        trainset = Dataset.from_dict({
            'id': [str(idx) for idx in train_indices],
            'turn': [1 for idx in train_indices],
            'messages': [training_set[idx]['messages'] for idx in train_indices],
            'question': [training_set[idx]['question'] for idx in train_indices],
            'answer': [training_set[idx]['answer'] for idx in train_indices],
            'num_calls': [training_set[idx]['num_calls'] for idx in train_indices],
            'tag': [training_set[idx]['tag'] for idx in train_indices],
            'apis': [training_set[idx]['apis'] for idx in train_indices],
            'api_calls': [training_set[idx]['api_calls'] for idx in train_indices],
            'solved': [False for idx in train_indices],
        })
        
        testset = Dataset.from_dict({
            'id': [str(idx) for idx in test_indices],
            'turn': [1 for idx in test_indices],
            'messages': [testing_set[idx]['messages'] for idx in test_indices],
            'question': [testing_set[idx]['question'] for idx in test_indices],
            'answer': [testing_set[idx]['answer'] for idx in test_indices],
            'num_calls': [testing_set[idx]['num_calls'] for idx in test_indices],
            'tag': [testing_set[idx]['tag'] for idx in test_indices],
            'apis': [testing_set[idx]['apis'] for idx in test_indices],
            'api_calls': [testing_set[idx]['api_calls'] for idx in test_indices],
            'solved': [False for idx in test_indices],
        })
        
        print(f"Train dataset size: {len(trainset)}")
        print(f"Test dataset size: {len(testset)}")
        
        return trainset, testset
    
    def setup_dataset(self, parser, args, dataset_dir=None):
        """Set up and prepare the training and testing datasets.
        
        This method handles both single-turn and multi-turn training modes.
        For multi-turn, it checks for existing turn datasets and loads the latest one.
        
        Args:
            parser: Parser instance with preprocessor for preparing prompts.
            args: Parsed command line arguments.
            dataset_dir: Directory for storing/loading turn-based datasets (multiturn only).
                        If None and multiturn is enabled, will be created automatically.
            
        Returns:
            tuple: (train_dataset, test_dataset) - Two Dataset objects.
        """
        # Update objective from args if available
        if hasattr(args, 'objective'):
            self.objective = args.objective

        if args.toolace:
            if args.multiturn:
                # Create dataset directory if not provided
                if dataset_dir is None:
                    dataset_dir = f"{args.output_dir}/datasets"
                os.makedirs(dataset_dir, exist_ok=True)
                return self._setup_toolace_multiturn_dataset(parser, args, dataset_dir)
            else:
                return self._setup_toolace_singleturn_dataset(parser, args)
        
        if hasattr(args, 'xlam') and args.xlam:
            if args.multiturn:
                # Create dataset directory if not provided
                if dataset_dir is None:
                    dataset_dir = f"{args.output_dir}/datasets"
                os.makedirs(dataset_dir, exist_ok=True)
                return self._setup_xlam_multiturn_dataset(parser, args, dataset_dir)
            else:
                return self._setup_xlam_singleturn_dataset(parser, args)
        
        if args.multiturn:
            # Create dataset directory if not provided
            if dataset_dir is None:
                dataset_dir = f"{args.output_dir}/datasets"
            os.makedirs(dataset_dir, exist_ok=True)
            return self._setup_multiturn_dataset(parser, args, dataset_dir)
        else:
            return self._setup_singleturn_dataset(parser, args)
    
    def _setup_toolace_singleturn_dataset(self, parser, args):
        """Set up single-turn ToolACE training and testing datasets.
        
        Args:
            parser: Parser instance with preprocessor.
            args: Parsed command line arguments.
        """
        # use toolace dataset path
        self.dataset_path = str(DATA_DIR / 'toolace' / 'rl_dataset.json')
        data = self._load_raw_dataset()

        import json
        
        # Helper function to serialize dicts to JSON strings
        def serialize_if_dict(value):
            if isinstance(value, dict):
                return json.dumps(value)
            return value
        
        train_dataset = Dataset.from_dict({
            'system_prompt': [data[q]['system_prompt'] for q in data],
            'question': [data[q]['prompt'] for q in data],
            'answer': [serialize_if_dict(data[q]['response']) for q in data],
            'num_calls': [data[q]['num_calls'] for q in data],
            'time': [data[q]['time'] for q in data],
            'tag': [data[q]['tag'] for q in data],
            'apis': [data[q]['apis'] for q in data],
            'api_calls': [serialize_if_dict(data[q]['api_calls']) for q in data],
        })
        
        train_dataset = parser.preprocessor.prepare_prompts_for_toolace(
            train_dataset, 
            k_extra_functions=args.k_extra_functions
        )
        
        return train_dataset, None
    
    def _setup_toolace_multiturn_dataset(self, parser, args, dataset_dir):
        """Set up multi-turn ToolACE training and testing datasets.
        
        Args:
            parser: Parser instance with preprocessor.
            args: Parsed command line arguments.
            dataset_dir: Directory for storing/loading turn-based datasets.
            
        Returns:
            tuple: (train_dataset, test_dataset) - Two Dataset objects.
        """
        # Check for existing turn dataset files
        existing_files = glob.glob(f"{dataset_dir}/combined_toolace_train_dataset_turn-*.json")
        
        if existing_files:
            # Extract turn numbers and find the latest
            turn_files = []
            for file in existing_files:
                match = re.search(r'combined_toolace_train_dataset_turn-(\d+)\.json', file)
                if match:
                    turn_files.append((int(match.group(1)), file))
            
            # Sort by turn number and get the latest
            turn_files.sort(key=lambda x: x[0], reverse=True)
            latest_file = turn_files[0][1]
            
            print(f"Loading ToolACE dataset from {latest_file}")
            # Use pandas to read JSONL format (each line is a JSON object)
            df = pd.read_json(latest_file, lines=True)
            # Ensure 'id' column is always string type to maintain consistency
            if 'id' in df.columns:
                df['id'] = df['id'].astype(str)
            train_dataset = Dataset.from_pandas(df)
            print(f"Loaded {len(train_dataset)} ToolACE examples from turn {turn_files[0][0]}")
            print(f"Dataset columns after validation: {list(train_dataset.column_names)}")
            test_dataset = None  # No test set when loading from existing turns
        else:
            # No existing files, create ToolACE dataset from scratch
            print("No existing ToolACE turn datasets found, creating new dataset")
            
            # Use create_toolace_dataset_multiturn with filter arguments
            raw_dataset = self.create_toolace_dataset_multiturn(
                filter_dataset_by_tools=args.filter_dataset_by_tools,
                filter_dataset_by_num_calls=args.filter_dataset_by_num_calls,
            )
            
            # Prepare prompts for ToolACE
            dataset = parser.preprocessor.prepare_prompts_for_toolace(
                raw_dataset, 
                k_extra_functions=args.k_extra_functions
            )
            
            # Check if full_dataset flag is set (used in evaluation)
            use_full_dataset = getattr(args, 'full_dataset', False)
            
            if use_full_dataset:
                # Use entire dataset without splitting
                train_dataset = dataset.shuffle(seed=self.seed)
                test_dataset = None
            elif args.test_size > 0:
                # Split dataset based on test_size
                split_datasets = dataset.train_test_split(
                    test_size=args.test_size, 
                    seed=self.seed, 
                    shuffle=True
                )
                train_dataset = split_datasets['train']
                test_dataset = split_datasets['test']
            else:
                # No splitting, use all as training data
                train_dataset = dataset.shuffle(seed=self.seed)
                test_dataset = None
        
        print(f"ToolACE Train dataset size: {len(train_dataset)}")
        if test_dataset is not None:
            print(f"ToolACE Test dataset size: {len(test_dataset)}")
        
        return train_dataset, test_dataset
    
    def _setup_xlam_singleturn_dataset(self, parser, args):
        """Set up single-turn XLAM training and testing datasets.
        
        Args:
            parser: Parser instance with preprocessor.
            args: Parsed command line arguments.
        """
        # use XLAM dataset path
        self.dataset_path = str(DATA_DIR / 'xlam' / 'rl_dataset.json')
        data = self._load_raw_dataset()

        import json
        
        # Helper function to serialize dicts to JSON strings
        def serialize_if_dict(value):
            if isinstance(value, dict):
                return json.dumps(value)
            return value
        
        train_dataset = Dataset.from_dict({
            'system_prompt': ['' for q in data],
            'question': [data[q]['prompt'] for q in data],
            'answer': [serialize_if_dict(data[q]['response']) for q in data],
            'num_calls': [data[q]['num_calls'] for q in data],
            'time': ['' for q in data],
            'tag': [data[q]['tag'] for q in data],
            'apis': [data[q]['apis'] for q in data],
            'api_calls': [serialize_if_dict(data[q]['api_calls']) for q in data],
        })
        
        train_dataset = parser.preprocessor.prepare_prompts_for_xlam(
            train_dataset, 
            k_extra_functions=args.k_extra_functions
        )
        
        return train_dataset, None
    
    def _setup_xlam_multiturn_dataset(self, parser, args, dataset_dir):
        """Set up multi-turn XLAM training and testing datasets.
        
        Args:
            parser: Parser instance with preprocessor.
            args: Parsed command line arguments.
            dataset_dir: Directory for storing/loading turn-based datasets.
            
        Returns:
            tuple: (train_dataset, test_dataset) - Two Dataset objects.
        """
        # Check for existing turn dataset files
        existing_files = glob.glob(f"{dataset_dir}/combined_xlam_train_dataset_turn-*.json")
        
        if existing_files:
            # Extract turn numbers and find the latest
            turn_files = []
            for file in existing_files:
                match = re.search(r'combined_xlam_train_dataset_turn-(\d+)\.json', file)
                if match:
                    turn_files.append((int(match.group(1)), file))
            
            # Sort by turn number and get the latest
            turn_files.sort(key=lambda x: x[0], reverse=True)
            latest_file = turn_files[0][1]
            
            print(f"Loading XLAM dataset from {latest_file}")
            # Use pandas to read JSONL format (each line is a JSON object)
            df = pd.read_json(latest_file, lines=True)
            # Ensure 'id' column is always string type to maintain consistency
            if 'id' in df.columns:
                df['id'] = df['id'].astype(str)
            train_dataset = Dataset.from_pandas(df)
            print(f"Loaded {len(train_dataset)} XLAM examples from turn {turn_files[0][0]}")
            print(f"Dataset columns after validation: {list(train_dataset.column_names)}")
            test_dataset = None  # No test set when loading from existing turns
        else:
            # No existing files, create XLAM dataset from scratch
            print("No existing XLAM turn datasets found, creating new dataset")
            
            # Use create_xlam_dataset_multiturn with filter arguments
            raw_dataset = self.create_xlam_dataset_multiturn(
                filter_dataset_by_tools=args.filter_dataset_by_tools,
                filter_dataset_by_num_calls=args.filter_dataset_by_num_calls,
            )
            
            # Prepare prompts for XLAM using dedicated XLAM method
            dataset = parser.preprocessor.prepare_prompts_for_xlam(
                raw_dataset, 
                k_extra_functions=args.k_extra_functions
            )
            
            # Check if full_dataset flag is set (used in evaluation)
            use_full_dataset = getattr(args, 'full_dataset', False)
            
            if use_full_dataset:
                # Use entire dataset without splitting
                train_dataset = dataset.shuffle(seed=self.seed)
                test_dataset = None
            elif args.test_size > 0:
                # Split dataset based on test_size
                split_datasets = dataset.train_test_split(
                    test_size=args.test_size, 
                    seed=self.seed, 
                    shuffle=True
                )
                train_dataset = split_datasets['train']
                test_dataset = split_datasets['test']
            else:
                # No splitting, use all as training data
                train_dataset = dataset.shuffle(seed=self.seed)
                test_dataset = None
        
        print(f"XLAM Train dataset size: {len(train_dataset)}")
        if test_dataset is not None:
            print(f"XLAM Test dataset size: {len(test_dataset)}")
        
        return train_dataset, test_dataset
    
    def _setup_singleturn_dataset(self, parser, args):
        """Set up single-turn training and testing datasets.
        
        Args:
            parser: Parser instance with preprocessor.
            args: Parsed command line arguments.
            
        Returns:
            tuple: (train_dataset, test_dataset) - Two Dataset objects.
        """
        if args.split_dataset:
            # Use seen/unseen split - ignore test_size and filter arguments
            if self.objective == 'SFT':
                train_dataset, test_dataset = self.create_sft_seen_unseen_dataset(chain=args.chain)
            else:
                train_dataset, test_dataset = self.create_seen_unseen_dataset(chain=args.chain)
            
            # Prepare prompts based on objective
            if self.objective == 'SFT':
                # Add system prompts to SFT datasets
                train_dataset = parser.preprocessor.prepare_prompts_for_sft(
                    train_dataset, 
                    k_extra_functions=args.k_extra_functions
                )
                test_dataset = parser.preprocessor.prepare_prompts_for_sft(
                    test_dataset, 
                    k_extra_functions=args.k_extra_functions
                )
            else:
                # Prepare prompts for RL datasets
                train_dataset = parser.preprocessor.prepare_prompts(
                    train_dataset, 
                    k_extra_functions=args.k_extra_functions
                )
                test_dataset = parser.preprocessor.prepare_prompts(
                    test_dataset, 
                    k_extra_functions=args.k_extra_functions
                )
        else:
            # Use create_dataset with test_size and filter arguments
            if self.objective == 'SFT':
                raw_dataset = self.create_sft_dataset(
                    filter_dataset_by_tools=args.filter_dataset_by_tools,
                    filter_dataset_by_num_calls=args.filter_dataset_by_num_calls,
                    chain=args.chain
                )
                # Add system prompts to SFT dataset
                dataset = parser.preprocessor.prepare_prompts_for_sft(
                    raw_dataset, 
                    k_extra_functions=args.k_extra_functions
                )
            else:
                raw_dataset = self.create_dataset(
                    filter_dataset_by_tools=args.filter_dataset_by_tools,
                    filter_dataset_by_num_calls=args.filter_dataset_by_num_calls,
                    chain=args.chain
                )
                dataset = parser.preprocessor.prepare_prompts(
                    raw_dataset, 
                    k_extra_functions=args.k_extra_functions
                )
            
            # Check if full_dataset flag is set (used in evaluation)
            use_full_dataset = getattr(args, 'full_dataset', False)
            
            if use_full_dataset:
                # Use entire dataset without splitting
                train_dataset = dataset.shuffle(seed=self.seed)
                test_dataset = None
            elif args.test_size > 0:
                # Split dataset based on test_size
                split_datasets = dataset.train_test_split(
                    test_size=args.test_size, 
                    seed=self.seed, 
                    shuffle=True
                )
                train_dataset = split_datasets['train']
                test_dataset = split_datasets['test']
            else:
                # No splitting, use all as training data
                train_dataset = dataset.shuffle(seed=self.seed)
                test_dataset = None
        
        print(f"Train dataset size: {len(train_dataset)}")
        if test_dataset is not None:
            print(f"Test dataset size: {len(test_dataset)}")
        
        return train_dataset, test_dataset
    
    def _setup_multiturn_dataset(self, parser, args, dataset_dir):
        """Set up multi-turn training and testing datasets.
        
        Checks for existing turn datasets and loads the latest one.
        If none exist, creates a new dataset from scratch.
        
        Args:
            parser: Parser instance with preprocessor.
            args: Parsed command line arguments.
            dataset_dir: Directory for storing/loading turn-based datasets.
            
        Returns:
            tuple: (train_dataset, test_dataset) - Two Dataset objects.
        """
        # Check for existing turn dataset files
        existing_files = glob.glob(f"{dataset_dir}/combined_train_dataset_turn-*.json")
        
        if existing_files:
            # Extract turn numbers and find the latest
            turn_files = []
            for file in existing_files:
                match = re.search(r'combined_train_dataset_turn-(\d+)\.json', file)
                if match:
                    turn_files.append((int(match.group(1)), file))
            
            # Sort by turn number and get the latest
            turn_files.sort(key=lambda x: x[0], reverse=True)
            latest_file = turn_files[0][1]
            
            print(f"Loading dataset from {latest_file}")
            # Use pandas to read JSONL format (each line is a JSON object)
            df = pd.read_json(latest_file, lines=True)
            # Ensure 'id' column is always string type to maintain consistency
            if 'id' in df.columns:
                df['id'] = df['id'].astype(str)
            train_dataset = Dataset.from_pandas(df)
            print(f"Loaded {len(train_dataset)} examples from turn {turn_files[0][0]}")
            print(f"Dataset columns after validation: {list(train_dataset.column_names)}")
            test_dataset = None  # No test set when loading from existing turns
        else:
            # No existing files, create dataset from scratch
            print("No existing turn datasets found, creating new dataset")
            if args.split_dataset:
                # Use seen/unseen split - ignore test_size and filter arguments
                if self.objective == 'SFT':
                    train_dataset, test_dataset = self.create_sft_seen_unseen_dataset(chain=args.chain)
                else:
                    train_dataset, test_dataset = self.create_seen_unseen_dataset(chain=args.chain)
                
                # Add 'solved' column for multiturn (initially False for all)
                train_dataset = train_dataset.add_column('solved', [False] * len(train_dataset))
                test_dataset = test_dataset.add_column('solved', [False] * len(test_dataset))
                
                # Prepare prompts based on objective
                if self.objective == 'SFT':
                    # Add system prompts to SFT datasets
                    train_dataset = parser.preprocessor.prepare_prompts_for_sft(
                        train_dataset, 
                        k_extra_functions=args.k_extra_functions
                    )
                    test_dataset = parser.preprocessor.prepare_prompts_for_sft(
                        test_dataset, 
                        k_extra_functions=args.k_extra_functions
                    )
                else:
                    # Prepare prompts for RL datasets
                    train_dataset = parser.preprocessor.prepare_prompts(
                        train_dataset, 
                        k_extra_functions=args.k_extra_functions
                    )
                    test_dataset = parser.preprocessor.prepare_prompts(
                        test_dataset, 
                        k_extra_functions=args.k_extra_functions
                    )
            else:
                # Use create_dataset_multiturn with test_size and filter arguments
                if self.objective == 'SFT':
                    raw_dataset = self.create_sft_dataset_multiturn(
                        filter_dataset_by_tools=args.filter_dataset_by_tools,
                        filter_dataset_by_num_calls=args.filter_dataset_by_num_calls,
                        chain=args.chain
                    )
                    # Add system prompts to SFT dataset
                    dataset = parser.preprocessor.prepare_prompts_for_sft(
                        raw_dataset, 
                        k_extra_functions=args.k_extra_functions
                    )
                else:
                    raw_dataset = self.create_dataset_multiturn(
                        filter_dataset_by_tools=args.filter_dataset_by_tools,
                        filter_dataset_by_num_calls=args.filter_dataset_by_num_calls,
                        chain=args.chain
                    )
                    dataset = parser.preprocessor.prepare_prompts(
                        raw_dataset, 
                        k_extra_functions=args.k_extra_functions
                    )
                
                # Check if full_dataset flag is set (used in evaluation)
                use_full_dataset = getattr(args, 'full_dataset', False)
                
                if use_full_dataset:
                    # Use entire dataset without splitting
                    train_dataset = dataset.shuffle(seed=self.seed)
                    test_dataset = None
                elif args.test_size > 0:
                    # Split dataset based on test_size
                    split_datasets = dataset.train_test_split(
                        test_size=args.test_size, 
                        seed=self.seed, 
                        shuffle=True
                    )
                    train_dataset = split_datasets['train']
                    test_dataset = split_datasets['test']
                else:
                    # No splitting, use all as training data
                    train_dataset = dataset.shuffle(seed=self.seed)
                    test_dataset = None
        
        print(f"Train dataset size: {len(train_dataset)}")
        if test_dataset is not None:
            print(f"Test dataset size: {len(test_dataset)}")
        
        return train_dataset, test_dataset
    
    def store_dataset_for_next_run(self, dataset_for_next_run, dataset_dir=None, args=None):
        """Store incorrect samples for the next training iteration.
        
        Args:
            dataset_for_next_run: List of dataset entries to store.
            dataset_dir: Directory to store the dataset file. If None, will be constructed from args.
            args: Parsed command line arguments (used if dataset_dir is None).
        """
        # Construct dataset_dir if not provided
        if dataset_dir is None:
            if args is None:
                raise ValueError("Either dataset_dir or args must be provided")
            dataset_dir = f"{args.output_dir}/datasets"
        
        # Ensure directory exists
        os.makedirs(dataset_dir, exist_ok=True)
        
        # Find existing turn files
        existing_files = glob.glob(f"{dataset_dir}/train_dataset_turn-*.json")
        
        # Extract turn numbers from existing files
        turn_numbers = []
        for file in existing_files:
            match = re.search(r'train_dataset_turn-(\d+)\.json', file)
            if match:
                turn_numbers.append(int(match.group(1)))
        
        # Determine next turn number
        next_turn = max(turn_numbers) + 1 if turn_numbers else 1
        
        train_dataset = Dataset.from_list(dataset_for_next_run)
        train_dataset = train_dataset.shuffle(seed=self.seed)
        train_dataset.to_json(f"{dataset_dir}/train_dataset_turn-{next_turn}.json")
        print(f"Stored dataset for next run in {dataset_dir}/train_dataset_turn-{next_turn}.json")
    
    def store_toolace_dataset_for_next_run(self, dataset_for_next_run, dataset_dir=None, args=None):
        """Store incorrect ToolACE samples for the next training iteration.
        
        Args:
            dataset_for_next_run: List of ToolACE dataset entries to store.
            dataset_dir: Directory to store the dataset file. If None, will be constructed from args.
            args: Parsed command line arguments (used if dataset_dir is None).
        """
        # Construct dataset_dir if not provided
        if dataset_dir is None:
            if args is None:
                raise ValueError("Either dataset_dir or args must be provided")
            dataset_dir = f"{args.output_dir}/datasets"
        
        # Ensure directory exists
        os.makedirs(dataset_dir, exist_ok=True)
        
        # Find existing ToolACE turn files
        existing_files = glob.glob(f"{dataset_dir}/toolace_train_dataset_turn-*.json")
        
        # Extract turn numbers from existing files
        turn_numbers = []
        for file in existing_files:
            match = re.search(r'toolace_train_dataset_turn-(\d+)\.json', file)
            if match:
                turn_numbers.append(int(match.group(1)))
        
        # Determine next turn number
        next_turn = max(turn_numbers) + 1 if turn_numbers else 1
        
        train_dataset = Dataset.from_list(dataset_for_next_run)
        train_dataset = train_dataset.shuffle(seed=self.seed)
        train_dataset.to_json(f"{dataset_dir}/toolace_train_dataset_turn-{next_turn}.json")
        print(f"Stored ToolACE dataset for next run in {dataset_dir}/toolace_train_dataset_turn-{next_turn}.json")
    
    def create_seen_unseen_dataset(self, chain=True):
        """Create training and testing sets with disjoint functions.
        
        Args:
            chain: Whether chaining is enabled (affects filtering of chaining functions).
            
        Returns:
            tuple: (trainset, testset) - Two Dataset objects with disjoint function sets.
        """
        training_functions = set([
            'BookSearchAPI',
            'CryptoPriceAPI',
            'CurrencyExchangeAPI',
            'EnglishDictionaryAPI',
            'FlightStatusAPI',
            'MovieSearchAPI',
            'GetLocation',  
            'FindDealershipsByLocation',
            'GetCarListingByDealerships',
            'FilterByCarBuild',
            'FilterByCarBrand',
            'FilterByCarPrice',
            'FilterByCarMileage',
            'FilterByCarProductionYear',
            'FilterByCarTitle',
            'SearchFlight',
            'BookFlight',
            'CancelFlight',    
            'SearchSKU',
            'CreateCart',
            'CancelStoreOrder'
        ])
        
        testing_functions = set([
            'SongLyricsAPI',
            'SpanishDictionaryAPI',
            'StockPriceAPI',
            'TimeZoneConverterAPI',
            'UnitConversionAPI',
            'GetLocation',
            'GetDate',
            'GetTime',
            'GetWeather',
            'GetAirQuality',
            'FindRestaurantsByLocation',
            'FilterByCuisine',   
            'FilterByRatings',
            'FilterByOpeningHours',
            'SearchHotel',
            'BookHotel',
            'CancelHotel',
            'SearchProducts',
            'CheckoutCart'
        ])
        
        # Remove chaining functions if chaining is disabled
        if not chain:
            chaining_functions = set([
                'FilterByCarBuild',
                'FilterByCarBrand',
                'FilterByCarPrice',
                'FilterByCarMileage',
                'FilterByCarProductionYear',
                'FilterByCarTitle',
                'FilterByCuisine',   
                'FilterByRatings',
                'FilterByOpeningHours',
            ])
            training_functions -= chaining_functions
            testing_functions -= chaining_functions
        
        raw_dataset = self._load_raw_dataset()
        
        # Apply chaining function filtering if chain is disabled
        if not chain:
            raw_dataset = self._filter_chaining_functions(raw_dataset)
        
        # Irrelevance detection - use actual keys from filtered dataset
        no_call_idx = [idx for idx in raw_dataset.keys() if raw_dataset[idx]['num_calls'] == 0]
        
        # Populate training set and test set with equal number of no call indices
        training_set = {idx: raw_dataset[idx] for idx in no_call_idx[:50]}
        testing_set = {idx: raw_dataset[idx] for idx in no_call_idx[50:]}
        
        # Samples requiring tool calls - use actual keys from filtered dataset
        call_idx = [idx for idx in raw_dataset.keys() if raw_dataset[idx]['num_calls'] > 0]
        
        # Populate training set with call_idx
        for i in call_idx:
            apis = raw_dataset[i]['apis']
            if any(f not in training_functions for f in apis):
                # problem requires apis that are not available in training functions
                continue
            training_set[i] = raw_dataset[i]
        
        # Populate testing set with call_idx
        for i in call_idx:
            apis = raw_dataset[i]['apis']
            if any(f not in testing_functions for f in apis):
                # problem requires apis that are not available in testing functions
                continue
            testing_set[i] = raw_dataset[i]
        
        # Patch GetLocation to GetCurrentLocation to avoid function leakage in testing set
        for i in testing_set:
            for j in range(len(testing_set[i]['apis'])):
                if testing_set[i]['apis'][j] == 'GetLocation':
                    testing_set[i]['apis'][j] = 'GetCurrentLocation'
            testing_set[i]['api_calls'] = testing_set[i]['api_calls'].replace('GetLocation', 'GetCurrentLocation')
        
        print(f"{len(raw_dataset) - len(training_set) - len(testing_set)} samples remain unused")
        
        train_indices = list(training_set.keys())
        test_indices = list(testing_set.keys())
        
        random.shuffle(train_indices)
        random.shuffle(test_indices)
        
        trainset = Dataset.from_dict({
            'id': [idx for idx in train_indices],
            'turn': [1 for idx in train_indices],
            'question': [training_set[idx]['prompt'] for idx in train_indices],
            'answer': [training_set[idx]['response'] for idx in train_indices],
            'num_calls': [training_set[idx]['num_calls'] for idx in train_indices],
            'tag': [training_set[idx]['tag'] for idx in train_indices],
            'apis': [training_set[idx]['apis'] for idx in train_indices],
            'api_calls': [training_set[idx]['api_calls'] for idx in train_indices],
            'solved': [False for idx in train_indices],
        })
        
        testset = Dataset.from_dict({
            'id': [idx for idx in test_indices],
            'turn': [1 for idx in test_indices],
            'question': [testing_set[idx]['prompt'] for idx in test_indices],
            'answer': [testing_set[idx]['response'] for idx in test_indices],
            'num_calls': [testing_set[idx]['num_calls'] for idx in test_indices],
            'tag': [testing_set[idx]['tag'] for idx in test_indices],
            'apis': [testing_set[idx]['apis'] for idx in test_indices],
            'api_calls': [testing_set[idx]['api_calls'] for idx in test_indices],
            'solved': [False for idx in test_indices],
        })
        
        print(f"Train dataset size: {len(trainset)}")
        print(f"Test dataset size: {len(testset)}")
        
        return trainset, testset
    
    def create_toolace_dataset(self, filter_dataset_by_tools='', filter_dataset_by_num_calls=None):
        """Create a single-turn ToolACE dataset.
        
        Args:
            filter_dataset_by_tools: Comma-separated list of tools to filter by.
            filter_dataset_by_num_calls: Comma-separated list of call counts to filter by.
            
        Returns:
            Dataset: Hugging Face Dataset object with ToolACE format.
        """
        # Use ToolACE dataset path
        original_path = self.dataset_path
        self.dataset_path = str(DATA_DIR / 'toolace' / 'rl_dataset.json')
        
        try:
            data = self._load_raw_dataset()
            data = self._filter_by_tools(data, filter_dataset_by_tools)
            data = self._filter_by_num_calls(data, filter_dataset_by_num_calls)
            
            # Helper function to serialize dicts to JSON strings
            def serialize_if_dict(value):
                if isinstance(value, dict):
                    return json.dumps(value)
                return value
            
            dataset = Dataset.from_dict({
                'system_prompt': [data[q]['system_prompt'] for q in data],
                'question': [data[q]['prompt'] for q in data],
                'answer': [serialize_if_dict(data[q]['response']) for q in data],
                'num_calls': [data[q]['num_calls'] for q in data],
                'time': [data[q]['time'] for q in data],
                'tag': [data[q]['tag'] for q in data],
                'apis': [data[q]['apis'] for q in data],
                'api_calls': [serialize_if_dict(data[q]['api_calls']) for q in data],
            })
            
            print(f"ToolACE dataset size: {len(dataset)}")
            return dataset
        finally:
            # Restore original dataset path
            self.dataset_path = original_path
    
    def create_toolace_dataset_multiturn(self, filter_dataset_by_tools='', filter_dataset_by_num_calls=None):
        """Create a multi-turn ToolACE dataset with 'solved' field.
        
        Args:
            filter_dataset_by_tools: Comma-separated list of tools to filter by.
            filter_dataset_by_num_calls: Comma-separated list of call counts to filter by.
            
        Returns:
            Dataset: Hugging Face Dataset object with ToolACE format and 'solved' field.
        """
        # Use ToolACE dataset path
        original_path = self.dataset_path
        self.dataset_path = str(DATA_DIR / 'toolace' / 'rl_dataset.json')
        
        try:
            data = self._load_raw_dataset()
            data = self._filter_by_tools(data, filter_dataset_by_tools)
            data = self._filter_by_num_calls(data, filter_dataset_by_num_calls)
            
            # Helper function to serialize dicts to JSON strings
            def serialize_if_dict(value):
                if isinstance(value, dict):
                    return json.dumps(value)
                return value
            
            dataset = Dataset.from_dict({
                'id': [q for q in data],
                'turn': [1 for q in data],
                'system_prompt': [data[q]['system_prompt'] for q in data],
                'question': [data[q]['prompt'] for q in data],
                'answer': [serialize_if_dict(data[q]['response']) for q in data],
                'num_calls': [data[q]['num_calls'] for q in data],
                'time': [data[q]['time'] for q in data],
                'tag': [data[q]['tag'] for q in data],
                'apis': [data[q]['apis'] for q in data],
                'api_calls': [serialize_if_dict(data[q]['api_calls']) for q in data],
                'solved': [False for q in data],
            })
            
            print(f"ToolACE dataset size: {len(dataset)}")
            return dataset
        finally:
            # Restore original dataset path
            self.dataset_path = original_path
    
    def create_xlam_dataset(self, filter_dataset_by_tools='', filter_dataset_by_num_calls=None):
        """Create a single-turn XLAM dataset.
        
        Args:
            filter_dataset_by_tools: Comma-separated list of tools to filter by.
            filter_dataset_by_num_calls: Comma-separated list of call counts to filter by.
            
        Returns:
            Dataset: Hugging Face Dataset object with XLAM format.
        """
        # Use XLAM dataset path
        original_path = self.dataset_path
        self.dataset_path = str(DATA_DIR / 'xlam' / 'rl_dataset.json')
        
        try:
            data = self._load_raw_dataset()
            data = self._filter_by_tools(data, filter_dataset_by_tools)
            data = self._filter_by_num_calls(data, filter_dataset_by_num_calls)
            
            # Helper function to serialize dicts to JSON strings
            def serialize_if_dict(value):
                if isinstance(value, dict):
                    return json.dumps(value)
                return value
            
            dataset = Dataset.from_dict({
                'system_prompt': ['' for q in data],
                'question': [data[q]['prompt'] for q in data],
                'answer': [serialize_if_dict(data[q]['response']) for q in data],
                'num_calls': [data[q]['num_calls'] for q in data],
                'time': ['' for q in data],
                'tag': [data[q]['tag'] for q in data],
                'apis': [data[q]['apis'] for q in data],
                'api_calls': [serialize_if_dict(data[q]['api_calls']) for q in data],
            })
            
            print(f"XLAM dataset size: {len(dataset)}")
            return dataset
        finally:
            # Restore original dataset path
            self.dataset_path = original_path
    
    def create_xlam_dataset_multiturn(self, filter_dataset_by_tools='', filter_dataset_by_num_calls=None):
        """Create a multi-turn XLAM dataset with 'solved' field.
        
        Args:
            filter_dataset_by_tools: Comma-separated list of tools to filter by.
            filter_dataset_by_num_calls: Comma-separated list of call counts to filter by.
            
        Returns:
            Dataset: Hugging Face Dataset object with XLAM format and 'solved' field.
        """
        # Use XLAM dataset path
        original_path = self.dataset_path
        self.dataset_path = str(DATA_DIR / 'xlam' / 'rl_dataset.json')
        
        try:
            data = self._load_raw_dataset()
            data = self._filter_by_tools(data, filter_dataset_by_tools)
            data = self._filter_by_num_calls(data, filter_dataset_by_num_calls)
            
            # Helper function to serialize dicts to JSON strings
            def serialize_if_dict(value):
                if isinstance(value, dict):
                    return json.dumps(value)
                return value
            
            dataset = Dataset.from_dict({
                'id': [q for q in data],
                'turn': [1 for q in data],
                'system_prompt': ['' for q in data],
                'question': [data[q]['prompt'] for q in data],
                'answer': [serialize_if_dict(data[q]['response']) for q in data],
                'num_calls': [data[q]['num_calls'] for q in data],
                'time': ['' for q in data],
                'tag': [data[q]['tag'] for q in data],
                'apis': [data[q]['apis'] for q in data],
                'api_calls': [serialize_if_dict(data[q]['api_calls']) for q in data],
                'solved': [False for q in data],
            })
            
            print(f"XLAM dataset size: {len(dataset)}")
            return dataset
        finally:
            # Restore original dataset path
            self.dataset_path = original_path
    
    def store_xlam_dataset_for_next_run(self, dataset_for_next_run, dataset_dir=None, args=None):
        """Store incorrect XLAM samples for the next training iteration.
        
        Args:
            dataset_for_next_run: List of XLAM dataset entries to store.
            dataset_dir: Directory to store the dataset file. If None, will be constructed from args.
            args: Parsed command line arguments (used if dataset_dir is None).
        """
        # Construct dataset_dir if not provided
        if dataset_dir is None:
            if args is None:
                raise ValueError("Either dataset_dir or args must be provided")
            dataset_dir = f"{args.output_dir}/datasets"
        
        # Ensure directory exists
        os.makedirs(dataset_dir, exist_ok=True)
        
        # Find existing XLAM turn files
        existing_files = glob.glob(f"{dataset_dir}/xlam_train_dataset_turn-*.json")
        
        # Extract turn numbers from existing files
        turn_numbers = []
        for file in existing_files:
            match = re.search(r'xlam_train_dataset_turn-(\d+)\.json', file)
            if match:
                turn_numbers.append(int(match.group(1)))
        
        # Determine next turn number
        next_turn = max(turn_numbers) + 1 if turn_numbers else 1
        
        train_dataset = Dataset.from_list(dataset_for_next_run)
        train_dataset = train_dataset.shuffle(seed=self.seed)
        train_dataset.to_json(f"{dataset_dir}/xlam_train_dataset_turn-{next_turn}.json")
        print(f"Stored XLAM dataset for next run in {dataset_dir}/xlam_train_dataset_turn-{next_turn}.json")


# Backward compatibility: Keep old function signatures
def create_dataset(dataset_path=None, seed=42, filter_dataset_by_tools='', filter_dataset_by_num_calls=None, chain=True):
    """Legacy function for backward compatibility."""
    manager = DatasetManager(seed=seed, dataset_path=dataset_path)
    return manager.create_dataset(filter_dataset_by_tools, filter_dataset_by_num_calls, chain)


def create_dataset_multiturn(dataset_path=None, seed=42, filter_dataset_by_tools='', filter_dataset_by_num_calls=None, chain=True):
    """Legacy function for backward compatibility."""
    manager = DatasetManager(seed=seed, dataset_path=dataset_path)
    return manager.create_dataset_multiturn(filter_dataset_by_tools, filter_dataset_by_num_calls, chain)


def create_seen_unseen_dataset(dataset_path=None, seed=42, chain=True):
    """Legacy function for backward compatibility."""
    manager = DatasetManager(seed=seed, dataset_path=dataset_path)
    return manager.create_seen_unseen_dataset(chain=chain)

def create_toolace_dataset(dataset_path=None, seed=42, filter_dataset_by_tools='', filter_dataset_by_num_calls=None):
    """Legacy function for backward compatibility."""
    manager = DatasetManager(seed=seed, dataset_path=dataset_path)
    return manager.create_toolace_dataset(filter_dataset_by_tools, filter_dataset_by_num_calls)

def create_toolace_dataset_multiturn(dataset_path=None, seed=42, filter_dataset_by_tools='', filter_dataset_by_num_calls=None):
    """Legacy function for backward compatibility."""
    manager = DatasetManager(seed=seed, dataset_path=dataset_path)
    return manager.create_toolace_dataset_multiturn(filter_dataset_by_tools, filter_dataset_by_num_calls)


# SFT dataset functions for backward compatibility
def create_sft_dataset(dataset_path=None, seed=42, filter_dataset_by_tools='', filter_dataset_by_num_calls=None, chain=True):
    """Legacy function for backward compatibility - SFT version."""
    manager = DatasetManager(seed=seed, dataset_path=dataset_path, objective='SFT')
    return manager.create_sft_dataset(filter_dataset_by_tools, filter_dataset_by_num_calls, chain)


def create_sft_dataset_multiturn(dataset_path=None, seed=42, filter_dataset_by_tools='', filter_dataset_by_num_calls=None, chain=True):
    """Legacy function for backward compatibility - SFT version."""
    manager = DatasetManager(seed=seed, dataset_path=dataset_path, objective='SFT')
    return manager.create_sft_dataset_multiturn(filter_dataset_by_tools, filter_dataset_by_num_calls, chain)


def create_sft_seen_unseen_dataset(dataset_path=None, seed=42, chain=True):
    """Legacy function for backward compatibility - SFT version."""
    manager = DatasetManager(seed=seed, dataset_path=dataset_path, objective='SFT')
    return manager.create_sft_seen_unseen_dataset(chain=chain)

def create_xlam_dataset(dataset_path=None, seed=42, filter_dataset_by_tools='', filter_dataset_by_num_calls=None):
    """Legacy function for backward compatibility - XLAM version."""
    manager = DatasetManager(seed=seed, dataset_path=dataset_path)
    return manager.create_xlam_dataset(filter_dataset_by_tools, filter_dataset_by_num_calls)

def create_xlam_dataset_multiturn(dataset_path=None, seed=42, filter_dataset_by_tools='', filter_dataset_by_num_calls=None):
    """Legacy function for backward compatibility - XLAM version."""
    manager = DatasetManager(seed=seed, dataset_path=dataset_path)
    return manager.create_xlam_dataset_multiturn(filter_dataset_by_tools, filter_dataset_by_num_calls)
