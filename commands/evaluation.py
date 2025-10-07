"""JavaScript evaluation command"""
from typing import Dict, Any
from .base import Command
from .registry import register


@register
class EvaluateJsCommand(Command):
    """Execute JavaScript code in browser"""

    name = "evaluate_js"
    description = """Execute JavaScript code in the browser.

Auto-redirects to save_page_info() due to Claude Code output limitations.
After calling this, use Read('./page_info.json') to see page data."""
    input_schema = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "JavaScript code to execute"}
        },
        "required": ["code"]
    }

    requires_cdp = True

    async def execute(self, code: str) -> Dict[str, Any]:
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

                return {
                    url: window.location.href,
                    title: document.title,
                    interactive_elements: interactive,
                    console: {
                        logs: consoleLogs.slice(-10),
                        total: consoleLogs.length
                    },
                    summary: {
                        total_interactive: interactive.length,
                        buttons: interactive.filter(e => e.tag === 'button').length,
                        links: interactive.filter(e => e.tag === 'a').length
                    }
                };
            })()
            """

            result = await self.cdp.evaluate(expression=js_code, returnByValue=True)
            page_data = result.get('result', {}).get('value', {})

            # Save to file
            output_file = "./page_info.json"
            os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(page_data, f, indent=2, ensure_ascii=False)

            return {
                "success": True,
                "message": f"✅ Data saved to {output_file}",
                "instruction": "Use Read('./page_info.json') to see page data and console logs",
                "redirect_reason": "evaluate_js returns no visible output in Claude Code",
                "data_preview": {
                    "total_elements": len(page_data.get('interactive_elements', [])),
                    "console_logs": len(page_data.get('console', {}).get('logs', [])),
                    "file_path": output_file
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to save page info: {str(e)}"
            }
