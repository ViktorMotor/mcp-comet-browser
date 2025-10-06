"""DevTools commands: console, network, element inspection"""
from typing import Dict, Any, Optional
from .base import Command


class OpenDevtoolsCommand(Command):
    """Open DevTools (F12)"""

    @property
    def name(self) -> str:
        return "open_devtools"

    @property
    def description(self) -> str:
        return "Open DevTools (F12) in the browser"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    async def execute(self) -> Dict[str, Any]:
        """Send F12 keyboard event"""
        try:
            js_code = """
            (function() {
                if (window.chrome && window.chrome.devtools) {
                    return {success: true, message: 'DevTools already open'};
                }
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
            self.tab.Runtime.evaluate(expression=js_code, returnByValue=True)
            return {
                "success": True,
                "message": "DevTools opened (F12). Note: UI may not show via CDP, but debugging is active.",
                "tip": "DevTools functionality is available through console_command and get_console_logs"
            }
        except Exception as e:
            raise RuntimeError(f"Failed to open DevTools: {str(e)}")


class CloseDevtoolsCommand(Command):
    """Close DevTools"""

    @property
    def name(self) -> str:
        return "close_devtools"

    @property
    def description(self) -> str:
        return "Close DevTools in the browser"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    async def execute(self) -> Dict[str, Any]:
        """Send F12 keyboard event to toggle close"""
        try:
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
            self.tab.Runtime.evaluate(expression=js_code, returnByValue=True)
            return {"success": True, "message": "DevTools closed (F12)"}
        except Exception as e:
            raise RuntimeError(f"Failed to close DevTools: {str(e)}")


class ConsoleCommandCommand(Command):
    """Execute console command"""

    @property
    def name(self) -> str:
        return "console_command"

    @property
    def description(self) -> str:
        return "Execute a command in the DevTools console and get the result"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Console command to execute"}
            },
            "required": ["command"]
        }

    async def execute(self, command: str) -> Dict[str, Any]:
        """Execute command in console context"""
        try:
            # First try with returnByValue=True
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

            if result_type == 'undefined':
                return {"success": True, "result": None, "type": "undefined"}
            elif result_type == 'object' and result_obj.get('subtype') == 'null':
                return {"success": True, "result": None, "type": "null"}
            elif result_obj.get('objectId'):
                description = result_obj.get('description', str(result_value))
                return {
                    "success": True,
                    "result": description,
                    "type": result_type,
                    "objectId": result_obj.get('objectId')
                }
            else:
                return {"success": True, "result": result_value, "type": result_type}
        except Exception as e:
            error_msg = str(e)
            # If "reference chain is too long", try to get string representation
            if "reference chain is too long" in error_msg.lower() or "object reference chain" in error_msg.lower():
                try:
                    # Wrap in JSON.stringify or toString
                    wrapped_command = f"""
                    (function() {{
                        const result = {command};
                        if (typeof result === 'object' && result !== null) {{
                            try {{
                                return JSON.stringify(result, null, 2);
                            }} catch (e) {{
                                return String(result);
                            }}
                        }}
                        return result;
                    }})()
                    """
                    retry_result = self.tab.Runtime.evaluate(
                        expression=wrapped_command,
                        returnByValue=True,
                        awaitPromise=True
                    )

                    retry_obj = retry_result.get('result', {})
                    return {
                        "success": True,
                        "result": retry_obj.get('value'),
                        "type": retry_obj.get('type'),
                        "note": "Converted to string due to complex object structure"
                    }
                except:
                    pass

            raise RuntimeError(f"Failed to execute console command: {error_msg}")


class GetConsoleLogsCommand(Command):
    """Retrieve console logs"""

    @property
    def name(self) -> str:
        return "get_console_logs"

    @property
    def description(self) -> str:
        return "⚠️ NO OUTPUT: Use save_page_info() instead - includes last 10 console logs"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "clear": {"type": "boolean", "description": "Clear logs after retrieving", "default": False}
            }
        }

    async def execute(self, clear: bool = False, console_logs=None) -> Dict[str, Any]:
        """Get console logs from CDP and JS interceptor"""
        try:
            # Get logs from CDP listeners
            cdp_logs = console_logs.copy() if console_logs else []

            # Get logs from JS interceptor
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

            # Combine sources
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

            # Sort by timestamp
            try:
                all_logs.sort(key=lambda x: x.get("timestamp", 0))
            except:
                pass

            # Clear logs if requested
            if clear:
                if console_logs:
                    console_logs.clear()
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


class InspectElementCommand(Command):
    """Inspect element like DevTools"""

    @property
    def name(self) -> str:
        return "inspect_element"

    @property
    def description(self) -> str:
        return "Inspect an element like DevTools inspector (get HTML, attributes, styles, position)"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector of element to inspect"}
            },
            "required": ["selector"]
        }

    async def execute(self, selector: str) -> Dict[str, Any]:
        """Inspect element properties, styles, and position"""
        try:
            # Try to find element using JS first (supports more complex selectors)
            # Escape single quotes in selector for JS string
            selector_escaped = selector.replace("'", "\\'")

            js_find_code = f"""
            (function() {{
                let el = null;

                // Try direct querySelector first
                try {{
                    el = document.querySelector('{selector_escaped}');
                }} catch(e) {{
                    // Selector might not be valid CSS
                }}

                // If selector contains :has-text or similar pseudo-selectors
                if (!el && '{selector}'.includes('has-text')) {{
                    // Extract text from selector like button:has-text("Тестирование")
                    const textMatch = '{selector}'.match(/has-text\\(["']([^"']+)["']\\)/);
                    if (textMatch) {{
                        const searchText = textMatch[1];
                        const tagMatch = '{selector}'.match(/^([a-z]+):/);
                        const tag = tagMatch ? tagMatch[1] : '*';

                        const elements = Array.from(document.querySelectorAll(tag));
                        el = elements.find(e => e.textContent.includes(searchText));
                    }}
                }}

                if (!el) {{
                    return {{success: false, message: 'Element not found: {selector}'}};
                }}

                const styles = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();

                return {{
                    success: true,
                    tagName: el.tagName,
                    id: el.id,
                    className: el.className,
                    textContent: el.textContent.trim().substring(0, 200),
                    outerHTML: el.outerHTML.substring(0, 1000),
                    attributes: Array.from(el.attributes).map(a => ({{name: a.name, value: a.value}})),
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
                        fontFamily: styles.fontFamily,
                        visibility: styles.visibility,
                        opacity: styles.opacity
                    }}
                }};
            }})()
            """

            js_result = self.tab.Runtime.evaluate(expression=js_find_code, returnByValue=True)
            result = js_result.get('result', {}).get('value', {})

            if not result.get('success'):
                return {
                    "success": False,
                    "message": result.get('message', f"Element not found: {selector}")
                }

            return {
                "success": True,
                "selector": selector,
                "tagName": result.get('tagName'),
                "id": result.get('id'),
                "className": result.get('className'),
                "textContent": result.get('textContent'),
                "html": result.get('outerHTML'),
                "attributes": result.get('attributes', []),
                "position": result.get('position'),
                "styles": result.get('styles')
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to inspect element: {str(e)}"
            }


class GetNetworkActivityCommand(Command):
    """Get network activity"""

    @property
    def name(self) -> str:
        return "get_network_activity"

    @property
    def description(self) -> str:
        return "Get network activity like DevTools Network panel (resources, timings, sizes)"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    async def execute(self) -> Dict[str, Any]:
        """Get network activity using Performance API"""
        try:
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
