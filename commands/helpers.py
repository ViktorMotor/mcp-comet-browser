"""Helper commands for debugging and advanced interactions"""
from typing import Dict, Any
from .base import Command
from .registry import register


@register
class DebugElementCommand(Command):
    """Debug element to see all available click methods"""

    name = "debug_element"
    description = "Debug an element to see all ways to interact with it (for troubleshooting clicks)"
    input_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to search for"},
            "selector": {"type": "string", "description": "CSS selector (optional)"}
        }
    }

    async def execute(self, text: str = None, selector: str = None) -> Dict[str, Any]:
        """Debug element and return all possible selectors and click methods"""
        try:
            search_strategy = f"text='{text}'" if text else f"selector='{selector}'"

            js_code = f"""
            (function() {{
                let elements = [];

                // Search by text if provided
                if ('{text}') {{
                    const searchText = '{text}';
                    elements = Array.from(document.querySelectorAll('*'))
                        .filter(el => el.textContent.includes(searchText) && el.children.length === 0);
                }} else if ('{selector}') {{
                    elements = Array.from(document.querySelectorAll('{selector}'));
                }}

                if (elements.length === 0) {{
                    return {{success: false, message: 'No elements found for {search_strategy}'}};
                }}

                // Analyze each element
                const results = elements.slice(0, 5).map((el, idx) => {{
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    const isVisible = rect.width > 0 && rect.height > 0 &&
                                     style.display !== 'none' &&
                                     style.visibility !== 'hidden' &&
                                     parseFloat(style.opacity) > 0;

                    // Try to generate unique selectors
                    const selectors = [];
                    if (el.id) selectors.push('#' + el.id);
                    if (el.className) {{
                        const classes = el.className.split(' ').filter(c => c);
                        if (classes.length > 0) {{
                            selectors.push(el.tagName.toLowerCase() + '.' + classes[0]);
                        }}
                    }}

                    // Get all event listeners
                    const hasClickHandler = el.onclick !== null;
                    const hasEventListeners = typeof getEventListeners === 'function'
                        ? Object.keys(getEventListeners(el)).length > 0
                        : 'unknown';

                    return {{
                        index: idx,
                        tagName: el.tagName,
                        text: el.textContent.trim().substring(0, 100),
                        visible: isVisible,
                        position: {{
                            x: Math.round(rect.left + rect.width / 2),
                            y: Math.round(rect.top + rect.height / 2),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height)
                        }},
                        selectors: selectors,
                        attributes: Array.from(el.attributes).map(a => ({{
                            name: a.name,
                            value: a.value
                        }})),
                        styles: {{
                            display: style.display,
                            visibility: style.visibility,
                            opacity: style.opacity,
                            pointerEvents: style.pointerEvents,
                            cursor: style.cursor,
                            zIndex: style.zIndex
                        }},
                        clickable: {{
                            hasClickHandler: hasClickHandler,
                            hasEventListeners: hasEventListeners,
                            isButton: el.tagName === 'BUTTON',
                            isLink: el.tagName === 'A',
                            hasRole: el.getAttribute('role') !== null,
                            role: el.getAttribute('role')
                        }},
                        parent: {{
                            tagName: el.parentElement ? el.parentElement.tagName : null,
                            classes: el.parentElement ? el.parentElement.className : null
                        }}
                    }};
                }});

                return {{
                    success: true,
                    count: elements.length,
                    showing: results.length,
                    elements: results
                }};
            }})()
            """

            result = self.tab.Runtime.evaluate(expression=js_code, returnByValue=True)
            return result.get('result', {}).get('value', {})
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to debug element: {str(e)}"
            }


@register
class ForceClickCommand(Command):
    """Force click using multiple aggressive strategies"""

    name = "force_click"
    description = "Force click on element using all available methods (use when normal click fails)"
    input_schema = {
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "X coordinate"},
            "y": {"type": "integer", "description": "Y coordinate"},
            "text": {"type": "string", "description": "Text to find (alternative to coordinates)"}
        }
    }

    requires_cursor = True

    async def execute(self, x: int = None, y: int = None, text: str = None, **kwargs) -> Dict[str, Any]:
        """Force click at coordinates or on text"""
        try:
            cursor = self.context.cursor
            if cursor:
                await cursor.initialize()

            if x is not None and y is not None:
                # Click at specific coordinates
                js_code = f"""
                (function() {{
                    const x = {x};
                    const y = {y};

                    // Get element at coordinates
                    const el = document.elementFromPoint(x, y);

                    if (!el) {{
                        return {{success: false, message: 'No element at coordinates ({x}, {y})'}};
                    }}

                    // Move cursor
                    if (window.__moveAICursor__) {{
                        window.__moveAICursor__(x, y, 300);
                    }}

                    return new Promise((resolve) => {{
                        setTimeout(() => {{
                            // Show click animation
                            if (window.__clickAICursor__) {{
                                window.__clickAICursor__();
                            }}

                            // Try ALL click methods
                            const methods = [];

                            // 1. Direct click
                            try {{ el.click(); methods.push('click()'); }} catch(e) {{}}

                            // 2. Mouse events
                            try {{
                                ['mousedown', 'mouseup', 'click'].forEach(type => {{
                                    el.dispatchEvent(new MouseEvent(type, {{
                                        view: window, bubbles: true, cancelable: true,
                                        clientX: x, clientY: y
                                    }}));
                                }});
                                methods.push('MouseEvent');
                            }} catch(e) {{}}

                            // 3. Pointer events
                            try {{
                                ['pointerdown', 'pointerup', 'click'].forEach(type => {{
                                    el.dispatchEvent(new PointerEvent(type, {{
                                        view: window, bubbles: true, cancelable: true,
                                        clientX: x, clientY: y, isPrimary: true
                                    }}));
                                }});
                                methods.push('PointerEvent');
                            }} catch(e) {{}}

                            // 4. Touch events
                            try {{
                                const touch = new Touch({{
                                    identifier: 0,
                                    target: el,
                                    clientX: x,
                                    clientY: y
                                }});
                                ['touchstart', 'touchend'].forEach(type => {{
                                    el.dispatchEvent(new TouchEvent(type, {{
                                        touches: [touch],
                                        bubbles: true,
                                        cancelable: true
                                    }}));
                                }});
                                methods.push('TouchEvent');
                            }} catch(e) {{}}

                            // 5. Focus and trigger
                            try {{
                                if (el.focus) el.focus();
                                if (el.onclick) el.onclick.call(el);
                                methods.push('focus+onclick');
                            }} catch(e) {{}}

                            resolve({{
                                success: true,
                                element: {{
                                    tagName: el.tagName,
                                    id: el.id,
                                    text: el.textContent.trim().substring(0, 50),
                                    role: el.getAttribute('role')
                                }},
                                methods: methods,
                                position: {{x: x, y: y}},
                                message: 'Executed ' + methods.length + ' click methods'
                            }});
                        }}, 350);
                    }});
                }})()
                """
            elif text:
                # Find by text and force click
                js_code = f"""
                (function() {{
                    const searchText = '{text}';
                    const elements = Array.from(document.querySelectorAll('*'))
                        .filter(el => el.textContent.includes(searchText) && el.children.length === 0);

                    if (elements.length === 0) {{
                        return {{success: false, message: 'No elements with text: {text}'}};
                    }}

                    const el = elements[0];
                    const rect = el.getBoundingClientRect();
                    const x = rect.left + rect.width / 2;
                    const y = rect.top + rect.height / 2;

                    // Scroll into view
                    el.scrollIntoView({{behavior: 'smooth', block: 'center'}});

                    // Move cursor
                    if (window.__moveAICursor__) {{
                        window.__moveAICursor__(x, y, 300);
                    }}

                    return new Promise((resolve) => {{
                        setTimeout(() => {{
                            if (window.__clickAICursor__) {{
                                window.__clickAICursor__();
                            }}

                            const methods = [];

                            try {{ el.click(); methods.push('click()'); }} catch(e) {{}}
                            try {{
                                ['mousedown', 'mouseup', 'click'].forEach(type => {{
                                    el.dispatchEvent(new MouseEvent(type, {{
                                        view: window, bubbles: true, cancelable: true,
                                        clientX: x, clientY: y
                                    }}));
                                }});
                                methods.push('MouseEvent');
                            }} catch(e) {{}}

                            try {{
                                if (el.focus) el.focus();
                                if (el.onclick) el.onclick.call(el);
                                methods.push('focus+onclick');
                            }} catch(e) {{}}

                            resolve({{
                                success: true,
                                element: {{
                                    tagName: el.tagName,
                                    id: el.id,
                                    text: el.textContent.trim().substring(0, 50)
                                }},
                                methods: methods,
                                position: {{x: Math.round(x), y: Math.round(y)}},
                                message: 'Executed ' + methods.length + ' click methods on text: {text}'
                            }});
                        }}, 350);
                    }});
                }})()
                """
            else:
                return {"success": False, "message": "Provide either x,y coordinates or text"}

            result = self.tab.Runtime.evaluate(expression=js_code, returnByValue=True, awaitPromise=True)
            return result.get('result', {}).get('value', {})
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to force click: {str(e)}"
            }
