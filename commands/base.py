"""Base command class for MCP browser commands"""
from typing import Any, Dict
from abc import ABC, abstractmethod


class Command(ABC):
    """Abstract base class for browser commands

    Subclasses must define class attributes:
        name: str - Command name for MCP registration
        description: str - Command description for MCP
        input_schema: Dict[str, Any] - JSON schema for command parameters
    """

    # Class attributes - must be overridden by subclasses
    name: str = None
    description: str = None
    input_schema: Dict[str, Any] = None

    def __init__(self, tab):
        """Initialize command with browser tab reference

        Args:
            tab: pychrome Tab instance
        """
        self.tab = tab

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
