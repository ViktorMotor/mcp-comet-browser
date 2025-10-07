"""
Command execution context for dependency injection.

Provides explicit dependency management for browser commands,
replacing hardcoded kwargs injection.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import pychrome


@dataclass
class CommandContext:
    """
    Execution context for browser commands.

    Provides all dependencies a command might need:
    - tab: Chrome DevTools Protocol tab instance
    - cursor: AI cursor for visual feedback
    - browser: Browser instance for tab management
    - console_logs: Console log history
    - connection: Full browser connection (for advanced use)
    """

    tab: pychrome.Tab
    cursor: Optional[Any] = None
    browser: Optional[pychrome.Browser] = None
    console_logs: Optional[List[Dict[str, Any]]] = None
    connection: Optional[Any] = None  # BrowserConnection instance

    def validate_requirements(
        self,
        requires_cursor: bool = False,
        requires_browser: bool = False,
        requires_console_logs: bool = False,
        requires_connection: bool = False
    ):
        """
        Validate that all required dependencies are present.

        Args:
            requires_cursor: Command needs cursor
            requires_browser: Command needs browser instance
            requires_console_logs: Command needs console logs
            requires_connection: Command needs full connection

        Raises:
            ValueError: If required dependency is missing
        """
        if requires_cursor and self.cursor is None:
            raise ValueError("Command requires cursor but none provided in context")

        if requires_browser and self.browser is None:
            raise ValueError("Command requires browser but none provided in context")

        if requires_console_logs and self.console_logs is None:
            raise ValueError("Command requires console_logs but none provided in context")

        if requires_connection and self.connection is None:
            raise ValueError("Command requires connection but none provided in context")

    def get_cursor(self):
        """Get cursor with validation"""
        if self.cursor is None:
            raise ValueError("Cursor not available in context")
        return self.cursor

    def get_browser(self):
        """Get browser with validation"""
        if self.browser is None:
            raise ValueError("Browser not available in context")
        return self.browser

    def get_console_logs(self):
        """Get console logs with validation"""
        if self.console_logs is None:
            raise ValueError("Console logs not available in context")
        return self.console_logs

    def get_connection(self):
        """Get connection with validation"""
        if self.connection is None:
            raise ValueError("Connection not available in context")
        return self.connection
