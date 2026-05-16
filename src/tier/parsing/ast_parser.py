from re import Match


import lxml.etree as ET
import html
import re, json, pandas as pd
import importlib, builtins
import collections
import ast
from tier.data.preprocessor import Preprocessor
from tier.parsing.validator import ASTValidator
from tier.environment.simulator import SimulatedAPIEnvironment

class Parser():
    def __init__(self, seed = 42, instructions_fp = None, function_definitions_fp = None):
        self.env = SimulatedAPIEnvironment()
        self.preprocessor = Preprocessor(instructions_fp, function_definitions_fp)
        self.validator = ASTValidator()
        self.parsed_function_definitions = self.parse_function_definitions(self.preprocessor.function_definitions)
        self.TYPE_CONVERTERS = {
            "boolean": self._parse_bool,
            "integer": lambda s: int(float(s)),
            "float": float,
            "string": str,
        }
    
    def check_format(self, completion: str, style="xml"):
        if style == "xml":
            return self.check_xml_format(completion)
        elif style == "json":
            return self.check_json_format(completion)
        elif style == "direct":
            return self.check_direct_call_format(completion)
        else:
            raise ValueError(f"Invalid style: {style}")
    
    def check_json_format(self, completion: str):
        errors = []

        m: Match[str] | None = re.search(r"(<think\b[^>]*>[\s\S]*?</think>)\s*(<tool_call\b[^>]*>[\s\S]*?</tool_call>)", completion, re.S)
        if not m:
            return False, ["Missing or malformed <think> and <tool_call> block"]
            
        reasoning_block = m.group(1)
        answer_block = m.group(2)
        # Escape XML special characters only in the reasoning content
        reasoning_match = re.search(r'<think\b[^>]*>([\s\S]*?)</think>', reasoning_block, re.S)
        if reasoning_match:
            reasoning_content = reasoning_match.group(1)
            reasoning_block = reasoning_block.replace(reasoning_content, html.escape(reasoning_content, quote=False))
        
        block = reasoning_block + answer_block

        try:
            root = ET.fromstring(f"<root>{block}</root>")
        except ET.ParseError as e:
            return False, [f"XML parsing error: {e}"]

        # Check top level, if there is a reasoning tag and an answer tag 
        children = list(root)

        reasoning_nodes = [n for n in children if n.tag == "think"]
        answer_nodes = [n for n in children if n.tag == "tool_call"]
        other_nodes = [n.tag for n in children if n.tag not in ("tool_call", "think")]

        if other_nodes:
            errors.append(f"Unexpected top-level tags: {other_nodes}")
        if len(reasoning_nodes) != 1:
            errors.append(f"Expected exactly one <think>, found {len(reasoning_nodes)}")
        if len(answer_nodes)    != 1:
            errors.append(f"Expected exactly one <tool_call>, found {len(answer_nodes)}")
        if len(reasoning_nodes) == 1 and len(answer_nodes) == 1:
            if children.index(reasoning_nodes[0]) > children.index(answer_nodes[0]):
                errors.append("<think> must precede <tool_call>")

        if answer_nodes:
            answer = answer_nodes[0]
            return_attrib = answer.attrib.get("return", None)
            if not return_attrib:
                errors.append("Missing return attribute in <tool_call>")
            if return_attrib and return_attrib not in ["one", "all"]:
                errors.append(f"Invalid return attribute in <tool_call>: {return_attrib}")

            try:
                tool_call = json.loads(answer.text.strip())
            except json.JSONDecodeError:
                errors.append("Invalid JSON format in <tool_call>")
                return False, errors

            if not isinstance(tool_call, dict):
                errors.append("<tool_call> should contain a dictionary with numeric string keys and dictionary values")
                return False, errors

            if tool_call != {} and not all(isinstance(k, str) and k.isdigit() for k in tool_call.keys()):
                errors.append("tool_call JSON should have numeric string keys")
                return False, errors

            if tool_call != {} and not all(isinstance(v, dict) for v in tool_call.values()):
                errors.append("tool_call JSON should have dictionary values")
                return False, errors

        return (not errors), errors

    def check_direct_call_format(self, completion: str):
        errors = []

        # Match the full <think>...</think> followed by <tool_call ...>...</tool_call>
        m: Match[str] | None = re.search(r"(<think\b[^>]*>[\s\S]*?</think>)\s*(<tool_call\b[^>]*>[\s\S]*?</tool_call>)", completion, re.S)
        if not m:
            return False, ["Missing or malformed <think> and <tool_call> block"]
            
        reasoning_block = m.group(1)
        answer_block = m.group(2)
        # Escape XML special characters only in the reasoning content
        reasoning_match = re.search(r'<think\b[^>]*>([\s\S]*?)</think>', reasoning_block, re.S)
        if reasoning_match:
            reasoning_content = reasoning_match.group(1)
            reasoning_block = reasoning_block.replace(reasoning_content, html.escape(reasoning_content, quote=False))
        
        block = reasoning_block + answer_block

        try:
            root = ET.fromstring(f"<root>{block}</root>")
        except ET.ParseError as e:
            return False, [f"XML parsing error: {e}"]

        # Check top level, if there is a reasoning tag and an answer tag 
        children = list(root)

        reasoning_nodes = [n for n in children if n.tag == "think"]
        answer_nodes = [n for n in children if n.tag == "tool_call"]
        other_nodes = [n.tag for n in children if n.tag not in ("tool_call", "think")]

        if other_nodes:
            errors.append(f"Unexpected top-level tags: {other_nodes}")
        if len(reasoning_nodes) != 1:
            errors.append(f"Expected exactly one <think>, found {len(reasoning_nodes)}")
        if len(answer_nodes)    != 1:
            errors.append(f"Expected exactly one <tool_call>, found {len(answer_nodes)}")
        if len(reasoning_nodes) == 1 and len(answer_nodes) == 1:
            if children.index(reasoning_nodes[0]) > children.index(answer_nodes[0]):
                errors.append("<think> must precede <tool_call>")

        if answer_nodes:
            answer = answer_nodes[0]
            # Extract and validate tool_call content directly
            tool_call_content = answer.text.strip() if answer.text else ""
            
            try:
                tool_call = ast.literal_eval(tool_call_content)
                if not isinstance(tool_call, list):
                    errors.append("<tool_call> should contain a list of function call strings")
                elif not all(isinstance(call, str) for call in tool_call):
                    errors.append("<tool_call> should contain a list of function call strings")
            except (ValueError, SyntaxError) as e:
                errors.append(f"Invalid Python literal format in <tool_call>: {e}")

        return not errors, errors
    
    def check_xml_format(self, completion: str) : 
        errors = []
        # Match the full <think>...</think> followed by <tool_call ...>...</tool_call>
        m = re.search(r"(<think\b[^>]*>[\s\S]*?</think>)\s*(<tool_call\b[^>]*>[\s\S]*?</tool_call>)", completion, re.S)
        if not m:
            return False, ["Missing or malformed <think> and <tool_call> block"]
            
        think_block = m.group(1)
        tool_call_block = m.group(2)
        # Escape XML special characters only in the think content
        think_match = re.search(r'<think\b[^>]*>([\s\S]*?)</think>', think_block, re.S)
        if think_match:
            think_content = think_match.group(1)
            think_block = think_block.replace(think_content, html.escape(think_content, quote=False))
        
        block = think_block + tool_call_block

        try:
            root = ET.fromstring(f"<root>{block}</root>")
        except ET.ParseError as e:
            return False, [f"XML parsing error: {e}"]

        # Check top level, if there is a think tag and a tool_call tag 
        children = list(root)

        think_nodes = [n for n in children if n.tag == "think"]
        tool_call_nodes = [n for n in children if n.tag == "tool_call"]
        other_nodes = [n.tag for n in children if n.tag not in ("tool_call", "think")]

        if other_nodes:
            errors.append(f"Unexpected top-level tags: {other_nodes}")
        if len(think_nodes) != 1:
            errors.append(f"Expected exactly one <think>, found {len(think_nodes)}")
        if len(tool_call_nodes)    != 1:
            errors.append(f"Expected exactly one <tool_call>,    found {len(tool_call_nodes)}")
        if len(think_nodes) == 1 and len(tool_call_nodes) == 1:
            if children.index(think_nodes[0]) > children.index(tool_call_nodes[0]):
                errors.append("<think> must precede <tool_call>")

        if tool_call_nodes:
            tool_call = tool_call_nodes[0]
            return_attrib = tool_call.attrib.get("return", None)
            if not return_attrib:
                errors.append("Missing return attribute in <tool_call>")
            if return_attrib and return_attrib not in ["one", "all"]:
                errors.append(f"Invalid return attribute in <tool_call>: {return_attrib}")

            if any(c.tag not in ["api", "none"] for c in tool_call):
                wrong = [c.tag for c in tool_call if c.tag != "api"]
                errors.append(f"Unexpected tag(s) in <tool_call>: {wrong}")

            none_nodes = tool_call.findall("./none")
            api_nodes = tool_call.findall("./api")
            if not api_nodes and not none_nodes:
                errors.append("No <api> tags inside <tool_call>")
            if none_nodes and api_nodes:
                errors.append("Cannot have both <none> and <api> tags inside <tool_call>")
            if none_nodes:
                if len(none_nodes) > 1:
                        errors.append("Multiple <none> tags inside <tool_call>")

            api_ids = []
            for api in api_nodes:
                api_id = api.attrib.get("id")
                if api_id is None:
                    errors.append("<api> tag missing required ‘id’ attribute")
                else:
                    api_ids.append(api_id)

                name_nodes   = [c for c in api if c.tag == "name"]
                param_nodes  = [c for c in api if c.tag == "param"]
                extra_nodes  = [c.tag for c in api
                                if c.tag not in ("name", "param")]

                if len(name_nodes) != 1:
                    errors.append(
                        f"<api id='{api_id or '?'}'> must contain exactly ONE <name>")

                for node in extra_nodes:
                    errors.append(
                        f"Unexpected <{node}> inside <api id='{api_id or '?'}'>")

                q = collections.deque()
                q.extend(param_nodes)
                while q:
                    node = q.popleft()
                    if node.tag == "param":
                        if "name" not in node.attrib:
                            errors.append(f"<param> missing required ‘name’ attribute inside <api id='{api_id or '?'}'>")
                        if "type" not in node.attrib:
                            errors.append(f"<param> missing required ‘type’ attribute inside <api id='{api_id or '?'}'>")
                    elif node.tag == "field":
                        if "name" not in node.attrib:
                            errors.append(f"<field> missing required ‘name’ attribute inside <api id='{api_id or '?'}'>")
                        if "type" not in node.attrib:
                            errors.append(f"<field> missing required ‘type’ attribute inside <api id='{api_id or '?'}'>")
                    elif node.tag == "item":
                        if "type" not in node.attrib:
                            errors.append(f"<item> missing required ‘type’ attribute inside <api id='{api_id or '?'}'>")
                    elif node.tag == "response":
                        if "api_id" not in node.attrib:
                            errors.append(f"<response> missing required ‘api_id’ attribute inside <api id='{api_id or '?'}'>")
                        if "api_name" not in node.attrib:
                            errors.append(f"<response> missing required ‘api_name’ attribute inside <api id='{api_id or '?'}'>")
                        if "field" not in node.attrib:
                            errors.append(f"<response> missing required ‘field’ attribute inside <api id='{api_id or '?'}'>")
                    else:
                        errors.append(f"Unexpected <{node.tag}> inside <api id='{api_id or '?'}'>")
                    children = list(node)
                    if children:
                        q.extend(children)

        return (not errors), errors

    def extract_tool_calls(self, completion: str, tag: str, style="xml"):
        if style == "xml":
            return self.decode_syntax_tree(
                result=self.extract_xml_tool_call(completion), 
                tag=tag
            )
        elif style == "json":
            return self.extract_json_tool_calls(
                result=completion,
                tag=tag
            )
        elif style == "direct":
            return self.extract_direct_tool_calls(
                result=completion,
                tag=tag
            )
        else:
            raise ValueError(f"Invalid style: {style}")
    
    def extract_json_tool_calls(self, result: str, tag: str):
        # Use regex to find content inside <tool_call>...</tool_call>
        pattern = r'<tool_call[^>]*>.*?</tool_call>'
        match = re.search(pattern, result, re.DOTALL)
        calls = {}
        return_all = False
        
        if match:
            xml = match.group(0).strip()
            # Escape bare ampersands so XML parser can handle values like "S&P 500"
            xml = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)', '&amp;', xml)
            try:
                root = ET.fromstring(xml)
                json_text = root.text.strip()
                # Convert Python tuple syntax to JSON array syntax
                # Replace tuples like (x, y, z) with [x, y, z]
                json_text = re.sub(r'\(([^()]+)\)', r'[\1]', json_text)
                calls = json.loads(json_text)
                return_all = root.attrib.get('return', '') == 'all' # whether to return response of all API call executions.
            except Exception as e:
                # print(e)
                return {}, False
        
        # Only add a tag if no params are present. Tags (pseudo) randomize state queries like GetLocation, GetTime, etc.
        if calls != {}:
            for k, v in calls.items():
                if isinstance(v, dict) and v != {}:
                    for k_, v_ in v.items():
                        if isinstance(v_, dict) and v_ == {} and k_ in ["GetLocation", "GetTime", "GetDate", "GetCurrentLocation"]:
                            v_['tag'] = tag

        return calls, return_all
    
    def extract_direct_tool_calls(self, result: str, tag: str):
        # Use regex to find content inside <tool_call>...</tool_call> (attributes allowed but ignored)
        pattern = r'<tool_call[^>]*>(.*?)</tool_call>'
        match = re.search(pattern, result, re.DOTALL)
        calls, return_all = {}, True
        if match:
            # Extract the raw content without XML parsing
            python_text = match.group(1).strip()
            try:
                # Convert Python tuple syntax to list syntax if needed
                # Replace tuples like (x, y, z) with [x, y, z]
                python_text = re.sub(r'\(([^()]+)\)', r'[\1]', python_text)
                calls = ast.literal_eval(python_text)
            except Exception as e:
                # print(e)
                return calls, False

        # Create AST from the function call strings
        function_calls = {}
        for i, call_string in enumerate(calls):
            # Convert square brackets to parentheses for proper Python function call syntax
            normalized_call = call_string.replace('[', '(').replace(']', ')')
            function_name, args_dict = self.parse_function_call_string(normalized_call)
            if function_name is not None:
                function_calls[str(i)] = {function_name: args_dict}
        
        if function_calls != {}:
            for k, v in function_calls.items():
                if isinstance(v, dict) and v != {}:
                    for k_, v_ in v.items():
                        if isinstance(v_, dict) and v_ == {} and k_ in ["GetLocation", "GetTime", "GetDate", "GetCurrentLocation"]:
                            v_['tag'] = tag

        return function_calls, return_all
    
    def extract_xml_tool_call(self, completion: str):
        # Use regex to find <tool_call> with any attributes
        pattern = r'<tool_call[^>]*>.*?</tool_call>'
        match = re.search(pattern, completion, re.DOTALL)
        
        if match:
            return match.group(0).strip()
        
        return ""

    def _parse_bool(self, value: str):
        v = value.strip().lower()
        if v in ("true", "1", "yes"): 
            return True
        if v in ("false", "0", "no"): 
            return False
        raise ValueError("Unrecognized boolean value")   

    def _resolve_type_callable(self, type_name: str):
        converter = self.TYPE_CONVERTERS.get(type_name)
        if converter:
            return converter

        builtin_attr = getattr(builtins, type_name, None)
        if callable(builtin_attr):
            return builtin_attr

        for sep in (".", ":"):
            if sep in type_name:
                try:
                    module_path, attr_name = type_name.rsplit(sep, 1)
                    if sep == ":":
                        module = importlib.import_module(module_path)
                    else:
                        module = importlib.import_module(module_path)
                    attr = getattr(module, attr_name, None)
                    if callable(attr):
                        return attr
                except Exception:
                    pass
        return None

    def _parse_element(self, elem):
        children = list(elem)

        # No children -> primitive
        if not children:
            param_value = (elem.text or "").strip()
            param_type = elem.attrib.get("type", "str")
            converter = self._resolve_type_callable(param_type)
            if converter is None:
                return param_value
            try:
                return converter(param_value)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Failed to convert '{param_value}' to {param_type}: {str(e)}")

        # Process <response> -> API_RESPONSE_x.field_name
        if len(children) == 1 and children[0].tag == "response":
            resp = children[0]
            field = resp.attrib.get("field")
            if not field:
                raise ValueError(
                    f"<response api_id='{resp.attrib.get('api_id', '?')}'> "
                    f"missing required 'field' attribute"
                )
            return f"API_RESPONSE_{resp.attrib['api_id']}.{field}"
            
        # All <field> -> object/dict
        if all(child.tag == "field" for child in children):
            return {
                child.attrib["name"]: self._parse_element(child)
                for child in children
            }

        # All <item> -> list/array
        if all(child.tag == "item" for child in children):
            return [self._parse_element(child) for child in children]

        # Fallback -> generic dict
        return {child.tag: self._parse_element(child) for child in children}

    def _parse_xml_to_function_calls(self, xml_string: str, tag='A'):
        try:
            root = ET.fromstring(xml_string)
        except ET.ParseError as e:
            return None, False

        return_all = root.attrib.get('return', '') == 'all' # whether to return response of all API call executions.

        function_calls = {}

        for api_element in root.findall('.//api'):
            api_id = api_element.get('id', '')

            api_name_element = api_element.find("name")
            if api_name_element is None or not api_name_element.text:
                continue

            api_name = api_name_element.text.strip()
            if api_name not in self.preprocessor.function_definitions:
                continue
            params = {
                p.attrib["name"]: self._parse_element(p) for p in api_element.findall("param")
            }

            # Only add a tag if no params are present. Tags (pseudo) randomize state queries like GetLocation, GetTime, etc.
            if not params and api_name in ["GetLocation", "GetTime", "GetDate", "GetCurrentLocation"]:
                params['tag'] = tag

            function_calls[str(api_id)] = {
                str(api_name): params
            }

        return function_calls, return_all

    def _resolve_placeholders(self, value, function_calls, responses):
        """
        Recursively resolve placeholders like "API_RESPONSE_x.field_name"
        inside nested dicts/lists to their actual values from prior responses.

        The placeholder must include a field name (e.g. API_RESPONSE_0.Date).
        A bare "API_RESPONSE_x" without a field name raises a ValueError.
        """
        if isinstance(value, str) and value.startswith("API_RESPONSE_"):
            remainder = value[len("API_RESPONSE_"):]
            if "." not in remainder:
                raise ValueError(
                    f"Placeholder '{value}' is missing a field name. "
                    f"Expected format: API_RESPONSE_X.field_name"
                )
            response_id, field_name = remainder.split(".", 1)
            try:
                response_obj = responses[response_id]
                return response_obj.get(field_name, response_obj)
            except Exception:
                return value

        if isinstance(value, dict):
            return {k: self._resolve_placeholders(v, function_calls, responses) for k, v in value.items()}
        if isinstance(value, list):
            return [self._resolve_placeholders(v, function_calls, responses) for v in value]

        return value

    def _prepare_function_call_and_execute(self, name, args, function_calls, responses):
        if self.preprocessor.function_definitions.get(name, ''):
            # Resolve placeholders recursively across nested structures
            resolved_args = {k: self._resolve_placeholders(v, function_calls, responses) for k, v in args.items()}
            # Call the API method directly with resolved kwargs
            # api_method = getattr(self.env, name, None)
            # if api_method is None:
            #     return None
            api_method = self.env
            for attr in name.split('.'):
                api_method = getattr(api_method, attr, None)
                if api_method is None:
                    return None
            response = api_method.execute(**resolved_args)
            return response 

        return None

    def decode_syntax_tree(self, result, tag='A'):
        xml = self.extract_xml_tool_call(result)
        if xml:
            function_calls, return_all = self._parse_xml_to_function_calls(xml, tag)
            if function_calls:
                return function_calls, return_all
        return {}, False
    
    def parse_function_call_string(self, call_string):
        """
        Parse a function call string like "function_name(param1=val1, param2=val2)"
        Returns tuple of (function_name, args_dict) or (None, None) if parsing fails.
        
        Handles edge cases like:
        - Values containing '=' or ',' characters
        - Nested data structures (lists, dicts)
        - Proper string quoting and escaping
        - Boolean and numeric values
        
        Examples:
        - "search(query='hello=world', limit=10)" -> ("search", {"query": "hello=world", "limit": 10})
        - "process(data=[1,2,3], config={'key': 'val,ue'})" -> ("process", {"data": [1,2,3], "config": {"key": "val,ue"}})
        """
        try:
            # Parse the string as a Python expression
            parsed = ast.parse(call_string.strip(), mode='eval')
            
            # The parsed expression should be a function call
            if not isinstance(parsed.body, ast.Call):
                return None, None
            
            call_node = parsed.body
            
            # Extract function name
            if isinstance(call_node.func, ast.Name):
                function_name = call_node.func.id
            else:
                return None, None
            
            # Extract arguments
            args_dict = {}
            
            # Handle positional arguments (convert to keyword args with indices)
            for i, arg in enumerate(call_node.args):
                args_dict[f'arg_{i}'] = ast.literal_eval(arg)
            
            # Handle keyword arguments
            for keyword in call_node.keywords:
                if keyword.arg is None:  # **kwargs case
                    continue
                args_dict[keyword.arg] = ast.literal_eval(keyword.value)
            
            return function_name, args_dict
            
        except (SyntaxError, ValueError, TypeError) as e:
            # Return None if parsing fails
            return None, None
        
    def execute_syntax_tree(self, function_calls, return_all):
        execution_order = sorted(function_calls.keys(), key=lambda x: int(x))
        if not execution_order:
            return {}

        responses = {}
        for i in execution_order:
            name, args = list(function_calls[i].items())[0]
            responses[i] = self._prepare_function_call_and_execute(name, args, function_calls, responses)

        # if return_all:
        #     return responses[execution_order[-1]] if len(responses) == 1 else responses # return all or one is same if there is only one response
        # return responses[execution_order[-1]]

        if return_all:
            return responses
        return {str(execution_order[-1]): responses[execution_order[-1]]}

    def decode_syntax_tree_and_execute(self, result, tag='A'):
        function_calls, return_all = self.decode_syntax_tree(result, tag)
        if function_calls:
            return self.execute_syntax_tree(function_calls, return_all)
        return {}
    
    def serialize_response(self, response):
        if not response:
            return ""

        for id in response.keys():
            function_response = response[id]
            for k, v in function_response.items():
                if isinstance(v, pd.DataFrame):
                    function_response[k] = v.to_dict(orient="records")
                    
        return json.dumps(response)

    def check_response_equivalence(self, predicted_response, ground_truth_response, order_aware=True):

        if order_aware:
            return predicted_response == ground_truth_response
        
        # Handle empty strings and None values
        if isinstance(predicted_response, str) and predicted_response.strip() == "":
            predicted_response = {}
        elif isinstance(predicted_response, str):
            predicted_response = json.loads(predicted_response)
        elif predicted_response is None:
            predicted_response = {}
            
        if isinstance(ground_truth_response, str) and ground_truth_response.strip() == "":
            ground_truth_response = {}
        elif isinstance(ground_truth_response, str):
            ground_truth_response = json.loads(ground_truth_response)
        elif ground_truth_response is None:
            ground_truth_response = {}

        # Convert response values to JSON strings for comparison
        # This handles cases where responses are complex objects (dicts, lists, etc.)
        predicted_values = set()
        ground_truth_values = set()
        
        for value in predicted_response.values():
            # Convert to JSON string for hashability
            predicted_values.add(json.dumps(value, sort_keys=True))
            
        for value in ground_truth_response.values():
            # Convert to JSON string for hashability
            ground_truth_values.add(json.dumps(value, sort_keys=True))
        
        return predicted_values == ground_truth_values

    def _flatten_nested_definitions(self, properties, prefix="", required_params=None):
        flattened = {}
        
        if required_params is None:
            required_params = []
    
        for param_name, param_info in properties.items():
            current_name = f"{prefix}.{param_name}" if prefix else param_name
            param_type = param_info.get("type", "unknown")
            
            # Determine if this parameter is required
            is_required = param_name in required_params
            required_status = "required" if is_required else "optional"
            
            if param_type == "dict" and "properties" in param_info:
                # Recursively flatten nested dictionary properties
                nested_props = param_info["properties"]
                # For nested objects, we don't have required/optional info, so mark as optional
                flattened.update(self._flatten_nested_definitions(nested_props, current_name, []))
            elif param_type == "array" and "items" in param_info:
                # Handle array items
                items_info = param_info["items"]
                if items_info.get("type") == "dict" and "properties" in items_info:
                    # Array of objects - flatten the object structure
                    nested_props = items_info["properties"]
                    # For array items, we don't have required/optional info, so mark as optional
                    flattened.update(self._flatten_nested_definitions(nested_props, f"{current_name}[]", []))
                else:
                    # Array of primitives
                    items_type = items_info.get("type", "unknown")
                    flattened[current_name] = [f"array<{items_type}>", required_status]
            else:
                # Simple parameter
                flattened[current_name] = [param_type, required_status]
        
        return flattened

    def parse_function_definitions(self, function_definitions):

        result = {}
    
        for func_name, func_info in function_definitions.items():
            if "parameters" in func_info and "properties" in func_info["parameters"]:
                parameters = func_info["parameters"]["properties"]
                # Get the list of required parameters
                required_params = func_info["parameters"].get("required", [])
                flattened_params = self._flatten_nested_definitions(parameters, "", required_params)
                result[func_name] = flattened_params
        
        return result
    
    def _flatten_nested_ast(self, nested_dict, prefix=""):
        flattened = {}
        
        for key, value in nested_dict.items():
            current_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                # Recursively flatten nested dictionaries
                flattened.update(self._flatten_nested_ast(value, current_key))
            elif isinstance(value, list):
                # Handle arrays - flatten each element
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        # Array of objects - flatten the object structure
                        flattened.update(self._flatten_nested_ast(item, f"{current_key}[{i}]"))
                    else:
                        # Array of primitives
                        flattened[f"{current_key}[{i}]"] = item
            else:
                # Simple value
                flattened[current_key] = value
        
        return flattened
    
    def parse_generated_ast(self, ast):
        result = {}
        
        for step_id, step_info in ast.items():
            for func_name, func_params in step_info.items():
                # Flatten the nested parameters
                flattened_params = self._flatten_nested_ast(func_params)
                result[step_id] = {func_name: flattened_params}
        
        return result

    def validate_ast_against_function_definitions(self, ast):
        parsed_ast = self.parse_generated_ast(ast)
        validation_results = self.validator.validate_function_call(parsed_ast, self.parsed_function_definitions)
        
        # summarize the results
        fn_name_errors = sum([1 for result in validation_results.values() if not result.get('fn_name_match', False)])
        param_errors = sum([
            (r['missing_required_params'].__len__() + r['extra_params'].__len__())
            for r in validation_results.values()
        ])
        type_errors = sum([
            r['type_mismatch_params'].__len__()
            for r in validation_results.values()
        ])
        
        return (fn_name_errors, param_errors, type_errors), validation_results
    
    def format_validation_results(self, validation_results):
        response = ""
        for fn_name, result in validation_results.items():
            if result.get('success', False):
                continue
            api_id = fn_name.split('.')[0]
            api_name = fn_name.split('.')[1]
            response += f"API ID: {api_id}, API Name: {api_name}\n"
            response += self.validator.format_validation_report(result) + "\n"
        return response
