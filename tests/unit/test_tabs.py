"""Unit tests for commands/tabs.py - Tab management commands

Coverage target: 70%+
Focus: Tab lifecycle, errors, concurrent operations
"""
import pytest
from unittest.mock import AsyncMock, Mock, MagicMock
from commands.tabs import (
    ListTabsCommand,
    CreateTabCommand,
    CloseTabCommand,
    SwitchTabCommand
)
from commands.context import CommandContext
from mcp.errors import BrowserError, TabNotFoundError, InvalidArgumentError


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_tab():
    """Create a mock tab with standard attributes"""
    tab = Mock()
    tab.id = "tab-123"
    tab.url = "https://example.com"
    tab.title = "Example Page"
    tab.type = "page"
    tab.start = Mock()
    tab.stop = Mock()

    # Mock CDP domains
    tab.Page = Mock()
    tab.Page.enable = Mock()
    tab.DOM = Mock()
    tab.DOM.enable = Mock()
    tab.Runtime = Mock()
    tab.Runtime.enable = Mock()
    tab.Console = Mock()
    tab.Console.enable = Mock()
    tab.Network = Mock()
    tab.Network.enable = Mock()
    tab.Debugger = Mock()
    tab.Debugger.enable = Mock()

    return tab


@pytest.fixture
def mock_browser(mock_tab):
    """Create a mock browser with tab management methods"""
    browser = Mock()
    browser.list_tab = Mock(return_value=[mock_tab])
    browser.new_tab = Mock(return_value=mock_tab)
    browser.close_tab = Mock()
    return browser


@pytest.fixture
def context_with_browser(mock_tab, mock_browser):
    """Create CommandContext with browser and tab"""
    context = CommandContext(
        tab=mock_tab,
        cursor=None,
        browser=mock_browser,
        cdp=None
    )
    return context


# ============================================================================
# ListTabsCommand Tests
# ============================================================================

class TestListTabsCommand:
    """Test ListTabsCommand"""

    @pytest.mark.asyncio
    async def test_list_single_tab(self, context_with_browser, mock_tab):
        """Should list single tab with all info"""
        cmd = ListTabsCommand(context_with_browser)
        result = await cmd.execute()

        assert result["success"] is True
        assert result["count"] == 1
        assert len(result["tabs"]) == 1
        assert result["tabs"][0]["id"] == "tab-123"
        assert result["tabs"][0]["url"] == "https://example.com"
        assert result["tabs"][0]["title"] == "Example Page"
        assert result["tabs"][0]["type"] == "page"
        assert result["currentTabId"] == "tab-123"

    @pytest.mark.asyncio
    async def test_list_multiple_tabs(self, context_with_browser, mock_browser):
        """Should list all tabs"""
        # Create multiple tabs
        tab1 = Mock(id="tab-1", url="https://site1.com", title="Site 1", type="page")
        tab2 = Mock(id="tab-2", url="https://site2.com", title="Site 2", type="page")
        tab3 = Mock(id="tab-3", url="about:blank", title="", type="page")
        mock_browser.list_tab.return_value = [tab1, tab2, tab3]

        cmd = ListTabsCommand(context_with_browser)
        result = await cmd.execute()

        assert result["success"] is True
        assert result["count"] == 3
        assert len(result["tabs"]) == 3
        assert result["tabs"][0]["id"] == "tab-1"
        assert result["tabs"][1]["id"] == "tab-2"
        assert result["tabs"][2]["id"] == "tab-3"

    @pytest.mark.asyncio
    async def test_list_empty_tabs(self, context_with_browser, mock_browser):
        """Should handle empty tab list"""
        mock_browser.list_tab.return_value = []

        cmd = ListTabsCommand(context_with_browser)
        result = await cmd.execute()

        assert result["success"] is True
        assert result["count"] == 0
        assert result["tabs"] == []

    @pytest.mark.asyncio
    async def test_list_tabs_missing_attributes(self, context_with_browser, mock_browser):
        """Should handle tabs with missing attributes gracefully"""
        tab = Mock(spec=[])  # Tab without any attributes
        mock_browser.list_tab.return_value = [tab]

        cmd = ListTabsCommand(context_with_browser)
        result = await cmd.execute()

        assert result["success"] is True
        assert result["tabs"][0]["id"] == "unknown"
        assert result["tabs"][0]["url"] == "unknown"
        assert result["tabs"][0]["title"] == "untitled"
        assert result["tabs"][0]["type"] == "page"

    @pytest.mark.asyncio
    async def test_list_tabs_no_current_tab(self, mock_browser):
        """Should handle case when no current tab"""
        context = CommandContext(tab=None, browser=mock_browser)
        cmd = ListTabsCommand(context)
        result = await cmd.execute()

        assert result["success"] is True
        assert result["currentTabId"] is None

    @pytest.mark.asyncio
    async def test_list_tabs_browser_error(self, context_with_browser, mock_browser):
        """Should raise BrowserError on failure"""
        mock_browser.list_tab.side_effect = Exception("Connection lost")

        cmd = ListTabsCommand(context_with_browser)
        with pytest.raises(BrowserError, match="Failed to list tabs: Connection lost"):
            await cmd.execute()


# ============================================================================
# CreateTabCommand Tests
# ============================================================================

class TestCreateTabCommand:
    """Test CreateTabCommand"""

    @pytest.mark.asyncio
    async def test_create_tab_without_url(self, context_with_browser, mock_browser, mock_tab):
        """Should create blank tab when no URL provided"""
        cmd = CreateTabCommand(context_with_browser)
        result = await cmd.execute()

        assert result["success"] is True
        assert result["tabId"] == "tab-123"
        assert result["url"] == "about:blank"
        assert "Created new tab" in result["message"]
        mock_browser.new_tab.assert_called_once_with(url=None)

    @pytest.mark.asyncio
    async def test_create_tab_with_http_url(self, context_with_browser, mock_browser):
        """Should create tab with HTTP URL"""
        cmd = CreateTabCommand(context_with_browser)
        result = await cmd.execute(url="http://example.com")

        assert result["success"] is True
        assert result["url"] == "http://example.com"
        assert "opened http://example.com" in result["message"]
        mock_browser.new_tab.assert_called_once_with(url="http://example.com")

    @pytest.mark.asyncio
    async def test_create_tab_with_https_url(self, context_with_browser, mock_browser):
        """Should create tab with HTTPS URL"""
        cmd = CreateTabCommand(context_with_browser)
        result = await cmd.execute(url="https://secure.example.com")

        assert result["success"] is True
        assert result["url"] == "https://secure.example.com"
        mock_browser.new_tab.assert_called_once_with(url="https://secure.example.com")

    @pytest.mark.asyncio
    async def test_create_tab_with_file_url(self, context_with_browser, mock_browser):
        """Should accept file:// URLs"""
        cmd = CreateTabCommand(context_with_browser)
        result = await cmd.execute(url="file:///path/to/file.html")

        assert result["success"] is True
        mock_browser.new_tab.assert_called_once_with(url="file:///path/to/file.html")

    @pytest.mark.asyncio
    async def test_create_tab_invalid_url_no_scheme(self, context_with_browser):
        """Should reject URL without scheme"""
        cmd = CreateTabCommand(context_with_browser)

        with pytest.raises(InvalidArgumentError) as exc_info:
            await cmd.execute(url="example.com")

        assert exc_info.value.data["argument"] == "url"
        assert "valid URL with scheme" in exc_info.value.data["expected"]
        assert exc_info.value.data["received"] == "example.com"

    @pytest.mark.asyncio
    async def test_create_tab_invalid_url_relative(self, context_with_browser):
        """Should reject relative URLs"""
        cmd = CreateTabCommand(context_with_browser)

        with pytest.raises(InvalidArgumentError):
            await cmd.execute(url="/path/to/page")

    @pytest.mark.asyncio
    async def test_create_tab_browser_error(self, context_with_browser, mock_browser):
        """Should raise BrowserError on creation failure"""
        mock_browser.new_tab.side_effect = Exception("Out of memory")

        cmd = CreateTabCommand(context_with_browser)
        with pytest.raises(BrowserError, match="Failed to create tab: Out of memory"):
            await cmd.execute(url="https://example.com")

    @pytest.mark.asyncio
    async def test_create_tab_missing_id(self, context_with_browser, mock_browser):
        """Should handle tab without ID attribute"""
        tab = Mock(spec=[])  # No id attribute
        mock_browser.new_tab.return_value = tab

        cmd = CreateTabCommand(context_with_browser)
        result = await cmd.execute()

        assert result["success"] is True
        assert result["tabId"] == "unknown"


# ============================================================================
# CloseTabCommand Tests
# ============================================================================

class TestCloseTabCommand:
    """Test CloseTabCommand"""

    @pytest.mark.asyncio
    async def test_close_current_tab_implicit(self, context_with_browser, mock_browser, mock_tab):
        """Should close current tab when no tab_id provided"""
        cmd = CloseTabCommand(context_with_browser)
        result = await cmd.execute()

        assert result["success"] is True
        assert result["tabId"] == "tab-123"
        assert result["wasCurrentTab"] is True
        assert "Closed tab: tab-123" in result["message"]
        mock_browser.close_tab.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_specific_tab_by_id(self, context_with_browser, mock_browser):
        """Should close specific tab by ID"""
        target_tab = Mock(id="tab-456", url="https://other.com", title="Other")
        mock_browser.list_tab.return_value = [mock_browser.list_tab()[0], target_tab]

        cmd = CloseTabCommand(context_with_browser)
        result = await cmd.execute(tab_id="tab-456")

        assert result["success"] is True
        assert result["tabId"] == "tab-456"
        assert result["wasCurrentTab"] is False
        mock_browser.close_tab.assert_called_once_with(target_tab)

    @pytest.mark.asyncio
    async def test_close_current_tab_explicit(self, context_with_browser, mock_browser, mock_tab):
        """Should close current tab when explicitly specified"""
        cmd = CloseTabCommand(context_with_browser)
        result = await cmd.execute(tab_id="tab-123")

        assert result["success"] is True
        assert result["wasCurrentTab"] is True

    @pytest.mark.asyncio
    async def test_close_tab_not_found(self, context_with_browser, mock_browser):
        """Should raise TabNotFoundError for non-existent tab"""
        cmd = CloseTabCommand(context_with_browser)

        with pytest.raises(TabNotFoundError) as exc_info:
            await cmd.execute(tab_id="tab-nonexistent")

        assert exc_info.value.data["tab_id"] == "tab-nonexistent"
        assert "Tab not found: tab-nonexistent" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_close_tab_no_current_tab(self, mock_browser):
        """Should raise BrowserError when no current tab and no tab_id"""
        context = CommandContext(tab=None, browser=mock_browser)
        cmd = CloseTabCommand(context)

        with pytest.raises(BrowserError, match="No current tab to close"):
            await cmd.execute()

    @pytest.mark.asyncio
    async def test_close_tab_current_tab_no_id(self, mock_browser):
        """Should raise BrowserError when current tab has no ID"""
        tab = Mock(spec=[])  # No id attribute
        context = CommandContext(tab=tab, browser=mock_browser)
        cmd = CloseTabCommand(context)

        with pytest.raises(BrowserError, match="Current tab has no ID"):
            await cmd.execute()

    @pytest.mark.asyncio
    async def test_close_tab_browser_error(self, context_with_browser, mock_browser, mock_tab):
        """Should raise BrowserError on close failure"""
        mock_browser.close_tab.side_effect = Exception("Tab is protected")

        cmd = CloseTabCommand(context_with_browser)
        with pytest.raises(BrowserError, match="Failed to close tab: Tab is protected"):
            await cmd.execute()

    @pytest.mark.asyncio
    async def test_close_tab_empty_tab_list(self, context_with_browser, mock_browser):
        """Should raise TabNotFoundError when tab list is empty"""
        mock_browser.list_tab.return_value = []

        cmd = CloseTabCommand(context_with_browser)
        with pytest.raises(TabNotFoundError):
            await cmd.execute(tab_id="tab-123")


# ============================================================================
# SwitchTabCommand Tests
# ============================================================================

class TestSwitchTabCommand:
    """Test SwitchTabCommand"""

    @pytest.mark.asyncio
    async def test_switch_to_valid_tab(self, context_with_browser, mock_browser, mock_tab):
        """Should switch to valid tab and enable domains"""
        target_tab = Mock(id="tab-456", url="https://target.com", title="Target Page")
        # Mock CDP domains
        target_tab.start = Mock()
        target_tab.Page = Mock()
        target_tab.Page.enable = Mock()
        target_tab.DOM = Mock()
        target_tab.DOM.enable = Mock()
        target_tab.Runtime = Mock()
        target_tab.Runtime.enable = Mock()
        target_tab.Console = Mock()
        target_tab.Console.enable = Mock()
        target_tab.Network = Mock()
        target_tab.Network.enable = Mock()
        target_tab.Debugger = Mock()
        target_tab.Debugger.enable = Mock()

        mock_browser.list_tab.return_value = [mock_tab, target_tab]

        cmd = SwitchTabCommand(context_with_browser)
        result = await cmd.execute(tab_id="tab-456")

        assert result["success"] is True
        assert result["tabId"] == "tab-456"
        assert result["url"] == "https://target.com"
        assert result["title"] == "Target Page"
        assert "Switched to tab: tab-456" in result["message"]
        assert result["newTab"] == target_tab

        # Verify current tab stopped
        mock_tab.stop.assert_called_once()

        # Verify new tab started
        target_tab.start.assert_called_once()

        # Verify all domains enabled
        target_tab.Page.enable.assert_called_once()
        target_tab.DOM.enable.assert_called_once()
        target_tab.Runtime.enable.assert_called_once()
        target_tab.Console.enable.assert_called_once()
        target_tab.Network.enable.assert_called_once()
        target_tab.Debugger.enable.assert_called_once()

    @pytest.mark.asyncio
    async def test_switch_tab_not_found(self, context_with_browser):
        """Should raise TabNotFoundError for non-existent tab"""
        cmd = SwitchTabCommand(context_with_browser)

        with pytest.raises(TabNotFoundError) as exc_info:
            await cmd.execute(tab_id="tab-nonexistent")

        assert exc_info.value.data["tab_id"] == "tab-nonexistent"
        assert "Tab not found: tab-nonexistent" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_switch_tab_no_current_tab(self, mock_browser):
        """Should work even without current tab"""
        target_tab = Mock(id="tab-456", url="https://target.com", title="Target")
        target_tab.start = Mock()
        target_tab.Page = Mock()
        target_tab.Page.enable = Mock()
        target_tab.DOM = Mock()
        target_tab.DOM.enable = Mock()
        target_tab.Runtime = Mock()
        target_tab.Runtime.enable = Mock()
        target_tab.Console = Mock()
        target_tab.Console.enable = Mock()
        target_tab.Network = Mock()
        target_tab.Network.enable = Mock()
        target_tab.Debugger = Mock()
        target_tab.Debugger.enable = Mock()

        mock_browser.list_tab.return_value = [target_tab]
        context = CommandContext(tab=None, browser=mock_browser)

        cmd = SwitchTabCommand(context)
        result = await cmd.execute(tab_id="tab-456")

        assert result["success"] is True
        target_tab.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_switch_tab_stop_current_fails(self, context_with_browser, mock_browser, mock_tab):
        """Should continue even if stopping current tab fails"""
        mock_tab.stop.side_effect = Exception("Stop failed")
        target_tab = Mock(id="tab-456", url="https://target.com", title="Target")
        target_tab.start = Mock()
        target_tab.Page = Mock()
        target_tab.Page.enable = Mock()
        target_tab.DOM = Mock()
        target_tab.DOM.enable = Mock()
        target_tab.Runtime = Mock()
        target_tab.Runtime.enable = Mock()
        target_tab.Console = Mock()
        target_tab.Console.enable = Mock()
        target_tab.Network = Mock()
        target_tab.Network.enable = Mock()
        target_tab.Debugger = Mock()
        target_tab.Debugger.enable = Mock()

        mock_browser.list_tab.return_value = [mock_tab, target_tab]

        cmd = SwitchTabCommand(context_with_browser)
        result = await cmd.execute(tab_id="tab-456")

        # Should still succeed
        assert result["success"] is True
        target_tab.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_switch_tab_start_fails(self, context_with_browser, mock_browser, mock_tab):
        """Should raise BrowserError if tab.start() fails"""
        target_tab = Mock(id="tab-456")
        target_tab.start.side_effect = Exception("Start failed")
        mock_browser.list_tab.return_value = [mock_tab, target_tab]

        cmd = SwitchTabCommand(context_with_browser)
        with pytest.raises(BrowserError, match="Failed to switch tab: Start failed"):
            await cmd.execute(tab_id="tab-456")

    @pytest.mark.asyncio
    async def test_switch_tab_enable_domain_fails(self, context_with_browser, mock_browser, mock_tab):
        """Should raise BrowserError if domain enabling fails"""
        target_tab = Mock(id="tab-456", url="https://target.com", title="Target")
        target_tab.start = Mock()
        target_tab.Page = Mock()
        target_tab.Page.enable.side_effect = Exception("Page.enable failed")

        mock_browser.list_tab.return_value = [mock_tab, target_tab]

        cmd = SwitchTabCommand(context_with_browser)
        with pytest.raises(BrowserError, match="Failed to switch tab: Page.enable failed"):
            await cmd.execute(tab_id="tab-456")

    @pytest.mark.asyncio
    async def test_switch_tab_missing_attributes(self, context_with_browser, mock_browser, mock_tab):
        """Should handle tab with missing url/title attributes"""
        target_tab = Mock(id="tab-456", spec=['id', 'start', 'Page', 'DOM', 'Runtime', 'Console', 'Network', 'Debugger'])
        target_tab.start = Mock()
        target_tab.Page = Mock()
        target_tab.Page.enable = Mock()
        target_tab.DOM = Mock()
        target_tab.DOM.enable = Mock()
        target_tab.Runtime = Mock()
        target_tab.Runtime.enable = Mock()
        target_tab.Console = Mock()
        target_tab.Console.enable = Mock()
        target_tab.Network = Mock()
        target_tab.Network.enable = Mock()
        target_tab.Debugger = Mock()
        target_tab.Debugger.enable = Mock()

        mock_browser.list_tab.return_value = [mock_tab, target_tab]

        cmd = SwitchTabCommand(context_with_browser)
        result = await cmd.execute(tab_id="tab-456")

        assert result["success"] is True
        assert result["url"] == "unknown"
        assert result["title"] == "untitled"

    @pytest.mark.asyncio
    async def test_switch_tab_returns_new_tab_object(self, context_with_browser, mock_browser, mock_tab):
        """Should return new tab object for caller to update reference"""
        target_tab = Mock(id="tab-456", url="https://target.com", title="Target")
        target_tab.start = Mock()
        target_tab.Page = Mock()
        target_tab.Page.enable = Mock()
        target_tab.DOM = Mock()
        target_tab.DOM.enable = Mock()
        target_tab.Runtime = Mock()
        target_tab.Runtime.enable = Mock()
        target_tab.Console = Mock()
        target_tab.Console.enable = Mock()
        target_tab.Network = Mock()
        target_tab.Network.enable = Mock()
        target_tab.Debugger = Mock()
        target_tab.Debugger.enable = Mock()

        mock_browser.list_tab.return_value = [mock_tab, target_tab]

        cmd = SwitchTabCommand(context_with_browser)
        result = await cmd.execute(tab_id="tab-456")

        assert "newTab" in result
        assert result["newTab"] == target_tab


# ============================================================================
# Command Metadata Tests
# ============================================================================

class TestTabsCommandMetadata:
    """Test command metadata (name, description, schema)"""

    def test_list_tabs_metadata(self):
        """ListTabsCommand should have correct metadata"""
        assert ListTabsCommand.name == "list_tabs"
        assert "List all open tabs" in ListTabsCommand.description
        assert ListTabsCommand.input_schema["type"] == "object"
        assert ListTabsCommand.requires_browser is True

    def test_create_tab_metadata(self):
        """CreateTabCommand should have correct metadata"""
        assert CreateTabCommand.name == "create_tab"
        assert "new tab" in CreateTabCommand.description
        assert "url" in CreateTabCommand.input_schema["properties"]
        assert CreateTabCommand.requires_browser is True

    def test_close_tab_metadata(self):
        """CloseTabCommand should have correct metadata"""
        assert CloseTabCommand.name == "close_tab"
        assert "Close a tab" in CloseTabCommand.description
        assert "tab_id" in CloseTabCommand.input_schema["properties"]
        assert CloseTabCommand.requires_browser is True

    def test_switch_tab_metadata(self):
        """SwitchTabCommand should have correct metadata"""
        assert SwitchTabCommand.name == "switch_tab"
        assert "Switch to" in SwitchTabCommand.description
        assert "tab_id" in SwitchTabCommand.input_schema["properties"]
        assert "tab_id" in SwitchTabCommand.input_schema["required"]
        assert SwitchTabCommand.requires_browser is True
