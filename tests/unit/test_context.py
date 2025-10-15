"""Unit tests for commands/context.py - CommandContext dependency injection

Coverage target: 80%+
Focus: Context creation, dependency validation, getter methods
"""
import pytest
from unittest.mock import Mock
from commands.context import CommandContext


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_tab():
    """Create a mock pychrome Tab"""
    return Mock(spec=['id', 'url', 'title'])


@pytest.fixture
def mock_cursor():
    """Create a mock AICursor"""
    return Mock(spec=['move', 'click', 'hide'])


@pytest.fixture
def mock_browser():
    """Create a mock pychrome Browser"""
    return Mock(spec=['list_tab', 'new_tab', 'close_tab'])


@pytest.fixture
def mock_cdp():
    """Create a mock AsyncCDP wrapper"""
    return Mock(spec=['call', 'evaluate', 'query_selector'])


@pytest.fixture
def mock_connection():
    """Create a mock BrowserConnection"""
    return Mock(spec=['ensure_connected', 'reconnect'])


@pytest.fixture
def mock_console_logs():
    """Create mock console logs"""
    return [
        {"level": "log", "args": ["test message"]},
        {"level": "error", "args": ["error message"]}
    ]


@pytest.fixture
def full_context(mock_tab, mock_cursor, mock_browser, mock_cdp, mock_connection, mock_console_logs):
    """Create CommandContext with all dependencies"""
    return CommandContext(
        tab=mock_tab,
        cdp=mock_cdp,
        cursor=mock_cursor,
        browser=mock_browser,
        console_logs=mock_console_logs,
        connection=mock_connection
    )


@pytest.fixture
def minimal_context(mock_tab):
    """Create CommandContext with only required tab"""
    return CommandContext(tab=mock_tab)


# ============================================================================
# CommandContext Initialization Tests
# ============================================================================

class TestCommandContextInit:
    """Test CommandContext initialization and properties"""

    def test_context_with_all_dependencies(self, full_context, mock_tab, mock_cursor, mock_browser, mock_cdp, mock_connection, mock_console_logs):
        """Should initialize with all dependencies"""
        assert full_context.tab == mock_tab
        assert full_context.cursor == mock_cursor
        assert full_context.browser == mock_browser
        assert full_context.cdp == mock_cdp
        assert full_context.connection == mock_connection
        assert full_context.console_logs == mock_console_logs

    def test_context_with_minimal_dependencies(self, minimal_context, mock_tab):
        """Should initialize with only tab (required)"""
        assert minimal_context.tab == mock_tab
        assert minimal_context.cursor is None
        assert minimal_context.browser is None
        assert minimal_context.cdp is None
        assert minimal_context.connection is None
        assert minimal_context.console_logs is None

    def test_context_is_dataclass(self):
        """CommandContext should be a dataclass"""
        from dataclasses import is_dataclass
        assert is_dataclass(CommandContext)

    def test_context_with_partial_dependencies(self, mock_tab, mock_browser, mock_cdp):
        """Should initialize with partial dependencies"""
        context = CommandContext(
            tab=mock_tab,
            browser=mock_browser,
            cdp=mock_cdp
        )
        assert context.tab == mock_tab
        assert context.browser == mock_browser
        assert context.cdp == mock_cdp
        assert context.cursor is None
        assert context.connection is None
        assert context.console_logs is None


# ============================================================================
# validate_requirements Method Tests
# ============================================================================

class TestValidateRequirements:
    """Test validate_requirements method"""

    def test_validate_no_requirements(self, full_context):
        """Should pass when no requirements specified"""
        # Should not raise
        full_context.validate_requirements()

    def test_validate_requires_cursor_success(self, full_context):
        """Should pass when cursor required and present"""
        full_context.validate_requirements(requires_cursor=True)

    def test_validate_requires_cursor_failure(self, minimal_context):
        """Should raise ValueError when cursor required but missing"""
        with pytest.raises(ValueError, match="Command requires cursor but none provided"):
            minimal_context.validate_requirements(requires_cursor=True)

    def test_validate_requires_browser_success(self, full_context):
        """Should pass when browser required and present"""
        full_context.validate_requirements(requires_browser=True)

    def test_validate_requires_browser_failure(self, minimal_context):
        """Should raise ValueError when browser required but missing"""
        with pytest.raises(ValueError, match="Command requires browser but none provided"):
            minimal_context.validate_requirements(requires_browser=True)

    def test_validate_requires_cdp_success(self, full_context):
        """Should pass when cdp required and present"""
        full_context.validate_requirements(requires_cdp=True)

    def test_validate_requires_cdp_failure(self, minimal_context):
        """Should raise ValueError when cdp required but missing"""
        with pytest.raises(ValueError, match="Command requires cdp but none provided"):
            minimal_context.validate_requirements(requires_cdp=True)

    def test_validate_requires_console_logs_success(self, full_context):
        """Should pass when console_logs required and present"""
        full_context.validate_requirements(requires_console_logs=True)

    def test_validate_requires_console_logs_failure(self, minimal_context):
        """Should raise ValueError when console_logs required but missing"""
        with pytest.raises(ValueError, match="Command requires console_logs but none provided"):
            minimal_context.validate_requirements(requires_console_logs=True)

    def test_validate_requires_connection_success(self, full_context):
        """Should pass when connection required and present"""
        full_context.validate_requirements(requires_connection=True)

    def test_validate_requires_connection_failure(self, minimal_context):
        """Should raise ValueError when connection required but missing"""
        with pytest.raises(ValueError, match="Command requires connection but none provided"):
            minimal_context.validate_requirements(requires_connection=True)

    def test_validate_multiple_requirements_success(self, full_context):
        """Should pass when multiple requirements all present"""
        full_context.validate_requirements(
            requires_cursor=True,
            requires_browser=True,
            requires_cdp=True,
            requires_console_logs=True,
            requires_connection=True
        )

    def test_validate_multiple_requirements_partial_failure(self, mock_tab, mock_browser):
        """Should raise ValueError when one of multiple requirements missing"""
        context = CommandContext(tab=mock_tab, browser=mock_browser)

        with pytest.raises(ValueError, match="Command requires cursor"):
            context.validate_requirements(
                requires_cursor=True,
                requires_browser=True
            )

    def test_validate_all_requirements_failure(self, minimal_context):
        """Should raise ValueError when all requirements missing"""
        # Should fail on first missing requirement (cursor)
        with pytest.raises(ValueError, match="Command requires cursor"):
            minimal_context.validate_requirements(
                requires_cursor=True,
                requires_browser=True,
                requires_cdp=True,
                requires_console_logs=True,
                requires_connection=True
            )


# ============================================================================
# get_* Methods Tests
# ============================================================================

class TestGetterMethods:
    """Test get_cursor, get_browser, get_cdp, get_console_logs, get_connection"""

    # get_cursor tests
    def test_get_cursor_success(self, full_context, mock_cursor):
        """Should return cursor when present"""
        assert full_context.get_cursor() == mock_cursor

    def test_get_cursor_failure(self, minimal_context):
        """Should raise ValueError when cursor not available"""
        with pytest.raises(ValueError, match="Cursor not available in context"):
            minimal_context.get_cursor()

    # get_browser tests
    def test_get_browser_success(self, full_context, mock_browser):
        """Should return browser when present"""
        assert full_context.get_browser() == mock_browser

    def test_get_browser_failure(self, minimal_context):
        """Should raise ValueError when browser not available"""
        with pytest.raises(ValueError, match="Browser not available in context"):
            minimal_context.get_browser()

    # get_cdp tests
    def test_get_cdp_success(self, full_context, mock_cdp):
        """Should return cdp when present"""
        assert full_context.get_cdp() == mock_cdp

    def test_get_cdp_failure(self, minimal_context):
        """Should raise ValueError when cdp not available"""
        with pytest.raises(ValueError, match="AsyncCDP wrapper not available in context"):
            minimal_context.get_cdp()

    # get_console_logs tests
    def test_get_console_logs_success(self, full_context, mock_console_logs):
        """Should return console logs when present"""
        assert full_context.get_console_logs() == mock_console_logs

    def test_get_console_logs_failure(self, minimal_context):
        """Should raise ValueError when console logs not available"""
        with pytest.raises(ValueError, match="Console logs not available in context"):
            minimal_context.get_console_logs()

    # get_connection tests
    def test_get_connection_success(self, full_context, mock_connection):
        """Should return connection when present"""
        assert full_context.get_connection() == mock_connection

    def test_get_connection_failure(self, minimal_context):
        """Should raise ValueError when connection not available"""
        with pytest.raises(ValueError, match="Connection not available in context"):
            minimal_context.get_connection()


# ============================================================================
# Edge Cases and Integration Tests
# ============================================================================

class TestCommandContextEdgeCases:
    """Test edge cases and integration scenarios"""

    def test_context_with_explicit_none_values(self, mock_tab):
        """Should handle explicitly set None values"""
        context = CommandContext(
            tab=mock_tab,
            cursor=None,
            browser=None,
            cdp=None,
            console_logs=None,
            connection=None
        )
        assert context.cursor is None
        assert context.browser is None
        assert context.cdp is None
        assert context.console_logs is None
        assert context.connection is None

    def test_context_empty_console_logs(self, mock_tab):
        """Should handle empty console logs list"""
        context = CommandContext(tab=mock_tab, console_logs=[])
        assert context.console_logs == []
        # Should not raise (empty list is not None)
        assert context.get_console_logs() == []

    def test_context_console_logs_with_various_levels(self, mock_tab):
        """Should handle console logs with various log levels"""
        logs = [
            {"level": "log", "args": ["info"]},
            {"level": "warn", "args": ["warning"]},
            {"level": "error", "args": ["error"]},
            {"level": "debug", "args": ["debug"]}
        ]
        context = CommandContext(tab=mock_tab, console_logs=logs)
        assert len(context.get_console_logs()) == 4
        assert context.get_console_logs()[2]["level"] == "error"

    def test_validate_requirements_with_false_flags(self, minimal_context):
        """Should pass when all flags are False"""
        # Should not raise
        minimal_context.validate_requirements(
            requires_cursor=False,
            requires_browser=False,
            requires_cdp=False,
            requires_console_logs=False,
            requires_connection=False
        )

    def test_context_tab_cannot_be_none(self):
        """Tab is required parameter (not Optional in dataclass)"""
        # This should work (tab is required)
        with pytest.raises(TypeError):
            # Missing required positional argument
            CommandContext()

    def test_context_with_real_like_objects(self):
        """Should work with real-like mock objects"""
        # Create more realistic mocks
        tab = Mock()
        tab.id = "E8F5A2B3-4C1D-4A2E-8F9B-1C2D3E4F5A6B"
        tab.url = "https://example.com"
        tab.title = "Example Domain"

        cursor = Mock()
        cursor.x = 100
        cursor.y = 200

        browser = Mock()
        browser.host = "localhost"
        browser.port = 9222

        context = CommandContext(tab=tab, cursor=cursor, browser=browser)
        assert context.tab.id == "E8F5A2B3-4C1D-4A2E-8F9B-1C2D3E4F5A6B"
        assert context.cursor.x == 100
        assert context.browser.port == 9222

    def test_validate_requirements_order_independence(self, mock_tab, mock_browser, mock_cursor):
        """Validation should check all requirements in order"""
        context = CommandContext(tab=mock_tab, browser=mock_browser)

        # Should fail on cursor (first in validation order)
        with pytest.raises(ValueError, match="cursor"):
            context.validate_requirements(requires_cursor=True, requires_browser=True)

    def test_multiple_get_calls_same_object(self, full_context, mock_cursor):
        """Multiple get_cursor calls should return same object"""
        cursor1 = full_context.get_cursor()
        cursor2 = full_context.get_cursor()
        assert cursor1 is cursor2
        assert cursor1 is mock_cursor

    def test_context_attribute_access(self, full_context, mock_tab):
        """Should allow direct attribute access"""
        # Direct access
        assert full_context.tab == mock_tab
        # Getter method
        assert full_context.get_cursor() == full_context.cursor

    def test_context_repr(self, full_context):
        """CommandContext should have readable repr (dataclass feature)"""
        repr_str = repr(full_context)
        assert "CommandContext" in repr_str
        assert "tab=" in repr_str

    def test_validate_requirements_with_mixed_presence(self, mock_tab, mock_cursor, mock_cdp):
        """Should validate correctly with mixed presence"""
        context = CommandContext(tab=mock_tab, cursor=mock_cursor, cdp=mock_cdp)

        # Should pass (cursor and cdp present)
        context.validate_requirements(requires_cursor=True, requires_cdp=True)

        # Should fail (browser missing)
        with pytest.raises(ValueError, match="browser"):
            context.validate_requirements(requires_browser=True)


# ============================================================================
# Real-world Usage Scenarios
# ============================================================================

class TestRealWorldScenarios:
    """Test real-world command execution scenarios"""

    def test_scenario_navigation_command(self, mock_tab, mock_cursor):
        """Navigation command needs tab and cursor"""
        context = CommandContext(tab=mock_tab, cursor=mock_cursor)
        # Should pass
        context.validate_requirements(requires_cursor=True)
        assert context.get_cursor() == mock_cursor

    def test_scenario_tab_management_command(self, mock_tab, mock_browser):
        """Tab management command needs tab and browser"""
        context = CommandContext(tab=mock_tab, browser=mock_browser)
        # Should pass
        context.validate_requirements(requires_browser=True)
        assert context.get_browser() == mock_browser

    def test_scenario_devtools_command(self, mock_tab, mock_console_logs):
        """DevTools command needs tab and console logs"""
        context = CommandContext(tab=mock_tab, console_logs=mock_console_logs)
        # Should pass
        context.validate_requirements(requires_console_logs=True)
        assert len(context.get_console_logs()) == 2

    def test_scenario_evaluation_command(self, mock_tab, mock_cdp):
        """Evaluation command needs tab and async CDP"""
        context = CommandContext(tab=mock_tab, cdp=mock_cdp)
        # Should pass
        context.validate_requirements(requires_cdp=True)
        assert context.get_cdp() == mock_cdp

    def test_scenario_connection_command(self, mock_tab, mock_connection):
        """Connection management command needs connection"""
        context = CommandContext(tab=mock_tab, connection=mock_connection)
        # Should pass
        context.validate_requirements(requires_connection=True)
        assert context.get_connection() == mock_connection

    def test_scenario_command_missing_optional_dependency(self, mock_tab):
        """Command with optional dependency should handle gracefully"""
        context = CommandContext(tab=mock_tab)

        # Try to get optional cursor
        try:
            context.get_cursor()
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Cursor not available" in str(e)
            # Command should handle this gracefully
