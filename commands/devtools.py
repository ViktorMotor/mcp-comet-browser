"""DevTools commands: console, network, element inspection"""
from typing import Dict, Any, Optional
from .base import Command


class OpenDevtoolsCommand(Command):
    """Open DevTools (F12)"""

    name = "open_devtools"
    description = "Open DevTools (F12) in the browser"
    input_schema = {
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

    name = "close_devtools"
    description = "Close DevTools in the browser"
    input_schema = {
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

    name = "console_command"
    description = "Execute a command in the DevTools console and get the result"
    input_schema = {
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

    name = "get_console_logs"
    description = """Get console logs from the browser.

Auto-redirects to save_page_info() due to Claude Code output limitations.
After calling this, use Read('./page_info.json') to see console logs."""
    input_schema = {
        "type": "object",
        "properties": {
            "clear": {"type": "boolean", "description": "Clear logs after retrieving", "default": False}
        }
    }

    requires_console_logs = True

    async def execute(self, clear: bool = False, **kwargs) -> Dict[str, Any]:
        """Auto-redirect to save_page_info (workaround for MCP output issue)"""
        import json
        import os

        try:
            # Call save_page_info logic inline
            js_code = """
            (function() {
                // Get all interactive elements
                const selector = 'button, a, input, select, textarea, [role="button"], [role="tab"], [onclick]';
                const elements = Array.from(document.querySelectorAll(selector));

                const interactive = elements
                    .filter(el => {
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        return rect.width > 0 && rect.height > 0 &&
                               el.offsetParent !== null &&
                               style.visibility !== 'hidden';
                    })
                    .map(el => {
                        const rect = el.getBoundingClientRect();
                        return {
                            tag: el.tagName.toLowerCase(),
                            type: el.type || el.getAttribute('role') || 'unknown',
                            text: el.textContent.trim().substring(0, 100),
                            id: el.id || null,
                            className: el.className || null,
                            position: {
                                x: Math.round(rect.left + rect.width/2),
                                y: Math.round(rect.top + rect.height/2),
                                width: Math.round(rect.width),
                                height: Math.round(rect.height)
                            }
                        };
                    });

                // Get console logs
                const consoleLogs = window.__consoleHistory || [];

                // Get network info
                const networkEntries = performance.getEntriesByType('resource') || [];

                return {
                    url: window.location.href,
                    title: document.title,
                    interactive_elements: interactive,
                    console: {
                        logs: consoleLogs.slice(-10),
                        total: consoleLogs.length
                    },
                    network: {
                        total_requests: networkEntries.length,
                        failed: networkEntries.filter(e => e.transferSize === 0).length
                    },
                    summary: {
                        total_interactive: interactive.length,
                        buttons: interactive.filter(e => e.tag === 'button').length,
                        links: interactive.filter(e => e.tag === 'a').length
                    }
                };
            })()
            """

            result = self.tab.Runtime.evaluate(expression=js_code, returnByValue=True)
            page_data = result.get('result', {}).get('value', {})

            # Save to file
            output_file = "./page_info.json"
            os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(page_data, f, indent=2, ensure_ascii=False)

            return {
                "success": True,
                "message": f"✅ Data saved to {output_file}",
                "instruction": "Use Read('./page_info.json') to see console logs and page data",
                "redirect_reason": "get_console_logs returns no visible output in Claude Code",
                "data_preview": {
                    "console_logs": len(page_data.get('console', {}).get('logs', [])),
                    "total_elements": len(page_data.get('interactive_elements', [])),
                    "file_path": output_file
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to save page info: {str(e)}"
            }


class InspectElementCommand(Command):
    """Inspect element like DevTools"""

    name = "inspect_element"
    description = "Inspect an element like DevTools inspector (get HTML, attributes, styles, position)"
    input_schema = {
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

    name = "get_network_activity"
    description = "Get network activity like DevTools Network panel (resources, timings, sizes)"
    input_schema = {
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
