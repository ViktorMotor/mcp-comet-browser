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
        self.console_logs = []  # Store console logs from CDP events

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
                    import sys
                    print(f"Tab connection lost: {str(e)}, reconnecting...", file=sys.stderr)
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
            self.tab.Console.enable()  # Enable console for logs
            self.tab.Network.enable()  # Enable network monitoring
            self.tab.Debugger.enable()  # Enable debugger

            # Set up console message listener via CDP
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
                    print(f"Error handling console message: {e}", file=sys.stderr)

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
                    print(f"Error handling console API call: {e}", file=sys.stderr)

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
                    print(f"Error handling exception: {e}", file=sys.stderr)

            self.tab.set_listener("Runtime.exceptionThrown", exception_handler)

            # Initialize JavaScript interceptor as backup
            await self._initialize_js_console_interceptor()

            # Initialize AI cursor visualization
            await self._initialize_ai_cursor()

            return True
        except Exception as e:
            raise ConnectionError(f"Failed to connect to browser on port {self.debug_port}: {str(e)}")

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
            print(f"Failed to initialize JS console interceptor: {e}", file=sys.stderr)
            return {"success": False, "error": str(e)}

    async def _initialize_ai_cursor(self):
        """Initialize visual AI cursor overlay"""
        try:
            js_code = """
            (function() {
                if (window.__aiCursorInitialized) {
                    return {success: true, message: 'AI cursor already initialized'};
                }

                // Create cursor element
                const cursor = document.createElement('div');
                cursor.id = '__ai_cursor__';
                cursor.style.cssText = `
                    position: fixed;
                    width: 24px;
                    height: 24px;
                    border-radius: 50%;
                    background: radial-gradient(circle, rgba(59, 130, 246, 0.8) 0%, rgba(37, 99, 235, 0.6) 50%, rgba(29, 78, 216, 0.4) 100%);
                    border: 2px solid rgba(59, 130, 246, 1);
                    box-shadow: 0 0 20px rgba(59, 130, 246, 0.8), 0 0 40px rgba(59, 130, 246, 0.4);
                    pointer-events: none;
                    z-index: 2147483647;
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                    display: none;
                `;

                // Add pulse animation
                const style = document.createElement('style');
                style.textContent = `
                    @keyframes __ai_cursor_pulse__ {
                        0%, 100% {
                            transform: scale(1);
                            opacity: 1;
                        }
                        50% {
                            transform: scale(1.2);
                            opacity: 0.8;
                        }
                    }
                    @keyframes __ai_cursor_click__ {
                        0% {
                            transform: scale(1);
                        }
                        50% {
                            transform: scale(0.8);
                        }
                        100% {
                            transform: scale(1);
                        }
                    }
                    #__ai_cursor__.clicking {
                        animation: __ai_cursor_click__ 0.3s ease;
                        background: radial-gradient(circle, rgba(34, 197, 94, 0.9) 0%, rgba(22, 163, 74, 0.7) 50%, rgba(21, 128, 61, 0.5) 100%);
                        border-color: rgba(34, 197, 94, 1);
                        box-shadow: 0 0 25px rgba(34, 197, 94, 0.9), 0 0 50px rgba(34, 197, 94, 0.5);
                    }
                `;

                document.head.appendChild(style);
                document.body.appendChild(cursor);

                // Store cursor reference
                window.__aiCursor__ = cursor;
                window.__aiCursorInitialized = true;

                // Helper function to move cursor
                window.__moveAICursor__ = function(x, y, duration = 300) {
                    cursor.style.display = 'block';
                    cursor.style.left = (x - 12) + 'px';
                    cursor.style.top = (y - 12) + 'px';
                    cursor.style.transition = `all ${duration}ms cubic-bezier(0.4, 0, 0.2, 1)`;
                };

                // Helper function to show click animation
                window.__clickAICursor__ = function() {
                    cursor.classList.add('clicking');
                    setTimeout(() => cursor.classList.remove('clicking'), 300);
                };

                // Helper function to hide cursor
                window.__hideAICursor__ = function() {
                    cursor.style.display = 'none';
                };

                return {success: true, message: 'AI cursor initialized'};
            })()
            """
            result = self.tab.Runtime.evaluate(expression=js_code, returnByValue=True)
            return result.get('result', {}).get('value', {})
        except Exception as e:
            print(f"Failed to initialize AI cursor: {e}", file=sys.stderr)
            return {"success": False, "error": str(e)}

    async def open_url(self, url: str) -> Dict[str, Any]:
        """Open a URL in the browser"""
        try:
            await self.ensure_connected()
            self.tab.Page.navigate(url=url, _timeout=30)
            # Wait for page load
            await asyncio.sleep(2)

            # Re-initialize cursor after page load (page navigation clears it)
            await self._initialize_ai_cursor()

            return {"success": True, "url": url, "message": f"Opened {url}"}
        except Exception as e:
            raise RuntimeError(f"Failed to open URL: {str(e)}")

    async def get_text(self, selector: str) -> Dict[str, Any]:
        """Get text content from elements matching CSS selector"""
        try:
            await self.ensure_connected()
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

    async def click(self, selector: str, show_cursor: bool = True) -> Dict[str, Any]:
        """Click on an element matching CSS selector with optional cursor animation"""
        try:
            await self.ensure_connected()

            # Re-initialize cursor if needed (in case page was reloaded)
            await self._initialize_ai_cursor()

            # Enhanced click with multiple search strategies and cursor animation
            js_code = f"""
            (function() {{
                // Try multiple strategies to find the element
                let el = null;
                let strategy = '';

                // Strategy 1: Direct CSS selector
                el = document.querySelector('{selector}');
                if (el) strategy = 'css';

                // Strategy 2: XPath (if selector starts with //)
                if (!el && '{selector}'.startsWith('//')) {{
                    try {{
                        const result = document.evaluate('{selector}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                        el = result.singleNodeValue;
                        if (el) strategy = 'xpath';
                    }} catch(e) {{}}
                }}

                // Strategy 3: Text content search (if selector contains text)
                if (!el && ('{selector}'.includes('text') || '{selector}'.includes('содержит'))) {{
                    const textMatch = '{selector}'.match(/["']([^"']+)["']/);
                    if (textMatch) {{
                        const searchText = textMatch[1];
                        el = Array.from(document.querySelectorAll('button, a, [role="button"], [role="tab"], [onclick]'))
                            .find(e => e.textContent.trim() === searchText || e.textContent.includes(searchText));
                        if (el) strategy = 'text-exact';
                    }}
                }}

                // Strategy 4: Try common clickable patterns
                if (!el) {{
                    const patterns = [
                        'button:contains("{selector}")',
                        'a:contains("{selector}")',
                        '[role="button"]:contains("{selector}")',
                        '[role="tab"]:contains("{selector}")'
                    ];

                    // Manual contains implementation
                    const allClickable = document.querySelectorAll('button, a, [role="button"], [role="tab"], [onclick], input[type="button"], input[type="submit"]');
                    el = Array.from(allClickable).find(e =>
                        e.textContent.includes('{selector}') ||
                        e.getAttribute('aria-label')?.includes('{selector}') ||
                        e.title?.includes('{selector}')
                    );
                    if (el) strategy = 'text-contains';
                }}

                if (!el) {{
                    // Check if selector matches multiple elements
                    const allMatches = document.querySelectorAll('{selector}');
                    return {{
                        success: false,
                        reason: 'not_found',
                        message: 'Element not found: {selector}',
                        matchCount: allMatches.length,
                        suggestion: allMatches.length > 0 ? 'Selector matches ' + allMatches.length + ' elements' : 'Try using text content or XPath'
                    }};
                }}

                // Check if element is visible
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                const isVisible = rect.width > 0 && rect.height > 0 &&
                                 style.display !== 'none' &&
                                 style.visibility !== 'hidden' &&
                                 style.opacity !== '0';

                if (!isVisible) {{
                    return {{
                        success: false,
                        reason: 'not_visible',
                        message: 'Element found but not visible',
                        display: style.display,
                        visibility: style.visibility,
                        opacity: style.opacity,
                        dimensions: {{ width: rect.width, height: rect.height }},
                        suggestion: 'Element may be hidden or have zero dimensions'
                    }};
                }}

                // Check if element is in viewport
                const inViewport = rect.top >= 0 &&
                                  rect.left >= 0 &&
                                  rect.bottom <= window.innerHeight &&
                                  rect.right <= window.innerWidth;

                // Scroll element into view if not in viewport
                if (!inViewport) {{
                    el.scrollIntoView({{ behavior: 'smooth', block: 'center', inline: 'center' }});
                    // Wait a bit for scroll
                    await new Promise(r => setTimeout(r, 300));
                    // Recalculate position after scroll
                    const newRect = el.getBoundingClientRect();
                    rect.top = newRect.top;
                    rect.left = newRect.left;
                }}

                // Calculate click position (center of element)
                const clickX = rect.left + rect.width / 2;
                const clickY = rect.top + rect.height / 2;

                // Animate cursor to element if requested
                const showCursor = {str(show_cursor).lower()};
                if (showCursor && window.__moveAICursor__) {{
                    window.__moveAICursor__(clickX, clickY, 400);
                }}

                // Wait for cursor animation, then click
                return new Promise((resolve) => {{
                    setTimeout(() => {{
                        try {{
                            // Show click animation
                            if (showCursor && window.__clickAICursor__) {{
                                window.__clickAICursor__();
                            }}

                            // Try multiple click methods for maximum compatibility
                            let clickSuccess = false;

                            // Method 1: Standard click
                            try {{
                                el.click();
                                clickSuccess = true;
                            }} catch (e1) {{
                                console.warn('Standard click failed:', e1);
                            }}

                            // Method 2: MouseEvent sequence (for React/Vue apps)
                            if (!clickSuccess || true) {{ // Always try for reliability
                                try {{
                                    ['mousedown', 'mouseup', 'click'].forEach(eventType => {{
                                        const event = new MouseEvent(eventType, {{
                                            view: window,
                                            bubbles: true,
                                            cancelable: true,
                                            clientX: clickX,
                                            clientY: clickY
                                        }});
                                        el.dispatchEvent(event);
                                    }});
                                    clickSuccess = true;
                                }} catch (e2) {{
                                    console.warn('MouseEvent click failed:', e2);
                                }}
                            }}

                            // Method 3: Focus and trigger (for form elements)
                            if (el.tagName === 'BUTTON' || el.tagName === 'INPUT' || el.tagName === 'A') {{
                                try {{
                                    el.focus();
                                    if (el.onclick) {{
                                        el.onclick.call(el);
                                    }}
                                }} catch (e3) {{
                                    console.warn('Focus/trigger click failed:', e3);
                                }}
                            }}

                            resolve({{
                                success: true,
                                selector: '{selector}',
                                strategy: strategy,
                                message: 'Clicked element using strategy: ' + strategy,
                                cursorAnimated: showCursor,
                                cursorVisible: window.__aiCursor__ && window.__aiCursor__.style.display !== 'none',
                                elementInfo: {{
                                    tagName: el.tagName,
                                    id: el.id,
                                    className: el.className,
                                    text: el.textContent.trim().substring(0, 100),
                                    position: {{
                                        top: rect.top,
                                        left: rect.left,
                                        width: rect.width,
                                        height: rect.height,
                                        clickX: clickX,
                                        clickY: clickY
                                    }},
                                    inViewport: inViewport
                                }}
                            }});
                        }} catch (clickError) {{
                            resolve({{
                                success: false,
                                reason: 'click_failed',
                                message: 'All click methods failed: ' + clickError.message,
                                error: clickError.toString()
                            }});
                        }}
                    }}, showCursor ? 450 : 0);
                }});
            }})()
            """

            result = self.tab.Runtime.evaluate(expression=js_code, returnByValue=True, awaitPromise=True)
            click_result = result.get('result', {}).get('value', {})

            # Return the detailed result
            if click_result.get('success'):
                await asyncio.sleep(0.3)  # Brief wait after click

            return click_result
        except Exception as e:
            return {
                "success": False,
                "reason": "exception",
                "message": f"Failed to click element: {str(e)}",
                "error": str(e)
            }

    async def click_by_text(self, text: str, tag: str = None, exact: bool = False) -> Dict[str, Any]:
        """Click on an element by its text content (more reliable than CSS selectors)"""
        try:
            await self.ensure_connected()
            await self._initialize_ai_cursor()

            tag_filter = f", '{tag}'" if tag else ""
            match_method = "===" if exact else "includes"

            # Prepare tags list outside f-string to avoid backslash issue
            if tag:
                tags_js = f"['{tag}']"
            else:
                tags_js = "['button', 'a', '[role=\"button\"]', '[role=\"tab\"]', 'input[type=\"button\"]', 'input[type=\"submit\"]', '[onclick]']"

            js_code = f"""
            (function() {{
                // Find all potentially clickable elements
                const tags = {tags_js};
                const selector = tags.join(', ');
                const elements = Array.from(document.querySelectorAll(selector));

                // Search for element with matching text
                const searchText = '{text}';
                const el = elements.find(e =>
                    (e.textContent.trim() {match_method} searchText) ||
                    (e.getAttribute('aria-label') {match_method} searchText) ||
                    (e.title {match_method} searchText) ||
                    (e.value {match_method} searchText)
                );

                if (!el) {{
                    return {{
                        success: false,
                        message: 'Element with text not found: {text}',
                        searchedTags: tags,
                        totalElements: elements.length,
                        availableTexts: elements.slice(0, 10).map(e => e.textContent.trim().substring(0, 50))
                    }};
                }}

                // Get element position
                const rect = el.getBoundingClientRect();
                const clickX = rect.left + rect.width / 2;
                const clickY = rect.top + rect.height / 2;

                // Scroll into view if needed
                const inViewport = rect.top >= 0 && rect.left >= 0 &&
                                  rect.bottom <= window.innerHeight &&
                                  rect.right <= window.innerWidth;

                if (!inViewport) {{
                    el.scrollIntoView({{ behavior: 'smooth', block: 'center', inline: 'center' }});
                    await new Promise(r => setTimeout(r, 300));
                }}

                // Animate cursor
                if (window.__moveAICursor__) {{
                    window.__moveAICursor__(clickX, clickY, 400);
                }}

                // Wait and click
                return new Promise((resolve) => {{
                    setTimeout(() => {{
                        try {{
                            if (window.__clickAICursor__) {{
                                window.__clickAICursor__();
                            }}

                            // Multiple click methods
                            el.click();

                            ['mousedown', 'mouseup', 'click'].forEach(eventType => {{
                                const event = new MouseEvent(eventType, {{
                                    view: window,
                                    bubbles: true,
                                    cancelable: true,
                                    clientX: clickX,
                                    clientY: clickY
                                }});
                                el.dispatchEvent(event);
                            }});

                            resolve({{
                                success: true,
                                text: '{text}',
                                message: 'Clicked element with text: {text}',
                                cursorVisible: window.__aiCursor__ && window.__aiCursor__.style.display !== 'none',
                                element: {{
                                    tag: el.tagName,
                                    id: el.id,
                                    className: el.className,
                                    actualText: el.textContent.trim().substring(0, 100),
                                    position: {{ x: clickX, y: clickY }}
                                }}
                            }});
                        }} catch (e) {{
                            resolve({{
                                success: false,
                                message: 'Click failed: ' + e.message,
                                error: e.toString()
                            }});
                        }}
                    }}, 450);
                }});
            }})()
            """

            result = self.tab.Runtime.evaluate(expression=js_code, returnByValue=True, awaitPromise=True)
            return result.get('result', {}).get('value', {})
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to click by text: {str(e)}",
                "error": str(e)
            }

    async def move_cursor(self, x: int = None, y: int = None, selector: str = None, duration: int = 400) -> Dict[str, Any]:
        """Move the AI cursor to coordinates or element center"""
        try:
            await self.ensure_connected()

            if selector:
                # Move to element center
                js_code = f"""
                (function() {{
                    const el = document.querySelector('{selector}');
                    if (!el) {{
                        return {{
                            success: false,
                            message: 'Element not found: {selector}'
                        }};
                    }}

                    const rect = el.getBoundingClientRect();
                    const centerX = rect.left + rect.width / 2;
                    const centerY = rect.top + rect.height / 2;

                    if (window.__moveAICursor__) {{
                        window.__moveAICursor__(centerX, centerY, {duration});
                        return {{
                            success: true,
                            message: 'Cursor moved to element: {selector}',
                            position: {{
                                x: centerX,
                                y: centerY
                            }},
                            element: {{
                                tagName: el.tagName,
                                id: el.id,
                                className: el.className,
                                bounds: {{
                                    top: rect.top,
                                    left: rect.left,
                                    width: rect.width,
                                    height: rect.height
                                }}
                            }}
                        }};
                    }} else {{
                        return {{
                            success: false,
                            message: 'AI cursor not initialized'
                        }};
                    }}
                }})()
                """
            elif x is not None and y is not None:
                # Move to specific coordinates
                js_code = f"""
                (function() {{
                    if (window.__moveAICursor__) {{
                        window.__moveAICursor__({x}, {y}, {duration});
                        return {{
                            success: true,
                            message: 'Cursor moved to coordinates',
                            position: {{
                                x: {x},
                                y: {y}
                            }}
                        }};
                    }} else {{
                        return {{
                            success: false,
                            message: 'AI cursor not initialized'
                        }};
                    }}
                }})()
                """
            else:
                return {
                    "success": False,
                    "message": "Either provide x,y coordinates or selector"
                }

            result = self.tab.Runtime.evaluate(expression=js_code, returnByValue=True)
            return result.get('result', {}).get('value', {})
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to move cursor: {str(e)}",
                "error": str(e)
            }

    async def screenshot(self, path: str = "./screenshot.png") -> Dict[str, Any]:
        """Take a screenshot of the current page"""
        try:
            await self.ensure_connected()
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
            await self.ensure_connected()
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

    async def open_devtools(self) -> Dict[str, Any]:
        """Open DevTools (F12) in the browser"""
        try:
            await self.ensure_connected()
            # Use the browser API to open DevTools window
            # This sends a command to open the DevTools UI
            js_code = """
            (function() {
                // Try to open DevTools programmatically
                if (window.chrome && window.chrome.devtools) {
                    return {success: true, message: 'DevTools already open'};
                }
                // Alternative: use keyboard shortcut simulation
                const event = new KeyboardEvent('keydown', {
                    key: 'F12',
                    code: 'F12',
                    keyCode: 123,
                    which: 123,
                    bubbles: true
                });
                document.dispatchEvent(event);
                return {success: true, message: 'DevTools open command sent'};
            })()
            """

            result = self.tab.Runtime.evaluate(expression=js_code, returnByValue=True)

            return {
                "success": True,
                "message": "DevTools opened (F12). Note: UI may not show via CDP, but debugging is active.",
                "tip": "DevTools functionality is available through console_command and get_console_logs"
            }
        except Exception as e:
            raise RuntimeError(f"Failed to open DevTools: {str(e)}")

    async def close_devtools(self) -> Dict[str, Any]:
        """Close DevTools in the browser"""
        try:
            await self.ensure_connected()
            js_code = """
            (function() {
                const event = new KeyboardEvent('keydown', {
                    key: 'F12',
                    code: 'F12',
                    keyCode: 123,
                    which: 123,
                    bubbles: true
                });
                document.dispatchEvent(event);
                return {success: true, message: 'DevTools close command sent'};
            })()
            """

            result = self.tab.Runtime.evaluate(expression=js_code, returnByValue=True)

            return {"success": True, "message": "DevTools closed (F12)"}
        except Exception as e:
            raise RuntimeError(f"Failed to close DevTools: {str(e)}")

    async def console_command(self, command: str) -> Dict[str, Any]:
        """Execute a command in the DevTools console"""
        try:
            await self.ensure_connected()
            # Execute command in console context
            result = self.tab.Runtime.evaluate(
                expression=command,
                returnByValue=True,
                awaitPromise=True
            )

            if result.get('exceptionDetails'):
                error_text = result['exceptionDetails'].get('text', 'Unknown error')
                exception = result['exceptionDetails'].get('exception', {})
                error_description = exception.get('description', error_text)

                return {
                    "success": False,
                    "error": error_description,
                    "type": "exception"
                }

            result_obj = result.get('result', {})
            result_type = result_obj.get('type')
            result_value = result_obj.get('value')

            # Handle different result types
            if result_type == 'undefined':
                return {"success": True, "result": None, "type": "undefined"}
            elif result_type == 'object' and result_obj.get('subtype') == 'null':
                return {"success": True, "result": None, "type": "null"}
            elif result_obj.get('objectId'):
                # Complex object - get string representation
                description = result_obj.get('description', str(result_value))
                return {
                    "success": True,
                    "result": description,
                    "type": result_type,
                    "objectId": result_obj.get('objectId')
                }
            else:
                return {
                    "success": True,
                    "result": result_value,
                    "type": result_type
                }

        except Exception as e:
            raise RuntimeError(f"Failed to execute console command: {str(e)}")

    async def get_console_logs(self, clear: bool = False) -> Dict[str, Any]:
        """Get console logs from the browser (from CDP events and JS interceptor)"""
        try:
            await self.ensure_connected()

            # Get logs from CDP listeners (these are captured in real-time)
            cdp_logs = self.console_logs.copy()

            # Also get logs from JavaScript interceptor (backup for logs before CDP connection)
            js_code = """
            (function() {
                if (window.__consoleHistory) {
                    return window.__consoleHistory.slice();
                }
                return [];
            })()
            """

            result = self.tab.Runtime.evaluate(expression=js_code, returnByValue=True)
            js_logs = result.get('result', {}).get('value', [])

            # Combine both sources (CDP logs + JS interceptor logs)
            all_logs = []

            # Add CDP logs with unified format
            for log in cdp_logs:
                all_logs.append({
                    "type": log.get("type", "log"),
                    "message": log.get("message", log.get("text", "")),
                    "timestamp": log.get("timestamp", ""),
                    "source": log.get("source", "cdp"),
                    "url": log.get("url", ""),
                    "lineNumber": log.get("lineNumber", 0)
                })

            # Add JS interceptor logs
            for log in js_logs:
                all_logs.append({
                    "type": log.get("type", "log"),
                    "message": log.get("message", ""),
                    "timestamp": log.get("timestamp", ""),
                    "source": "js-interceptor"
                })

            # Sort by timestamp if available
            try:
                all_logs.sort(key=lambda x: x.get("timestamp", 0))
            except:
                pass  # If sorting fails, keep original order

            # Clear logs if requested
            if clear:
                self.console_logs.clear()
                # Clear JS interceptor logs
                clear_js = """
                (function() {
                    if (window.__consoleHistory) {
                        window.__consoleHistory = [];
                    }
                    return {cleared: true};
                })()
                """
                self.tab.Runtime.evaluate(expression=clear_js, returnByValue=True)

            return {
                "success": True,
                "logs": all_logs,
                "count": len(all_logs),
                "cdpCount": len(cdp_logs),
                "jsInterceptorCount": len(js_logs),
                "cleared": clear,
                "tip": "CDP listeners capture logs in real-time. If you see empty results, check if console logs occurred after MCP connection."
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to get console logs: {str(e)}"
            }

    async def inspect_element(self, selector: str) -> Dict[str, Any]:
        """Inspect an element (like DevTools inspector)"""
        try:
            await self.ensure_connected()
            # Get document root
            doc = self.tab.DOM.getDocument()
            root_node_id = doc['root']['nodeId']

            # Query selector
            node_result = self.tab.DOM.querySelector(nodeId=root_node_id, selector=selector)
            node_id = node_result.get('nodeId')

            if not node_id:
                return {"success": False, "message": f"Element not found: {selector}"}

            # Get element properties
            outer_html = self.tab.DOM.getOuterHTML(nodeId=node_id)
            attributes = self.tab.DOM.getAttributes(nodeId=node_id)

            # Get computed styles using JavaScript
            js_code = f"""
            (function() {{
                const el = document.querySelector('{selector}');
                if (!el) return null;

                const styles = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();

                return {{
                    tagName: el.tagName,
                    id: el.id,
                    className: el.className,
                    textContent: el.textContent.trim().substring(0, 200),
                    position: {{
                        top: rect.top,
                        left: rect.left,
                        width: rect.width,
                        height: rect.height
                    }},
                    styles: {{
                        display: styles.display,
                        position: styles.position,
                        color: styles.color,
                        backgroundColor: styles.backgroundColor,
                        fontSize: styles.fontSize,
                        fontFamily: styles.fontFamily
                    }}
                }};
            }})()
            """

            js_result = self.tab.Runtime.evaluate(expression=js_code, returnByValue=True)
            element_info = js_result.get('result', {}).get('value', {})

            return {
                "success": True,
                "selector": selector,
                "nodeId": node_id,
                "html": outer_html.get('outerHTML', ''),
                "attributes": attributes.get('attributes', []),
                "info": element_info
            }
        except Exception as e:
            raise RuntimeError(f"Failed to inspect element: {str(e)}")

    async def get_network_activity(self) -> Dict[str, Any]:
        """Get network activity (like DevTools Network panel)"""
        try:
            await self.ensure_connected()
            # Use JavaScript to access performance API
            js_code = """
            (function() {
                const resources = performance.getEntriesByType('resource');
                const navigation = performance.getEntriesByType('navigation')[0];

                return {
                    navigation: navigation ? {
                        url: navigation.name,
                        duration: navigation.duration,
                        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
                        loadComplete: navigation.loadEventEnd - navigation.loadEventStart
                    } : null,
                    resources: resources.slice(-50).map(r => ({
                        name: r.name,
                        type: r.initiatorType,
                        duration: r.duration,
                        size: r.transferSize || 0,
                        startTime: r.startTime
                    }))
                };
            })()
            """

            result = self.tab.Runtime.evaluate(expression=js_code, returnByValue=True)
            network_data = result.get('result', {}).get('value', {})

            return {
                "success": True,
                "navigation": network_data.get('navigation'),
                "resources": network_data.get('resources', []),
                "resourceCount": len(network_data.get('resources', []))
            }
        except Exception as e:
            raise RuntimeError(f"Failed to get network activity: {str(e)}")

    async def list_tabs(self) -> Dict[str, Any]:
        """List all open tabs in the browser"""
        try:
            tabs = self.browser.list_tab()

            tabs_info = []
            for tab in tabs:
                # Access tab properties as attributes
                tabs_info.append({
                    "id": getattr(tab, 'id', 'unknown'),
                    "url": getattr(tab, 'url', 'unknown'),
                    "title": getattr(tab, 'title', 'untitled'),
                    "type": getattr(tab, 'type', 'page')
                })

            return {
                "success": True,
                "tabs": tabs_info,
                "count": len(tabs_info),
                "currentTabId": getattr(self.tab, 'id', None) if self.tab else None
            }
        except Exception as e:
            raise RuntimeError(f"Failed to list tabs: {str(e)}")

    async def create_tab(self, url: str = None) -> Dict[str, Any]:
        """Create a new tab and optionally navigate to URL"""
        try:
            new_tab = self.browser.new_tab(url=url)

            return {
                "success": True,
                "tabId": getattr(new_tab, 'id', 'unknown'),
                "url": url or "about:blank",
                "message": f"Created new tab{' and opened ' + url if url else ''}"
            }
        except Exception as e:
            raise RuntimeError(f"Failed to create tab: {str(e)}")

    async def close_tab(self, tab_id: str = None) -> Dict[str, Any]:
        """Close a tab by ID (closes current tab if no ID provided)"""
        try:
            if tab_id is None:
                # Close current tab
                if self.tab:
                    tab_id = getattr(self.tab, 'id', None)
                    if not tab_id:
                        return {"success": False, "message": "Current tab has no ID"}
                else:
                    return {"success": False, "message": "No current tab to close"}

            # Find tab by ID
            tabs = self.browser.list_tab()
            tab_to_close = None
            for tab in tabs:
                if getattr(tab, 'id', None) == tab_id:
                    tab_to_close = tab
                    break

            if not tab_to_close:
                return {"success": False, "message": f"Tab not found: {tab_id}"}

            # Close the tab
            self.browser.close_tab(tab_to_close)

            # If we closed the current tab, clear reference
            if self.tab and getattr(self.tab, 'id', None) == tab_id:
                try:
                    self.tab.stop()
                except:
                    pass
                self.tab = None

            return {
                "success": True,
                "tabId": tab_id,
                "message": f"Closed tab: {tab_id}"
            }
        except Exception as e:
            raise RuntimeError(f"Failed to close tab: {str(e)}")

    async def switch_tab(self, tab_id: str) -> Dict[str, Any]:
        """Switch to a different tab by ID"""
        try:
            # Find tab by ID
            tabs = self.browser.list_tab()
            target_tab = None
            for tab in tabs:
                if getattr(tab, 'id', None) == tab_id:
                    target_tab = tab
                    break

            if not target_tab:
                return {"success": False, "message": f"Tab not found: {tab_id}"}

            # Stop current tab
            if self.tab:
                try:
                    self.tab.stop()
                except:
                    pass

            # Switch to new tab
            self.tab = target_tab
            self.tab.start()

            # Enable necessary domains
            self.tab.Page.enable()
            self.tab.DOM.enable()
            self.tab.Runtime.enable()
            self.tab.Console.enable()
            self.tab.Network.enable()
            self.tab.Debugger.enable()

            return {
                "success": True,
                "tabId": tab_id,
                "url": getattr(target_tab, 'url', 'unknown'),
                "title": getattr(target_tab, 'title', 'untitled'),
                "message": f"Switched to tab: {tab_id}"
            }
        except Exception as e:
            raise RuntimeError(f"Failed to switch tab: {str(e)}")

    async def scroll_page(self, direction: str = "down", amount: int = None, x: int = None, y: int = None, selector: str = None) -> Dict[str, Any]:
        """Scroll the page or a specific element"""
        try:
            await self.ensure_connected()

            # Build JavaScript code based on parameters
            if x is not None and y is not None:
                # Scroll to specific coordinates
                js_code = f"""
                (function() {{
                    window.scrollTo({x}, {y});
                    return {{
                        x: window.pageXOffset || window.scrollX,
                        y: window.pageYOffset || window.scrollY,
                        maxX: document.documentElement.scrollWidth - window.innerWidth,
                        maxY: document.documentElement.scrollHeight - window.innerHeight,
                        viewportHeight: window.innerHeight,
                        viewportWidth: window.innerWidth,
                        pageHeight: document.documentElement.scrollHeight,
                        pageWidth: document.documentElement.scrollWidth
                    }};
                }})()
                """
            elif selector:
                # Scroll specific element
                if amount is None:
                    amount = 300

                scroll_delta = amount if direction in ["down", "right"] else -amount
                scroll_property = "scrollTop" if direction in ["down", "up"] else "scrollLeft"

                js_code = f"""
                (function() {{
                    const el = document.querySelector('{selector}');
                    if (!el) return {{success: false, message: 'Element not found: {selector}'}};

                    el.{scroll_property} += {scroll_delta};

                    return {{
                        success: true,
                        element: '{selector}',
                        scrollTop: el.scrollTop,
                        scrollLeft: el.scrollLeft,
                        scrollHeight: el.scrollHeight,
                        scrollWidth: el.scrollWidth,
                        clientHeight: el.clientHeight,
                        clientWidth: el.clientWidth
                    }};
                }})()
                """
            else:
                # Scroll whole page by direction
                if amount is None:
                    amount = 500  # Default scroll amount in pixels

                if direction == "down":
                    scroll_expr = f"window.scrollBy(0, {amount})"
                elif direction == "up":
                    scroll_expr = f"window.scrollBy(0, -{amount})"
                elif direction == "left":
                    scroll_expr = f"window.scrollBy(-{amount}, 0)"
                elif direction == "right":
                    scroll_expr = f"window.scrollBy({amount}, 0)"
                elif direction == "top":
                    scroll_expr = "window.scrollTo(0, 0)"
                elif direction == "bottom":
                    scroll_expr = "window.scrollTo(0, document.documentElement.scrollHeight)"
                else:
                    return {"success": False, "message": f"Invalid direction: {direction}. Use: up, down, left, right, top, bottom"}

                js_code = f"""
                (function() {{
                    {scroll_expr};

                    return {{
                        x: window.pageXOffset || window.scrollX,
                        y: window.pageYOffset || window.scrollY,
                        maxX: document.documentElement.scrollWidth - window.innerWidth,
                        maxY: document.documentElement.scrollHeight - window.innerHeight,
                        viewportHeight: window.innerHeight,
                        viewportWidth: window.innerWidth,
                        pageHeight: document.documentElement.scrollHeight,
                        pageWidth: document.documentElement.scrollWidth,
                        scrolledToBottom: (window.innerHeight + window.pageYOffset) >= document.documentElement.scrollHeight - 10,
                        scrolledToTop: window.pageYOffset <= 10
                    }};
                }})()
                """

            result = self.tab.Runtime.evaluate(expression=js_code, returnByValue=True)
            scroll_info = result.get('result', {}).get('value', {})

            # Handle element-specific scroll result
            if selector and not scroll_info.get('success', True):
                return scroll_info

            return {
                "success": True,
                "direction": direction if not (x is not None and y is not None) else "absolute",
                "amount": amount,
                "selector": selector,
                "position": scroll_info,
                "message": f"Scrolled {'element ' + selector if selector else 'page'} {direction if not (x is not None and y is not None) else f'to ({x}, {y})'}"
            }
        except Exception as e:
            raise RuntimeError(f"Failed to scroll page: {str(e)}")

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
                    "description": "Click on an element matching a CSS selector. Supports XPath (//), text search, and ARIA attributes. Auto-scrolls to element and shows cursor animation.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector, XPath (//button), or text content"}
                        },
                        "required": ["selector"]
                    }
                },
                {
                    "name": "click_by_text",
                    "description": "Click on an element by its visible text content. More reliable than CSS selectors for buttons and links. Searches in textContent, aria-label, title, and value attributes.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "Text to search for (e.g. 'Тестирование', 'Submit', 'Next')"},
                            "tag": {"type": "string", "description": "Optional: limit search to specific tag (e.g. 'button', 'a')"},
                            "exact": {"type": "boolean", "description": "If true, match exact text; if false, match partial text (default: false)", "default": false}
                        },
                        "required": ["text"]
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
                },
                {
                    "name": "open_devtools",
                    "description": "Open DevTools (F12) in the browser",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "close_devtools",
                    "description": "Close DevTools in the browser",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "console_command",
                    "description": "Execute a command in the DevTools console and get the result",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Console command to execute (e.g., 'document.title', 'console.log(\"test\")')"}
                        },
                        "required": ["command"]
                    }
                },
                {
                    "name": "get_console_logs",
                    "description": "Get console logs from the browser (includes log, warn, error, info, debug)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "clear": {"type": "boolean", "description": "Clear logs after retrieving", "default": False}
                        }
                    }
                },
                {
                    "name": "inspect_element",
                    "description": "Inspect an element like DevTools inspector (get HTML, attributes, styles, position)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector of element to inspect"}
                        },
                        "required": ["selector"]
                    }
                },
                {
                    "name": "get_network_activity",
                    "description": "Get network activity like DevTools Network panel (resources, timings, sizes)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "list_tabs",
                    "description": "List all open tabs in the browser",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "create_tab",
                    "description": "Create a new tab and optionally navigate to a URL",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to open in new tab (optional)"}
                        }
                    }
                },
                {
                    "name": "close_tab",
                    "description": "Close a tab by ID (closes current tab if no ID provided)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "tab_id": {"type": "string", "description": "Tab ID to close (optional, defaults to current tab)"}
                        }
                    }
                },
                {
                    "name": "switch_tab",
                    "description": "Switch to a different tab by ID",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "tab_id": {"type": "string", "description": "Tab ID to switch to"}
                        },
                        "required": ["tab_id"]
                    }
                },
                {
                    "name": "scroll_page",
                    "description": "Scroll the page or a specific element. Returns detailed position information including viewport size, page dimensions, and scroll state.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "direction": {"type": "string", "description": "Scroll direction: 'up', 'down', 'left', 'right', 'top', 'bottom' (default: 'down')", "default": "down"},
                            "amount": {"type": "integer", "description": "Pixels to scroll (default: 500 for page, 300 for element)"},
                            "x": {"type": "integer", "description": "Absolute X coordinate to scroll to (use with y for absolute positioning)"},
                            "y": {"type": "integer", "description": "Absolute Y coordinate to scroll to (use with x for absolute positioning)"},
                            "selector": {"type": "string", "description": "CSS selector of element to scroll (scrolls page if omitted)"}
                        }
                    }
                },
                {
                    "name": "move_cursor",
                    "description": "Move the visual AI cursor to specific coordinates or element center. Useful for showing where the AI is focusing attention.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "integer", "description": "X coordinate to move cursor to"},
                            "y": {"type": "integer", "description": "Y coordinate to move cursor to"},
                            "selector": {"type": "string", "description": "CSS selector of element to move cursor to (center of element)"},
                            "duration": {"type": "integer", "description": "Animation duration in milliseconds (default: 400)", "default": 400}
                        }
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
        elif tool_name == 'click_by_text':
            text = arguments['text']
            tag = arguments.get('tag')
            exact = arguments.get('exact', False)
            return await self.comet.click_by_text(text, tag, exact)
        elif tool_name == 'screenshot':
            path = arguments.get('path', './screenshot.png')
            return await self.comet.screenshot(path)
        elif tool_name == 'evaluate_js':
            return await self.comet.evaluate_js(arguments['code'])
        elif tool_name == 'open_devtools':
            return await self.comet.open_devtools()
        elif tool_name == 'close_devtools':
            return await self.comet.close_devtools()
        elif tool_name == 'console_command':
            return await self.comet.console_command(arguments['command'])
        elif tool_name == 'get_console_logs':
            clear = arguments.get('clear', False)
            return await self.comet.get_console_logs(clear)
        elif tool_name == 'inspect_element':
            return await self.comet.inspect_element(arguments['selector'])
        elif tool_name == 'get_network_activity':
            return await self.comet.get_network_activity()
        elif tool_name == 'list_tabs':
            return await self.comet.list_tabs()
        elif tool_name == 'create_tab':
            url = arguments.get('url')
            return await self.comet.create_tab(url)
        elif tool_name == 'close_tab':
            tab_id = arguments.get('tab_id')
            return await self.comet.close_tab(tab_id)
        elif tool_name == 'switch_tab':
            return await self.comet.switch_tab(arguments['tab_id'])
        elif tool_name == 'scroll_page':
            direction = arguments.get('direction', 'down')
            amount = arguments.get('amount')
            x = arguments.get('x')
            y = arguments.get('y')
            selector = arguments.get('selector')
            return await self.comet.scroll_page(direction, amount, x, y, selector)
        elif tool_name == 'move_cursor':
            x = arguments.get('x')
            y = arguments.get('y')
            selector = arguments.get('selector')
            duration = arguments.get('duration', 400)
            return await self.comet.move_cursor(x, y, selector, duration)
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
