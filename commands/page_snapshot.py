"""Lightweight text-based page snapshot (replaces heavy screenshots)"""
from typing import Dict, Any
from .base import Command


class PageSnapshotCommand(Command):
    """Get lightweight text-based page snapshot instead of heavy screenshot"""

    @property
    def name(self) -> str:
        return "get_page_snapshot"

    @property
    def description(self) -> str:
        return "⚠️ NO OUTPUT: Use save_page_info() instead - same data, actually returns results"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "include_styles": {"type": "boolean", "description": "Include computed styles", "default": False},
                "max_depth": {"type": "integer", "description": "Max DOM depth to traverse", "default": 3}
            }
        }

    async def execute(self, include_styles: bool = False, max_depth: int = 3) -> Dict[str, Any]:
        """Get text-based page snapshot"""
        try:
            js_code = f"""
            (function() {{
                // Helper: Get visible text content
                function getVisibleText(el) {{
                    if (!el || el.nodeType !== 1) return '';
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {{
                        return '';
                    }}
                    return el.innerText || el.textContent || '';
                }}

                // Helper: Get element description
                function describeElement(el, depth = 0, maxDepth = {max_depth}) {{
                    if (!el || depth > maxDepth) return null;

                    const rect = el.getBoundingClientRect();
                    const isVisible = rect.width > 0 && rect.height > 0 &&
                                     el.offsetParent !== null &&
                                     window.getComputedStyle(el).visibility !== 'hidden';

                    if (!isVisible && depth > 0) return null;

                    const desc = {{
                        tag: el.tagName?.toLowerCase(),
                        text: getVisibleText(el).trim().substring(0, 100),
                        id: el.id || null,
                        classes: Array.from(el.classList || []),
                        attributes: {{}},
                        position: isVisible ? {{
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height)
                        }} : null,
                        children: []
                    }};

                    // Important attributes
                    const importantAttrs = ['href', 'src', 'alt', 'title', 'placeholder', 'value', 'type', 'role', 'aria-label'];
                    for (let attr of importantAttrs) {{
                        if (el.hasAttribute(attr)) {{
                            desc.attributes[attr] = el.getAttribute(attr);
                        }}
                    }}

                    // Add computed styles if requested
                    {f'''
                    if ({str(include_styles).lower()}) {{
                        const style = window.getComputedStyle(el);
                        desc.styles = {{
                            display: style.display,
                            position: style.position,
                            color: style.color,
                            backgroundColor: style.backgroundColor,
                            fontSize: style.fontSize
                        }};
                    }}
                    ''' if include_styles else ''}

                    // Traverse children
                    if (depth < maxDepth) {{
                        for (let child of el.children || []) {{
                            const childDesc = describeElement(child, depth + 1, maxDepth);
                            if (childDesc) desc.children.push(childDesc);
                        }}
                    }}

                    return desc;
                }}

                // Get interactive elements
                function getInteractiveElements() {{
                    const selector = 'button, a, input, select, textarea, [role="button"], [role="tab"], [onclick]';
                    const elements = Array.from(document.querySelectorAll(selector));

                    return elements.filter(el => {{
                        const rect = el.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0 && el.offsetParent !== null;
                    }}).map(el => {{
                        const rect = el.getBoundingClientRect();
                        return {{
                            tag: el.tagName.toLowerCase(),
                            type: el.type || el.getAttribute('role') || 'button',
                            text: getVisibleText(el).substring(0, 50),
                            id: el.id || null,
                            position: {{
                                x: Math.round(rect.left + rect.width/2),
                                y: Math.round(rect.top + rect.height/2)
                            }}
                        }};
                    }}).slice(0, 50); // Limit to 50 most important
                }}

                // Get active/focused element
                function getActiveElement() {{
                    const active = document.activeElement;
                    if (!active || active === document.body) return null;

                    return {{
                        tag: active.tagName?.toLowerCase(),
                        id: active.id || null,
                        text: getVisibleText(active).substring(0, 50),
                        classes: Array.from(active.classList || [])
                    }};
                }}

                // Main snapshot
                return {{
                    url: window.location.href,
                    title: document.title,
                    viewport: {{
                        width: window.innerWidth,
                        height: window.innerHeight,
                        scrollX: window.scrollX,
                        scrollY: window.scrollY
                    }},
                    activeElement: getActiveElement(),
                    body: describeElement(document.body, 0, {max_depth}),
                    interactive: getInteractiveElements(),
                    summary: {{
                        totalElements: document.querySelectorAll('*').length,
                        visibleButtons: document.querySelectorAll('button:not([style*="display: none"])').length,
                        visibleLinks: document.querySelectorAll('a:not([style*="display: none"])').length,
                        forms: document.querySelectorAll('form').length,
                        images: document.querySelectorAll('img').length
                    }}
                }};
            }})()
            """

            result = self.tab.Runtime.evaluate(expression=js_code, returnByValue=True)
            snapshot = result.get('result', {}).get('value', {})

            return {
                "success": True,
                "snapshot": snapshot,
                "message": f"Page snapshot captured: {snapshot.get('title', 'Untitled')}"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to capture page snapshot: {str(e)}",
                "error": str(e)
            }
