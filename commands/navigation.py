"""Navigation commands: open_url, get_text"""
import asyncio
from typing import Dict, Any
from urllib.parse import urlparse
from .base import Command
from .registry import register
from mcp.logging_config import get_logger
from mcp.errors import (
    CommandError,
    CommandTimeoutError,
    ElementNotFoundError,
    InvalidArgumentError,
    CDPError
)

logger = get_logger("commands.navigation")


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
        logger.info(f"open_url: navigating to {url}")

        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme:
            logger.error(f"✗ Invalid URL: {url} (missing scheme)")
            raise InvalidArgumentError(
                argument="url",
                expected="valid URL with scheme (http:// or https://)",
                received=url
            )

        try:
            await self.cdp.navigate(url=url, timeout=30)
        except asyncio.TimeoutError:
            logger.error(f"✗ Navigation timeout: {url} (30s)")
            raise CommandTimeoutError(command="open_url", timeout_seconds=30)
        except Exception as e:
            logger.error(f"✗ Navigation failed: {url} - {str(e)}")
            raise CDPError(f"Failed to navigate to URL: {str(e)}")

        # Wait for page load
        await asyncio.sleep(2)

        # Re-initialize cursor after page load (navigation clears it)
        cursor = self.context.cursor
        if cursor:
            try:
                await cursor.initialize()
            except Exception as e:
                # Cursor init failure is not critical
                logger.debug(f"Cursor init failed after navigation: {e}")

        logger.info(f"✓ Navigation complete: {url}")
        return {"success": True, "url": url, "message": f"Opened {url}"}


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
        logger.debug(f"get_text: selector='{selector}'")

        # Validate selector (basic check)
        if not selector or not selector.strip():
            logger.error(f"✗ Invalid selector: empty")
            raise InvalidArgumentError(
                argument="selector",
                expected="non-empty CSS selector",
                received=selector
            )

        try:
            # Query selector using AsyncCDP
            result = await self.cdp.query_selector(selector=selector)

            if not result.get('nodeId'):
                logger.warning(f"✗ Element not found: '{selector}'")
                raise ElementNotFoundError(selector=selector)

            # Use JS to get text content (escape selector properly)
            js_code = f"""
            (function() {{
                const el = document.querySelector({repr(selector)});
                return el ? el.textContent.trim() : '';
            }})()
            """

            eval_result = await self.cdp.evaluate(expression=js_code, returnByValue=True)
            text = eval_result.get('result', {}).get('value', '')

            logger.info(f"✓ Text extracted from '{selector}': {text[:50]}{'...' if len(text) > 50 else ''}")
            return {"success": True, "text": text, "selector": selector}
        except ElementNotFoundError:
            raise
        except Exception as e:
            logger.error(f"✗ Failed to get text from '{selector}': {str(e)}")
            raise CommandError(f"Failed to get text from '{selector}': {str(e)}")
