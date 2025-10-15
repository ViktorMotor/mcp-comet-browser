"""
Unit tests for mcp/errors.py - Exception hierarchy
"""
import pytest
from mcp.errors import (
    MCPError,
    CommandError,
    BrowserError,
    InvalidArgumentError,
    ValidationError,
    ElementNotFoundError,
    TabNotFoundError,
    CommandTimeoutError,
    CDPError
)


class TestMCPErrorHierarchy:
    """Test exception hierarchy and serialization"""

    def test_base_mcp_error(self):
        """Test base MCPError exception"""
        error = MCPError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_command_error(self):
        """Test CommandError with message"""
        error = CommandError("Failed to click element")
        assert "Failed to click element" in str(error)

    def test_browser_error(self):
        """Test BrowserError"""
        error = BrowserError("Browser connection failed")
        assert isinstance(error, MCPError)
        assert "Browser connection failed" in str(error)

    def test_invalid_argument_error(self):
        """Test InvalidArgumentError with parameter details"""
        error = InvalidArgumentError(
            argument="x",
            expected="0-10000",
            received=-100
        )
        assert "x" in str(error)
        assert isinstance(error, ValidationError)

    def test_validation_error(self):
        """Test ValidationError"""
        error = ValidationError("Invalid input format")
        assert isinstance(error, MCPError)

    def test_element_not_found_error(self):
        """Test ElementNotFoundError with selector"""
        error = ElementNotFoundError(selector="#submit-btn")
        assert "#submit-btn" in str(error)
        assert isinstance(error, CommandError)

    def test_tab_not_found_error(self):
        """Test TabNotFoundError with tab ID"""
        error = TabNotFoundError(message="Tab not found: tab-123", tab_id="tab-123")
        assert "tab-123" in str(error)
        assert isinstance(error, BrowserError)

    def test_command_timeout_error(self):
        """Test CommandTimeoutError"""
        error = CommandTimeoutError(
            command="open_url",
            timeout_seconds=30
        )
        assert "open_url" in str(error)
        assert "30" in str(error)
        assert isinstance(error, CommandError)

    def test_cdp_error(self):
        """Test CDPError"""
        error = CDPError("CDP method failed")
        assert isinstance(error, MCPError)
        assert "CDP" in str(error)


class TestErrorSerialization:
    """Test error serialization to JSON-RPC format"""

    def test_error_has_message(self):
        """All errors should have a message"""
        errors = [
            MCPError("test"),
            CommandError("test"),
            BrowserError("test"),
            ValidationError("test"),
            ElementNotFoundError("#btn")
        ]

        for error in errors:
            assert str(error)
            assert len(str(error)) > 0

    def test_error_inheritance(self):
        """Test proper exception inheritance chain"""
        # CommandError inherits from MCPError
        assert issubclass(CommandError, MCPError)

        # BrowserError inherits from MCPError
        assert issubclass(BrowserError, MCPError)

        # ElementNotFoundError inherits from CommandError
        assert issubclass(ElementNotFoundError, CommandError)

        # TabNotFoundError inherits from BrowserError
        assert issubclass(TabNotFoundError, BrowserError)

    def test_can_catch_with_base_exception(self):
        """Test that derived exceptions can be caught with base class"""
        try:
            raise ElementNotFoundError("#btn")
        except CommandError as e:
            assert isinstance(e, ElementNotFoundError)
        except Exception:
            pytest.fail("Should have caught with CommandError")

        try:
            raise TabNotFoundError("not found", tab_id="tab-1")
        except BrowserError as e:
            assert isinstance(e, TabNotFoundError)
        except Exception:
            pytest.fail("Should have caught with BrowserError")
