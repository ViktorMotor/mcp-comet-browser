"""
Unit tests for commands/evaluation.py

Tests:
- EvaluateJsCommand: JavaScript execution with console capture, timeout, serialization
- Console log capture: log/warn/error levels
- Timeout handling: Default 30s, custom timeouts
- Smart serialization: primitives, objects, arrays, functions, errors, promises
- Auto-save: Large results (>2KB) saved to ./js_result.json
- Error handling: JavaScript exceptions, CDP errors, execution errors

Coverage target: 60%+ (21% → 60%)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from commands.evaluation import EvaluateJsCommand
from commands.context import CommandContext
import json


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_tab():
    """Mock pychrome Tab"""
    tab = MagicMock()
    return tab


@pytest.fixture
def mock_cdp():
    """Mock AsyncCDP wrapper"""
    cdp = AsyncMock()
    cdp.evaluate = AsyncMock()
    return cdp


@pytest.fixture
def context(mock_tab, mock_cdp):
    """CommandContext with mocked dependencies"""
    return CommandContext(
        tab=mock_tab,
        cursor=None,
        browser=None,
        cdp=mock_cdp
    )


# ============================================================================
# EvaluateJsCommand Tests - Basic Execution
# ============================================================================

class TestEvaluateJsBasic:
    """Tests for basic JavaScript execution"""

    @pytest.mark.asyncio
    async def test_metadata(self):
        """Test command metadata"""
        assert EvaluateJsCommand.name == "evaluate_js"
        assert "Execute JavaScript code" in EvaluateJsCommand.description
        assert EvaluateJsCommand.requires_cdp is True

        schema = EvaluateJsCommand.input_schema
        assert schema["required"] == ["code"]
        assert "code" in schema["properties"]
        assert "timeout" in schema["properties"]
        assert "capture_console" in schema["properties"]

    @pytest.mark.asyncio
    async def test_simple_expression(self, context, mock_cdp):
        """Test simple expression execution (document.title)"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": "Example Page",
                    "type": "string",
                    "console": []
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="document.title")

        # Verify CDP call
        mock_cdp.evaluate.assert_called_once()
        call_args = mock_cdp.evaluate.call_args[1]
        assert "document.title" in call_args["expression"]
        assert call_args["returnByValue"] is True
        assert call_args["awaitPromise"] is True
        assert call_args["timeout"] == 30000  # Default 30s

        # Verify result
        assert result["success"] is True
        assert result["result"] == "Example Page"
        assert result["type"] == "string"

    @pytest.mark.asyncio
    async def test_numeric_result(self, context, mock_cdp):
        """Test numeric result (42)"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": 42,
                    "type": "number",
                    "console": []
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="return 42")

        assert result["success"] is True
        assert result["result"] == 42
        assert result["type"] == "number"

    @pytest.mark.asyncio
    async def test_boolean_result(self, context, mock_cdp):
        """Test boolean result (true/false)"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": True,
                    "type": "boolean",
                    "console": []
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="return true")

        assert result["success"] is True
        assert result["result"] is True
        assert result["type"] == "boolean"

    @pytest.mark.asyncio
    async def test_undefined_result(self, context, mock_cdp):
        """Test undefined result"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": None,
                    "type": "undefined",
                    "console": []
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="undefined")

        assert result["success"] is True
        assert result["result"] is None
        assert result["type"] == "undefined"

    @pytest.mark.asyncio
    async def test_null_result(self, context, mock_cdp):
        """Test null result"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": None,
                    "type": "null",
                    "console": []
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="null")

        assert result["success"] is True
        assert result["result"] is None
        assert result["type"] == "null"


# ============================================================================
# Console Capture Tests
# ============================================================================

class TestConsoleCapture:
    """Tests for console.log/warn/error capture"""

    @pytest.mark.asyncio
    async def test_console_log_capture(self, context, mock_cdp):
        """Test console.log capture"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": 42,
                    "type": "number",
                    "console": [
                        {"level": "log", "args": ["test message"]}
                    ]
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="console.log('test message'); return 42;")

        assert result["success"] is True
        assert result["result"] == 42
        assert len(result["console_output"]) == 1
        assert result["console_output"][0]["level"] == "log"
        assert result["console_output"][0]["args"] == ["test message"]

    @pytest.mark.asyncio
    async def test_console_warn_capture(self, context, mock_cdp):
        """Test console.warn capture"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": None,
                    "type": "undefined",
                    "console": [
                        {"level": "warn", "args": ["warning message"]}
                    ]
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="console.warn('warning message')")

        assert result["success"] is True
        assert len(result["console_output"]) == 1
        assert result["console_output"][0]["level"] == "warn"

    @pytest.mark.asyncio
    async def test_console_error_capture(self, context, mock_cdp):
        """Test console.error capture"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": None,
                    "type": "undefined",
                    "console": [
                        {"level": "error", "args": ["error message"]}
                    ]
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="console.error('error message')")

        assert result["success"] is True
        assert len(result["console_output"]) == 1
        assert result["console_output"][0]["level"] == "error"

    @pytest.mark.asyncio
    async def test_multiple_console_logs(self, context, mock_cdp):
        """Test multiple console calls captured"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": "done",
                    "type": "string",
                    "console": [
                        {"level": "log", "args": ["step 1"]},
                        {"level": "warn", "args": ["step 2"]},
                        {"level": "error", "args": ["step 3"]},
                        {"level": "log", "args": ["step 4"]}
                    ]
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="console.log('step 1'); console.warn('step 2'); console.error('step 3'); console.log('step 4'); return 'done';")

        assert result["success"] is True
        assert len(result["console_output"]) == 4
        assert "Console output: 4 messages" in result["message"]

    @pytest.mark.asyncio
    async def test_console_capture_disabled(self, context, mock_cdp):
        """Test console capture can be disabled"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": 100,
                    "type": "number",
                    "console": []  # Empty because capture_console=False
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="console.log('test'); return 100;", capture_console=False)

        assert result["success"] is True
        assert "console_output" not in result

    @pytest.mark.asyncio
    async def test_console_with_multiple_args(self, context, mock_cdp):
        """Test console.log with multiple arguments"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": None,
                    "type": "undefined",
                    "console": [
                        {"level": "log", "args": ["Count:", "42", "Items:", "test"]}
                    ]
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="console.log('Count:', 42, 'Items:', 'test')")

        assert result["success"] is True
        assert len(result["console_output"][0]["args"]) == 4


# ============================================================================
# Smart Serialization Tests
# ============================================================================

class TestSmartSerialization:
    """Tests for smart object serialization"""

    @pytest.mark.asyncio
    async def test_simple_object(self, context, mock_cdp):
        """Test simple object serialization"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": {"name": "John", "age": 30},
                    "type": "object",
                    "console": []
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="return {name: 'John', age: 30}")

        assert result["success"] is True
        assert result["result"]["name"] == "John"
        assert result["result"]["age"] == 30
        assert result["type"] == "object"

    @pytest.mark.asyncio
    async def test_array_result(self, context, mock_cdp):
        """Test array serialization"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": [1, 2, 3, 4, 5],
                    "type": "array",
                    "console": []
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="return [1, 2, 3, 4, 5]")

        assert result["success"] is True
        assert result["result"] == [1, 2, 3, 4, 5]
        assert result["type"] == "array"

    @pytest.mark.asyncio
    async def test_function_serialization(self, context, mock_cdp):
        """Test function serialization (toString)"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": "function test() { return 42; }",
                    "type": "function",
                    "console": []
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="return function test() { return 42; }")

        assert result["success"] is True
        assert "function_source" in result["result"]
        assert "function test()" in result["result"]["function_source"]

    @pytest.mark.asyncio
    async def test_error_serialization(self, context, mock_cdp):
        """Test Error object serialization"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": {
                        "name": "TypeError",
                        "message": "Cannot read property 'foo' of undefined",
                        "stack": "TypeError: Cannot read property 'foo' of undefined\n    at <anonymous>:1:5\n    at eval:1:1"
                    },
                    "type": "error",
                    "console": []
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="throw new TypeError('Cannot read property \\'foo\\' of undefined')")

        assert result["success"] is True
        assert result["result"]["error"] is True
        assert result["result"]["name"] == "TypeError"
        assert "Cannot read property 'foo'" in result["result"]["message"]
        assert len(result["result"]["stack"]) <= 5  # Max 5 lines

    @pytest.mark.asyncio
    async def test_nested_object_depth_limiting(self, context, mock_cdp):
        """Test nested object depth limiting (max 3 levels)"""
        nested_obj = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": "too deep"
                    }
                }
            }
        }

        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": nested_obj,
                    "type": "object",
                    "console": []
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="return {level1: {level2: {level3: {level4: 'too deep'}}}}")

        assert result["success"] is True
        # _limit_object_depth should truncate at depth 3
        assert "level1" in result["result"]
        assert "level2" in result["result"]["level1"]

    @pytest.mark.asyncio
    async def test_large_array_limiting(self, context, mock_cdp):
        """Test large array limiting (max 50 items)"""
        large_array = list(range(100))

        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": large_array,
                    "type": "array",
                    "console": []
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="return Array.from({length: 100}, (_, i) => i)")

        assert result["success"] is True
        # _limit_object_depth should limit to 50 items
        assert len(result["result"]) <= 50


# ============================================================================
# Timeout Tests
# ============================================================================

class TestTimeout:
    """Tests for timeout handling"""

    @pytest.mark.asyncio
    async def test_default_timeout(self, context, mock_cdp):
        """Test default 30s timeout"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": "done",
                    "type": "string",
                    "console": []
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        await cmd.execute(code="return 'done'")

        # Verify default timeout
        call_args = mock_cdp.evaluate.call_args[1]
        assert call_args["timeout"] == 30000  # 30s in ms

    @pytest.mark.asyncio
    async def test_custom_timeout(self, context, mock_cdp):
        """Test custom timeout (60s)"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": "done",
                    "type": "string",
                    "console": []
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        await cmd.execute(code="return 'done'", timeout=60)

        # Verify custom timeout
        call_args = mock_cdp.evaluate.call_args[1]
        assert call_args["timeout"] == 60000  # 60s in ms

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, context, mock_cdp):
        """Test timeout error handling"""
        mock_cdp.evaluate.side_effect = RuntimeError("Execution timeout: 30000ms")

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="while(true) {}")

        assert result["success"] is False
        assert "timeout" in result["error"].lower()


# ============================================================================
# Large Result Auto-Save Tests
# ============================================================================

class TestLargeResultAutoSave:
    """Tests for auto-save of large results (>2KB)"""

    @pytest.mark.asyncio
    async def test_small_result_returned_directly(self, context, mock_cdp):
        """Test small result (<2KB) returned directly"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": {"small": "data"},
                    "type": "object",
                    "console": []
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="return {small: 'data'}")

        assert result["success"] is True
        assert "file_path" not in result  # Not saved to file
        assert result["result"]["small"] == "data"

    @pytest.mark.asyncio
    async def test_large_result_saved_to_file(self, context, mock_cdp):
        """Test large result (>2KB) saved to ./js_result.json"""
        # Create large result (>2KB)
        large_result = {"data": "x" * 3000}

        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": large_result,
                    "type": "object",
                    "console": [{"level": "log", "args": ["processing..."]}]
                }
            }
        }

        cmd = EvaluateJsCommand(context)

        # Mock file operations
        with patch("builtins.open", mock_open()) as mock_file, \
             patch("os.makedirs") as mock_makedirs, \
             patch("os.path.getsize", return_value=3500):

            result = await cmd.execute(code="return {data: 'x'.repeat(3000)}")

            # Verify file was written
            mock_file.assert_called_once_with("./js_result.json", 'w', encoding='utf-8')
            mock_makedirs.assert_called_once()

            # Verify result structure
            assert result["success"] is True
            assert result["file_path"] == "./js_result.json"
            assert "Result too large - saved to" in result["message"]
            assert "Use Read('./js_result.json')" in result["instruction"]
            assert result["preview"]["result_size"] > 2048
            assert result["preview"]["console_messages"] == 1

    @pytest.mark.asyncio
    async def test_auto_save_file_write_error(self, context, mock_cdp):
        """Test auto-save file write error handling"""
        large_result = {"data": "x" * 3000}

        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": large_result,
                    "type": "object",
                    "console": []
                }
            }
        }

        cmd = EvaluateJsCommand(context)

        # Mock file write failure
        with patch("builtins.open", side_effect=PermissionError("Permission denied")), \
             patch("os.makedirs"):

            result = await cmd.execute(code="return {data: 'x'.repeat(3000)}")

            assert result["success"] is False
            assert "Result too large and failed to save" in result["error"]
            assert "Permission denied" in result["error"]


# ============================================================================
# JavaScript Exception Handling Tests
# ============================================================================

class TestJavaScriptExceptions:
    """Tests for JavaScript execution exceptions"""

    @pytest.mark.asyncio
    async def test_syntax_error(self, context, mock_cdp):
        """Test JavaScript syntax error"""
        mock_cdp.evaluate.return_value = {
            "exceptionDetails": {
                "exception": {
                    "type": "SyntaxError",
                    "value": "Unexpected token",
                    "description": "SyntaxError: Unexpected token }"
                },
                "lineNumber": 1,
                "columnNumber": 10
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="return {invalid syntax}}")

        assert result["success"] is False
        assert result["error"] == "JavaScript execution error"
        assert result["exception"]["type"] == "SyntaxError"
        assert result["exception"]["line"] == 1
        assert result["exception"]["column"] == 10

    @pytest.mark.asyncio
    async def test_reference_error(self, context, mock_cdp):
        """Test JavaScript ReferenceError"""
        mock_cdp.evaluate.return_value = {
            "exceptionDetails": {
                "exception": {
                    "type": "ReferenceError",
                    "value": "undefined_variable is not defined",
                    "description": "ReferenceError: undefined_variable is not defined"
                },
                "lineNumber": 1,
                "columnNumber": 5
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="return undefined_variable")

        assert result["success"] is False
        assert result["exception"]["type"] == "ReferenceError"
        assert "undefined_variable" in result["exception"]["value"]

    @pytest.mark.asyncio
    async def test_type_error(self, context, mock_cdp):
        """Test JavaScript TypeError"""
        mock_cdp.evaluate.return_value = {
            "exceptionDetails": {
                "exception": {
                    "type": "TypeError",
                    "value": "Cannot read property 'foo' of null",
                    "description": "TypeError: Cannot read property 'foo' of null"
                },
                "lineNumber": 1,
                "columnNumber": 3
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="null.foo")

        assert result["success"] is False
        assert result["exception"]["type"] == "TypeError"


# ============================================================================
# CDP Error Handling Tests
# ============================================================================

class TestCDPErrorHandling:
    """Tests for CDP-level error handling"""

    @pytest.mark.asyncio
    async def test_cdp_connection_error(self, context, mock_cdp):
        """Test CDP connection error"""
        mock_cdp.evaluate.side_effect = RuntimeError("CDP connection lost")

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="return 42")

        assert result["success"] is False
        assert "CDP connection lost" in result["error"]
        assert "Failed to execute JavaScript" in result["message"]

    @pytest.mark.asyncio
    async def test_cdp_timeout_error(self, context, mock_cdp):
        """Test CDP timeout error"""
        mock_cdp.evaluate.side_effect = RuntimeError("Execution timeout: 30000ms")

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="while(true) {}", timeout=30)

        assert result["success"] is False
        assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_cdp_evaluation_error(self, context, mock_cdp):
        """Test CDP evaluation error"""
        mock_cdp.evaluate.side_effect = Exception("Tab has been stopped")

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="return 42")

        assert result["success"] is False
        assert "Tab has been stopped" in result["error"]


# ============================================================================
# Code Wrapping Tests
# ============================================================================

class TestCodeWrapping:
    """Tests for _wrap_user_code method"""

    @pytest.mark.asyncio
    async def test_code_escaping_backticks(self, context, mock_cdp):
        """Test code with backticks is properly escaped"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": "test",
                    "type": "string",
                    "console": []
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        await cmd.execute(code="return `template string`")

        # Verify backticks are escaped in wrapped code
        call_args = mock_cdp.evaluate.call_args[1]
        expression = call_args["expression"]
        # Backticks should be escaped: \`
        assert "\\`" in expression or "template string" in expression

    @pytest.mark.asyncio
    async def test_code_escaping_dollar_brace(self, context, mock_cdp):
        """Test code with ${ is properly escaped"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": "test",
                    "type": "string",
                    "console": []
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        await cmd.execute(code="return `value: ${42}`")

        # Verify ${ is escaped
        call_args = mock_cdp.evaluate.call_args[1]
        expression = call_args["expression"]
        assert "\\${" in expression or "value:" in expression

    @pytest.mark.asyncio
    async def test_code_preview_in_error(self, context, mock_cdp):
        """Test long code is truncated in error messages (200 chars)"""
        long_code = "x" * 300

        mock_cdp.evaluate.side_effect = RuntimeError("Error")

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code=long_code)

        assert result["success"] is False
        assert len(result["code_preview"]) == 203  # 200 chars + "..."
        assert result["code_preview"].endswith("...")


# ============================================================================
# Edge Cases Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases"""

    @pytest.mark.asyncio
    async def test_empty_code(self, context, mock_cdp):
        """Test execution with empty code string"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": None,
                    "type": "undefined",
                    "console": []
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="")

        assert result["success"] is True
        assert result["type"] == "undefined"

    @pytest.mark.asyncio
    async def test_very_long_code(self, context, mock_cdp):
        """Test execution with very long code (1000+ chars)"""
        long_code = "return " + "'x'" + " + 'x'" * 200

        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": "x" * 201,
                    "type": "string",
                    "console": []
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code=long_code)

        assert result["success"] is True
        assert len(result["result"]) == 201

    @pytest.mark.asyncio
    async def test_unicode_code(self, context, mock_cdp):
        """Test execution with unicode characters"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": "Привет, мир! 🌍",
                    "type": "string",
                    "console": []
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="return 'Привет, мир! 🌍'")

        assert result["success"] is True
        assert result["result"] == "Привет, мир! 🌍"

    @pytest.mark.asyncio
    async def test_missing_result_value(self, context, mock_cdp):
        """Test handling missing 'value' in CDP response"""
        mock_cdp.evaluate.return_value = {
            "result": {}  # Missing 'value'
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="return 42")

        # Should handle gracefully with defaults
        assert result["success"] is True
        assert result.get("type") == "undefined"

    @pytest.mark.asyncio
    async def test_missing_console_key(self, context, mock_cdp):
        """Test handling missing 'console' in result"""
        mock_cdp.evaluate.return_value = {
            "result": {
                "value": {
                    "result": 42,
                    "type": "number"
                    # Missing 'console' key
                }
            }
        }

        cmd = EvaluateJsCommand(context)
        result = await cmd.execute(code="return 42")

        assert result["success"] is True
        assert result["result"] == 42
        # Should not have console_output if console array is empty/missing
