"""Open DevTools in separate tab"""
import requests
from typing import Dict, Any
from .base import Command
from .registry import register
from mcp.logging_config import get_logger

logger = get_logger("commands.open_devtools_url")


@register
class OpenDevToolsUrlCommand(Command):
    """Open DevTools UI in a new browser tab"""

    name = "open_devtools_ui"
    description = "Open Chrome DevTools UI in a new tab for full debugging access"
    input_schema = {
        "type": "object",
        "properties": {}
    }

    requires_browser = True

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Open DevTools UI in new tab"""
        try:
            browser = self.context.browser
            current_tab = self.tab

            # Get debug host from browser connection
            if hasattr(browser, '_url'):
                debug_host = browser._url.split('://')[1].split(':')[0]
            else:
                # Fallback: auto-detect WSL host
                try:
                    with open('/etc/resolv.conf', 'r') as f:
                        for line in f:
                            if line.startswith('nameserver'):
                                debug_host = line.split()[1]
                                break
                except:
                    debug_host = "127.0.0.1"

            debug_port = 9222

            # Get current tab's DevTools URL
            response = requests.get(f"http://{debug_host}:{debug_port}/json")
            tabs_info = response.json()

            if not tabs_info:
                return {
                    "success": False,
                    "message": "No tabs found"
                }

            # Find current tab or use first one
            tab_info = tabs_info[0]

            devtools_url = tab_info.get('devtoolsFrontendUrl', '')

            if not devtools_url:
                return {
                    "success": False,
                    "message": "DevTools URL not available"
                }

            # Convert appspot URL to use local debug host
            # Format: https://chrome-devtools-frontend.appspot.com/.../inspector.html?ws=HOST:PORT/...
            if 'ws=' in devtools_url:
                ws_part = devtools_url.split('ws=')[1]
                # Keep just the path part
                ws_path = '/'.join(ws_part.split('/')[1:])
                devtools_url = f"http://{debug_host}:{debug_port}/devtools/inspector.html?ws={debug_host}:{debug_port}/devtools/page/{ws_path.split('/')[-1]}"

            # Open DevTools URL in new tab using CDP
            new_tab_response = requests.put(f"http://{debug_host}:{debug_port}/json/new?{devtools_url}")

            return {
                "success": True,
                "message": f"DevTools UI opened in new tab",
                "devtools_url": devtools_url,
                "tab_title": tab_info.get('title'),
                "tab_url": tab_info.get('url')
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to open DevTools UI: {str(e)}",
                "error": str(e)
            }
