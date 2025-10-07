"""MCP JSON-RPC protocol handler"""
import sys
import json
import asyncio
from typing import Dict, Any
from browser.connection import BrowserConnection
from mcp.logging_config import get_logger
from mcp.errors import (
    MCPError, ParseError, MethodNotFound, InternalError,
    BrowserError, CommandError, ValidationError
)
from commands.context import CommandContext
from commands.registry import CommandRegistry

logger = get_logger("protocol")


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

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }

        except MCPError as e:
            # Handle typed MCP errors
            logger.error(f"MCP error: {e.message}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": e.to_jsonrpc_error()
            }
        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Unexpected error: {str(e)}")
            error = InternalError(str(e))
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": error.to_jsonrpc_error()
            }

    def list_tools(self) -> Dict[str, Any]:
        """List available MCP tools"""
        tools = []

        # Access metadata as class attributes (no instance needed)
        for cmd_name, cmd_class in self.commands.items():
            tools.append(cmd_class.to_mcp_tool())

        return {"tools": tools}

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool by name with arguments"""
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

        # Execute command
        result = await cmd_instance.execute(**arguments)

        # Handle tab switching - update connection's tab reference
        if tool_name == 'switch_tab' and result.get('success') and 'newTab' in result:
            self.connection.tab = result.pop('newTab')  # Remove internal field from result
            # Reinitialize cursor on new tab
            self.connection.cursor = self.connection.cursor.__class__(self.connection.tab)
            await self.connection.cursor.initialize()

        # Handle tab closing - clear reference if current tab was closed
        if tool_name == 'close_tab' and result.get('wasCurrentTab'):
            self.connection.tab = None

        return result

    async def run(self):
        """Main server loop: read from stdin, write to stdout"""
        loop = asyncio.get_event_loop()

        # Log startup
        logger.info("MCP Comet Server starting...")
        logger.info("Listening for JSON-RPC requests on stdin...")

        while True:
            try:
                # Read line from stdin
                line = await loop.run_in_executor(None, sys.stdin.readline)

                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                # Parse JSON-RPC request
                request = json.loads(line)

                # Handle request
                response = await self.handle_request(request)

                # Write response to stdout
                print(json.dumps(response), flush=True)

            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error: {str(e)}")
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
