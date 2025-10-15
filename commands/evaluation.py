"""JavaScript evaluation command"""
from typing import Dict, Any
import json
import os
from .base import Command
from .registry import register
from mcp.logging_config import get_logger

logger = get_logger(__name__)


@register
class EvaluateJsCommand(Command):
    """Execute JavaScript code in browser with smart output handling"""

    name = "evaluate_js"
    description = """Execute JavaScript code in the browser and return the result.

Supports:
- Automatic console.log capture (appended to result)
- Timeout protection (30s default)
- Smart serialization for complex objects
- Error handling with stack traces
- Auto-saves large results to ./js_result.json

Examples:
  evaluate_js(code="document.title")  // Returns page title
  evaluate_js(code="console.log('test'); return 42;")  // Returns 42 + console output
  evaluate_js(code="document.querySelectorAll('a').length")  // Count links"""

    input_schema = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "JavaScript code to execute. Can use 'return' for explicit results."
            },
            "timeout": {
                "type": "number",
                "description": "Timeout in seconds (default: 30)",
                "default": 30
            },
            "capture_console": {
                "type": "boolean",
                "description": "Capture console.log output (default: true)",
                "default": True
            }
        },
        "required": ["code"]
    }

    requires_cdp = True

    async def execute(self, code: str, timeout: int = 30, capture_console: bool = True, **kwargs) -> Dict[str, Any]:
        """Execute user's JavaScript code with proper handling"""

        try:
            logger.info(f"[evaluate_js] Executing JS code ({len(code)} chars), timeout={timeout}s")

            # Wrap user code with console capture and serialization
            wrapped_code = self._wrap_user_code(code, capture_console)

            # Execute with timeout
            result = await self.cdp.evaluate(
                expression=wrapped_code,
                returnByValue=True,
                awaitPromise=True,
                timeout=timeout * 1000  # ms
            )

            # Handle CDP response
            if 'exceptionDetails' in result:
                return self._handle_exception(result['exceptionDetails'])

            result_data = result.get('result', {})
            result_value = result_data.get('value', {})

            # Extract components
            user_result = result_value.get('result')
            console_output = result_value.get('console', [])
            result_type = result_value.get('type', 'undefined')

            # Format output
            formatted_result = self._format_result(user_result, result_type)

            # Check if result is too large (>2KB) -> save to file
            result_str = json.dumps(formatted_result, ensure_ascii=False)
            if len(result_str) > 2048:
                return self._save_large_result(formatted_result, console_output, code)

            # Small result - return directly
            response = {
                "success": True,
                "result": formatted_result,
                "type": result_type
            }

            if console_output and capture_console:
                response["console_output"] = console_output
                response["message"] = f"Executed successfully. Console output: {len(console_output)} messages"
            else:
                response["message"] = "Executed successfully"

            logger.info(f"[evaluate_js] Success: type={result_type}, console_logs={len(console_output)}")
            return response

        except Exception as e:
            logger.error(f"[evaluate_js] Exception: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to execute JavaScript: {str(e)}",
                "code_preview": code[:200] + "..." if len(code) > 200 else code
            }

    def _wrap_user_code(self, user_code: str, capture_console: bool) -> str:
        """Wrap user code with console capture and serialization"""

        # Escape user code for safe embedding
        escaped_code = user_code.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')

        return f"""
        (function() {{
            const capturedConsole = [];

            // Console capture
            {self._get_console_capture() if capture_console else ''}

            // Execute user code
            let result;
            let resultType = 'undefined';

            try {{
                // Wrap in IIFE to allow both expressions and statements
                const userFunction = new Function(`{escaped_code}`);
                result = userFunction();

                // Determine type
                if (result === null) {{
                    resultType = 'null';
                }} else if (result === undefined) {{
                    resultType = 'undefined';
                }} else if (typeof result === 'object') {{
                    if (Array.isArray(result)) {{
                        resultType = 'array';
                    }} else if (result instanceof Error) {{
                        resultType = 'error';
                        result = {{
                            name: result.name,
                            message: result.message,
                            stack: result.stack
                        }};
                    }} else if (result instanceof Promise) {{
                        resultType = 'promise';
                        result = '[Promise object - use await or .then()]';
                    }} else {{
                        resultType = 'object';
                    }}
                }} else {{
                    resultType = typeof result;
                }}

                // Serialize functions
                if (typeof result === 'function') {{
                    result = result.toString();
                }}

            }} catch (err) {{
                resultType = 'error';
                result = {{
                    name: err.name,
                    message: err.message,
                    stack: err.stack
                }};
            }}

            return {{
                result: result,
                type: resultType,
                console: capturedConsole
            }};
        }})()
        """

    def _get_console_capture(self) -> str:
        """JavaScript code to capture console.log calls"""
        return """
        const originalLog = console.log;
        const originalWarn = console.warn;
        const originalError = console.error;

        console.log = function(...args) {
            capturedConsole.push({level: 'log', args: args.map(String)});
            originalLog.apply(console, args);
        };
        console.warn = function(...args) {
            capturedConsole.push({level: 'warn', args: args.map(String)});
            originalWarn.apply(console, args);
        };
        console.error = function(...args) {
            capturedConsole.push({level: 'error', args: args.map(String)});
            originalError.apply(console, args);
        };
        """

    def _format_result(self, result: Any, result_type: str) -> Any:
        """Format result for display"""
        if result_type == 'error':
            return {
                "error": True,
                "name": result.get('name', 'Error'),
                "message": result.get('message', 'Unknown error'),
                "stack": result.get('stack', '').split('\n')[:5]  # First 5 lines
            }

        if result_type == 'function':
            # Already stringified in wrapper
            return {"function_source": result}

        if result_type in ['object', 'array']:
            # Try to make objects more readable
            try:
                # Limit depth for very nested objects
                return self._limit_object_depth(result, max_depth=3)
            except:
                return str(result)

        return result

    def _limit_object_depth(self, obj: Any, max_depth: int, current_depth: int = 0) -> Any:
        """Limit object nesting depth to prevent huge outputs"""
        if current_depth >= max_depth:
            return "[Object - max depth reached]"

        if isinstance(obj, dict):
            return {
                k: self._limit_object_depth(v, max_depth, current_depth + 1)
                for k, v in list(obj.items())[:50]  # Limit keys
            }
        elif isinstance(obj, list):
            return [
                self._limit_object_depth(item, max_depth, current_depth + 1)
                for item in obj[:50]  # Limit array items
            ]
        else:
            return obj

    def _handle_exception(self, exception_details: Dict[str, Any]) -> Dict[str, Any]:
        """Handle JavaScript execution exception"""
        exception = exception_details.get('exception', {})

        return {
            "success": False,
            "error": "JavaScript execution error",
            "exception": {
                "type": exception.get('type', 'Error'),
                "value": exception.get('value', 'Unknown error'),
                "description": exception.get('description', ''),
                "line": exception_details.get('lineNumber', 0),
                "column": exception_details.get('columnNumber', 0)
            },
            "message": "JavaScript code threw an exception"
        }

    def _save_large_result(self, result: Any, console_output: list, code: str) -> Dict[str, Any]:
        """Save large results to file"""
        output_file = "./js_result.json"

        try:
            data = {
                "executed_code": code,
                "result": result,
                "console_output": console_output,
                "metadata": {
                    "result_size_bytes": len(json.dumps(result, ensure_ascii=False)),
                    "console_messages": len(console_output)
                }
            }

            os.makedirs(os.path.dirname(os.path.abspath(output_file)) or '.', exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"[evaluate_js] Large result saved to {output_file}")

            return {
                "success": True,
                "message": f"Result too large - saved to {output_file}",
                "instruction": f"Use Read('{output_file}') to see the full result",
                "file_path": output_file,
                "preview": {
                    "result_type": type(result).__name__,
                    "result_size": len(json.dumps(result, ensure_ascii=False)),
                    "console_messages": len(console_output)
                }
            }

        except Exception as e:
            logger.error(f"[evaluate_js] Failed to save large result: {str(e)}")
            return {
                "success": False,
                "error": f"Result too large and failed to save: {str(e)}",
                "message": "Try simplifying the JavaScript code to return less data"
            }
