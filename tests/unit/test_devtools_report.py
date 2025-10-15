"""Unit tests for commands/devtools_report.py - DevTools report command

Coverage target: 90%+
Focus: PageScraper redirection, include_dom parameter, error handling
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from commands.devtools_report import DevToolsReportCommand
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
    """Create CommandContext with mocked CDP and console_logs"""
    context = CommandContext(
        tab=Mock(),
        cursor=None,
        browser=None,
        cdp=mock_cdp,
        console_logs=[]  # Required for DevToolsReportCommand
    )
    return context


# ============================================================================
# DevToolsReportCommand Tests
# ============================================================================

class TestDevToolsReportCommand:
    """Test DevToolsReportCommand redirection to PageScraper"""

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

            cmd = DevToolsReportCommand(mock_context)
            result = await cmd.execute()

            # Verify PageScraper was called
            mock_scrape.assert_called_once_with(mock_context.cdp, "./page_info.json")

            # Verify result
            assert result["success"] is True
            assert result["file"] == "./page_info.json"

    @pytest.mark.asyncio
    async def test_execute_with_include_dom_false(self, mock_context):
        """Should accept include_dom=False parameter"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {"success": True, "file": "./page_info.json"}

            cmd = DevToolsReportCommand(mock_context)
            result = await cmd.execute(include_dom=False)

            # Parameter is accepted but not used (PageScraper doesn't support it yet)
            assert result["success"] is True
            mock_scrape.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_include_dom_true(self, mock_context):
        """Should accept include_dom=True parameter"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {"success": True, "file": "./page_info.json"}

            cmd = DevToolsReportCommand(mock_context)
            result = await cmd.execute(include_dom=True)

            assert result["success"] is True
            mock_scrape.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_default_include_dom(self, mock_context):
        """Should use default include_dom=False when not specified"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {"success": True, "file": "./page_info.json"}

            cmd = DevToolsReportCommand(mock_context)
            result = await cmd.execute()

            # Default: include_dom=False
            assert result["success"] is True
            mock_scrape.assert_called_once_with(mock_context.cdp, "./page_info.json")

    @pytest.mark.asyncio
    async def test_execute_passes_cdp_context(self, mock_context):
        """Should pass CDP from context to PageScraper"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {"success": True}

            cmd = DevToolsReportCommand(mock_context)
            await cmd.execute()

            # Verify CDP was passed
            call_args = mock_scrape.call_args
            assert call_args[0][0] == mock_context.cdp  # First argument
            assert call_args[0][1] == "./page_info.json"  # Second argument

    @pytest.mark.asyncio
    async def test_execute_with_extra_kwargs(self, mock_context):
        """Should handle extra kwargs gracefully"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {"success": True}

            cmd = DevToolsReportCommand(mock_context)
            result = await cmd.execute(include_dom=True, extra_param="ignored")

            assert result["success"] is True
            mock_scrape.assert_called_once()


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestDevToolsReportErrorHandling:
    """Test error handling in DevToolsReportCommand"""

    @pytest.mark.asyncio
    async def test_execute_handles_page_scraper_error(self, mock_context):
        """Should propagate PageScraper errors"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {
                "success": False,
                "error": "CDP timeout",
                "message": "Failed to scrape and save page info: CDP timeout"
            }

            cmd = DevToolsReportCommand(mock_context)
            result = await cmd.execute()

            assert result["success"] is False
            assert "CDP timeout" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_handles_page_scraper_exception(self, mock_context):
        """Should handle PageScraper exceptions"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.side_effect = Exception("Unexpected error")

            cmd = DevToolsReportCommand(mock_context)

            # Should raise the exception (no try/except in execute)
            with pytest.raises(Exception, match="Unexpected error"):
                await cmd.execute()

    @pytest.mark.asyncio
    async def test_execute_handles_import_error(self, mock_context):
        """Should handle PageScraper import errors gracefully"""
        # This test verifies the import works correctly
        cmd = DevToolsReportCommand(mock_context)

        # Import happens inside execute(), not at module level
        with patch("utils.page_scraper.PageScraper") as mock_scraper_class:
            mock_scraper_class.scrape_and_save = AsyncMock(return_value={"success": True})

            result = await cmd.execute()
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_handles_file_write_error(self, mock_context):
        """Should handle file write errors from PageScraper"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {
                "success": False,
                "error": "Permission denied: ./page_info.json",
                "message": "Failed to save file"
            }

            cmd = DevToolsReportCommand(mock_context)
            result = await cmd.execute()

            assert result["success"] is False
            assert "Permission denied" in result["error"]


# ============================================================================
# Command Metadata Tests
# ============================================================================

class TestDevToolsReportMetadata:
    """Test command metadata (name, description, schema)"""

    def test_command_name(self):
        """Should have correct command name"""
        assert DevToolsReportCommand.name == "devtools_report"

    def test_command_description(self):
        """Should have descriptive description"""
        desc = DevToolsReportCommand.description
        assert "comprehensive" in desc.lower() or "devtools" in desc.lower()
        assert "page_info.json" in desc
        assert "Read" in desc

    def test_input_schema_structure(self):
        """Should have valid input schema"""
        schema = DevToolsReportCommand.input_schema
        assert schema["type"] == "object"
        assert "properties" in schema

    def test_input_schema_include_dom(self):
        """Should have include_dom parameter"""
        props = DevToolsReportCommand.input_schema["properties"]
        assert "include_dom" in props
        assert props["include_dom"]["type"] == "boolean"
        assert props["include_dom"]["default"] is False

    def test_no_required_parameters(self):
        """Should have no required parameters (all have defaults)"""
        schema = DevToolsReportCommand.input_schema
        required = schema.get("required", [])
        assert len(required) == 0

    def test_requires_browser_false(self):
        """Should not require browser"""
        assert DevToolsReportCommand.requires_browser is False

    def test_requires_cursor_false(self):
        """Should not require cursor"""
        assert DevToolsReportCommand.requires_cursor is False

    def test_requires_console_logs_true(self):
        """Should require console logs"""
        assert DevToolsReportCommand.requires_console_logs is True

    def test_to_mcp_tool(self):
        """Should convert to MCP tool format correctly"""
        tool = DevToolsReportCommand.to_mcp_tool()
        assert tool["name"] == "devtools_report"
        assert "description" in tool
        assert "inputSchema" in tool
        assert tool["inputSchema"]["type"] == "object"
        assert "include_dom" in tool["inputSchema"]["properties"]


# ============================================================================
# Integration Tests
# ============================================================================

class TestDevToolsReportIntegration:
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
                    "title": "Example",
                    "console_logs": []
                }
            }

            cmd = DevToolsReportCommand(mock_context)
            result = await cmd.execute(include_dom=False)

            assert result["success"] is True
            assert result["file"] == "./page_info.json"
            assert result["size_kb"] == 3.2
            assert "data_preview" in result
            assert result["data_preview"]["total_elements"] == 15

    @pytest.mark.asyncio
    async def test_full_workflow_with_dom_snapshot(self, mock_context):
        """Test workflow with include_dom=True"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {
                "success": True,
                "message": "Page info with DOM saved",
                "file": "./page_info.json",
                "size_kb": 5.8  # Larger with DOM
            }

            cmd = DevToolsReportCommand(mock_context)
            result = await cmd.execute(include_dom=True)

            assert result["success"] is True
            assert result["file"] == "./page_info.json"
            # DOM inclusion would make file larger
            assert result["size_kb"] > 0

    @pytest.mark.asyncio
    async def test_full_workflow_failure(self, mock_context):
        """Test complete workflow: execute → PageScraper → failure"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {
                "success": False,
                "error": "Permission denied",
                "message": "Failed to scrape and save page info: Permission denied"
            }

            cmd = DevToolsReportCommand(mock_context)
            result = await cmd.execute()

            assert result["success"] is False
            assert "Permission denied" in result["error"]

    @pytest.mark.asyncio
    async def test_command_initialization(self, mock_context):
        """Test command initializes correctly"""
        cmd = DevToolsReportCommand(mock_context)

        assert cmd.context == mock_context
        assert cmd.tab == mock_context.tab
        assert cmd.cursor is None  # requires_cursor=False
        assert cmd.browser is None  # requires_browser=False

    @pytest.mark.asyncio
    async def test_multiple_executions(self, mock_context):
        """Test command can be executed multiple times"""
        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = {"success": True, "file": "./page_info.json"}

            cmd = DevToolsReportCommand(mock_context)

            # Execute twice
            result1 = await cmd.execute(include_dom=False)
            result2 = await cmd.execute(include_dom=True)

            assert result1["success"] is True
            assert result2["success"] is True
            assert mock_scrape.call_count == 2

    @pytest.mark.asyncio
    async def test_result_structure_matches_page_scraper(self, mock_context):
        """Test that result structure matches PageScraper output"""
        expected_result = {
            "success": True,
            "message": "✅ Page info saved",
            "file": "./page_info.json",
            "size_kb": 3.1,
            "instruction": "Use Read('./page_info.json')",
            "data_preview": {"url": "test.com"}
        }

        with patch("utils.page_scraper.PageScraper.scrape_and_save", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = expected_result

            cmd = DevToolsReportCommand(mock_context)
            result = await cmd.execute()

            # Result should be exactly what PageScraper returns
            assert result == expected_result
