"""Save page info to file for debugging MCP output issues"""
import json
import os
from typing import Dict, Any
from .base import Command


class SavePageInfoCommand(Command):
    """Save page snapshot to file (workaround for Claude Code not showing MCP results)"""

    @property
    def name(self) -> str:
        return "save_page_info"

    @property
    def description(self) -> str:
        return """Save complete page state to JSON file. ALWAYS use Read tool after this to see results!

Returns: All interactive elements with coordinates, console logs, network info
Usage: 1) Call save_page_info() 2) Read('./page_info.json') to see data
Contains: buttons/links positions, DevTools console (last 10 logs), network requests"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "output_file": {"type": "string", "description": "Output file path", "default": "./page_info.json"}
            }
        }

    async def execute(self, output_file: str = "./page_info.json") -> Dict[str, Any]:
        """Save page info to file"""
        try:
            js_code = """
            (function() {
                function getVisibleText(el) {
                    if (!el) return '';
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden') return '';
                    return (el.innerText || el.textContent || '').trim();
                }

                const interactive = Array.from(document.querySelectorAll('button, a, [role="button"], [role="tab"]'))
                    .filter(el => {
                        const rect = el.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0 && el.offsetParent !== null;
                    })
                    .map(el => {
                        const rect = el.getBoundingClientRect();
                        return {
                            tag: el.tagName.toLowerCase(),
                            text: getVisibleText(el).substring(0, 100),
                            id: el.id || null,
                            classes: Array.from(el.classList || []),
                            position: {
                                x: Math.round(rect.left + rect.width/2),
                                y: Math.round(rect.top + rect.height/2)
                            }
                        };
                    });

                // Get console logs if available
                const consoleLogs = window.__consoleHistory || [];

                // Get network info
                const networkEntries = performance.getEntriesByType('resource') || [];

                return {
                    url: window.location.href,
                    title: document.title,
                    viewport: {
                        width: window.innerWidth,
                        height: window.innerHeight
                    },
                    interactive_elements: interactive,
                    console: {
                        logs: consoleLogs.slice(-10),  // Last 10 logs
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
                        total_buttons: document.querySelectorAll('button').length,
                        total_links: document.querySelectorAll('a').length,
                        visible_interactive: interactive.length,
                        page_loaded: document.readyState === 'complete'
                    }
                };
            })()
            """

            result = self.tab.Runtime.evaluate(expression=js_code, returnByValue=True)
            page_info = result.get('result', {}).get('value', {})

            # Save to file
            os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(page_info, f, indent=2, ensure_ascii=False)

            return {
                "success": True,
                "message": f"Page info saved to {output_file}",
                "file": output_file,
                "summary": page_info.get('summary', {})
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to save page info: {str(e)}",
                "error": str(e)
            }
