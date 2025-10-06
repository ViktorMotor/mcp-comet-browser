"""Screenshot command"""
import base64
import os
from typing import Dict, Any
from .base import Command


class ScreenshotCommand(Command):
    """Capture page screenshot"""

    @property
    def name(self) -> str:
        return "screenshot"

    @property
    def description(self) -> str:
        return "Take a screenshot of the current page"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to save screenshot", "default": "./screenshots/screenshot.png"}
            }
        }

    async def execute(self, path: str = "./screenshots/screenshot.png") -> Dict[str, Any]:
        """Capture and save screenshot"""
        try:
            # Create screenshots directory if it doesn't exist
            os.makedirs(os.path.dirname(path), exist_ok=True)

            result = self.tab.Page.captureScreenshot(format='png')
            img_data = result.get('data', '')

            # Decode base64 and save to file
            with open(path, 'wb') as f:
                f.write(base64.b64decode(img_data))

            return {"success": True, "path": path, "message": f"Screenshot saved to {path}"}
        except Exception as e:
            raise RuntimeError(f"Failed to take screenshot: {str(e)}")
