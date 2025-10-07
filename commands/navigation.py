"""Navigation commands: open_url, get_text"""
import asyncio
from typing import Dict, Any
from .base import Command
from .registry import register


@register
class OpenUrlCommand(Command):
    """Navigate to a URL"""

    name = "open_url"
    description = "Open a URL in the Comet browser"
    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL to open"}
        },
        "required": ["url"]
    }

    requires_cursor = True
    requires_cdp = True

    async def execute(self, url: str, **kwargs) -> Dict[str, Any]:
        """Navigate to URL and reinitialize cursor"""
        try:
            await self.cdp.navigate(url=url, timeout=30)
            # Wait for page load
            await asyncio.sleep(2)

            # Re-initialize cursor after page load (navigation clears it)
            cursor = self.context.cursor
            if cursor:
                await cursor.initialize()

            return {"success": True, "url": url, "message": f"Opened {url}"}
        except Exception as e:
            raise RuntimeError(f"Failed to open URL: {str(e)}")


@register
class GetTextCommand(Command):
    """Extract text from elements"""

    name = "get_text"
    description = "Get text content from elements matching a CSS selector"
    input_schema = {
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "CSS selector"}
        },
        "required": ["selector"]
    }

    requires_cdp = True

    async def execute(self, selector: str) -> Dict[str, Any]:
        """Extract text content from selected element"""
        try:
            # Query selector using AsyncCDP
            result = await self.cdp.query_selector(selector=selector)

            if not result.get('nodeId'):
                return {"success": False, "text": "", "message": f"No element found for selector: {selector}"}

            # Use JS to get text content
            js_code = f"""
            (function() {{
                const el = document.querySelector('{selector}');
                return el ? el.textContent.trim() : '';
            }})()
            """

            eval_result = await self.cdp.evaluate(expression=js_code, returnByValue=True)
            text = eval_result.get('result', {}).get('value', '')

            return {"success": True, "text": text, "selector": selector}
        except Exception as e:
            raise RuntimeError(f"Failed to get text: {str(e)}")
