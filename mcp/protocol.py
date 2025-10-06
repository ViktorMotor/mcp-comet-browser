"""MCP JSON-RPC protocol handler"""
import sys
import json
import asyncio
from typing import Dict, Any
from browser.connection import BrowserConnection
from commands.navigation import OpenUrlCommand, GetTextCommand
from commands.interaction import ClickCommand, ClickByTextCommand, ScrollPageCommand, MoveCursorCommand
from commands.devtools import (
    OpenDevtoolsCommand, CloseDevtoolsCommand, ConsoleCommandCommand,
    GetConsoleLogsCommand, InspectElementCommand, GetNetworkActivityCommand
)
from commands.tabs import ListTabsCommand, CreateTabCommand, CloseTabCommand, SwitchTabCommand
from commands.evaluation import EvaluateJsCommand
from commands.screenshot import ScreenshotCommand
from commands.search import FindElementsCommand, GetPageStructureCommand
from commands.helpers import DebugElementCommand, ForceClickCommand
from commands.diagnostics import (
    EnableConsoleLoggingCommand, DiagnosePageCommand, GetClickableElementsCommand
)


class MCPJSONRPCServer:
    """JSON-RPC 2.0 server for MCP protocol"""

    def __init__(self):
        self.connection = BrowserConnection()
        self.connected = False
        self.commands = {}
        self._register_commands()

    def _register_commands(self):
        """Register all available commands"""
        # Navigation commands
        self.commands['open_url'] = OpenUrlCommand
        self.commands['get_text'] = GetTextCommand

        # Interaction commands
        self.commands['click'] = ClickCommand
        self.commands['click_by_text'] = ClickByTextCommand
        self.commands['scroll_page'] = ScrollPageCommand
        self.commands['move_cursor'] = MoveCursorCommand

        # DevTools commands
        self.commands['open_devtools'] = OpenDevtoolsCommand
        self.commands['close_devtools'] = CloseDevtoolsCommand
        self.commands['console_command'] = ConsoleCommandCommand
        self.commands['get_console_logs'] = GetConsoleLogsCommand
        self.commands['inspect_element'] = InspectElementCommand
        self.commands['get_network_activity'] = GetNetworkActivityCommand

        # Tab commands
        self.commands['list_tabs'] = ListTabsCommand
        self.commands['create_tab'] = CreateTabCommand
        self.commands['close_tab'] = CloseTabCommand
        self.commands['switch_tab'] = SwitchTabCommand

        # Evaluation and screenshot
        self.commands['evaluate_js'] = EvaluateJsCommand
        self.commands['screenshot'] = ScreenshotCommand

        # Search and query
        self.commands['find_elements'] = FindElementsCommand
        self.commands['get_page_structure'] = GetPageStructureCommand

        # Debugging helpers
        self.commands['debug_element'] = DebugElementCommand
        self.commands['force_click'] = ForceClickCommand

        # Diagnostics
        self.commands['enable_console_logging'] = EnableConsoleLoggingCommand
        self.commands['diagnose_page'] = DiagnosePageCommand
        self.commands['get_clickable_elements'] = GetClickableElementsCommand

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
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }

        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32000,
                    "message": str(e)
                }
            }

    def list_tools(self) -> Dict[str, Any]:
        """List available MCP tools"""
        tools = []

        # Instantiate each command temporarily to get its MCP definition
        for cmd_name, cmd_class in self.commands.items():
            # Create dummy instance (tab will be set later when executing)
            cmd_instance = cmd_class(tab=None)
            tools.append(cmd_instance.to_mcp_tool())

        return {"tools": tools}

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool by name with arguments"""
        if tool_name not in self.commands:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Ensure connection is valid
        await self.connection.ensure_connected()

        # Get command class and instantiate with current tab
        cmd_class = self.commands[tool_name]
        cmd_instance = cmd_class(tab=self.connection.tab)

        # Handle special cases that need extra context
        if tool_name in ['click', 'click_by_text', 'move_cursor', 'force_click']:
            arguments['cursor'] = self.connection.cursor
        elif tool_name == 'open_url':
            arguments['cursor'] = self.connection.cursor
        elif tool_name == 'get_console_logs':
            arguments['console_logs'] = self.connection.console_logs
        elif tool_name == 'enable_console_logging':
            arguments['connection'] = self.connection
        elif tool_name in ['list_tabs', 'create_tab', 'close_tab', 'switch_tab']:
            arguments['browser'] = self.connection.browser
            arguments['current_tab'] = self.connection.tab

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

        # Log startup to stderr
        print("MCP Comet Server starting...", file=sys.stderr)
        print("Listening for JSON-RPC requests on stdin...", file=sys.stderr)

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
                print(f"Server error: {str(e)}", file=sys.stderr)
                # Continue running even on errors

    def close(self):
        """Cleanup resources"""
        self.connection.close()
