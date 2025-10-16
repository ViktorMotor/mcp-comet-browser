"""Screenshot command with optimization support"""
import base64
import os
from typing import Dict, Any, Optional
from .base import Command
from .registry import register
from mcp.errors import InvalidArgumentError
from utils.validators import Validators

try:
    from PIL import Image
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


@register
class ScreenshotCommand(Command):
    """Capture page screenshot with optimization options"""

    name = "screenshot"
    description = """Take screenshot of current page with optimization options.

Optimization tips:
- Use format='jpeg' for 50-80% size reduction (default: png)
- Use quality=60-80 for JPEG to balance quality vs size
- Use max_width to auto-resize large screenshots
- Use element selector to capture specific element only

Auto-saves to ./screenshots/ folder. Use Read tool to view: Read('./screenshots/screenshot.png')

Note: Requires Pillow for JPEG/resize support. Install: pip install Pillow"""
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to save screenshot",
                "default": "./screenshots/screenshot.png"
            },
            "format": {
                "type": "string",
                "enum": ["png", "jpeg"],
                "description": "Image format (jpeg is 50-80% smaller)",
                "default": "png"
            },
            "quality": {
                "type": "integer",
                "description": "JPEG quality 1-100 (default: 80, requires Pillow)",
                "default": 80,
                "minimum": 1,
                "maximum": 100
            },
            "max_width": {
                "type": "integer",
                "description": "Max width - auto-resize if larger (requires Pillow)"
            },
            "element": {
                "type": "string",
                "description": "CSS selector - capture only this element"
            },
            "full_page": {
                "type": "boolean",
                "description": "Capture full scrollable page (not just viewport)",
                "default": False
            }
        }
    }

    async def execute(
        self,
        path: str = "./screenshots/screenshot.png",
        format: str = "png",
        quality: int = 80,
        max_width: Optional[int] = None,
        element: Optional[str] = None,
        full_page: bool = False
    ) -> Dict[str, Any]:
        """Capture and save screenshot with optimization"""
        # Validate inputs BEFORE try block (so exceptions propagate)
        # Validate path (security check)
        path = Validators.validate_path(path, allowed_prefixes=['./screenshots/'])

        # Validate format
        if format not in ['png', 'jpeg']:
            raise InvalidArgumentError(
                argument="format",
                expected="'png' or 'jpeg'",
                received=format
            )

        # Validate quality (1-100)
        quality = int(Validators.validate_range(quality, "quality", min_value=1, max_value=100))

        # Validate max_width if provided
        if max_width is not None:
            max_width = int(Validators.validate_range(max_width, "max_width", min_value=100, max_value=10000))

        # Validate element selector if provided
        if element:
            element = Validators.validate_selector(element, "element")

        try:
            # Create screenshots directory
            os.makedirs(os.path.dirname(path), exist_ok=True)

            # Get element bounds if selector provided
            clip_region = None
            if element:
                clip_region = await self._get_element_bounds(element)

            # Capture screenshot via CDP
            capture_params = {
                'format': 'png' if format == 'png' else 'jpeg',
                'quality': quality if format == 'jpeg' else None,
                'captureBeyondViewport': full_page
            }

            # Add clip region if element specified
            if clip_region:
                capture_params['clip'] = clip_region

            # Remove None values
            capture_params = {k: v for k, v in capture_params.items() if v is not None}

            # Capture screenshot via CDP Page.captureScreenshot
            cdp_result = self.tab.Page.captureScreenshot(**capture_params)
            img_data = cdp_result.get('data', '')

            # Decode base64
            img_bytes = base64.b64decode(img_data)
            original_size = len(img_bytes)

            # Apply optimization if Pillow available and needed
            if PIL_AVAILABLE and (max_width or format == 'jpeg'):
                img_bytes = self._optimize_image(img_bytes, format, quality, max_width)

            # Save to file
            with open(path, 'wb') as f:
                f.write(img_bytes)

            # Calculate size reduction
            final_size = len(img_bytes)
            size_kb = round(final_size / 1024, 1)
            reduction_pct = round((1 - final_size / original_size) * 100, 1) if original_size > final_size else 0

            message = f"Screenshot saved to {path} ({size_kb}KB"
            if reduction_pct > 0:
                message += f", {reduction_pct}% reduction"
            message += ")"

            return {
                "success": True,
                "path": path,
                "message": message,
                "size_kb": size_kb,
                "format": format,
                "optimized": PIL_AVAILABLE and (max_width is not None or format == 'jpeg')
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to take screenshot: {str(e)}"
            }

    async def _get_element_bounds(self, selector: str) -> Optional[Dict[str, float]]:
        """Get element bounding box for clipping"""
        try:
            js_code = f"""
            (function() {{
                const el = document.querySelector({repr(selector)});
                if (!el) return null;
                const rect = el.getBoundingClientRect();
                return {{
                    x: rect.left,
                    y: rect.top,
                    width: rect.width,
                    height: rect.height,
                    scale: window.devicePixelRatio || 1
                }};
            }})()
            """
            result = await self.context.cdp.evaluate(expression=js_code, returnByValue=True)
            bounds = result.get('result', {}).get('value')
            return bounds
        except Exception:
            return None

    def _optimize_image(
        self,
        img_bytes: bytes,
        format: str,
        quality: int,
        max_width: Optional[int]
    ) -> bytes:
        """Optimize image using Pillow"""
        if not PIL_AVAILABLE:
            return img_bytes

        try:
            # Load image
            img = Image.open(io.BytesIO(img_bytes))

            # Resize if needed
            if max_width and img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

            # Save with optimization
            output = io.BytesIO()
            if format == 'jpeg':
                # Convert RGBA to RGB for JPEG
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                img.save(output, format='JPEG', quality=quality, optimize=True)
            else:
                img.save(output, format='PNG', optimize=True)

            return output.getvalue()
        except Exception:
            # Return original if optimization fails
            return img_bytes
