"""
Exception hierarchy for MCP Comet Browser.

Provides typed exceptions with JSON-RPC error codes for better error handling.
"""

import traceback
from typing import Optional, Dict, Any


class MCPError(Exception):
    """Base exception for all MCP errors"""

    def __init__(self, message: str, code: int = -32000, data: Optional[Dict[str, Any]] = None):
        """
        Initialize MCP error.

        Args:
            message: Human-readable error message
            code: JSON-RPC error code
            data: Optional additional error data
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data or {}

    def to_jsonrpc_error(self, include_stack: bool = True) -> Dict[str, Any]:
        """Convert to JSON-RPC error response (v3.0.0: with stack traces)

        Args:
            include_stack: Include stack trace in error data (default: True)

        Returns:
            JSON-RPC error dict
        """
        error = {
            "code": self.code,
            "message": self.message
        }

        # Merge data with stack trace (v3.0.0)
        data = self.data.copy() if self.data else {}

        if include_stack and self.__traceback__:
            # Extract stack trace for debugging
            tb_lines = traceback.format_tb(self.__traceback__)
            data["traceback"] = tb_lines
            data["traceback_summary"] = "".join(tb_lines[-3:])  # Last 3 frames

        if data:
            error["data"] = data

        return error


# Browser connection errors (-32100 to -32199)
class BrowserError(MCPError):
    """Base class for browser-related errors"""

    def __init__(self, message: str, code: int = -32100, data: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, data)


class ConnectionError(BrowserError):
    """Failed to connect to browser"""

    def __init__(self, message: str, host: Optional[str] = None, port: Optional[int] = None):
        data = {}
        if host:
            data["host"] = host
        if port:
            data["port"] = port
        super().__init__(message, code=-32101, data=data)


class TabNotFoundError(BrowserError):
    """Tab not found or closed"""

    def __init__(self, message: str, tab_id: Optional[str] = None):
        data = {"tab_id": tab_id} if tab_id else {}
        super().__init__(message, code=-32102, data=data)


class TabStoppedError(BrowserError):
    """Tab has been stopped or disconnected"""

    def __init__(self, message: str = "Tab has been stopped"):
        super().__init__(message, code=-32103)


# Command execution errors (-32200 to -32299)
class CommandError(MCPError):
    """Base class for command execution errors"""

    def __init__(self, message: str, code: int = -32200, data: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, data)


class ElementNotFoundError(CommandError):
    """Element not found on page"""

    def __init__(self, selector: str, message: Optional[str] = None):
        msg = message or f"Element not found: {selector}"
        super().__init__(msg, code=-32201, data={"selector": selector})


class ElementNotVisibleError(CommandError):
    """Element found but not visible"""

    def __init__(self, selector: str, reason: Optional[str] = None):
        msg = f"Element not visible: {selector}"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg, code=-32202, data={"selector": selector, "reason": reason})


class InvalidSelectorError(CommandError):
    """Invalid CSS selector or XPath"""

    def __init__(self, selector: str, details: Optional[str] = None):
        msg = f"Invalid selector: {selector}"
        if details:
            msg += f" - {details}"
        super().__init__(msg, code=-32203, data={"selector": selector})


class CommandTimeoutError(CommandError):
    """Command execution timed out"""

    def __init__(self, command: str, timeout_seconds: float):
        msg = f"Command '{command}' timed out after {timeout_seconds}s"
        super().__init__(msg, code=-32204, data={
            "command": command,
            "timeout": timeout_seconds
        })


# CDP protocol errors (-32300 to -32399)
class CDPError(MCPError):
    """Base class for Chrome DevTools Protocol errors"""

    def __init__(self, message: str, code: int = -32300, data: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, data)


class CDPTimeoutError(CDPError):
    """CDP command timed out"""

    def __init__(self, method: str, timeout_seconds: float):
        msg = f"CDP command '{method}' timed out after {timeout_seconds}s"
        super().__init__(msg, code=-32301, data={
            "method": method,
            "timeout": timeout_seconds
        })


class CDPProtocolError(CDPError):
    """CDP protocol error"""

    def __init__(self, method: str, error_message: str):
        msg = f"CDP error in '{method}': {error_message}"
        super().__init__(msg, code=-32302, data={
            "method": method,
            "cdp_error": error_message
        })


# Validation errors (-32400 to -32499)
class ValidationError(MCPError):
    """Base class for validation errors"""

    def __init__(self, message: str, code: int = -32400, data: Optional[Dict[str, Any]] = None):
        super().__init__(message, code, data)


class InvalidArgumentError(ValidationError):
    """Invalid argument provided"""

    def __init__(self, argument: str, expected: str, received: Any):
        msg = f"Invalid argument '{argument}': expected {expected}, got {type(received).__name__}"
        super().__init__(msg, code=-32401, data={
            "argument": argument,
            "expected": expected,
            "received": str(received)
        })


class MissingArgumentError(ValidationError):
    """Required argument missing"""

    def __init__(self, argument: str):
        msg = f"Missing required argument: {argument}"
        super().__init__(msg, code=-32402, data={"argument": argument})


# Standard JSON-RPC errors
class ParseError(MCPError):
    """JSON parse error"""

    def __init__(self, details: str):
        super().__init__(f"Parse error: {details}", code=-32700)


class InvalidRequest(MCPError):
    """Invalid JSON-RPC request"""

    def __init__(self, details: str):
        super().__init__(f"Invalid request: {details}", code=-32600)


class MethodNotFound(MCPError):
    """JSON-RPC method not found"""

    def __init__(self, method: str):
        super().__init__(f"Method not found: {method}", code=-32601, data={"method": method})


class InternalError(MCPError):
    """Internal JSON-RPC error"""

    def __init__(self, details: str):
        super().__init__(f"Internal error: {details}", code=-32603)
