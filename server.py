#!/usr/bin/env python3
"""
MCP Server for Comet Browser Control via Chrome DevTools Protocol
Compatible with Model Context Protocol (MCP) v0.3 draft
"""

import sys
import json
import asyncio
import base64
from typing import Any, Dict, Optional
import pychrome


class CometMCPServer:
    """MCP Server for controlling Comet browser via CDP"""

    def __init__(self, debug_port: int = 9222, debug_host: str = None):
        self.debug_port = debug_port
        # Auto-detect Windows host IP from /etc/resolv.conf in WSL
        if debug_host is None:
            try:
                with open('/etc/resolv.conf', 'r') as f:
                    for line in f:
                        if line.startswith('nameserver'):
                            debug_host = line.split()[1]
                            break
            except:
                pass
        self.debug_host = debug_host or "127.0.0.1"
        self.browser: Optional[pychrome.Browser] = None
        self.tab: Optional[pychrome.Tab] = None

    async def connect(self):
        """Connect to the existing Comet browser instance"""
        try:
            self.browser = pychrome.Browser(url=f"http://{self.debug_host}:{self.debug_port}")
            tabs = self.browser.list_tab()

            if not tabs:
                # Create a new tab if none exist
                self.tab = self.browser.new_tab()
            else:
                # Use the first available tab
                self.tab = tabs[0]

            # Start the tab to enable CDP commands
            self.tab.start()

            # Enable necessary domains
            self.tab.Page.enable()
            self.tab.DOM.enable()
            self.tab.Runtime.enable()

            return True
        except Exception as e:
            raise ConnectionError(f"Failed to connect to browser on port {self.debug_port}: {str(e)}")

    async def open_url(self, url: str) -> Dict[str, Any]:
        """Open a URL in the browser"""
        try:
            self.tab.Page.navigate(url=url, _timeout=30)
            # Wait for page load
            await asyncio.sleep(2)
            return {"success": True, "url": url, "message": f"Opened {url}"}
        except Exception as e:
            raise RuntimeError(f"Failed to open URL: {str(e)}")

    async def get_text(self, selector: str) -> Dict[str, Any]:
        """Get text content from elements matching CSS selector"""
        try:
            # Get document root
            doc = self.tab.DOM.getDocument()
            root_node_id = doc['root']['nodeId']

            # Query selector
            node_id = self.tab.DOM.querySelector(nodeId=root_node_id, selector=selector)

            if not node_id.get('nodeId'):
                return {"success": False, "text": "", "message": f"No element found for selector: {selector}"}

            # Get outer HTML to extract text
            result = self.tab.DOM.getOuterHTML(nodeId=node_id['nodeId'])
            html = result.get('outerHTML', '')

            # Use JS to get text content
            js_code = f"""
            (function() {{
                const el = document.querySelector('{selector}');
                return el ? el.textContent.trim() : '';
            }})()
            """

            eval_result = self.tab.Runtime.evaluate(expression=js_code)
            text = eval_result.get('result', {}).get('value', '')

            return {"success": True, "text": text, "selector": selector}
        except Exception as e:
            raise RuntimeError(f"Failed to get text: {str(e)}")

    async def click(self, selector: str) -> Dict[str, Any]:
        """Click on an element matching CSS selector"""
        try:
            js_code = f"""
            (function() {{
                const el = document.querySelector('{selector}');
                if (el) {{
                    el.click();
                    return true;
                }}
                return false;
            }})()
            """

            result = self.tab.Runtime.evaluate(expression=js_code)
            success = result.get('result', {}).get('value', False)

            if success:
                await asyncio.sleep(0.5)  # Brief wait after click
                return {"success": True, "selector": selector, "message": f"Clicked element: {selector}"}
            else:
                return {"success": False, "message": f"Element not found: {selector}"}
        except Exception as e:
            raise RuntimeError(f"Failed to click element: {str(e)}")

    async def screenshot(self, path: str = "./screenshot.png") -> Dict[str, Any]:
        """Take a screenshot of the current page"""
        try:
            result = self.tab.Page.captureScreenshot(format='png')
            img_data = result.get('data', '')

            # Decode base64 and save to file
            with open(path, 'wb') as f:
                f.write(base64.b64decode(img_data))

            return {"success": True, "path": path, "message": f"Screenshot saved to {path}"}
        except Exception as e:
            raise RuntimeError(f"Failed to take screenshot: {str(e)}")

    async def evaluate_js(self, code: str) -> Dict[str, Any]:
        """Execute JavaScript code and return the result"""
        try:
            # Wrap code in IIFE if it doesn't already return
            if not code.strip().startswith('(function'):
                code = f"(function() {{ {code} }})()"

            result = self.tab.Runtime.evaluate(expression=code, returnByValue=True)

            if result.get('exceptionDetails'):
                error_msg = result['exceptionDetails'].get('text', 'Unknown error')
                return {"success": False, "error": error_msg}

            value = result.get('result', {}).get('value')
            return {"success": True, "result": value}
        except Exception as e:
            raise RuntimeError(f"Failed to evaluate JavaScript: {str(e)}")

    def close(self):
        """Close connection to browser"""
        try:
            if self.tab:
                self.tab.stop()
        except:
            pass


class MCPJSONRPCServer:
    """JSON-RPC 2.0 server for MCP protocol"""

    def __init__(self):
        self.comet = CometMCPServer()
        self.connected = False

    async def initialize(self):
        """Initialize connection to browser"""
        if not self.connected:
            await self.comet.connect()
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

            # Ensure we're connected for browser operations
            if method not in ['initialize', 'tools/list'] and not self.connected:
                await self.initialize()

            # Route to appropriate method
            if method == 'open_url':
                result = await self.comet.open_url(params['url'])
            elif method == 'get_text':
                result = await self.comet.get_text(params['selector'])
            elif method == 'click':
                result = await self.comet.click(params['selector'])
            elif method == 'screenshot':
                path = params.get('path', './screenshot.png')
                result = await self.comet.screenshot(path)
            elif method == 'evaluate_js':
                result = await self.comet.evaluate_js(params['code'])
            elif method == 'tools/list':
                # MCP protocol: list available tools
                result = self.list_tools()
            elif method == 'tools/call':
                # MCP protocol: call a tool
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
        return {
            "tools": [
                {
                    "name": "open_url",
                    "description": "Open a URL in the Comet browser",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "The URL to open"}
                        },
                        "required": ["url"]
                    }
                },
                {
                    "name": "get_text",
                    "description": "Get text content from elements matching a CSS selector",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector"}
                        },
                        "required": ["selector"]
                    }
                },
                {
                    "name": "click",
                    "description": "Click on an element matching a CSS selector",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector"}
                        },
                        "required": ["selector"]
                    }
                },
                {
                    "name": "screenshot",
                    "description": "Take a screenshot of the current page",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Path to save screenshot", "default": "./screenshot.png"}
                        }
                    }
                },
                {
                    "name": "evaluate_js",
                    "description": "Execute JavaScript code in the browser",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string", "description": "JavaScript code to execute"}
                        },
                        "required": ["code"]
                    }
                }
            ]
        }

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool by name with arguments"""
        if tool_name == 'open_url':
            return await self.comet.open_url(arguments['url'])
        elif tool_name == 'get_text':
            return await self.comet.get_text(arguments['selector'])
        elif tool_name == 'click':
            return await self.comet.click(arguments['selector'])
        elif tool_name == 'screenshot':
            path = arguments.get('path', './screenshot.png')
            return await self.comet.screenshot(path)
        elif tool_name == 'evaluate_js':
            return await self.comet.evaluate_js(arguments['code'])
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def run(self):
        """Main server loop: read from stdin, write to stdout"""
        loop = asyncio.get_event_loop()

        # Log startup to stderr (not stdout, to avoid interfering with JSON-RPC)
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


async def main():
    """Entry point"""
    server = MCPJSONRPCServer()
    try:
        await server.run()
    except KeyboardInterrupt:
        print("\nShutting down...", file=sys.stderr)
    finally:
        server.comet.close()


if __name__ == '__main__':
    asyncio.run(main())
