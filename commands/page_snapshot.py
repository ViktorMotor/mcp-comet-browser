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
        return """Get lightweight text-based page snapshot.

Auto-redirects to save_page_info() due to Claude Code output limitations.
After calling this, use Read('./page_info.json') to see page snapshot."""

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
                "instruction": "Use Read('./page_info.json') to see page snapshot",
                "redirect_reason": "get_page_snapshot returns no visible output in Claude Code",
                "data_preview": {
                    "total_elements": len(page_data.get('interactive_elements', [])),
                    "file_path": output_file
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to capture page snapshot: {str(e)}",
                "error": str(e)
            }
