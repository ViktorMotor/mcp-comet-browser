"""Tab management commands: list, create, close, switch"""
from typing import Dict, Any, Optional
from .base import Command
from .registry import register
from mcp.logging_config import get_logger
from mcp.errors import BrowserError, TabNotFoundError, InvalidArgumentError

logger = get_logger("commands.tabs")


@register
class ListTabsCommand(Command):
    """List all open browser tabs"""

    name = "list_tabs"
    description = "List all open tabs in the browser"
    input_schema = {
        "type": "object",
        "properties": {}
    }

    requires_browser = True

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """List all tabs with their info"""
        logger.debug("list_tabs: querying browser tabs")
        try:
            browser = self.context.browser
            current_tab = self.tab
            tabs = browser.list_tab()

            tabs_info = []
            for tab in tabs:
                tabs_info.append({
                    "id": getattr(tab, 'id', 'unknown'),
                    "url": getattr(tab, 'url', 'unknown'),
                    "title": getattr(tab, 'title', 'untitled'),
                    "type": getattr(tab, 'type', 'page')
                })

            logger.info(f"✓ Listed {len(tabs_info)} tabs")
            return {
                "success": True,
                "tabs": tabs_info,
                "count": len(tabs_info),
                "currentTabId": getattr(current_tab, 'id', None) if current_tab else None
            }
        except Exception as e:
            logger.error(f"✗ Failed to list tabs: {str(e)}")
            raise BrowserError(f"Failed to list tabs: {str(e)}")


@register
class CreateTabCommand(Command):
    """Create a new browser tab"""

    name = "create_tab"
    description = "Create a new tab and optionally navigate to a URL"
    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to open in new tab (optional)"}
        }
    }

    requires_browser = True

    async def execute(self, url: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Create new tab with optional URL"""
        logger.info(f"create_tab: url={url or 'about:blank'}")

        # Validate URL if provided
        if url:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if not parsed.scheme:
                logger.error(f"✗ Invalid URL: {url} (missing scheme)")
                raise InvalidArgumentError(
                    argument="url",
                    expected="valid URL with scheme",
                    received=url
                )

        try:
            browser = self.context.browser
            new_tab = browser.new_tab(url=url)

            tab_id = getattr(new_tab, 'id', 'unknown')
            logger.info(f"✓ Created tab: {tab_id}")
            return {
                "success": True,
                "tabId": tab_id,
                "url": url or "about:blank",
                "message": f"Created new tab{' and opened ' + url if url else ''}"
            }
        except Exception as e:
            logger.error(f"✗ Failed to create tab: {str(e)}")
            raise BrowserError(f"Failed to create tab: {str(e)}")


@register
class CloseTabCommand(Command):
    """Close a browser tab"""

    name = "close_tab"
    description = "Close a tab by ID (closes current tab if no ID provided)"
    input_schema = {
        "type": "object",
        "properties": {
            "tab_id": {"type": "string", "description": "Tab ID to close (optional, defaults to current tab)"}
        }
    }

    requires_browser = True

    async def execute(self, tab_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Close tab by ID or current tab"""
        logger.info(f"close_tab: tab_id={tab_id or 'current'}")
        try:
            browser = self.context.browser
            current_tab = self.tab

            if tab_id is None:
                if current_tab:
                    tab_id = getattr(current_tab, 'id', None)
                    if not tab_id:
                        logger.error("✗ Current tab has no ID")
                        raise BrowserError("Current tab has no ID")
                else:
                    logger.error("✗ No current tab to close")
                    raise BrowserError("No current tab to close")

            # Find tab by ID
            tabs = browser.list_tab()
            tab_to_close = None
            for tab in tabs:
                if getattr(tab, 'id', None) == tab_id:
                    tab_to_close = tab
                    break

            if not tab_to_close:
                logger.warning(f"✗ Tab not found: {tab_id}")
                raise TabNotFoundError(message=f"Tab not found: {tab_id}", tab_id=tab_id)

            # Close the tab
            browser.close_tab(tab_to_close)

            was_current = current_tab and getattr(current_tab, 'id', None) == tab_id
            logger.info(f"✓ Closed tab: {tab_id} {'(was current)' if was_current else ''}")

            # Return info about closed tab
            return {
                "success": True,
                "tabId": tab_id,
                "message": f"Closed tab: {tab_id}",
                "wasCurrentTab": was_current
            }
        except (BrowserError, TabNotFoundError):
            raise
        except Exception as e:
            logger.error(f"✗ Failed to close tab: {str(e)}")
            raise BrowserError(f"Failed to close tab: {str(e)}")


@register
class SwitchTabCommand(Command):
    """Switch to a different tab"""

    name = "switch_tab"
    description = "Switch to a different tab by ID"
    input_schema = {
        "type": "object",
        "properties": {
            "tab_id": {"type": "string", "description": "Tab ID to switch to"}
        },
        "required": ["tab_id"]
    }

    requires_browser = True

    async def execute(self, tab_id: str, **kwargs) -> Dict[str, Any]:
        """Switch to target tab and enable necessary domains"""
        logger.info(f"switch_tab: switching to {tab_id}")
        try:
            browser = self.context.browser
            current_tab = self.tab

            # Find tab by ID
            tabs = browser.list_tab()
            target_tab = None
            for tab in tabs:
                if getattr(tab, 'id', None) == tab_id:
                    target_tab = tab
                    break

            if not target_tab:
                logger.warning(f"✗ Tab not found: {tab_id}")
                raise TabNotFoundError(message=f"Tab not found: {tab_id}", tab_id=tab_id)

            # Stop current tab
            if current_tab:
                try:
                    current_tab.stop()
                    logger.debug(f"Stopped previous tab: {getattr(current_tab, 'id', 'unknown')}")
                except Exception as e:
                    logger.debug(f"Failed to stop previous tab: {e}")

            # Switch to new tab
            target_tab.start()

            # Enable necessary domains
            target_tab.Page.enable()
            target_tab.DOM.enable()
            target_tab.Runtime.enable()
            target_tab.Console.enable()
            target_tab.Network.enable()
            target_tab.Debugger.enable()

            logger.info(f"✓ Switched to tab: {tab_id} ({getattr(target_tab, 'title', 'untitled')})")
            return {
                "success": True,
                "tabId": tab_id,
                "url": getattr(target_tab, 'url', 'unknown'),
                "title": getattr(target_tab, 'title', 'untitled'),
                "message": f"Switched to tab: {tab_id}",
                "newTab": target_tab  # Return tab object so caller can update reference
            }
        except TabNotFoundError:
            raise
        except Exception as e:
            logger.error(f"✗ Failed to switch tab: {str(e)}")
            raise BrowserError(f"Failed to switch tab: {str(e)}")
