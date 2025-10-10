"""Search and query commands for finding elements"""
from typing import Dict, Any, Optional
from .base import Command
from .registry import register


@register
class FindElementsCommand(Command):
    """Find all elements matching criteria (text, tag, attributes)"""

    name = "find_elements"
    description = """Find elements on the page (text, tag, attributes).

Auto-redirects to save_page_info() due to Claude Code output limitations.
After calling this, use Read('./page_info.json') to see all interactive elements."""
    input_schema = {
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

                return {
                    url: window.location.href,
                    title: document.title,
                    interactive_elements: interactive,
                    summary: {
                        total_interactive: interactive.length,
                        buttons: interactive.filter(e => e.tag === 'button').length,
                        links: interactive.filter(e => e.tag === 'a').length
                    }
                };
            })()
            """

            # Use AsyncCDP wrapper for thread-safe evaluation (STABILITY FIX)
            result = await self.context.cdp.evaluate(expression=js_code, returnByValue=True)
            page_data = result.get('result', {}).get('value', {})

            # Save to file
            output_file = "./page_info.json"
            os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(page_data, f, indent=2, ensure_ascii=False)

            return {
                "success": True,
                "message": f"✅ Data saved to {output_file}",
                "instruction": "Use Read('./page_info.json') to see all interactive elements",
                "redirect_reason": "find_elements returns no visible output in Claude Code",
                "data_preview": {
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


@register
class GetPageStructureCommand(Command):
    """Get page structure overview (headings, links, buttons, forms)"""

    name = "get_page_structure"
    description = """Get page structure (headings, links, buttons, forms).

Auto-redirects to save_page_info() due to Claude Code output limitations.
After calling this, use Read('./page_info.json') to see page structure."""
    input_schema = {
        "type": "object",
        "properties": {
            "include_text": {"type": "boolean", "description": "Include text content", "default": True}
        }
    }

    async def execute(self, include_text: bool = True) -> Dict[str, Any]:
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

                return {
                    url: window.location.href,
                    title: document.title,
                    interactive_elements: interactive,
                    summary: {
                        total_interactive: interactive.length,
                        buttons: interactive.filter(e => e.tag === 'button').length,
                        links: interactive.filter(e => e.tag === 'a').length
                    }
                };
            })()
            """

            # Use AsyncCDP wrapper for thread-safe evaluation (STABILITY FIX)
            result = await self.context.cdp.evaluate(expression=js_code, returnByValue=True)
            page_data = result.get('result', {}).get('value', {})

            # Save to file
            output_file = "./page_info.json"
            os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(page_data, f, indent=2, ensure_ascii=False)

            return {
                "success": True,
                "message": f"✅ Data saved to {output_file}",
                "instruction": "Use Read('./page_info.json') to see page structure and interactive elements",
                "redirect_reason": "get_page_structure returns no visible output in Claude Code",
                "data_preview": {
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
