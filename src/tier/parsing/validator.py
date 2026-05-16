from typing import Dict, Any, List, Tuple
import re


class ASTValidator:
    """
    Validates AST parameters against function definitions.
    """
    
    def __init__(self):
        """Initialize the AST validator."""
        pass
    
    def match_parameter_pattern(self, ast_param: str, def_param: str) -> bool:
        """
        Matches an AST parameter path against a definition parameter pattern.
        
        Args:
            ast_param: Parameter path from AST (e.g., 'items[0].sku', 'coupons[0]')
            def_param: Parameter pattern from definition (e.g., 'items[].sku', 'coupons')
        
        Returns:
            bool: True if the patterns match
        """
        # Case 1: Definition has [] pattern (e.g., 'items[].sku')
        if '[]' in def_param:
            # Split by the [] pattern and rebuild with regex
            parts = def_param.split('[]')
            regex_pattern = ''
            for i, part in enumerate(parts):
                if i > 0:
                    regex_pattern += r'\[\d+\]'  # Match any digit in brackets
                regex_pattern += re.escape(part)
            return bool(re.match(regex_pattern, ast_param))
        
        # Case 2: Definition is a simple array parameter (e.g., 'coupons')
        # Check if AST parameter matches the pattern: def_param + [digit]
        # e.g., 'coupons' should match 'coupons[0]', 'coupons[1]', etc.
        array_pattern = re.escape(def_param) + r'\[\d+\]'
        if re.match(array_pattern, ast_param):
            return True
        
        # Case 3: Exact match (no array pattern)
        return ast_param == def_param
    
    def find_matching_definition_param(self, ast_param: str, parsed_function_def: Dict[str, List[str]]) -> Tuple[str, List[str], bool]:
        """
        Finds the matching definition parameter for an AST parameter.
        
        Args:
            ast_param: Parameter path from AST
            parsed_function_def: Dictionary with expected parameter patterns and [datatype, required_status] lists
        
        Returns:
            Tuple of (matched_pattern, [datatype, required_status], is_array_element_match) or (None, None, False) if no match
        """
        for def_param, param_info in parsed_function_def.items():
            # Case: direct or items[] style match
            if self.match_parameter_pattern(ast_param, def_param):
                # Determine if this was an array element match for a simple array def (e.g., 'coupons' vs 'coupons[0]')
                is_array_element = False
                if '[]' not in def_param:
                    array_pattern = re.escape(def_param) + r'\[\d+\]'
                    if re.match(array_pattern, ast_param):
                        is_array_element = True
                return def_param, param_info, is_array_element
        return None, None, False
    
    def validate_datatype(self, value: Any, expected_type: str, param_path: str) -> Dict[str, Any]:
        """
        Validates that a value matches the expected datatype.
        
        Args:
            value: The actual value to validate
            expected_type: The expected datatype string
            param_path: Parameter path for error reporting
        
        Returns:
            dict: Validation result with validity status and error details
        """
        result = {
            'valid': False,
            'actual_type': type(value).__name__,
            'error': None
        }
        
        # Handle array types with specific element types
        if expected_type.startswith('array<') and expected_type.endswith('>'):
            element_type = expected_type[6:-1]  # Extract type from array<type>
            # If param_path refers to a specific indexed element (e.g., coupons[0]),
            # validate the element directly against element_type.
            if re.search(r"\[\d+\]$", param_path):
                return self.validate_datatype(value, element_type, param_path)
            
            if not isinstance(value, list):
                result['error'] = f"Parameter '{param_path}' should be array, got {type(value).__name__}"
                return result
            
            # Check if array is empty (which is valid)
            if len(value) == 0:
                result['valid'] = True
                return result
            
            # Validate each element in the array
            for i, element in enumerate(value):
                element_validation = self.validate_datatype(element, element_type, f"{param_path}[{i}]")
                if not element_validation['valid']:
                    result['error'] = element_validation['error']
                    return result
            
            result['valid'] = True
            return result
        
        # Handle basic types
        type_mapping = {
            'string': str,
            'integer': int,
            'float': float,
            'boolean': bool,
            'dict': dict,
            'array': list
        }
        
        if expected_type in type_mapping:
            expected_python_type = type_mapping[expected_type]
            if isinstance(value, expected_python_type):
                result['valid'] = True
            else:
                result['error'] = f"Parameter '{param_path}' should be {expected_type}, got {type(value).__name__}"
        else:
            result['error'] = f"Unknown expected type '{expected_type}' for parameter '{param_path}'"
        
        return result
    
    def validate_function_parameters(self, parsed_ast: Dict[str, Any], parsed_function_def: Dict[str, List[str]], function_name: str = None, function_definitions: Dict[str, Dict[str, List[str]]] = None) -> Dict[str, Any]:
        """
        Validates that the parsed AST matches the parsed function definition.
        
        Args:
            parsed_ast: Dictionary with flattened parameter paths and values
            parsed_function_def: Dictionary with expected parameter patterns and [datatype, required_status] lists
            function_name: Name of the function being validated (optional)
            function_definitions: Dictionary mapping function names to their parameter definitions (optional)
        
        Returns:
            dict: Validation results with success status, errors, warnings, and fn_name_match
        """
        validation_result = {
            'success': True,
            'errors': [],
            'warnings': [],
            'validated_params': [],
            'missing_required_params': [],
            'extra_params': [],
            'type_mismatch_params': [],
            'ignored_params': [],
            'fn_name_match': True,  # Default to True, will be set based on function_name check
            'expected_req_params': 0,
            'expected_optional_params': 0
        }
        
        # Check if function name matches any in function definitions
        if function_name and function_definitions:
            validation_result['fn_name_match'] = function_name in function_definitions
        
        # Count expected required and optional parameters from function definition
        if parsed_function_def:
            for param_info in parsed_function_def.values():
                if isinstance(param_info, list) and len(param_info) >= 2:
                    required_status = param_info[1]
                    if required_status == "required":
                        validation_result['expected_req_params'] += 1
                    elif required_status == "optional":
                        validation_result['expected_optional_params'] += 1
        
        # Track which definition parameters have been matched
        matched_def_params = set()
        
        # Validate datatypes for provided parameters
        for param_path, value in parsed_ast.items():
            # Skip tag parameters (pseudorandomization)
            if param_path == 'tag':
                validation_result['ignored_params'].append(param_path)
                continue
            
            matched_pattern, param_info, is_array_element = self.find_matching_definition_param(param_path, parsed_function_def)
            
            if matched_pattern:
                matched_def_params.add(matched_pattern)
                expected_type, required_status = param_info
                
                # Adjust expected type when a simple array def matched an indexed element
                if is_array_element and expected_type.startswith('array<') and expected_type.endswith('>'):
                    expected_type = expected_type[6:-1]
                
                # Check if this is an API_RESPONSE_X value (chained function output)
                if isinstance(value, str) and value.startswith('API_RESPONSE_'):
                    # Skip datatype validation for chained function outputs
                    validation_result['validated_params'].append({
                        'param': param_path,
                        'value': value,
                        'expected_type': expected_type,
                        'actual_type': 'API_RESPONSE',
                        'required_status': required_status,
                        'matched_pattern': matched_pattern,
                        'note': 'Chained function output - datatype validation skipped'
                    })
                else:
                    # Normal datatype validation
                    type_validation = self.validate_datatype(value, expected_type, param_path)
                    
                    if type_validation['valid']:
                        validation_result['validated_params'].append({
                            'param': param_path,
                            'value': value,
                            'expected_type': expected_type,
                            'actual_type': type_validation['actual_type'],
                            'required_status': required_status,
                            'matched_pattern': matched_pattern
                        })
                    else:
                        validation_result['type_mismatch_params'].append({
                            'param': param_path,
                            'value': value,
                            'expected_type': expected_type,
                            'actual_type': type_validation['actual_type'],
                            'error': type_validation['error']
                        })
                        validation_result['errors'].append(type_validation['error'])
                        validation_result['success'] = False
            else:
                # Check if this is a tag parameter that should be ignored
                if param_path == 'tag':
                    validation_result['ignored_params'].append(param_path)
                else:
                    validation_result['extra_params'].append(param_path)
                    validation_result['errors'].append(f"Parameter '{param_path}' does not exist in function definition")
                    validation_result['success'] = False
        
        # Check for missing required parameters
        missing_required_params = []
        for def_param, (param_type, required_status) in parsed_function_def.items():
            if required_status == "required" and def_param not in matched_def_params:
                missing_required_params.append(def_param)
        
        if missing_required_params:
            validation_result['missing_required_params'] = missing_required_params
            validation_result['errors'].append(f"Missing required parameters: {missing_required_params}")
            validation_result['success'] = False
        
        return validation_result
    
    def validate_function_call(self, parsed_ast: Dict[str, Any], function_definitions: Dict[str, Dict[str, List[str]]]) -> Dict[str, Any]:
        """
        Validate a complete AST with multiple function calls against their respective definitions.
        
        Args:
            parsed_ast: Complete AST with function calls (e.g., {'0': {'CreateCart': {...}}, '1': {'CheckoutCart': {...}}})
            function_definitions: Dictionary mapping function names to their parameter definitions
                                 e.g., {'CreateCart': {'items[].sku': ['string', 'required'], ...},
                                        'CheckoutCart': {'cartId': ['string', 'required'], ...}}
        
        Returns:
            dict: Validation results for all function calls
        """
        results = {}
        
        for call_id, call_data in parsed_ast.items():
            if isinstance(call_data, dict):
                for function_name, function_params in call_data.items():
                    if isinstance(function_params, dict):
                        # Get the function definition for this specific function
                        function_def = function_definitions.get(function_name, {})
                        # Validate this function call against its specific definition
                        validation_result = self.validate_function_parameters(function_params, function_def, function_name, function_definitions)
                        results[f"{call_id}.{function_name}"] = validation_result
        
        return results
    
    def format_validation_report(self, validation_result: Dict[str, Any]) -> str:
        """
        Formats the validation result into a readable report.
        
        Args:
            validation_result: Result from validate_function_parameters
        
        Returns:
            str: Formatted validation report
        """
        report = []
        
        if validation_result['success']:
            report.append("VALIDATION PASSED")
        else:
            report.append("VALIDATION FAILED")
        
        report.append("=" * 50)
        
        # Add function name match status
        if 'fn_name_match' in validation_result:
            fn_match_status = "MATCHED" if validation_result['fn_name_match'] else "NOT MATCHED"
            report.append(f"FUNCTION NAME: {fn_match_status}")
            report.append("")
        
        # Add expected parameter counts
        if 'expected_req_params' in validation_result and 'expected_optional_params' in validation_result:
            report.append(f"EXPECTED PARAMETERS: {validation_result['expected_req_params']} required, {validation_result['expected_optional_params']} optional")
            report.append("")
        
        if validation_result['validated_params']:
            report.append("VALIDATED PARAMETERS:")
            for param in validation_result['validated_params']:
                status_text = "REQUIRED" if param['required_status'] == "required" else "OPTIONAL"
                report.append(f"  {param['param']}: {param['value']} ({param['actual_type']}) - {status_text}")
                report.append(f"    Matches pattern: {param['matched_pattern']}")
                if 'note' in param:
                    report.append(f"    Note: {param['note']}")
        
        if validation_result['missing_required_params']:
            report.append("MISSING REQUIRED PARAMETERS:")
            for param in validation_result['missing_required_params']:
                report.append(f"  {param}")
        
        if validation_result['extra_params']:
            report.append("EXTRA PARAMETERS (not in function definition):")
            for param in validation_result['extra_params']:
                report.append(f"  {param}")
        
        if validation_result['type_mismatch_params']:
            report.append("TYPE MISMATCH PARAMETERS:")
            for param in validation_result['type_mismatch_params']:
                report.append(f"  {param['param']}: expected {param['expected_type']}, got {param['actual_type']}")
        
        if validation_result['ignored_params']:
            report.append("IGNORED PARAMETERS (pseudorandomization):")
            for param in validation_result['ignored_params']:
                report.append(f"  {param}")
        
        if validation_result['errors']:
            report.append("ERRORS:")
            for error in validation_result['errors']:
                report.append(f"  {error}")
        
        return "\n".join(report)
