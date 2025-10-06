"""Search and query commands for finding elements"""
from typing import Dict, Any, Optional
from .base import Command


class FindElementsCommand(Command):
    """Find all elements matching criteria (text, tag, attributes)"""

    @property
    def name(self) -> str:
        return "find_elements"

    @property
    def description(self) -> str:
        return "Find all elements matching text, tag, or attributes. Returns detailed info about each match."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text content to search for (partial match)"},
                "tag": {"type": "string", "description": "HTML tag name (e.g., 'button', 'a', 'div')"},
                "attribute": {"type": "string", "description": "Attribute name to check (e.g., 'role', 'aria-label')"},
                "attribute_value": {"type": "string", "description": "Value for the attribute"},
                "visible_only": {"type": "boolean", "description": "Only return visible elements", "default": True},
                "limit": {"type": "integer", "description": "Maximum number of results", "default": 20}
            }
        }

    async def execute(self, text: Optional[str] = None, tag: Optional[str] = None,
                     attribute: Optional[str] = None, attribute_value: Optional[str] = None,
                     visible_only: bool = True, limit: int = 20) -> Dict[str, Any]:
        """Search for elements matching criteria"""
        try:
            # Build JS search code
            text_escaped = text.replace("'", "\\'") if text else ""
            tag_js = f"'{tag}'" if tag else "'*'"
            attribute_js = f"'{attribute}'" if attribute else "null"
            attribute_value_js = f"'{attribute_value}'" if attribute_value else "null"

            js_code = f"""
            (function() {{
                const searchText = '{text_escaped}';
                const tag = {tag_js};
                const attribute = {attribute_js};
                const attributeValue = {attribute_value_js};
                const visibleOnly = {str(visible_only).lower()};
                const limit = {limit};

                // Get all elements of specified tag
                const elements = Array.from(document.querySelectorAll(tag));
                const results = [];

                for (const el of elements) {{
                    // Check text match
                    if (searchText && !el.textContent.includes(searchText)) {{
                        continue;
                    }}

                    // Check attribute match
                    if (attribute) {{
                        const attrValue = el.getAttribute(attribute);
                        if (!attrValue) continue;
                        if (attributeValue && !attrValue.includes(attributeValue)) continue;
                    }}

                    // Check visibility
                    if (visibleOnly) {{
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        const isVisible = rect.width > 0 && rect.height > 0 &&
                                         style.display !== 'none' &&
                                         style.visibility !== 'hidden' &&
                                         style.opacity !== '0';
                        if (!isVisible) continue;
                    }}

                    // Collect element info
                    const rect = el.getBoundingClientRect();
                    results.push({{
                        tagName: el.tagName,
                        id: el.id || null,
                        className: el.className || null,
                        textContent: el.textContent.trim().substring(0, 100),
                        innerHTML: el.innerHTML.substring(0, 200),
                        attributes: Array.from(el.attributes).map(a => ({{
                            name: a.name,
                            value: a.value
                        }})),
                        position: {{
                            top: Math.round(rect.top),
                            left: Math.round(rect.left),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height)
                        }},
                        selector: (() => {{
                            // Try to generate a selector
                            if (el.id) return `#{el.id}`;
                            if (el.className) {{
                                const classes = el.className.split(' ').filter(c => c);
                                if (classes.length > 0) {{
                                    return `${el.tagName.toLowerCase()}.${classes[0]}`;
                                }}
                            }}
                            return el.tagName.toLowerCase();
                        }})()
                    }});

                    if (results.length >= limit) break;
                }}

                return {{
                    success: true,
                    count: results.length,
                    elements: results,
                    searchCriteria: {{
                        text: searchText || null,
                        tag: tag,
                        attribute: attribute,
                        attributeValue: attributeValue,
                        visibleOnly: visibleOnly
                    }}
                }};
            }})()
            """

            result = self.tab.Runtime.evaluate(expression=js_code, returnByValue=True)
            return result.get('result', {}).get('value', {})

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to find elements: {str(e)}"
            }


class GetPageStructureCommand(Command):
    """Get page structure overview (headings, links, buttons, forms)"""

    @property
    def name(self) -> str:
        return "get_page_structure"

    @property
    def description(self) -> str:
        return "Get overview of page structure: headings, links, buttons, forms, inputs"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "include_text": {"type": "boolean", "description": "Include text content", "default": True}
            }
        }

    async def execute(self, include_text: bool = True) -> Dict[str, Any]:
        """Get page structure overview"""
        try:
            js_code = f"""
            (function() {{
                const includeText = {str(include_text).lower()};

                const getElements = (selector) => {{
                    return Array.from(document.querySelectorAll(selector))
                        .filter(el => {{
                            const rect = el.getBoundingClientRect();
                            const style = window.getComputedStyle(el);
                            return rect.width > 0 && rect.height > 0 &&
                                   style.display !== 'none' &&
                                   style.visibility !== 'hidden';
                        }})
                        .map(el => ({{
                            tag: el.tagName,
                            text: includeText ? el.textContent.trim().substring(0, 50) : undefined,
                            id: el.id || undefined,
                            className: el.className || undefined,
                            href: el.href || undefined,
                            type: el.type || undefined,
                            name: el.name || undefined,
                            value: el.value || undefined
                        }}));
                }};

                return {{
                    success: true,
                    url: window.location.href,
                    title: document.title,
                    headings: {{
                        h1: getElements('h1'),
                        h2: getElements('h2'),
                        h3: getElements('h3')
                    }},
                    links: getElements('a').slice(0, 20),
                    buttons: getElements('button, input[type="button"], input[type="submit"]').slice(0, 20),
                    forms: Array.from(document.forms).map(form => ({{
                        name: form.name,
                        action: form.action,
                        method: form.method,
                        inputCount: form.elements.length
                    }})),
                    inputs: getElements('input, textarea, select').slice(0, 20),
                    counts: {{
                        links: document.querySelectorAll('a').length,
                        buttons: document.querySelectorAll('button, input[type="button"], input[type="submit"]').length,
                        forms: document.forms.length,
                        inputs: document.querySelectorAll('input, textarea, select').length
                    }}
                }};
            }})()
            """

            result = self.tab.Runtime.evaluate(expression=js_code, returnByValue=True)
            return result.get('result', {}).get('value', {})

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to get page structure: {str(e)}"
            }
