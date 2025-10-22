"""Generate comprehensive DevTools report"""
from typing import Dict, Any
from .base import Command
from .registry import register
from mcp.logging_config import get_logger

logger = get_logger("commands.devtools_report")


@register
class DevToolsReportCommand(Command):
    """Generate comprehensive DevTools debugging report"""

    name = "devtools_report"
    description = """Generate comprehensive DevTools debugging report.

Auto-redirects to save_page_info() due to Claude Code output limitations.
After calling this, use Read('./page_info.json') to see full report."""
    input_schema = {
        "type": "object",
        "properties": {
            "include_dom": {"type": "boolean", "description": "Include DOM tree snapshot", "default": False}
        }
    }

    requires_console_logs = True

    async def execute(self, include_dom: bool = False, **kwargs) -> Dict[str, Any]:
        """Auto-redirect to save_page_info (workaround for MCP output issue)"""
        from utils.page_scraper import PageScraper

        # Use shared scraping utility (eliminates code duplication)
        return await PageScraper.scrape_and_save(self.context.cdp, "./page_info.json")
