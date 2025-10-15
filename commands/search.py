"""Search and query commands for finding elements"""
from typing import Dict, Any, Optional
from .base import Command
from .registry import register


@register
class FindElementsCommand(Command):
    """Find all elements matching criteria (text, tag, attributes)"""

    name = "find_elements"
    description = """Find elements on the page (text, tag, attributes).

Auto-redirects to save_page_info() due to Claude Code output limitations.
After calling this, use Read('./page_info.json') to see all interactive elements."""
    input_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text content to search for (partial match)"},
            "tag": {"type": "string", "description": "HTML tag name (e.g., 'button', 'a', 'div')"},
            "attribute": {"type": "string", "description": "Attribute name to check (e.g., 'role', 'aria-label')"},
            "attribute_value": {"type": "string", "description": "Value for the attribute"},
            "visible_only": {"type": "boolean", "description": "Only return visible elements", "default": True},
            "limit": {"type": "integer", "description": "Maximum number of results", "default": 20}
        }
    }

    async def execute(self, text: Optional[str] = None, tag: Optional[str] = None,
                     attribute: Optional[str] = None, attribute_value: Optional[str] = None,
                     visible_only: bool = True, limit: int = 20) -> Dict[str, Any]:
        """Auto-redirect to save_page_info (workaround for MCP output issue)"""
        from utils.page_scraper import PageScraper

        # Use shared scraping utility (eliminates code duplication)
        return await PageScraper.scrape_and_save(self.context.cdp, "./page_info.json")


@register
class GetPageStructureCommand(Command):
    """Get page structure overview (headings, links, buttons, forms)"""

    name = "get_page_structure"
    description = """Get page structure (headings, links, buttons, forms).

Auto-redirects to save_page_info() due to Claude Code output limitations.
After calling this, use Read('./page_info.json') to see page structure."""
    input_schema = {
        "type": "object",
        "properties": {
            "include_text": {"type": "boolean", "description": "Include text content", "default": True}
        }
    }

    async def execute(self, include_text: bool = True) -> Dict[str, Any]:
        """Auto-redirect to save_page_info (workaround for MCP output issue)"""
        from utils.page_scraper import PageScraper

        # Use shared scraping utility (eliminates code duplication)
        return await PageScraper.scrape_and_save(self.context.cdp, "./page_info.json")
