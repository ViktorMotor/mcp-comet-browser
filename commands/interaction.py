"""Interactive browser commands: click, scroll, cursor movement"""
import asyncio
from typing import Dict, Any, Optional
from .base import Command


class ClickCommand(Command):
    """Click on an element with multiple search strategies"""

    @property
    def name(self) -> str:
        return "click"

    @property
    def description(self) -> str:
        return "Click on an element matching a CSS selector. Supports XPath (//), text search, and ARIA attributes. Auto-scrolls to element and shows cursor animation."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector, XPath (//button), or text content"}
            },
            "required": ["selector"]
        }

    async def execute(self, selector: str, show_cursor: bool = True, cursor=None) -> Dict[str, Any]:
        """Execute click with multiple strategies and cursor animation"""
        try:
            # Re-initialize cursor if provided
            if cursor:
                await cursor.initialize()

            js_code = f"""
            (function() {{
                // Try multiple strategies to find the element
                let el = null;
                let strategy = '';

                // Strategy 1: Direct CSS selector
                el = document.querySelector('{selector}');
                if (el) strategy = 'css';

                // Strategy 2: XPath
                if (!el && '{selector}'.startsWith('//')) {{
                    try {{
                        const result = document.evaluate('{selector}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                        el = result.singleNodeValue;
                        if (el) strategy = 'xpath';
                    }} catch(e) {{}}
                }}

                // Strategy 3: Text content search
                if (!el && ('{selector}'.includes('text') || '{selector}'.includes('содержит'))) {{
                    const textMatch = '{selector}'.match(/["']([^"']+)["']/);
                    if (textMatch) {{
                        const searchText = textMatch[1];
                        el = Array.from(document.querySelectorAll('button, a, [role="button"], [role="tab"], [onclick]'))
                            .find(e => e.textContent.trim() === searchText || e.textContent.includes(searchText));
                        if (el) strategy = 'text-exact';
                    }}
                }}

                // Strategy 4: Common clickable patterns
                if (!el) {{
                    const allClickable = document.querySelectorAll('button, a, [role="button"], [role="tab"], [onclick], input[type="button"], input[type="submit"]');
                    el = Array.from(allClickable).find(e =>
                        e.textContent.includes('{selector}') ||
                        e.getAttribute('aria-label')?.includes('{selector}') ||
                        e.title?.includes('{selector}')
                    );
                    if (el) strategy = 'text-contains';
                }}

                if (!el) {{
                    const allMatches = document.querySelectorAll('{selector}');
                    return {{
                        success: false,
                        reason: 'not_found',
                        message: 'Element not found: {selector}',
                        matchCount: allMatches.length,
                        suggestion: allMatches.length > 0 ? 'Selector matches ' + allMatches.length + ' elements' : 'Try using text content or XPath'
                    }};
                }}

                // Check visibility
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
                        dimensions: {{ width: rect.width, height: rect.height }}
                    }};
                }}

                // Check viewport
                const inViewport = rect.top >= 0 && rect.left >= 0 &&
                                  rect.bottom <= window.innerHeight &&
                                  rect.right <= window.innerWidth;

                // Scroll into view if needed
                if (!inViewport) {{
                    el.scrollIntoView({{ behavior: 'smooth', block: 'center', inline: 'center' }});
                    await new Promise(r => setTimeout(r, 300));
                    const newRect = el.getBoundingClientRect();
                    rect.top = newRect.top;
                    rect.left = newRect.left;
                }}

                // Calculate click position
                const clickX = rect.left + rect.width / 2;
                const clickY = rect.top + rect.height / 2;

                // Animate cursor
                const showCursor = {str(show_cursor).lower()};
                if (showCursor && window.__moveAICursor__) {{
                    window.__moveAICursor__(clickX, clickY, 400);
                }}

                // Wait and click
                return new Promise((resolve) => {{
                    setTimeout(() => {{
                        try {{
                            if (showCursor && window.__clickAICursor__) {{
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

                            if (el.tagName === 'BUTTON' || el.tagName === 'INPUT' || el.tagName === 'A') {{
                                try {{
                                    el.focus();
                                    if (el.onclick) el.onclick.call(el);
                                }} catch (e3) {{}}
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

            if click_result.get('success'):
                await asyncio.sleep(0.3)

            return click_result
        except Exception as e:
            return {
                "success": False,
                "reason": "exception",
                "message": f"Failed to click element: {str(e)}",
                "error": str(e)
            }


class ClickByTextCommand(Command):
    """Click element by visible text content"""

    @property
    def name(self) -> str:
        return "click_by_text"

    @property
    def description(self) -> str:
        return "Click on an element by its visible text content. More reliable than CSS selectors for buttons and links."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to search for"},
                "tag": {"type": "string", "description": "Optional: limit search to specific tag"},
                "exact": {"type": "boolean", "description": "If true, match exact text", "default": False}
            },
            "required": ["text"]
        }

    async def execute(self, text: str, tag: Optional[str] = None, exact: bool = False, cursor=None) -> Dict[str, Any]:
        """Execute click by text with cursor animation"""
        try:
            if cursor:
                await cursor.initialize()

            match_method = "===" if exact else "includes"

            if tag:
                tags_js = f"['{tag}']"
            else:
                tags_js = "['button', 'a', '[role=\"button\"]', '[role=\"tab\"]', 'input[type=\"button\"]', 'input[type=\"submit\"]', '[onclick]']"

            js_code = f"""
            (function() {{
                const tags = {tags_js};
                const selector = tags.join(', ');
                const elements = Array.from(document.querySelectorAll(selector));

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

                const rect = el.getBoundingClientRect();
                const clickX = rect.left + rect.width / 2;
                const clickY = rect.top + rect.height / 2;

                const inViewport = rect.top >= 0 && rect.left >= 0 &&
                                  rect.bottom <= window.innerHeight &&
                                  rect.right <= window.innerWidth;

                if (!inViewport) {{
                    el.scrollIntoView({{ behavior: 'smooth', block: 'center', inline: 'center' }});
                    await new Promise(r => setTimeout(r, 300));
                }}

                if (window.__moveAICursor__) {{
                    window.__moveAICursor__(clickX, clickY, 400);
                }}

                return new Promise((resolve) => {{
                    setTimeout(() => {{
                        try {{
                            if (window.__clickAICursor__) {{
                                window.__clickAICursor__();
                            }}

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


class ScrollPageCommand(Command):
    """Scroll page or element"""

    @property
    def name(self) -> str:
        return "scroll_page"

    @property
    def description(self) -> str:
        return "Scroll the page or a specific element. Returns detailed position information."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "direction": {"type": "string", "description": "Scroll direction: 'up', 'down', 'left', 'right', 'top', 'bottom'", "default": "down"},
                "amount": {"type": "integer", "description": "Pixels to scroll (default: 500 for page, 300 for element)"},
                "x": {"type": "integer", "description": "Absolute X coordinate to scroll to"},
                "y": {"type": "integer", "description": "Absolute Y coordinate to scroll to"},
                "selector": {"type": "string", "description": "CSS selector of element to scroll"}
            }
        }

    async def execute(self, direction: str = "down", amount: Optional[int] = None,
                     x: Optional[int] = None, y: Optional[int] = None,
                     selector: Optional[str] = None) -> Dict[str, Any]:
        """Execute scroll operation"""
        try:
            # Build JavaScript based on parameters
            if x is not None and y is not None:
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
                if amount is None:
                    amount = 500

                scroll_map = {
                    "down": f"window.scrollBy(0, {amount})",
                    "up": f"window.scrollBy(0, -{amount})",
                    "left": f"window.scrollBy(-{amount}, 0)",
                    "right": f"window.scrollBy({amount}, 0)",
                    "top": "window.scrollTo(0, 0)",
                    "bottom": "window.scrollTo(0, document.documentElement.scrollHeight)"
                }

                scroll_expr = scroll_map.get(direction)
                if not scroll_expr:
                    return {"success": False, "message": f"Invalid direction: {direction}"}

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


class MoveCursorCommand(Command):
    """Move AI cursor to position"""

    @property
    def name(self) -> str:
        return "move_cursor"

    @property
    def description(self) -> str:
        return "Move the visual AI cursor to specific coordinates or element center."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate"},
                "y": {"type": "integer", "description": "Y coordinate"},
                "selector": {"type": "string", "description": "CSS selector to move cursor to (element center)"},
                "duration": {"type": "integer", "description": "Animation duration in ms", "default": 400}
            }
        }

    async def execute(self, x: Optional[int] = None, y: Optional[int] = None,
                     selector: Optional[str] = None, duration: int = 400, cursor=None) -> Dict[str, Any]:
        """Execute cursor movement"""
        try:
            if selector:
                js_code = f"""
                (function() {{
                    const el = document.querySelector('{selector}');
                    if (!el) {{
                        return {{success: false, message: 'Element not found: {selector}'}};
                    }}

                    const rect = el.getBoundingClientRect();
                    const centerX = rect.left + rect.width / 2;
                    const centerY = rect.top + rect.height / 2;

                    if (window.__moveAICursor__) {{
                        window.__moveAICursor__(centerX, centerY, {duration});
                        return {{
                            success: true,
                            message: 'Cursor moved to element: {selector}',
                            position: {{x: centerX, y: centerY}},
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
                        return {{success: false, message: 'AI cursor not initialized'}};
                    }}
                }})()
                """
            elif x is not None and y is not None:
                js_code = f"""
                (function() {{
                    if (window.__moveAICursor__) {{
                        window.__moveAICursor__({x}, {y}, {duration});
                        return {{
                            success: true,
                            message: 'Cursor moved to coordinates',
                            position: {{x: {x}, y: {y}}}
                        }};
                    }} else {{
                        return {{success: false, message: 'AI cursor not initialized'}};
                    }}
                }})()
                """
            else:
                return {"success": False, "message": "Either provide x,y coordinates or selector"}

            result = self.tab.Runtime.evaluate(expression=js_code, returnByValue=True)
            return result.get('result', {}).get('value', {})
        except Exception as e:
            return {"success": False, "message": f"Failed to move cursor: {str(e)}", "error": str(e)}
