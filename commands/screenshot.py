"""Screenshot command"""
import base64
import os
from typing import Dict, Any
from .base import Command
from .registry import register


@register
class ScreenshotCommand(Command):
    """Capture page screenshot"""

    name = "screenshot"
    description = """Take PNG screenshot of current page. HEAVY (~1800 tokens). Use save_page_info instead when possible (saves 75% tokens).

Auto-saves to ./screenshots/ folder. Use Read tool to view: Read('./screenshots/screenshot.png')"""
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to save screenshot", "default": "./screenshots/screenshot.png"}
        }
    }

    requires_cdp = True

    async def execute(self, path: str = "./screenshots/screenshot.png") -> Dict[str, Any]:
        """Capture and save screenshot"""
        try:
            # Create screenshots directory if it doesn't exist
            os.makedirs(os.path.dirname(path), exist_ok=True)

            result = await self.cdp.capture_screenshot(format='png')
            img_data = result.get('data', '')

            # Decode base64 and save to file
            with open(path, 'wb') as f:
                f.write(base64.b64decode(img_data))

            return {"success": True, "path": path, "message": f"Screenshot saved to {path}"}
        except Exception as e:
            raise RuntimeError(f"Failed to take screenshot: {str(e)}")
