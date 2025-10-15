"""
Unit tests for commands/navigation.py - Navigation commands (open_url, get_text)
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock
from commands.navigation import OpenUrlCommand, GetTextCommand
from mcp.errors import (
    InvalidArgumentError,
    CommandTimeoutError,
    ElementNotFoundError,
    CDPError,
    CommandError
)


class TestOpenUrlCommand:
    """Test OpenUrlCommand functionality"""

    @pytest.mark.asyncio
    async def test_open_url_basic_http(self, command_context):
        """Test opening basic HTTP URL"""
        cmd = OpenUrlCommand(command_context)

        # Mock CDP navigate
        command_context.cdp.navigate = AsyncMock(return_value={"frameId": "frame123"})

        # Mock cursor initialize
        command_context.cursor.initialize = AsyncMock()

        result = await cmd.execute(url="http://example.com")

        assert result["success"] is True
        assert result["url"] == "http://example.com"
        assert "Opened" in result["message"]

        # Verify CDP called with correct params
        command_context.cdp.navigate.assert_called_once_with(url="http://example.com", timeout=30)

        # Verify cursor reinitialized
        command_context.cursor.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_open_url_https(self, command_context):
        """Test opening HTTPS URL"""
        cmd = OpenUrlCommand(command_context)

        command_context.cdp.navigate = AsyncMock(return_value={"frameId": "frame123"})
        command_context.cursor.initialize = AsyncMock()

        result = await cmd.execute(url="https://secure.example.com/path?query=value")

        assert result["success"] is True
        assert result["url"] == "https://secure.example.com/path?query=value"

    @pytest.mark.asyncio
    async def test_open_url_invalid_no_scheme(self, command_context):
        """Test URL validation - missing scheme"""
        cmd = OpenUrlCommand(command_context)

        # URL without scheme should fail
        with pytest.raises(InvalidArgumentError) as exc:
            await cmd.execute(url="example.com")

        assert exc.value.data["argument"] == "url"
        assert "scheme" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_open_url_invalid_relative(self, command_context):
        """Test URL validation - relative URL"""
        cmd = OpenUrlCommand(command_context)

        with pytest.raises(InvalidArgumentError):
            await cmd.execute(url="/path/to/page")

    @pytest.mark.asyncio
    async def test_open_url_invalid_empty(self, command_context):
        """Test URL validation - empty URL"""
        cmd = OpenUrlCommand(command_context)

        with pytest.raises(InvalidArgumentError):
            await cmd.execute(url="")

    @pytest.mark.asyncio
    async def test_open_url_timeout(self, command_context):
        """Test navigation timeout handling"""
        cmd = OpenUrlCommand(command_context)

        # Mock timeout
        command_context.cdp.navigate = AsyncMock(side_effect=asyncio.TimeoutError())

        with pytest.raises(CommandTimeoutError) as exc:
            await cmd.execute(url="http://slow.example.com")

        assert exc.value.data["command"] == "open_url"
        assert exc.value.data["timeout"] == 30

    @pytest.mark.asyncio
    async def test_open_url_cdp_error(self, command_context):
        """Test CDP navigation error"""
        cmd = OpenUrlCommand(command_context)

        # Mock CDP error
        command_context.cdp.navigate = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        with pytest.raises(CDPError) as exc:
            await cmd.execute(url="http://example.com")

        assert "Failed to navigate" in str(exc.value)
        assert "Connection refused" in str(exc.value)

    @pytest.mark.asyncio
    async def test_open_url_cursor_init_fails_gracefully(self, command_context):
        """Test that cursor initialization failure doesn't fail command"""
        cmd = OpenUrlCommand(command_context)

        command_context.cdp.navigate = AsyncMock(return_value={"frameId": "frame123"})

        # Cursor init fails, but command should still succeed
        command_context.cursor.initialize = AsyncMock(
            side_effect=Exception("Cursor init failed")
        )

        result = await cmd.execute(url="http://example.com")

        # Command should still succeed
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_open_url_no_cursor(self, command_context):
        """Test opening URL when cursor is None"""
        cmd = OpenUrlCommand(command_context)

        # Set cursor to None
        command_context.cursor = None

        command_context.cdp.navigate = AsyncMock(return_value={"frameId": "frame123"})

        result = await cmd.execute(url="http://example.com")

        # Should succeed without trying to reinitialize cursor
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_open_url_special_schemes(self, command_context):
        """Test URLs with special schemes"""
        cmd = OpenUrlCommand(command_context)

        command_context.cdp.navigate = AsyncMock(return_value={"frameId": "frame123"})
        command_context.cursor.initialize = AsyncMock()

        # File URL
        result = await cmd.execute(url="file:///path/to/file.html")
        assert result["success"] is True

        # FTP URL
        result = await cmd.execute(url="ftp://ftp.example.com/file")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_open_url_unicode(self, command_context):
        """Test URL with unicode characters"""
        cmd = OpenUrlCommand(command_context)

        command_context.cdp.navigate = AsyncMock(return_value={"frameId": "frame123"})
        command_context.cursor.initialize = AsyncMock()

        result = await cmd.execute(url="http://example.com/путь?параметр=значение")

        assert result["success"] is True

    def test_open_url_command_metadata(self):
        """Test command metadata"""
        assert OpenUrlCommand.name == "open_url"
        assert OpenUrlCommand.description is not None
        assert "url" in OpenUrlCommand.description.lower()
        assert OpenUrlCommand.input_schema["type"] == "object"

        # Check schema
        props = OpenUrlCommand.input_schema["properties"]
        assert "url" in props
        assert "url" in OpenUrlCommand.input_schema["required"]

    def test_open_url_to_mcp_tool(self):
        """Test MCP tool conversion"""
        tool = OpenUrlCommand.to_mcp_tool()

        assert tool["name"] == "open_url"
        assert "description" in tool
        assert "inputSchema" in tool

    def test_open_url_requires_dependencies(self):
        """Test that command declares required dependencies"""
        assert OpenUrlCommand.requires_cursor is True
        assert OpenUrlCommand.requires_cdp is True


class TestGetTextCommand:
    """Test GetTextCommand functionality"""

    @pytest.mark.asyncio
    async def test_get_text_basic(self, command_context):
        """Test basic text extraction"""
        cmd = GetTextCommand(command_context)

        # Mock query_selector
        command_context.cdp.query_selector = AsyncMock(
            return_value={"nodeId": 123}
        )

        # Mock evaluate (text content)
        command_context.cdp.evaluate = AsyncMock(
            return_value={
                "result": {"value": "Hello World"}
            }
        )

        result = await cmd.execute(selector="h1")

        assert result["success"] is True
        assert result["text"] == "Hello World"
        assert result["selector"] == "h1"

    @pytest.mark.asyncio
    async def test_get_text_empty_content(self, command_context):
        """Test element with empty text content"""
        cmd = GetTextCommand(command_context)

        command_context.cdp.query_selector = AsyncMock(
            return_value={"nodeId": 123}
        )

        command_context.cdp.evaluate = AsyncMock(
            return_value={"result": {"value": ""}}
        )

        result = await cmd.execute(selector="div.empty")

        assert result["success"] is True
        assert result["text"] == ""

    @pytest.mark.asyncio
    async def test_get_text_complex_selector(self, command_context):
        """Test complex CSS selector"""
        cmd = GetTextCommand(command_context)

        command_context.cdp.query_selector = AsyncMock(
            return_value={"nodeId": 456}
        )

        command_context.cdp.evaluate = AsyncMock(
            return_value={"result": {"value": "Complex text"}}
        )

        result = await cmd.execute(selector="div.container > p:first-child")

        assert result["success"] is True
        assert result["text"] == "Complex text"

    @pytest.mark.asyncio
    async def test_get_text_selector_validation_empty(self, command_context):
        """Test selector validation - empty selector"""
        cmd = GetTextCommand(command_context)

        with pytest.raises(InvalidArgumentError) as exc:
            await cmd.execute(selector="")

        assert exc.value.data["argument"] == "selector"
        assert "non-empty" in str(exc.value)

    @pytest.mark.asyncio
    async def test_get_text_selector_validation_whitespace(self, command_context):
        """Test selector validation - whitespace only"""
        cmd = GetTextCommand(command_context)

        with pytest.raises(InvalidArgumentError):
            await cmd.execute(selector="   \n\t  ")

    @pytest.mark.asyncio
    async def test_get_text_element_not_found(self, command_context):
        """Test element not found"""
        cmd = GetTextCommand(command_context)

        # query_selector returns empty nodeId
        command_context.cdp.query_selector = AsyncMock(
            return_value={}
        )

        with pytest.raises(ElementNotFoundError) as exc:
            await cmd.execute(selector="#nonexistent")

        assert exc.value.data["selector"] == "#nonexistent"

    @pytest.mark.asyncio
    async def test_get_text_element_not_found_none_node_id(self, command_context):
        """Test element not found - None nodeId"""
        cmd = GetTextCommand(command_context)

        command_context.cdp.query_selector = AsyncMock(
            return_value={"nodeId": None}
        )

        with pytest.raises(ElementNotFoundError):
            await cmd.execute(selector=".missing")

    @pytest.mark.asyncio
    async def test_get_text_cdp_query_error(self, command_context):
        """Test CDP query selector error"""
        cmd = GetTextCommand(command_context)

        command_context.cdp.query_selector = AsyncMock(
            side_effect=Exception("Invalid selector syntax")
        )

        with pytest.raises(CommandError) as exc:
            await cmd.execute(selector="invalid[[[")

        assert "Failed to get text" in str(exc.value)

    @pytest.mark.asyncio
    async def test_get_text_cdp_evaluate_error(self, command_context):
        """Test CDP evaluate error"""
        cmd = GetTextCommand(command_context)

        command_context.cdp.query_selector = AsyncMock(
            return_value={"nodeId": 123}
        )

        command_context.cdp.evaluate = AsyncMock(
            side_effect=Exception("Evaluation failed")
        )

        with pytest.raises(CommandError):
            await cmd.execute(selector="h1")

    @pytest.mark.asyncio
    async def test_get_text_special_characters(self, command_context):
        """Test selector with special characters"""
        cmd = GetTextCommand(command_context)

        command_context.cdp.query_selector = AsyncMock(
            return_value={"nodeId": 789}
        )

        command_context.cdp.evaluate = AsyncMock(
            return_value={"result": {"value": "Text with \"quotes\" and 'apostrophes'"}}
        )

        result = await cmd.execute(selector="div[data-test='value']")

        assert result["success"] is True
        assert "quotes" in result["text"]

    @pytest.mark.asyncio
    async def test_get_text_unicode(self, command_context):
        """Test text with unicode characters"""
        cmd = GetTextCommand(command_context)

        command_context.cdp.query_selector = AsyncMock(
            return_value={"nodeId": 111}
        )

        command_context.cdp.evaluate = AsyncMock(
            return_value={"result": {"value": "Привет мир! 你好世界"}}
        )

        result = await cmd.execute(selector=".unicode-text")

        assert result["success"] is True
        assert "Привет" in result["text"]
        assert "你好" in result["text"]

    @pytest.mark.asyncio
    async def test_get_text_whitespace_normalization(self, command_context):
        """Test that textContent.trim() is used"""
        cmd = GetTextCommand(command_context)

        command_context.cdp.query_selector = AsyncMock(
            return_value={"nodeId": 222}
        )

        # Simulate JS trimming (this is done in browser)
        command_context.cdp.evaluate = AsyncMock(
            return_value={"result": {"value": "Trimmed text"}}
        )

        result = await cmd.execute(selector="p")

        assert result["success"] is True
        assert result["text"] == "Trimmed text"

    @pytest.mark.asyncio
    async def test_get_text_attribute_selector(self, command_context):
        """Test attribute selectors"""
        cmd = GetTextCommand(command_context)

        command_context.cdp.query_selector = AsyncMock(
            return_value={"nodeId": 333}
        )

        command_context.cdp.evaluate = AsyncMock(
            return_value={"result": {"value": "Button text"}}
        )

        result = await cmd.execute(selector="button[type='submit']")

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_get_text_element_not_found_reraise(self, command_context):
        """Test that ElementNotFoundError is re-raised correctly"""
        cmd = GetTextCommand(command_context)

        command_context.cdp.query_selector = AsyncMock(
            return_value={"nodeId": 0}  # Falsy nodeId
        )

        with pytest.raises(ElementNotFoundError):
            await cmd.execute(selector="#test")

    def test_get_text_command_metadata(self):
        """Test command metadata"""
        assert GetTextCommand.name == "get_text"
        assert GetTextCommand.description is not None
        assert "text" in GetTextCommand.description.lower()
        assert GetTextCommand.input_schema["type"] == "object"

        # Check schema
        props = GetTextCommand.input_schema["properties"]
        assert "selector" in props
        assert "selector" in GetTextCommand.input_schema["required"]

    def test_get_text_to_mcp_tool(self):
        """Test MCP tool conversion"""
        tool = GetTextCommand.to_mcp_tool()

        assert tool["name"] == "get_text"
        assert "description" in tool
        assert "inputSchema" in tool

    def test_get_text_requires_dependencies(self):
        """Test that command declares required dependencies"""
        assert GetTextCommand.requires_cdp is True
        # Cursor not required for get_text
        assert GetTextCommand.requires_cursor is False


class TestNavigationEdgeCases:
    """Test edge cases and integration scenarios"""

    @pytest.mark.asyncio
    async def test_open_url_then_get_text(self, command_context):
        """Test navigation followed by text extraction"""
        open_cmd = OpenUrlCommand(command_context)
        get_cmd = GetTextCommand(command_context)

        # Setup mocks
        command_context.cdp.navigate = AsyncMock(return_value={"frameId": "frame123"})
        command_context.cursor.initialize = AsyncMock()
        command_context.cdp.query_selector = AsyncMock(
            return_value={"nodeId": 123}
        )
        command_context.cdp.evaluate = AsyncMock(
            return_value={"result": {"value": "Page loaded"}}
        )

        # Navigate
        nav_result = await open_cmd.execute(url="http://example.com")
        assert nav_result["success"] is True

        # Extract text
        text_result = await get_cmd.execute(selector="h1")
        assert text_result["success"] is True
        assert text_result["text"] == "Page loaded"

    @pytest.mark.asyncio
    async def test_multiple_get_text_calls(self, command_context):
        """Test multiple text extractions in sequence"""
        cmd = GetTextCommand(command_context)

        # Mock different responses
        command_context.cdp.query_selector = AsyncMock(
            return_value={"nodeId": 123}
        )

        responses = [
            {"result": {"value": "First text"}},
            {"result": {"value": "Second text"}},
            {"result": {"value": "Third text"}},
        ]
        command_context.cdp.evaluate = AsyncMock(side_effect=responses)

        result1 = await cmd.execute(selector=".first")
        result2 = await cmd.execute(selector=".second")
        result3 = await cmd.execute(selector=".third")

        assert result1["text"] == "First text"
        assert result2["text"] == "Second text"
        assert result3["text"] == "Third text"

    @pytest.mark.asyncio
    async def test_open_url_with_fragment(self, command_context):
        """Test URL with fragment identifier"""
        cmd = OpenUrlCommand(command_context)

        command_context.cdp.navigate = AsyncMock(return_value={"frameId": "frame123"})
        command_context.cursor.initialize = AsyncMock()

        result = await cmd.execute(url="http://example.com/page#section")

        assert result["success"] is True
        assert "#section" in result["url"]

    @pytest.mark.asyncio
    async def test_get_text_pseudo_selector(self, command_context):
        """Test pseudo-class selectors"""
        cmd = GetTextCommand(command_context)

        command_context.cdp.query_selector = AsyncMock(
            return_value={"nodeId": 999}
        )

        command_context.cdp.evaluate = AsyncMock(
            return_value={"result": {"value": "First item"}}
        )

        result = await cmd.execute(selector="li:first-child")

        assert result["success"] is True
