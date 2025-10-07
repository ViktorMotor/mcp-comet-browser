"""Browser connection management via Chrome DevTools Protocol"""
import sys
import asyncio
from typing import Optional
import pychrome
from .cursor import AICursor
from mcp.logging_config import get_logger

logger = get_logger("browser.connection")


class BrowserConnection:
    """Manages connection to Comet browser via CDP"""

    def __init__(self, debug_port = 9222, debug_host: str = None):
        """Initialize browser connection

        Args:
            debug_port: CDP debug port (int) or full URL (str like 'http://host:port')
            debug_host: Debug host IP (auto-detects WSL host if None, ignored if debug_port is URL)
        """
        # Support both port number and full URL
        if isinstance(debug_port, str) and debug_port.startswith('http'):
            # Full URL provided
            self.debug_url = debug_port
            self.debug_port = None
            self.debug_host = None
        else:
            # Port number provided
            self.debug_port = debug_port
            self.debug_url = None

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
        self.console_logs = []  # Store console logs from CDP events
        self.cursor: Optional[AICursor] = None

    async def ensure_connected(self):
        """Ensure we have a valid connection to a browser tab"""
        try:
            # Test if current tab is still alive
            if self.tab:
                try:
                    # Try a simple command to check if tab is responsive
                    self.tab.Runtime.evaluate(expression="1+1")
                    return True
                except Exception as e:
                    # Tab is dead, need to reconnect
                    logger.warning(f"Tab connection lost: {str(e)}, reconnecting...")
                    try:
                        self.tab.stop()
                    except:
                        pass
                    self.tab = None

            # Reconnect to browser
            await self.connect()
            return True
        except Exception as e:
            raise ConnectionError(f"Failed to ensure connection: {str(e)}")

    async def connect(self):
        """Connect to the existing Comet browser instance"""
        try:
            # Use debug_url if provided, otherwise construct from host:port
            browser_url = self.debug_url or f"http://{self.debug_host}:{self.debug_port}"
            self.browser = pychrome.Browser(url=browser_url)
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
            self.tab.Console.enable()  # Enable console for logs
            self.tab.Network.enable()  # Enable network monitoring
            self.tab.Debugger.enable()  # Enable debugger

            # Set up console message listeners
            self._setup_console_listeners()

            # Initialize JavaScript console interceptor as backup
            await self._initialize_js_console_interceptor()

            # Initialize AI cursor
            self.cursor = AICursor(self.tab)
            await self.cursor.initialize()

            return True
        except Exception as e:
            raise ConnectionError(f"Failed to connect to browser on port {self.debug_port}: {str(e)}")

    async def force_enable_console_logging(self):
        """Force re-enable console logging and clear any issues"""
        try:
            # Re-enable Console domain
            self.tab.Console.enable()
            self.tab.Runtime.enable()

            # Clear and re-setup listeners
            self._setup_console_listeners()

            # Re-initialize JS interceptor
            await self._initialize_js_console_interceptor()

            # Test that logging works
            test_result = self.tab.Runtime.evaluate(
                expression="console.log('MCP Console Test'); 'test-success'",
                returnByValue=True
            )

            return {
                "success": True,
                "message": "Console logging re-enabled",
                "test": test_result.get('result', {}).get('value')
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _setup_console_listeners(self):
        """Set up CDP console event listeners"""
        def console_message_handler(message):
            """Handle console messages from CDP"""
            try:
                # Extract console message details
                log_entry = {
                    "type": message.get("type", "log"),
                    "level": message.get("level", "log"),
                    "text": message.get("text", ""),
                    "timestamp": message.get("timestamp", 0),
                    "source": message.get("source", "console-api"),
                    "url": message.get("url", ""),
                    "lineNumber": message.get("line", 0)
                }

                # Format args if available
                if "args" in message:
                    args = message["args"]
                    formatted_args = []
                    for arg in args:
                        if arg.get("type") == "string":
                            formatted_args.append(arg.get("value", ""))
                        elif arg.get("type") == "number":
                            formatted_args.append(str(arg.get("value", "")))
                        else:
                            formatted_args.append(arg.get("description", str(arg.get("value", ""))))
                    if formatted_args:
                        log_entry["text"] = " ".join(formatted_args)

                self.console_logs.append(log_entry)
            except Exception as e:
                logger.error(f"Error handling console message: {e}")

        # Subscribe to Console.messageAdded events
        self.tab.Console.messageAdded = console_message_handler

        # Also set up Runtime.consoleAPICalled listener (more reliable)
        def console_api_handler(method, **kwargs):
            """Handle Runtime.consoleAPICalled events"""
            try:
                log_type = kwargs.get("type", "log")
                args = kwargs.get("args", [])
                timestamp = kwargs.get("timestamp", 0)

                # Format arguments
                formatted_messages = []
                for arg in args:
                    if arg.get("type") == "string":
                        formatted_messages.append(arg.get("value", ""))
                    elif arg.get("type") in ["number", "boolean"]:
                        formatted_messages.append(str(arg.get("value", "")))
                    elif arg.get("type") == "undefined":
                        formatted_messages.append("undefined")
                    elif arg.get("type") == "object":
                        if arg.get("subtype") == "null":
                            formatted_messages.append("null")
                        else:
                            formatted_messages.append(arg.get("description", "[object]"))
                    else:
                        formatted_messages.append(arg.get("description", str(arg.get("value", ""))))

                log_entry = {
                    "type": log_type,
                    "message": " ".join(formatted_messages),
                    "timestamp": timestamp,
                    "source": "console-api"
                }

                self.console_logs.append(log_entry)
            except Exception as e:
                logger.error(f"Error handling console API call: {e}")

        # Subscribe to Runtime.consoleAPICalled
        self.tab.set_listener("Runtime.consoleAPICalled", console_api_handler)

        # Also capture exceptions
        def exception_handler(method, **kwargs):
            """Handle Runtime.exceptionThrown events"""
            try:
                exception_details = kwargs.get("exceptionDetails", {})
                exception = exception_details.get("exception", {})
                text = exception_details.get("text", "Exception")
                description = exception.get("description", text)

                log_entry = {
                    "type": "error",
                    "message": description,
                    "timestamp": exception_details.get("timestamp", 0),
                    "source": "exception",
                    "url": exception_details.get("url", ""),
                    "lineNumber": exception_details.get("lineNumber", 0),
                    "columnNumber": exception_details.get("columnNumber", 0)
                }

                self.console_logs.append(log_entry)
            except Exception as e:
                logger.error(f"Error handling exception: {e}")

        self.tab.set_listener("Runtime.exceptionThrown", exception_handler)

    async def _initialize_js_console_interceptor(self):
        """Initialize JavaScript console interceptor as backup"""
        try:
            js_code = """
            (function() {
                if (window.__consoleInterceptorInstalled) {
                    return {success: true, message: 'Interceptor already installed'};
                }

                window.__consoleHistory = window.__consoleHistory || [];
                window.__consoleInterceptorInstalled = true;

                // Intercept console methods
                ['log', 'warn', 'error', 'info', 'debug'].forEach(function(method) {
                    const original = console[method];
                    console[method] = function(...args) {
                        window.__consoleHistory.push({
                            type: method,
                            message: args.map(a => {
                                try {
                                    return typeof a === 'object' ? JSON.stringify(a) : String(a);
                                } catch(e) {
                                    return String(a);
                                }
                            }).join(' '),
                            timestamp: new Date().toISOString()
                        });
                        original.apply(console, args);
                    };
                });

                return {success: true, message: 'Console interceptor installed'};
            })()
            """
            result = self.tab.Runtime.evaluate(expression=js_code, returnByValue=True)
            return result.get('result', {}).get('value', {})
        except Exception as e:
            logger.error(f"Failed to initialize JS console interceptor: {e}")
            return {"success": False, "error": str(e)}

    async def close(self):
        """Close connection to browser"""
        try:
            if self.tab:
                self.tab.stop()
        except:
            pass
