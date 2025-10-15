"""Unit tests for commands/search.py - Search and query commands

Coverage target: 90%+
Focus: FindElementsCommand, GetPageStructureCommand, PageScraper redirection
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from commands.search import FindElementsCommand, GetPageStructureCommand
from commands.context import CommandContext


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_cdp():
    """Create mock AsyncCDP wrapper"""
    cdp = AsyncMock()
    return cdp


@pytest.fixture
def mock_context(mock_cdp):
    """Create CommandContext with mocked CDP"""
    context = CommandContext(
        tab=Mock(),
        cursor=None,
        browser=None,
        cdp=mock_cdp
    )
    return context


# ============================================================================
# FindElementsCommand Tests
# ============================================================================

class TestFindElementsCommand:
    """Test FindElementsCommand redirection to PageScraper"""

    @pytest.mark.asyncio
    async def test_execute_redirects_to_page_scraper(self, mock_context):
        """Should redirect to PageScraper.scrape_and_save()"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {
                "success": True,
                "message": "Page info saved to page_info.json",
                "file": "./page_info.json",
                "size_kb": 3.5
            }

            cmd = FindElementsCommand(mock_context)
            result = await cmd.execute()

            # Verify PageScraper was called
            mock_scrape.assert_called_once_with(mock_context.cdp, "./page_info.json")

            # Verify result
            assert result["success"] is True
            assert result["file"] == "./page_info.json"

    @pytest.mark.asyncio
    async def test_execute_with_text_param(self, mock_context):
        """Should accept text parameter (even if not used)"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {"success": True, "file": "./page_info.json"}

            cmd = FindElementsCommand(mock_context)
            result = await cmd.execute(text="Submit")

            # Parameters are accepted but not used (PageScraper doesn't support them yet)
            assert result["success"] is True
            mock_scrape.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_tag_param(self, mock_context):
        """Should accept tag parameter (even if not used)"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {"success": True, "file": "./page_info.json"}

            cmd = FindElementsCommand(mock_context)
            result = await cmd.execute(tag="button")

            assert result["success"] is True
            mock_scrape.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_attribute_params(self, mock_context):
        """Should accept attribute and attribute_value parameters"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {"success": True, "file": "./page_info.json"}

            cmd = FindElementsCommand(mock_context)
            result = await cmd.execute(attribute="role", attribute_value="button")

            assert result["success"] is True
            mock_scrape.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_visible_only_param(self, mock_context):
        """Should accept visible_only parameter"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {"success": True, "file": "./page_info.json"}

            cmd = FindElementsCommand(mock_context)
            result = await cmd.execute(visible_only=False)

            assert result["success"] is True
            mock_scrape.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_limit_param(self, mock_context):
        """Should accept limit parameter"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {"success": True, "file": "./page_info.json"}

            cmd = FindElementsCommand(mock_context)
            result = await cmd.execute(limit=50)

            assert result["success"] is True
            mock_scrape.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_all_params(self, mock_context):
        """Should accept all parameters"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {"success": True, "file": "./page_info.json"}

            cmd = FindElementsCommand(mock_context)
            result = await cmd.execute(
                text="Click me",
                tag="button",
                attribute="role",
                attribute_value="button",
                visible_only=True,
                limit=10
            )

            assert result["success"] is True
            mock_scrape.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_default_params(self, mock_context):
        """Should use default parameters when not specified"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {"success": True, "file": "./page_info.json"}

            cmd = FindElementsCommand(mock_context)
            result = await cmd.execute()

            # Defaults: visible_only=True, limit=20
            assert result["success"] is True
            mock_scrape.assert_called_once_with(mock_context.cdp, "./page_info.json")

    @pytest.mark.asyncio
    async def test_execute_passes_cdp_context(self, mock_context):
        """Should pass CDP from context to PageScraper"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {"success": True}

            cmd = FindElementsCommand(mock_context)
            await cmd.execute()

            # Verify CDP was passed
            call_args = mock_scrape.call_args
            assert call_args[0][0] == mock_context.cdp  # First argument
            assert call_args[0][1] == "./page_info.json"  # Second argument


# ============================================================================
# GetPageStructureCommand Tests
# ============================================================================

class TestGetPageStructureCommand:
    """Test GetPageStructureCommand redirection to PageScraper"""

    @pytest.mark.asyncio
    async def test_execute_redirects_to_page_scraper(self, mock_context):
        """Should redirect to PageScraper.scrape_and_save()"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {
                "success": True,
                "message": "Page info saved to page_info.json",
                "file": "./page_info.json",
                "size_kb": 3.5
            }

            cmd = GetPageStructureCommand(mock_context)
            result = await cmd.execute()

            # Verify PageScraper was called
            mock_scrape.assert_called_once_with(mock_context.cdp, "./page_info.json")

            # Verify result
            assert result["success"] is True
            assert result["file"] == "./page_info.json"

    @pytest.mark.asyncio
    async def test_execute_with_include_text_true(self, mock_context):
        """Should accept include_text=True parameter"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {"success": True, "file": "./page_info.json"}

            cmd = GetPageStructureCommand(mock_context)
            result = await cmd.execute(include_text=True)

            # Parameters are accepted but not used (PageScraper doesn't support them yet)
            assert result["success"] is True
            mock_scrape.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_include_text_false(self, mock_context):
        """Should accept include_text=False parameter"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {"success": True, "file": "./page_info.json"}

            cmd = GetPageStructureCommand(mock_context)
            result = await cmd.execute(include_text=False)

            assert result["success"] is True
            mock_scrape.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_default_params(self, mock_context):
        """Should use default parameters when not specified"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {"success": True, "file": "./page_info.json"}

            cmd = GetPageStructureCommand(mock_context)
            result = await cmd.execute()

            # Default: include_text=True
            assert result["success"] is True
            mock_scrape.assert_called_once_with(mock_context.cdp, "./page_info.json")

    @pytest.mark.asyncio
    async def test_execute_passes_cdp_context(self, mock_context):
        """Should pass CDP from context to PageScraper"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {"success": True}

            cmd = GetPageStructureCommand(mock_context)
            await cmd.execute()

            # Verify CDP was passed
            call_args = mock_scrape.call_args
            assert call_args[0][0] == mock_context.cdp  # First argument
            assert call_args[0][1] == "./page_info.json"  # Second argument


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestSearchErrorHandling:
    """Test error handling in search commands"""

    @pytest.mark.asyncio
    async def test_find_elements_handles_page_scraper_error(self, mock_context):
        """FindElementsCommand should propagate PageScraper errors"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {
                "success": False,
                "error": "CDP timeout",
                "message": "Failed to scrape and save page info: CDP timeout"
            }

            cmd = FindElementsCommand(mock_context)
            result = await cmd.execute()

            assert result["success"] is False
            assert "CDP timeout" in result["error"]

    @pytest.mark.asyncio
    async def test_find_elements_handles_page_scraper_exception(self, mock_context):
        """FindElementsCommand should handle PageScraper exceptions"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.side_effect = Exception("Unexpected error")

            cmd = FindElementsCommand(mock_context)

            # Should raise the exception (no try/except in execute)
            with pytest.raises(Exception, match="Unexpected error"):
                await cmd.execute()

    @pytest.mark.asyncio
    async def test_get_page_structure_handles_page_scraper_error(self, mock_context):
        """GetPageStructureCommand should propagate PageScraper errors"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {
                "success": False,
                "error": "Permission denied",
                "message": "Failed to scrape and save page info: Permission denied"
            }

            cmd = GetPageStructureCommand(mock_context)
            result = await cmd.execute()

            assert result["success"] is False
            assert "Permission denied" in result["error"]

    @pytest.mark.asyncio
    async def test_get_page_structure_handles_page_scraper_exception(self, mock_context):
        """GetPageStructureCommand should handle PageScraper exceptions"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.side_effect = Exception("Network error")

            cmd = GetPageStructureCommand(mock_context)

            # Should raise the exception (no try/except in execute)
            with pytest.raises(Exception, match="Network error"):
                await cmd.execute()


# ============================================================================
# Command Metadata Tests - FindElementsCommand
# ============================================================================

class TestFindElementsMetadata:
    """Test FindElementsCommand metadata (name, description, schema)"""

    def test_command_name(self):
        """Should have correct command name"""
        assert FindElementsCommand.name == "find_elements"

    def test_command_description(self):
        """Should have descriptive description"""
        desc = FindElementsCommand.description
        assert "find elements" in desc.lower()
        assert "page_info.json" in desc
        assert "Read" in desc

    def test_input_schema_structure(self):
        """Should have valid input schema"""
        schema = FindElementsCommand.input_schema
        assert schema["type"] == "object"
        assert "properties" in schema

    def test_input_schema_text(self):
        """Should have text parameter"""
        props = FindElementsCommand.input_schema["properties"]
        assert "text" in props
        assert props["text"]["type"] == "string"

    def test_input_schema_tag(self):
        """Should have tag parameter"""
        props = FindElementsCommand.input_schema["properties"]
        assert "tag" in props
        assert props["tag"]["type"] == "string"

    def test_input_schema_attribute(self):
        """Should have attribute parameter"""
        props = FindElementsCommand.input_schema["properties"]
        assert "attribute" in props
        assert props["attribute"]["type"] == "string"

    def test_input_schema_attribute_value(self):
        """Should have attribute_value parameter"""
        props = FindElementsCommand.input_schema["properties"]
        assert "attribute_value" in props
        assert props["attribute_value"]["type"] == "string"

    def test_input_schema_visible_only(self):
        """Should have visible_only parameter"""
        props = FindElementsCommand.input_schema["properties"]
        assert "visible_only" in props
        assert props["visible_only"]["type"] == "boolean"
        assert props["visible_only"]["default"] is True

    def test_input_schema_limit(self):
        """Should have limit parameter"""
        props = FindElementsCommand.input_schema["properties"]
        assert "limit" in props
        assert props["limit"]["type"] == "integer"
        assert props["limit"]["default"] == 20

    def test_no_required_parameters(self):
        """Should have no required parameters (all have defaults)"""
        schema = FindElementsCommand.input_schema
        required = schema.get("required", [])
        assert len(required) == 0

    def test_requires_browser_false(self):
        """Should not require browser"""
        assert FindElementsCommand.requires_browser is False

    def test_requires_cursor_false(self):
        """Should not require cursor"""
        assert FindElementsCommand.requires_cursor is False

    def test_to_mcp_tool(self):
        """Should convert to MCP tool format correctly"""
        tool = FindElementsCommand.to_mcp_tool()
        assert tool["name"] == "find_elements"
        assert "description" in tool
        assert "inputSchema" in tool
        assert tool["inputSchema"]["type"] == "object"
        assert "text" in tool["inputSchema"]["properties"]
        assert "tag" in tool["inputSchema"]["properties"]


# ============================================================================
# Command Metadata Tests - GetPageStructureCommand
# ============================================================================

class TestGetPageStructureMetadata:
    """Test GetPageStructureCommand metadata (name, description, schema)"""

    def test_command_name(self):
        """Should have correct command name"""
        assert GetPageStructureCommand.name == "get_page_structure"

    def test_command_description(self):
        """Should have descriptive description"""
        desc = GetPageStructureCommand.description
        assert "page structure" in desc.lower()
        assert "page_info.json" in desc
        assert "Read" in desc

    def test_input_schema_structure(self):
        """Should have valid input schema"""
        schema = GetPageStructureCommand.input_schema
        assert schema["type"] == "object"
        assert "properties" in schema

    def test_input_schema_include_text(self):
        """Should have include_text parameter"""
        props = GetPageStructureCommand.input_schema["properties"]
        assert "include_text" in props
        assert props["include_text"]["type"] == "boolean"
        assert props["include_text"]["default"] is True

    def test_no_required_parameters(self):
        """Should have no required parameters (all have defaults)"""
        schema = GetPageStructureCommand.input_schema
        required = schema.get("required", [])
        assert len(required) == 0

    def test_requires_browser_false(self):
        """Should not require browser"""
        assert GetPageStructureCommand.requires_browser is False

    def test_requires_cursor_false(self):
        """Should not require cursor"""
        assert GetPageStructureCommand.requires_cursor is False

    def test_to_mcp_tool(self):
        """Should convert to MCP tool format correctly"""
        tool = GetPageStructureCommand.to_mcp_tool()
        assert tool["name"] == "get_page_structure"
        assert "description" in tool
        assert "inputSchema" in tool
        assert tool["inputSchema"]["type"] == "object"
        assert "include_text" in tool["inputSchema"]["properties"]


# ============================================================================
# Integration Tests
# ============================================================================

class TestSearchIntegration:
    """Test integration with PageScraper"""

    @pytest.mark.asyncio
    async def test_find_elements_full_workflow_success(self, mock_context):
        """Test complete workflow: FindElementsCommand → PageScraper → success"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {
                "success": True,
                "message": "✅ Page info saved to ./page_info.json (3.2KB)",
                "file": "./page_info.json",
                "size_kb": 3.2,
                "instruction": "Use Read('./page_info.json') to view the data",
                "data_preview": {
                    "total_elements": 15,
                    "url": "https://example.com",
                    "title": "Example"
                }
            }

            cmd = FindElementsCommand(mock_context)
            result = await cmd.execute(text="Submit", tag="button")

            assert result["success"] is True
            assert result["file"] == "./page_info.json"
            assert result["size_kb"] == 3.2
            assert "data_preview" in result
            assert result["data_preview"]["total_elements"] == 15

    @pytest.mark.asyncio
    async def test_get_page_structure_full_workflow_success(self, mock_context):
        """Test complete workflow: GetPageStructureCommand → PageScraper → success"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {
                "success": True,
                "message": "✅ Page info saved to ./page_info.json (4.1KB)",
                "file": "./page_info.json",
                "size_kb": 4.1,
                "instruction": "Use Read('./page_info.json') to view the data",
                "data_preview": {
                    "total_elements": 20,
                    "url": "https://example.com",
                    "title": "Example Page"
                }
            }

            cmd = GetPageStructureCommand(mock_context)
            result = await cmd.execute(include_text=True)

            assert result["success"] is True
            assert result["file"] == "./page_info.json"
            assert result["size_kb"] == 4.1
            assert "data_preview" in result

    @pytest.mark.asyncio
    async def test_find_elements_command_initialization(self, mock_context):
        """Test FindElementsCommand initializes correctly"""
        cmd = FindElementsCommand(mock_context)

        assert cmd.context == mock_context
        assert cmd.tab == mock_context.tab
        assert cmd.cursor is None  # requires_cursor=False
        assert cmd.browser is None  # requires_browser=False

    @pytest.mark.asyncio
    async def test_get_page_structure_command_initialization(self, mock_context):
        """Test GetPageStructureCommand initializes correctly"""
        cmd = GetPageStructureCommand(mock_context)

        assert cmd.context == mock_context
        assert cmd.tab == mock_context.tab
        assert cmd.cursor is None  # requires_cursor=False
        assert cmd.browser is None  # requires_browser=False
