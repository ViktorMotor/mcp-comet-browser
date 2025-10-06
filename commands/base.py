"""Base command class for MCP browser commands"""
from typing import Any, Dict
from abc import ABC, abstractmethod


class Command(ABC):
    """Abstract base class for browser commands"""

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

    @property
    @abstractmethod
    def name(self) -> str:
        """Command name for MCP registration"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Command description for MCP"""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """JSON schema for command parameters"""
        pass

    def to_mcp_tool(self) -> Dict[str, Any]:
        """Convert command to MCP tool definition"""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        }
