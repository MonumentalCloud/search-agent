"""
Python Runtime for executing dynamically generated code in the adaptive agent.
"""

import logging
import sys
import io
import contextlib
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class PythonRuntime:
    """
    A sandboxed Python runtime for executing dynamically generated code.
    """
    
    def __init__(self):
        self.allowed_modules = {
            'datetime', 'time', 'calendar', 'math', 'statistics',
            'json', 're', 'string', 'collections', 'itertools',
            'operator', 'functools'
        }
        
    def execute_code(self, python_code: str, data: List[Dict[str, Any]], 
                    function_name: str = "process_data") -> List[Dict[str, Any]]:
        """
        Execute Python code with the provided data.
        
        Args:
            python_code: The Python code to execute
            data: The data to pass to the function
            function_name: The name of the function to call
            
        Returns:
            The result of executing the function
        """
        try:
            logger.info(f"Executing Python code for function: {function_name}")
            logger.debug(f"Python code:\n{python_code}")
            
            # Create a restricted globals environment
            restricted_globals = {
                '__builtins__': {
                    'len': len,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'list': list,
                    'dict': dict,
                    'tuple': tuple,
                    'set': set,
                    'range': range,
                    'enumerate': enumerate,
                    'zip': zip,
                    'min': min,
                    'max': max,
                    'sum': sum,
                    'abs': abs,
                    'round': round,
                    'sorted': sorted,
                    'reversed': reversed,
                    'any': any,
                    'all': all,
                    'isinstance': isinstance,
                    'hasattr': hasattr,
                    'getattr': getattr,
                    'setattr': setattr,
                    'print': print,
                    'open': open,
                    '__import__': __import__,
                }
            }
            
            # Add allowed modules
            for module_name in self.allowed_modules:
                try:
                    restricted_globals[module_name] = __import__(module_name)
                except ImportError:
                    logger.warning(f"Could not import module: {module_name}")
            
            # Execute the code
            exec(python_code, restricted_globals)
            
            # Get the function and execute it
            if function_name in restricted_globals:
                func = restricted_globals[function_name]
                result = func(data)
                logger.info(f"Python execution successful, returned {len(result) if isinstance(result, list) else 'non-list'} items")
                return result
            else:
                # Try common function names
                common_names = ['get_tuesday_meetings', 'filter_by_day', 'process_meetings', 'filter_data']
                for name in common_names:
                    if name in restricted_globals:
                        func = restricted_globals[name]
                        result = func(data)
                        logger.info(f"Python execution successful with {name}, returned {len(result) if isinstance(result, list) else 'non-list'} items")
                        return result
                
                logger.error(f"Function '{function_name}' not found in executed code")
                return []
                
        except Exception as e:
            logger.error(f"Python runtime execution failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    def execute_code_with_custom_function(self, python_code: str, data: List[Dict[str, Any]], 
                                        custom_function_name: str) -> List[Dict[str, Any]]:
        """
        Execute Python code with a custom function name.
        """
        return self.execute_code(python_code, data, custom_function_name)
