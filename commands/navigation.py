"""Navigation commands: open_url, get_text"""
import asyncio
from typing import Dict, Any
from .base import Command


class OpenUrlCommand(Command):
    """Navigate to a URL"""

    @property
    def name(self) -> str:
        return "open_url"

    @property
    def description(self) -> str:
        return "Open a URL in the Comet browser"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to open"}
            },
            "required": ["url"]
        }

    async def execute(self, url: str, cursor=None) -> Dict[str, Any]:
        """Navigate to URL and reinitialize cursor"""
        try:
            self.tab.Page.navigate(url=url, _timeout=30)
            # Wait for page load
            await asyncio.sleep(2)

            # Re-initialize cursor after page load (navigation clears it)
            if cursor:
                await cursor.initialize()

            return {"success": True, "url": url, "message": f"Opened {url}"}
        except Exception as e:
            raise RuntimeError(f"Failed to open URL: {str(e)}")


class GetTextCommand(Command):
    """Extract text from elements"""

    @property
    def name(self) -> str:
        return "get_text"

    @property
    def description(self) -> str:
        return "Get text content from elements matching a CSS selector"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector"}
            },
            "required": ["selector"]
        }

    async def execute(self, selector: str) -> Dict[str, Any]:
        """Extract text content from selected element"""
        try:
            # Get document root
            doc = self.tab.DOM.getDocument()
            root_node_id = doc['root']['nodeId']

            # Query selector
            node_id = self.tab.DOM.querySelector(nodeId=root_node_id, selector=selector)

            if not node_id.get('nodeId'):
                return {"success": False, "text": "", "message": f"No element found for selector: {selector}"}

            # Use JS to get text content
            js_code = f"""
            (function() {{
                const el = document.querySelector('{selector}');
                return el ? el.textContent.trim() : '';
            }})()
            """

            eval_result = self.tab.Runtime.evaluate(expression=js_code)
            text = eval_result.get('result', {}).get('value', '')

            return {"success": True, "text": text, "selector": selector}
        except Exception as e:
            raise RuntimeError(f"Failed to get text: {str(e)}")
