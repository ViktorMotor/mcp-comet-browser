"""MCP JSON-RPC protocol handler"""
import sys
import json
import asyncio
import time
from typing import Dict, Any
from datetime import datetime
from browser.connection import BrowserConnection
from mcp.logging_config import get_logger
from mcp.errors import (
    MCPError, ParseError, MethodNotFound, InternalError,
    BrowserError, CommandError, ValidationError
)
from commands.context import CommandContext
from commands.registry import CommandRegistry

logger = get_logger("protocol")


def _truncate_data(data: Any, max_length: int = 500) -> str:
    """
    Truncate data for logging to avoid overwhelming logs.

    Args:
        data: Data to truncate (dict, list, str, etc.)
        max_length: Maximum length of resulting string

    Returns:
        Truncated string representation
    """
    try:
        data_str = json.dumps(data, ensure_ascii=False, indent=None)
    except (TypeError, ValueError):
        data_str = str(data)

    if len(data_str) > max_length:
        return data_str[:max_length] + f"... (truncated {len(data_str) - max_length} chars)"
    return data_str


def _wrap_result_for_mcp(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert command result to MCP-compliant format.

    MCP requires tools/call responses to have this structure:
    {
        "content": [{"type": "text", "text": "..."}],
        "isError": false
    }

    This wrapper converts our legacy format to MCP-compliant format.

    Args:
        result: Command result dict (legacy format with 'success', 'result', etc.)

    Returns:
        MCP-compliant result dict with 'content' array and 'isError' flag
    """
    # If already in MCP format (has 'content' key), return as-is
    if "content" in result:
        return result

    # Determine if this is an error
    is_error = not result.get("success", True)

    # Convert result to readable text with smart formatting
    try:
        text_parts = []

        # Add message first if present (most important)
        if "message" in result and isinstance(result.get("message"), str):
            text_parts.append(result["message"])

        # Add main result data with smart formatting
        if "result" in result:
            result_data = result["result"]
            result_str = json.dumps(result_data, indent=2, ensure_ascii=False)

            # For small results, include directly
            if len(result_str) < 2000:
                text_parts.append(f"\nResult:\n{result_str}")
            else:
                # For large results, add summary
                text_parts.append(f"\n⚠️ Result is large ({len(result_str)} chars)")
                text_parts.append(f"Preview: {result_str[:500]}...")

        # Add type information if present (useful for evaluate_js)
        if "type" in result and result["type"] not in ["undefined", "null"]:
            text_parts.append(f"\nType: {result['type']}")

        # Add console output if present (for evaluate_js)
        if "console_output" in result and result["console_output"]:
            console_logs = result["console_output"]
            text_parts.append(f"\n📝 Console Output ({len(console_logs)} messages):")
            for log in console_logs[:10]:  # Limit to 10 messages
                level = log.get("level", "log")
                args = log.get("args", [])
                text_parts.append(f"  [{level.upper()}] {' '.join(str(a) for a in args)}")

        # Add file path if present (for save_page_info, screenshot, etc.)
        if "file" in result or "file_path" in result:
            file_path = result.get("file") or result.get("file_path")
            text_parts.append(f"\n📁 File: {file_path}")

        # Add instruction if present (hints for next steps)
        if "instruction" in result:
            text_parts.append(f"\n💡 {result['instruction']}")

        # Add error details if present
        if "error" in result:
            error_text = result["error"]
            text_parts.append(f"\n❌ Error: {error_text}")

        # Add exception details if present (for evaluate_js exceptions)
        if "exception" in result and isinstance(result["exception"], dict):
            exc = result["exception"]
            text_parts.append(f"\n❌ Exception: {exc.get('type', 'Error')}")
            text_parts.append(f"   {exc.get('value', 'Unknown')}")
            if "description" in exc:
                text_parts.append(f"   {exc['description']}")

        # If we have text parts, join them
        if text_parts:
            text_content = "\n".join(text_parts)
        else:
            # Fallback: serialize entire result as JSON
            text_content = json.dumps(result, indent=2, ensure_ascii=False)

    except (TypeError, ValueError) as e:
        # If JSON serialization fails, convert to string
        logger.warning(f"Failed to serialize result to JSON: {e}")
        text_content = str(result)

    return {
        "content": [
            {
                "type": "text",
                "text": text_content
            }
        ],
        "isError": is_error
    }


class MCPJSONRPCServer:
    """JSON-RPC 2.0 server for MCP protocol"""

    def __init__(self):
        self.connection = BrowserConnection()
        self.connected = False

        # Discover and register all commands automatically
        CommandRegistry.discover_commands('commands')
        self.commands = CommandRegistry.get_all_commands()

    async def initialize(self):
        """Initialize connection to browser"""
        if not self.connected:
            await self.connection.connect()
            self.connected = True

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming JSON-RPC request"""
        request_id = request.get('id')
        method = request.get('method')
        params = request.get('params', {})

        # Log incoming request
        logger.info(f"→ REQUEST [{request_id}] {method}")
        if params:
            logger.debug(f"  Params: {_truncate_data(params, max_length=300)}")

        try:
            # Handle MCP initialization
            if method == 'initialize':
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "comet-browser",
                            "version": "1.0.0"
                        }
                    }
                }

            # Ensure connected for browser operations
            if method not in ['initialize', 'tools/list'] and not self.connected:
                await self.initialize()

            # Route to appropriate method
            if method == 'tools/list':
                result = self.list_tools()
            elif method == 'tools/call':
                if not self.connected:
                    await self.initialize()
                tool_name = params.get('name')
                tool_params = params.get('arguments', {})
                result = await self.call_tool(tool_name, tool_params)
            else:
                raise MethodNotFound(method)

            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }

            # Log successful response
            logger.info(f"← RESPONSE [{request_id}] {method} - SUCCESS")
            logger.debug(f"  Result: {_truncate_data(result, max_length=500)}")

            return response

        except MCPError as e:
            # Handle typed MCP errors
            logger.error(f"← RESPONSE [{request_id}] {method} - ERROR: {e.message}")
            error_response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": e.to_jsonrpc_error()
            }
            logger.debug(f"  Error details: {_truncate_data(e.to_jsonrpc_error(), max_length=300)}")
            return error_response
        except Exception as e:
            # Handle unexpected errors
            logger.error(f"← RESPONSE [{request_id}] {method} - EXCEPTION: {str(e)}")
            error = InternalError(str(e))
            error_response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": error.to_jsonrpc_error()
            }
            logger.debug(f"  Exception details: {_truncate_data(str(e), max_length=300)}")
            return error_response

    def list_tools(self) -> Dict[str, Any]:
        """List available MCP tools"""
        tools = []

        # Access metadata as class attributes (no instance needed)
        for cmd_name, cmd_class in self.commands.items():
            tools.append(cmd_class.to_mcp_tool())

        return {"tools": tools}

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool by name with arguments"""
        logger.info(f"  ⚡ Calling tool: {tool_name}")
        logger.debug(f"     Arguments: {_truncate_data(arguments, max_length=300)}")

        if tool_name not in self.commands:
            raise ValidationError(
                f"Unknown tool: {tool_name}",
                data={"tool_name": tool_name, "available_tools": list(self.commands.keys())}
            )

        # Ensure connection is valid
        await self.connection.ensure_connected()

        # Create execution context with all dependencies
        context = CommandContext(
            tab=self.connection.tab,
            cdp=self.connection.cdp,
            cursor=self.connection.cursor,
            browser=self.connection.browser,
            console_logs=self.connection.console_logs,
            connection=self.connection
        )

        # Get command class and instantiate with context
        cmd_class = self.commands[tool_name]
        cmd_instance = cmd_class(context=context)

        # Execute command with timing
        start_time = time.time()
        result = await cmd_instance.execute(**arguments)
        execution_time = time.time() - start_time

        logger.info(f"  ✓ Tool completed: {tool_name} ({execution_time:.3f}s)")
        logger.debug(f"     Result: {_truncate_data(result, max_length=400)}")

        # Handle tab switching - update connection's tab reference
        if tool_name == 'switch_tab' and result.get('success') and 'newTab' in result:
            self.connection.tab = result.pop('newTab')  # Remove internal field from result
            # Reinitialize cursor on new tab
            self.connection.cursor = self.connection.cursor.__class__(self.connection.tab)
            await self.connection.cursor.initialize()

        # Handle tab closing - clear reference if current tab was closed
        if tool_name == 'close_tab' and result.get('wasCurrentTab'):
            self.connection.tab = None

        # Wrap result in MCP-compliant format (content array)
        mcp_result = _wrap_result_for_mcp(result)
        logger.debug(f"     MCP-wrapped result: {_truncate_data(mcp_result, max_length=200)}")

        return mcp_result

    async def run(self):
        """Main server loop: read from stdin, write to stdout"""
        loop = asyncio.get_event_loop()

        # Log startup
        logger.info("=" * 80)
        logger.info("MCP Comet Server starting...")
        logger.info("Listening for JSON-RPC requests on stdin...")
        logger.info("=" * 80)

        request_count = 0

        while True:
            try:
                # Read line from stdin
                line = await loop.run_in_executor(None, sys.stdin.readline)

                if not line:
                    logger.info("EOF received, shutting down...")
                    break

                line = line.strip()
                if not line:
                    continue

                request_count += 1
                logger.debug("-" * 80)
                logger.debug(f"Raw request #{request_count}: {_truncate_data(line, max_length=200)}")

                # Parse JSON-RPC request
                request = json.loads(line)

                # Handle request
                response = await self.handle_request(request)

                # Log response before sending
                response_str = json.dumps(response)
                logger.debug(f"Raw response #{request_count}: {_truncate_data(response_str, max_length=200)}")

                # Write response to stdout
                print(response_str, flush=True)
                logger.debug(f"Response #{request_count} sent to stdout")

            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error: {str(e)}")
                logger.debug(f"  Invalid JSON: {_truncate_data(line, max_length=200)}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    }
                }
                print(json.dumps(error_response), flush=True)
            except Exception as e:
                logger.error(f"Server error: {str(e)}")
                logger.debug(f"  Exception type: {type(e).__name__}")
                # Continue running even on errors

    def close(self):
        """Cleanup resources"""
        # Note: connection.close() is async but called from sync context
        # In practice, tab.stop() is synchronous so it's safe
        try:
            if self.connection.tab:
                self.connection.tab.stop()
        except Exception as e:
            logger.debug(f"Error closing connection: {e}")
