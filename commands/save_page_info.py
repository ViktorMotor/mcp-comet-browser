"""Save page info to file for debugging MCP output issues"""
import json
import os
from typing import Dict, Any
from .base import Command
from .registry import register
from utils.json_optimizer import JsonOptimizer


@register
class SavePageInfoCommand(Command):
    """Save page snapshot to file (workaround for Claude Code not showing MCP results)"""

    name = "save_page_info"
    description = """Save complete page state to JSON file. ALWAYS use Read tool after this to see results!

Returns: All interactive elements with coordinates, console logs, network info
Usage: 1) Call save_page_info() 2) Read('./page_info.json') to see data
Contains: buttons/links positions, DevTools console (last 10 logs), network requests"""
    input_schema = {
        "type": "object",
        "properties": {
            "output_file": {
                "type": "string",
                "description": "Output file path",
                "default": "./page_info.json"
            },
            "full": {
                "type": "boolean",
                "description": "If true, return full unoptimized data (for debugging)",
                "default": False
            }
        }
    }

    async def execute(self, output_file: str = "./page_info.json", full: bool = False) -> Dict[str, Any]:
        """Save page info to file (optimized by default, use full=True for debugging)"""
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

            # Use AsyncCDP wrapper for thread-safe evaluation (STABILITY FIX)
            result = await self.context.cdp.evaluate(expression=js_code, returnByValue=True)
            page_info = result.get('result', {}).get('value', {})

            # Optimize data (unless full=True)
            optimized_data = JsonOptimizer.optimize_page_info(page_info, full=full)

            # Save to file
            os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(optimized_data, f, indent=2, ensure_ascii=False)

            # Calculate size info
            file_size = os.path.getsize(output_file)
            size_kb = round(file_size / 1024, 1)

            return {
                "success": True,
                "message": f"Page info saved to {output_file} ({size_kb}KB, {'full' if full else 'optimized'} mode)",
                "file": output_file,
                "size_kb": size_kb,
                "optimized": not full,
                "summary": optimized_data.get('summary', {})
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to save page info: {str(e)}",
                "error": str(e)
            }
