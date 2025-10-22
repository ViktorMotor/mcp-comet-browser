"""Diagnostic commands for troubleshooting"""
from typing import Dict, Any
from .base import Command
from .registry import register
from mcp.logging_config import get_logger

logger = get_logger("commands.diagnostics")


@register
class EnableConsoleLoggingCommand(Command):
    """Force enable console logging"""

    name = "enable_console_logging"
    description = "Force enable console logging if get_console_logs returns empty results"
    input_schema = {
        "type": "object",
        "properties": {}
    }

    requires_connection = True

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Force re-enable console logging"""
        connection = self.context.connection
        if not connection:
            return {"success": False, "message": "No browser connection"}

        result = await connection.force_enable_console_logging()
        return result


@register
class DiagnosePageCommand(Command):
    """Diagnose page state and connection"""

    name = "diagnose_page"
    description = "Diagnose page state, connection, and common issues"
    input_schema = {
        "type": "object",
        "properties": {}
    }

    requires_cdp = True  # Uses AsyncCDP wrapper for thread-safe evaluation

    async def execute(self) -> Dict[str, Any]:
        """Run diagnostic checks"""
        try:
            js_code = """
            (function() {
                return {
                    url: window.location.href,
                    title: document.title,
                    readyState: document.readyState,
                    activeElement: document.activeElement ? {
                        tag: document.activeElement.tagName,
                        id: document.activeElement.id,
                        type: document.activeElement.type
                    } : null,
                    viewport: {
                        width: window.innerWidth,
                        height: window.innerHeight,
                        scrollX: window.scrollX,
                        scrollY: window.scrollY
                    },
                    cursors: {
                        aiCursor: window.__aiCursor__ ? 'initialized' : 'not initialized',
                        consoleInterceptor: window.__consoleInterceptorInstalled ? 'installed' : 'not installed'
                    },
                    counts: {
                        buttons: document.querySelectorAll('button').length,
                        links: document.querySelectorAll('a').length,
                        inputs: document.querySelectorAll('input').length,
                        tabs: document.querySelectorAll('[role="tab"]').length
                    },
                    devtools: {
                        open: typeof window.chrome !== 'undefined' && typeof window.chrome.devtools !== 'undefined'
                    }
                };
            })()
            """

            # Use AsyncCDP wrapper for thread-safe evaluation (STABILITY FIX)
            result = await self.context.cdp.evaluate(expression=js_code, returnByValue=True)
            diagnostics = result.get('result', {}).get('value', {})

            return {
                "success": True,
                "diagnostics": diagnostics
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to diagnose page: {str(e)}"
            }


@register
class GetClickableElementsCommand(Command):
    """Get all clickable elements on page"""

    name = "get_clickable_elements"
    description = "Get all clickable elements with their positions (for finding hard-to-click elements)"
    input_schema = {
        "type": "object",
        "properties": {
            "text_filter": {"type": "string", "description": "Filter by text content (optional)"},
            "visible_only": {"type": "boolean", "description": "Only visible elements", "default": True}
        }
    }

    requires_cdp = True  # Uses AsyncCDP wrapper for thread-safe evaluation

    async def execute(self, text_filter: str = None, visible_only: bool = True) -> Dict[str, Any]:
        """Get all clickable elements"""
        try:
            filter_js = f"el.textContent.includes('{text_filter}')" if text_filter else "true"

            js_code = f"""
            (function() {{
                const clickableSelectors = [
                    'button',
                    'a',
                    '[role="button"]',
                    '[role="tab"]',
                    '[role="link"]',
                    '[onclick]',
                    'input[type="button"]',
                    'input[type="submit"]',
                    '[tabindex]'
                ];

                const elements = Array.from(document.querySelectorAll(clickableSelectors.join(',')));
                const visibleOnly = {str(visible_only).lower()};

                const results = elements
                    .filter(el => {filter_js})
                    .map(el => {{
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        const isVisible = rect.width > 0 && rect.height > 0 &&
                                         style.display !== 'none' &&
                                         style.visibility !== 'hidden' &&
                                         parseFloat(style.opacity) > 0;

                        if (visibleOnly && !isVisible) return null;

                        return {{
                            tag: el.tagName,
                            text: el.textContent.trim().substring(0, 60),
                            id: el.id || null,
                            role: el.getAttribute('role'),
                            ariaLabel: el.getAttribute('aria-label'),
                            visible: isVisible,
                            position: {{
                                x: Math.round(rect.left + rect.width / 2),
                                y: Math.round(rect.top + rect.height / 2),
                                width: Math.round(rect.width),
                                height: Math.round(rect.height)
                            }},
                            hasClickHandler: el.onclick !== null,
                            disabled: el.disabled || el.getAttribute('aria-disabled') === 'true'
                        }};
                    }})
                    .filter(el => el !== null);

                return {{
                    success: true,
                    count: results.length,
                    elements: results.slice(0, 50)
                }};
            }})()
            """

            # Use AsyncCDP wrapper for thread-safe evaluation (STABILITY FIX)
            result = await self.context.cdp.evaluate(expression=js_code, returnByValue=True)
            return result.get('result', {}).get('value', {})
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to get clickable elements: {str(e)}"
            }
