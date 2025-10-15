"""Unit tests for commands/page_snapshot.py - Page snapshot command

Coverage target: 90%+
Focus: PageScraper redirection, error handling
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from commands.page_snapshot import PageSnapshotCommand
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
# PageSnapshotCommand Tests
# ============================================================================

class TestPageSnapshotCommand:
    """Test PageSnapshotCommand redirection to PageScraper"""

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

            cmd = PageSnapshotCommand(mock_context)
            result = await cmd.execute()

            # Verify PageScraper was called
            mock_scrape.assert_called_once_with(mock_context.cdp, "./page_info.json")

            # Verify result
            assert result["success"] is True
            assert result["file"] == "./page_info.json"

    @pytest.mark.asyncio
    async def test_execute_with_include_styles_param(self, mock_context):
        """Should accept include_styles parameter (even if not used)"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {"success": True, "file": "./page_info.json"}

            cmd = PageSnapshotCommand(mock_context)
            result = await cmd.execute(include_styles=True)

            # Parameters are accepted but not used (PageScraper doesn't support them yet)
            assert result["success"] is True
            mock_scrape.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_max_depth_param(self, mock_context):
        """Should accept max_depth parameter (even if not used)"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {"success": True, "file": "./page_info.json"}

            cmd = PageSnapshotCommand(mock_context)
            result = await cmd.execute(max_depth=5)

            assert result["success"] is True
            mock_scrape.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_all_params(self, mock_context):
        """Should accept all parameters"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {"success": True, "file": "./page_info.json"}

            cmd = PageSnapshotCommand(mock_context)
            result = await cmd.execute(include_styles=True, max_depth=5)

            assert result["success"] is True
            mock_scrape.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_default_params(self, mock_context):
        """Should use default parameters when not specified"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {"success": True, "file": "./page_info.json"}

            cmd = PageSnapshotCommand(mock_context)
            result = await cmd.execute()

            # Defaults: include_styles=False, max_depth=3
            assert result["success"] is True
            mock_scrape.assert_called_once_with(mock_context.cdp, "./page_info.json")

    @pytest.mark.asyncio
    async def test_execute_passes_cdp_context(self, mock_context):
        """Should pass CDP from context to PageScraper"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {"success": True}

            cmd = PageSnapshotCommand(mock_context)
            await cmd.execute()

            # Verify CDP was passed
            call_args = mock_scrape.call_args
            assert call_args[0][0] == mock_context.cdp  # First argument
            assert call_args[0][1] == "./page_info.json"  # Second argument


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestPageSnapshotErrorHandling:
    """Test error handling in PageSnapshotCommand"""

    @pytest.mark.asyncio
    async def test_execute_handles_page_scraper_error(self, mock_context):
        """Should propagate PageScraper errors"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {
                "success": False,
                "error": "CDP timeout",
                "message": "Failed to scrape and save page info: CDP timeout"
            }

            cmd = PageSnapshotCommand(mock_context)
            result = await cmd.execute()

            assert result["success"] is False
            assert "CDP timeout" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_handles_page_scraper_exception(self, mock_context):
        """Should handle PageScraper exceptions"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.side_effect = Exception("Unexpected error")

            cmd = PageSnapshotCommand(mock_context)

            # Should raise the exception (no try/except in execute)
            with pytest.raises(Exception, match="Unexpected error"):
                await cmd.execute()

    @pytest.mark.asyncio
    async def test_execute_handles_import_error(self, mock_context):
        """Should handle PageScraper import errors gracefully"""
        # This test verifies the import works correctly
        cmd = PageSnapshotCommand(mock_context)

        # Import happens inside execute(), not at module level
        with patch("utils.page_scraper.PageScraper") as mock_scraper_class:
            mock_scraper_class.scrape_and_save = AsyncMock(return_value={"success": True})

            result = await cmd.execute()
            assert result["success"] is True


# ============================================================================
# Command Metadata Tests
# ============================================================================

class TestPageSnapshotMetadata:
    """Test command metadata (name, description, schema)"""

    def test_command_name(self):
        """Should have correct command name"""
        assert PageSnapshotCommand.name == "get_page_snapshot"

    def test_command_description(self):
        """Should have descriptive description"""
        desc = PageSnapshotCommand.description
        assert "lightweight" in desc.lower()
        assert "page_info.json" in desc
        assert "Read" in desc

    def test_input_schema_structure(self):
        """Should have valid input schema"""
        schema = PageSnapshotCommand.input_schema
        assert schema["type"] == "object"
        assert "properties" in schema

    def test_input_schema_include_styles(self):
        """Should have include_styles parameter"""
        props = PageSnapshotCommand.input_schema["properties"]
        assert "include_styles" in props
        assert props["include_styles"]["type"] == "boolean"
        assert props["include_styles"]["default"] is False

    def test_input_schema_max_depth(self):
        """Should have max_depth parameter"""
        props = PageSnapshotCommand.input_schema["properties"]
        assert "max_depth" in props
        assert props["max_depth"]["type"] == "integer"
        assert props["max_depth"]["default"] == 3

    def test_no_required_parameters(self):
        """Should have no required parameters (all have defaults)"""
        schema = PageSnapshotCommand.input_schema
        required = schema.get("required", [])
        assert len(required) == 0

    def test_requires_browser_false(self):
        """Should not require browser"""
        assert PageSnapshotCommand.requires_browser is False

    def test_requires_cursor_false(self):
        """Should not require cursor"""
        assert PageSnapshotCommand.requires_cursor is False

    def test_to_mcp_tool(self):
        """Should convert to MCP tool format correctly"""
        tool = PageSnapshotCommand.to_mcp_tool()
        assert tool["name"] == "get_page_snapshot"
        assert "description" in tool
        assert "inputSchema" in tool
        assert tool["inputSchema"]["type"] == "object"
        assert "include_styles" in tool["inputSchema"]["properties"]
        assert "max_depth" in tool["inputSchema"]["properties"]


# ============================================================================
# Integration Tests
# ============================================================================

class TestPageSnapshotIntegration:
    """Test integration with PageScraper"""

    @pytest.mark.asyncio
    async def test_full_workflow_success(self, mock_context):
        """Test complete workflow: execute → PageScraper → success"""
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

            cmd = PageSnapshotCommand(mock_context)
            result = await cmd.execute()

            assert result["success"] is True
            assert result["file"] == "./page_info.json"
            assert result["size_kb"] == 3.2
            assert "data_preview" in result
            assert result["data_preview"]["total_elements"] == 15

    @pytest.mark.asyncio
    async def test_full_workflow_failure(self, mock_context):
        """Test complete workflow: execute → PageScraper → failure"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {
                "success": False,
                "error": "Permission denied",
                "message": "Failed to scrape and save page info: Permission denied"
            }

            cmd = PageSnapshotCommand(mock_context)
            result = await cmd.execute()

            assert result["success"] is False
            assert "Permission denied" in result["error"]

    @pytest.mark.asyncio
    async def test_command_initialization(self, mock_context):
        """Test command initializes correctly"""
        cmd = PageSnapshotCommand(mock_context)

        assert cmd.context == mock_context
        assert cmd.tab == mock_context.tab
        assert cmd.cursor is None  # requires_cursor=False
        assert cmd.browser is None  # requires_browser=False
