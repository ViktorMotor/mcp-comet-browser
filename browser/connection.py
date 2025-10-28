"""Browser connection management via Chrome DevTools Protocol"""
import sys
import os
import asyncio
from typing import Optional
import pychrome
from .cursor import AICursor
from .async_cdp import AsyncCDP
from mcp.logging_config import get_logger
from mcp.errors import ConnectionError as MCPConnectionError, TabStoppedError, BrowserError

logger = get_logger("browser.connection")

# Monkey-patch websocket library to disable proxy for CDP connections
# This fixes WebSocketProxyException: failed CONNECT via proxy status: 502
import websocket
_original_create_connection = websocket.create_connection

def _create_connection_no_proxy(url, **options):
    """Wrapper that disables proxy for WebSocket connections and enables keep-alive"""
    # Temporarily clear proxy environment variables
    proxy_vars = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
                  'ALL_PROXY', 'all_proxy']
    saved_env = {}

    try:
        # Save and clear proxy variables
        for var in proxy_vars:
            if var in os.environ:
                saved_env[var] = os.environ[var]
                del os.environ[var]

        # Force disable proxy in options
        options['http_proxy_host'] = None
        options['http_proxy_port'] = None
        options['proxy_type'] = None

        # STABILITY FIX (v3.0.0): Enable WebSocket keep-alive (ping/pong)
        # Prevents idle timeout disconnections. Reduced intervals for better stability.
        options['ping_interval'] = 20      # Send ping every 20 seconds (reduced from 30)
        options['ping_timeout'] = 10       # Wait for pong 10 seconds
        options['enable_multithread'] = True

        return _original_create_connection(url, **options)
    finally:
        # Restore proxy variables
        for var, value in saved_env.items():
            os.environ[var] = value

websocket.create_connection = _create_connection_no_proxy
logger.debug("WebSocket proxy disabled for CDP connections")

# Monkey-patch pychrome.Browser.list_tab to rewrite WebSocket URLs
_original_list_tab = pychrome.Browser.list_tab

def _list_tab_with_url_rewrite(self):
    """Wrapper that rewrites WebSocket URLs for WSL compatibility"""
    tabs = _original_list_tab(self)

    # Get proxy host from browser URL (e.g., http://172.23.128.1:9224)
    if hasattr(self, 'dev_url'):
        import re
        match = re.search(r'http://([^:]+):(\d+)', self.dev_url)
        if match:
            proxy_host = match.group(1)
            proxy_port = match.group(2)

            # Rewrite WebSocket URLs in each tab
            for tab in tabs:
                if hasattr(tab, '_websocket_url'):
                    # Replace ws://127.0.0.1:9222/ with ws://PROXY_HOST:PROXY_PORT/
                    original_ws = tab._websocket_url
                    tab._websocket_url = re.sub(
                        r'ws://127\.0\.0\.1:9222/',
                        f'ws://{proxy_host}:{proxy_port}/',
                        original_ws
                    )
                    if tab._websocket_url != original_ws:
                        logger.debug(f"Rewrote WebSocket URL: {original_ws} → {tab._websocket_url}")

    return tabs

pychrome.Browser.list_tab = _list_tab_with_url_rewrite
logger.debug("pychrome.Browser.list_tab monkey-patched for WebSocket URL rewriting")


class BrowserConnection:
    """Manages connection to Comet browser via CDP"""

    def __init__(self, debug_port = 9224, debug_host: str = None):
        """Initialize browser connection

        Args:
            debug_port: CDP debug port (default 9224 for Windows proxy)
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
                except (FileNotFoundError, PermissionError, IOError):
                    # Not in WSL or can't read resolv.conf - fallback to localhost
                    logger.debug("Could not read /etc/resolv.conf, using localhost")

            self.debug_host = debug_host or "127.0.0.1"
        self.browser: Optional[pychrome.Browser] = None
        self.tab: Optional[pychrome.Tab] = None
        self.cdp: Optional[AsyncCDP] = None  # Async CDP wrapper
        self.console_logs = []  # Store console logs from CDP events
        self.cursor: Optional[AICursor] = None

        # STABILITY FIX: Background health check
        self._health_check_running = False
        self._health_check_task: Optional[asyncio.Task] = None
        self._consecutive_failures = 0

    async def ensure_connected(self):
        """Ensure we have a valid connection to a browser tab"""
        try:
            # Test if current tab is still alive
            if self.cdp:
                try:
                    # Try a simple command to check if tab is responsive (use AsyncCDP for thread-safety)
                    await self.cdp.evaluate(expression="1+1", timeout=5)
                    return True
                except Exception as e:
                    # Tab is dead, need to reconnect
                    logger.warning(f"Tab connection lost: {str(e)}, reconnecting...")
                    try:
                        self.tab.stop()
                    except Exception as stop_error:
                        logger.debug(f"Failed to stop tab: {stop_error}")
                    self.tab = None

            # Reconnect to browser
            await self.connect()
            return True
        except MCPConnectionError:
            # Re-raise our typed errors
            raise
        except Exception as e:
            raise MCPConnectionError(f"Failed to ensure connection: {str(e)}")

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

            # Start the tab - WebSocket should work now (proxy rewrites URLs and proxies WebSocket)
            try:
                self.tab.start()
                logger.info(f"Connected to {self.debug_host}:{self.debug_port} via WebSocket")
            except Exception as e:
                logger.error(f"Failed to start tab: {e}")
                raise

            # Enable necessary domains
            self.tab.Page.enable()
            self.tab.DOM.enable()
            self.tab.Runtime.enable()
            self.tab.Console.enable()
            self.tab.Network.enable()
            self.tab.Debugger.enable()

            logger.debug("CDP domains enabled")

            # Set up console message listeners
            self._setup_console_listeners()

            # Initialize JavaScript console interceptor as backup
            await self._initialize_js_console_interceptor()

            # Initialize AsyncCDP wrapper
            self.cdp = AsyncCDP(self.tab, timeout=30.0)
            logger.debug("AsyncCDP wrapper initialized")

            # Initialize AI cursor
            self.cursor = AICursor(self.tab)
            await self.cursor.initialize()

            # STABILITY FIX: Start background health check loop
            # Stop existing task if any (reconnection scenario)
            if self._health_check_task:
                self._health_check_running = False
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass

            # Start new health check task
            self._health_check_running = True
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            logger.debug("Background health check started")

            return True
        except MCPConnectionError:
            # Re-raise our typed errors
            raise
        except Exception as e:
            # Use the browser_url for better error message
            browser_url = self.debug_url or f"http://{self.debug_host}:{self.debug_port}"
            raise MCPConnectionError(
                f"Failed to connect to browser at {browser_url}: {str(e)}",
                host=self.debug_host,
                port=self.debug_port
            )

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
        def console_api_handler(**kwargs):
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
        def exception_handler(**kwargs):
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

    async def _health_check_loop(self):
        """Background task that monitors connection health and auto-reconnects (v3.0.0: 30s interval)"""
        logger.info("Health check loop started (interval: 30s, reduced from 45s for better stability)")

        while self._health_check_running:
            try:
                # Wait before next check (v3.0.0: reduced from 45s to 30s)
                await asyncio.sleep(30)

                # Check if connection is alive with simple evaluation
                if self.cdp:
                    try:
                        # Use AsyncCDP wrapper for thread-safe evaluation
                        await self.cdp.evaluate(expression="1+1", timeout=5)
                        # Success - reset failure counter
                        if self._consecutive_failures > 0:
                            logger.info("Connection recovered after health check")
                            self._consecutive_failures = 0
                    except Exception as e:
                        # Health check failed
                        self._consecutive_failures += 1
                        logger.warning(
                            f"Health check failed ({self._consecutive_failures} consecutive): {e}"
                        )

                        # Calculate exponential backoff (max 60 seconds)
                        backoff = min(60, 2 ** self._consecutive_failures)
                        logger.info(f"Waiting {backoff}s before reconnection attempt...")
                        await asyncio.sleep(backoff)

                        # Attempt reconnection
                        try:
                            logger.info("Attempting automatic reconnection...")
                            await self.connect()
                            logger.info("✓ Automatic reconnection successful")
                            self._consecutive_failures = 0
                        except Exception as reconnect_error:
                            logger.error(f"✗ Automatic reconnection failed: {reconnect_error}")

            except asyncio.CancelledError:
                # Task was cancelled (normal shutdown)
                logger.debug("Health check loop cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in health check loop: {e}")
                # Continue running even if there's an error
                await asyncio.sleep(10)

        logger.info("Health check loop stopped")

    async def close(self):
        """Close connection to browser"""
        try:
            # Stop health check loop first
            if self._health_check_task:
                self._health_check_running = False
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
                self._health_check_task = None
                logger.debug("Health check loop stopped")

            # Shutdown AsyncCDP executor
            if self.cdp:
                await self.cdp.close()

            if self.tab:
                self.tab.stop()
        except Exception as e:
            logger.debug(f"Error stopping tab during close: {e}")
