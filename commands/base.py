"""Base command class for MCP browser commands"""
from typing import Any, Dict
from abc import ABC, abstractmethod
from .context import CommandContext


class Command(ABC):
    """Abstract base class for browser commands

    Subclasses must define class attributes:
        name: str - Command name for MCP registration
        description: str - Command description for MCP
        input_schema: Dict[str, Any] - JSON schema for command parameters

    Dependency declarations (optional class attributes):
        requires_cursor: bool = False - Command needs AI cursor
        requires_browser: bool = False - Command needs browser instance
        requires_console_logs: bool = False - Command needs console logs
        requires_connection: bool = False - Command needs full connection
        requires_cdp: bool = False - Command needs AsyncCDP wrapper
    """

    # Class attributes - must be overridden by subclasses
    name: str = None
    description: str = None
    input_schema: Dict[str, Any] = None

    # Dependency declarations - optional
    requires_cursor: bool = False
    requires_browser: bool = False
    requires_console_logs: bool = False
    requires_connection: bool = False
    requires_cdp: bool = False

    def __init__(self, context: CommandContext):
        """Initialize command with execution context

        Args:
            context: CommandContext with all dependencies
        """
        # Validate required dependencies
        context.validate_requirements(
            requires_cursor=self.requires_cursor,
            requires_browser=self.requires_browser,
            requires_console_logs=self.requires_console_logs,
            requires_connection=self.requires_connection,
            requires_cdp=self.requires_cdp
        )

        self.context = context
        self.tab = context.tab  # Backward compatibility
        self.cdp = context.cdp  # AsyncCDP wrapper

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the command

        Returns:
            Dict with command result including 'success' key
        """
        pass

    @classmethod
    def to_mcp_tool(cls) -> Dict[str, Any]:
        """Convert command to MCP tool definition

        Returns:
            Dict with tool definition for MCP protocol
        """
        return {
            "name": cls.name,
            "description": cls.description,
            "inputSchema": cls.input_schema
        }
