"""Tab management commands: list, create, close, switch"""
from typing import Dict, Any, Optional
from .base import Command


class ListTabsCommand(Command):
    """List all open browser tabs"""

    @property
    def name(self) -> str:
        return "list_tabs"

    @property
    def description(self) -> str:
        return "List all open tabs in the browser"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    async def execute(self, browser, current_tab) -> Dict[str, Any]:
        """List all tabs with their info"""
        try:
            tabs = browser.list_tab()

            tabs_info = []
            for tab in tabs:
                tabs_info.append({
                    "id": getattr(tab, 'id', 'unknown'),
                    "url": getattr(tab, 'url', 'unknown'),
                    "title": getattr(tab, 'title', 'untitled'),
                    "type": getattr(tab, 'type', 'page')
                })

            return {
                "success": True,
                "tabs": tabs_info,
                "count": len(tabs_info),
                "currentTabId": getattr(current_tab, 'id', None) if current_tab else None
            }
        except Exception as e:
            raise RuntimeError(f"Failed to list tabs: {str(e)}")


class CreateTabCommand(Command):
    """Create a new browser tab"""

    @property
    def name(self) -> str:
        return "create_tab"

    @property
    def description(self) -> str:
        return "Create a new tab and optionally navigate to a URL"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to open in new tab (optional)"}
            }
        }

    async def execute(self, browser, url: Optional[str] = None) -> Dict[str, Any]:
        """Create new tab with optional URL"""
        try:
            new_tab = browser.new_tab(url=url)

            return {
                "success": True,
                "tabId": getattr(new_tab, 'id', 'unknown'),
                "url": url or "about:blank",
                "message": f"Created new tab{' and opened ' + url if url else ''}"
            }
        except Exception as e:
            raise RuntimeError(f"Failed to create tab: {str(e)}")


class CloseTabCommand(Command):
    """Close a browser tab"""

    @property
    def name(self) -> str:
        return "close_tab"

    @property
    def description(self) -> str:
        return "Close a tab by ID (closes current tab if no ID provided)"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string", "description": "Tab ID to close (optional, defaults to current tab)"}
            }
        }

    async def execute(self, browser, current_tab, tab_id: Optional[str] = None) -> Dict[str, Any]:
        """Close tab by ID or current tab"""
        try:
            if tab_id is None:
                if current_tab:
                    tab_id = getattr(current_tab, 'id', None)
                    if not tab_id:
                        return {"success": False, "message": "Current tab has no ID"}
                else:
                    return {"success": False, "message": "No current tab to close"}

            # Find tab by ID
            tabs = browser.list_tab()
            tab_to_close = None
            for tab in tabs:
                if getattr(tab, 'id', None) == tab_id:
                    tab_to_close = tab
                    break

            if not tab_to_close:
                return {"success": False, "message": f"Tab not found: {tab_id}"}

            # Close the tab
            browser.close_tab(tab_to_close)

            # Return info about closed tab
            return {
                "success": True,
                "tabId": tab_id,
                "message": f"Closed tab: {tab_id}",
                "wasCurrentTab": current_tab and getattr(current_tab, 'id', None) == tab_id
            }
        except Exception as e:
            raise RuntimeError(f"Failed to close tab: {str(e)}")


class SwitchTabCommand(Command):
    """Switch to a different tab"""

    @property
    def name(self) -> str:
        return "switch_tab"

    @property
    def description(self) -> str:
        return "Switch to a different tab by ID"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string", "description": "Tab ID to switch to"}
            },
            "required": ["tab_id"]
        }

    async def execute(self, browser, current_tab, tab_id: str) -> Dict[str, Any]:
        """Switch to target tab and enable necessary domains"""
        try:
            # Find tab by ID
            tabs = browser.list_tab()
            target_tab = None
            for tab in tabs:
                if getattr(tab, 'id', None) == tab_id:
                    target_tab = tab
                    break

            if not target_tab:
                return {"success": False, "message": f"Tab not found: {tab_id}"}

            # Stop current tab
            if current_tab:
                try:
                    current_tab.stop()
                except:
                    pass

            # Switch to new tab
            target_tab.start()

            # Enable necessary domains
            target_tab.Page.enable()
            target_tab.DOM.enable()
            target_tab.Runtime.enable()
            target_tab.Console.enable()
            target_tab.Network.enable()
            target_tab.Debugger.enable()

            return {
                "success": True,
                "tabId": tab_id,
                "url": getattr(target_tab, 'url', 'unknown'),
                "title": getattr(target_tab, 'title', 'untitled'),
                "message": f"Switched to tab: {tab_id}",
                "newTab": target_tab  # Return tab object so caller can update reference
            }
        except Exception as e:
            raise RuntimeError(f"Failed to switch tab: {str(e)}")
