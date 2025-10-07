"""Generate comprehensive DevTools report"""
from typing import Dict, Any
from .base import Command


class DevToolsReportCommand(Command):
    """Generate comprehensive DevTools debugging report"""

    name = "devtools_report"
    description = """Generate comprehensive DevTools debugging report.

Auto-redirects to save_page_info() due to Claude Code output limitations.
After calling this, use Read('./page_info.json') to see full report."""
    input_schema = {
        "type": "object",
        "properties": {
            "include_dom": {"type": "boolean", "description": "Include DOM tree snapshot", "default": False}
        }
    }

    async def execute(self, include_dom: bool = False, console_logs=None) -> Dict[str, Any]:
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
                        failed: networkEntries.filter(e => e.transferSize === 0).length,
                        recent: networkEntries.slice(-5).map(e => ({
                            name: e.name.split('/').pop().substring(0, 50),
                            type: e.initiatorType,
                            duration: Math.round(e.duration)
                        }))
                    },
                    summary: {
                        total_interactive: interactive.length,
                        total_buttons: document.querySelectorAll('button').length,
                        total_links: document.querySelectorAll('a').length,
                        visible_interactive: interactive.length,
                        page_loaded: document.readyState === 'complete'
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
                "instruction": "Use Read('./page_info.json') to see full DevTools report",
                "redirect_reason": "devtools_report returns no visible output in Claude Code",
                "data_preview": {
                    "console_logs": len(page_data.get('console', {}).get('logs', [])),
                    "network_requests": page_data.get('network', {}).get('total_requests', 0),
                    "total_elements": len(page_data.get('interactive_elements', [])),
                    "file_path": output_file
                }
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to generate DevTools report: {str(e)}",
                "error": str(e)
            }
