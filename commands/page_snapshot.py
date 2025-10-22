"""Lightweight text-based page snapshot (replaces heavy screenshots)"""
from typing import Dict, Any
from .base import Command
from .registry import register
from mcp.logging_config import get_logger

logger = get_logger("commands.page_snapshot")


@register
class PageSnapshotCommand(Command):
    """Get lightweight text-based page snapshot instead of heavy screenshot"""

    name = "get_page_snapshot"
    description = """Get lightweight text-based page snapshot.

Auto-redirects to save_page_info() due to Claude Code output limitations.
After calling this, use Read('./page_info.json') to see page snapshot."""
    input_schema = {
        "type": "object",
        "properties": {
            "include_styles": {"type": "boolean", "description": "Include computed styles", "default": False},
            "max_depth": {"type": "integer", "description": "Max DOM depth to traverse", "default": 3}
        }
    }

    async def execute(self, include_styles: bool = False, max_depth: int = 3) -> Dict[str, Any]:
        """Auto-redirect to save_page_info (workaround for MCP output issue)"""
        from utils.page_scraper import PageScraper

        # Use shared scraping utility (eliminates code duplication)
        return await PageScraper.scrape_and_save(self.context.cdp, "./page_info.json")
