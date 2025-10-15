"""
Unit tests for commands/diagnostics.py

Tests:
- EnableConsoleLoggingCommand: Force enable console logging
- DiagnosePageCommand: Page state diagnostics (URL, viewport, cursors, counts)
- GetClickableElementsCommand: Clickable elements detection with filters

Coverage target: 70%+ (51% → 70%)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from commands.diagnostics import (
    EnableConsoleLoggingCommand,
    DiagnosePageCommand,
    GetClickableElementsCommand
)
from commands.context import CommandContext


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_tab():
    """Mock pychrome Tab"""
    tab = MagicMock()
    tab.Runtime = MagicMock()
    tab.Runtime.evaluate = MagicMock()
    return tab


@pytest.fixture
def mock_cdp():
    """Mock AsyncCDP wrapper"""
    cdp = AsyncMock()
    cdp.evaluate = AsyncMock()
    return cdp


@pytest.fixture
def mock_connection():
    """Mock BrowserConnection"""
    connection = MagicMock()
    connection.force_enable_console_logging = AsyncMock()
    return connection


@pytest.fixture
def context(mock_tab, mock_cdp):
    """CommandContext with mocked dependencies"""
    return CommandContext(
        tab=mock_tab,
        cursor=None,
        browser=None,
        cdp=mock_cdp,
        connection=None
    )


@pytest.fixture
def context_with_connection(mock_tab, mock_cdp, mock_connection):
    """CommandContext with connection"""
    return CommandContext(
        tab=mock_tab,
        cursor=None,
        browser=None,
        cdp=mock_cdp,
        connection=mock_connection
    )


# ============================================================================
# EnableConsoleLoggingCommand Tests
# ============================================================================

class TestEnableConsoleLoggingCommand:
    """Tests for EnableConsoleLoggingCommand"""

    @pytest.mark.asyncio
    async def test_metadata(self):
        """Test command metadata"""
        assert EnableConsoleLoggingCommand.name == "enable_console_logging"
        assert "Force enable console logging" in EnableConsoleLoggingCommand.description
        assert EnableConsoleLoggingCommand.input_schema["type"] == "object"
        assert EnableConsoleLoggingCommand.input_schema["properties"] == {}
        assert EnableConsoleLoggingCommand.requires_connection is True

    @pytest.mark.asyncio
    async def test_successful_enable_logging(self, context_with_connection, mock_connection):
        """Test successful console logging enable"""
        mock_connection.force_enable_console_logging.return_value = {
            "success": True,
            "message": "Console logging enabled"
        }

        cmd = EnableConsoleLoggingCommand(context_with_connection)
        result = await cmd.execute()

        mock_connection.force_enable_console_logging.assert_called_once()
        assert result["success"] is True
        assert "enabled" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_no_connection_available(self, context):
        """Test error when no browser connection (raises ValueError on init)"""
        with pytest.raises(ValueError) as exc:
            cmd = EnableConsoleLoggingCommand(context)

        assert "requires connection" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_connection_error_during_enable(self, context_with_connection, mock_connection):
        """Test connection error during enable"""
        mock_connection.force_enable_console_logging.return_value = {
            "success": False,
            "error": "CDP connection lost"
        }

        cmd = EnableConsoleLoggingCommand(context_with_connection)
        result = await cmd.execute()

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_to_mcp_tool(self):
        """Test MCP tool conversion"""
        tool = EnableConsoleLoggingCommand.to_mcp_tool()
        assert tool["name"] == "enable_console_logging"
        assert "Force enable console logging" in tool["description"]
        assert tool["inputSchema"]["type"] == "object"


# ============================================================================
# DiagnosePageCommand Tests
# ============================================================================

class TestDiagnosePageCommand:
    """Tests for DiagnosePageCommand (page diagnostics)"""

    @pytest.mark.asyncio
    async def test_metadata(self):
        """Test command metadata"""
        assert DiagnosePageCommand.name == "diagnose_page"
        assert "Diagnose page state, connection, and common issues" in DiagnosePageCommand.description
        assert DiagnosePageCommand.input_schema["type"] == "object"
        assert DiagnosePageCommand.input_schema["properties"] == {}

    @pytest.mark.asyncio
    async def test_successful_page_diagnostics(self, context, mock_cdp):
        """Test successful page diagnostics with all data"""
        diagnostics_data = {
            "url": "https://example.com/test",
            "title": "Test Page",
            "readyState": "complete",
            "activeElement": {
                "tag": "INPUT",
                "id": "username",
                "type": "text"
            },
            "viewport": {
                "width": 1920,
                "height": 1080,
                "scrollX": 0,
                "scrollY": 250
            },
            "cursors": {
                "aiCursor": "initialized",
                "consoleInterceptor": "installed"
            },
            "counts": {
                "buttons": 5,
                "links": 20,
                "inputs": 3,
                "tabs": 0
            },
            "devtools": {
                "open": False
            }
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": diagnostics_data}
        }

        cmd = DiagnosePageCommand(context)
        result = await cmd.execute()

        # Verify CDP call
        mock_cdp.evaluate.assert_called_once()
        call_args = mock_cdp.evaluate.call_args[1]
        assert "window.location.href" in call_args["expression"]
        assert "document.title" in call_args["expression"]
        assert "document.readyState" in call_args["expression"]
        assert "document.activeElement" in call_args["expression"]
        assert "window.innerWidth" in call_args["expression"]
        assert "window.__aiCursor__" in call_args["expression"]
        assert "window.__consoleInterceptorInstalled" in call_args["expression"]
        assert "querySelectorAll('button')" in call_args["expression"]
        assert "querySelectorAll('a')" in call_args["expression"]
        assert call_args["returnByValue"] is True

        # Verify result structure
        assert result["success"] is True
        assert result["diagnostics"]["url"] == "https://example.com/test"
        assert result["diagnostics"]["title"] == "Test Page"
        assert result["diagnostics"]["readyState"] == "complete"
        assert result["diagnostics"]["activeElement"]["tag"] == "INPUT"
        assert result["diagnostics"]["viewport"]["width"] == 1920
        assert result["diagnostics"]["viewport"]["scrollY"] == 250
        assert result["diagnostics"]["cursors"]["aiCursor"] == "initialized"
        assert result["diagnostics"]["counts"]["buttons"] == 5
        assert result["diagnostics"]["counts"]["links"] == 20
        assert result["diagnostics"]["devtools"]["open"] is False

    @pytest.mark.asyncio
    async def test_page_with_no_active_element(self, context, mock_cdp):
        """Test diagnostics when no active element"""
        diagnostics_data = {
            "url": "https://example.com",
            "title": "Example",
            "readyState": "interactive",
            "activeElement": None,  # No active element
            "viewport": {
                "width": 1024,
                "height": 768,
                "scrollX": 0,
                "scrollY": 0
            },
            "cursors": {
                "aiCursor": "not initialized",
                "consoleInterceptor": "not installed"
            },
            "counts": {
                "buttons": 0,
                "links": 0,
                "inputs": 0,
                "tabs": 0
            },
            "devtools": {
                "open": False
            }
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": diagnostics_data}
        }

        cmd = DiagnosePageCommand(context)
        result = await cmd.execute()

        assert result["success"] is True
        assert result["diagnostics"]["activeElement"] is None
        assert result["diagnostics"]["cursors"]["aiCursor"] == "not initialized"
        assert result["diagnostics"]["counts"]["buttons"] == 0

    @pytest.mark.asyncio
    async def test_page_loading_state(self, context, mock_cdp):
        """Test diagnostics during page loading"""
        diagnostics_data = {
            "url": "https://example.com",
            "title": "",
            "readyState": "loading",  # Page still loading
            "activeElement": None,
            "viewport": {
                "width": 1366,
                "height": 768,
                "scrollX": 0,
                "scrollY": 0
            },
            "cursors": {
                "aiCursor": "not initialized",
                "consoleInterceptor": "installed"
            },
            "counts": {
                "buttons": 0,
                "links": 0,
                "inputs": 0,
                "tabs": 0
            },
            "devtools": {
                "open": False
            }
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": diagnostics_data}
        }

        cmd = DiagnosePageCommand(context)
        result = await cmd.execute()

        assert result["success"] is True
        assert result["diagnostics"]["readyState"] == "loading"
        assert result["diagnostics"]["title"] == ""

    @pytest.mark.asyncio
    async def test_page_with_devtools_open(self, context, mock_cdp):
        """Test diagnostics when DevTools are open"""
        diagnostics_data = {
            "url": "https://example.com",
            "title": "Example",
            "readyState": "complete",
            "activeElement": None,
            "viewport": {
                "width": 1920,
                "height": 1080,
                "scrollX": 0,
                "scrollY": 0
            },
            "cursors": {
                "aiCursor": "initialized",
                "consoleInterceptor": "installed"
            },
            "counts": {
                "buttons": 10,
                "links": 50,
                "inputs": 5,
                "tabs": 3
            },
            "devtools": {
                "open": True  # DevTools open
            }
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": diagnostics_data}
        }

        cmd = DiagnosePageCommand(context)
        result = await cmd.execute()

        assert result["success"] is True
        assert result["diagnostics"]["devtools"]["open"] is True
        assert result["diagnostics"]["counts"]["tabs"] == 3

    @pytest.mark.asyncio
    async def test_page_with_large_scroll_offset(self, context, mock_cdp):
        """Test diagnostics with large scroll offset"""
        diagnostics_data = {
            "url": "https://example.com/long-page",
            "title": "Long Page",
            "readyState": "complete",
            "activeElement": None,
            "viewport": {
                "width": 1920,
                "height": 1080,
                "scrollX": 0,
                "scrollY": 5000  # Large scroll offset
            },
            "cursors": {
                "aiCursor": "initialized",
                "consoleInterceptor": "installed"
            },
            "counts": {
                "buttons": 100,
                "links": 500,
                "inputs": 20,
                "tabs": 0
            },
            "devtools": {
                "open": False
            }
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": diagnostics_data}
        }

        cmd = DiagnosePageCommand(context)
        result = await cmd.execute()

        assert result["success"] is True
        assert result["diagnostics"]["viewport"]["scrollY"] == 5000

    @pytest.mark.asyncio
    async def test_cdp_evaluation_error(self, context, mock_cdp):
        """Test CDP evaluation error"""
        mock_cdp.evaluate.side_effect = RuntimeError("CDP connection lost")

        cmd = DiagnosePageCommand(context)
        result = await cmd.execute()

        assert result["success"] is False
        assert "Failed to diagnose page" in result["message"]
        assert "CDP connection lost" in result["error"]

    @pytest.mark.asyncio
    async def test_general_exception_handling(self, context, mock_cdp):
        """Test general exception handling"""
        mock_cdp.evaluate.side_effect = Exception("Tab stopped")

        cmd = DiagnosePageCommand(context)
        result = await cmd.execute()

        assert result["success"] is False
        assert "Failed to diagnose page" in result["message"]
        assert "Tab stopped" in result["error"]

    @pytest.mark.asyncio
    async def test_to_mcp_tool(self):
        """Test MCP tool conversion"""
        tool = DiagnosePageCommand.to_mcp_tool()
        assert tool["name"] == "diagnose_page"
        assert "Diagnose page state" in tool["description"]
        assert tool["inputSchema"]["type"] == "object"


# ============================================================================
# GetClickableElementsCommand Tests
# ============================================================================

class TestGetClickableElementsCommand:
    """Tests for GetClickableElementsCommand (clickable elements detection)"""

    @pytest.mark.asyncio
    async def test_metadata(self):
        """Test command metadata"""
        assert GetClickableElementsCommand.name == "get_clickable_elements"
        assert "Get all clickable elements with their positions" in GetClickableElementsCommand.description

        schema = GetClickableElementsCommand.input_schema
        assert "text_filter" in schema["properties"]
        assert "visible_only" in schema["properties"]
        assert schema["properties"]["text_filter"]["type"] == "string"
        assert schema["properties"]["visible_only"]["type"] == "boolean"
        assert schema["properties"]["visible_only"]["default"] is True

    @pytest.mark.asyncio
    async def test_get_all_clickable_elements(self, context, mock_cdp):
        """Test getting all clickable elements (no filters)"""
        elements_data = {
            "success": True,
            "count": 3,
            "elements": [
                {
                    "tag": "BUTTON",
                    "text": "Submit",
                    "id": "submit-btn",
                    "role": "button",
                    "ariaLabel": None,
                    "visible": True,
                    "position": {"x": 100, "y": 200, "width": 120, "height": 40},
                    "hasClickHandler": True,
                    "disabled": False
                },
                {
                    "tag": "A",
                    "text": "Home",
                    "id": None,
                    "role": "link",
                    "ariaLabel": "Go to homepage",
                    "visible": True,
                    "position": {"x": 50, "y": 50, "width": 80, "height": 30},
                    "hasClickHandler": False,
                    "disabled": False
                },
                {
                    "tag": "INPUT",
                    "text": "",
                    "id": "login-submit",
                    "role": None,
                    "ariaLabel": "Submit login",
                    "visible": True,
                    "position": {"x": 300, "y": 400, "width": 100, "height": 35},
                    "hasClickHandler": False,
                    "disabled": False
                }
            ]
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": elements_data}
        }

        cmd = GetClickableElementsCommand(context)
        result = await cmd.execute()

        # Verify CDP call
        mock_cdp.evaluate.assert_called_once()
        call_args = mock_cdp.evaluate.call_args[1]
        js_code = call_args["expression"]
        assert "querySelectorAll" in js_code
        assert "'button'" in js_code
        assert "'a'" in js_code
        assert '[role="button"]' in js_code
        assert '[role="tab"]' in js_code
        assert '[onclick]' in js_code
        assert "getBoundingClientRect" in js_code
        assert "getComputedStyle" in js_code
        assert call_args["returnByValue"] is True

        # Verify result
        assert result["success"] is True
        assert result["count"] == 3
        assert len(result["elements"]) == 3
        assert result["elements"][0]["tag"] == "BUTTON"
        assert result["elements"][0]["text"] == "Submit"
        assert result["elements"][0]["position"]["x"] == 100
        assert result["elements"][1]["tag"] == "A"
        assert result["elements"][1]["ariaLabel"] == "Go to homepage"
        assert result["elements"][2]["tag"] == "INPUT"

    @pytest.mark.asyncio
    async def test_filter_by_text(self, context, mock_cdp):
        """Test filtering by text content"""
        elements_data = {
            "success": True,
            "count": 1,
            "elements": [
                {
                    "tag": "BUTTON",
                    "text": "Submit Form",
                    "id": "submit",
                    "role": "button",
                    "ariaLabel": None,
                    "visible": True,
                    "position": {"x": 100, "y": 200, "width": 120, "height": 40},
                    "hasClickHandler": True,
                    "disabled": False
                }
            ]
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": elements_data}
        }

        cmd = GetClickableElementsCommand(context)
        result = await cmd.execute(text_filter="Submit")

        # Verify text filter in JS code
        call_args = mock_cdp.evaluate.call_args[1]
        js_code = call_args["expression"]
        assert "el.textContent.includes('Submit')" in js_code

        assert result["success"] is True
        assert result["count"] == 1
        assert "Submit" in result["elements"][0]["text"]

    @pytest.mark.asyncio
    async def test_visible_only_true(self, context, mock_cdp):
        """Test visible_only=True (default, filters hidden elements)"""
        elements_data = {
            "success": True,
            "count": 2,
            "elements": [
                {
                    "tag": "BUTTON",
                    "text": "Visible Button",
                    "id": "btn1",
                    "role": "button",
                    "ariaLabel": None,
                    "visible": True,
                    "position": {"x": 100, "y": 200, "width": 120, "height": 40},
                    "hasClickHandler": True,
                    "disabled": False
                },
                {
                    "tag": "A",
                    "text": "Visible Link",
                    "id": "link1",
                    "role": "link",
                    "ariaLabel": None,
                    "visible": True,
                    "position": {"x": 50, "y": 50, "width": 80, "height": 30},
                    "hasClickHandler": False,
                    "disabled": False
                }
            ]
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": elements_data}
        }

        cmd = GetClickableElementsCommand(context)
        result = await cmd.execute(visible_only=True)

        # Verify visible_only check in JS code
        call_args = mock_cdp.evaluate.call_args[1]
        js_code = call_args["expression"]
        assert "const visibleOnly = true" in js_code
        assert "if (visibleOnly && !isVisible) return null" in js_code

        assert result["success"] is True
        assert all(el["visible"] for el in result["elements"])

    @pytest.mark.asyncio
    async def test_visible_only_false(self, context, mock_cdp):
        """Test visible_only=False (includes hidden elements)"""
        elements_data = {
            "success": True,
            "count": 3,
            "elements": [
                {
                    "tag": "BUTTON",
                    "text": "Visible Button",
                    "id": "btn1",
                    "role": "button",
                    "ariaLabel": None,
                    "visible": True,
                    "position": {"x": 100, "y": 200, "width": 120, "height": 40},
                    "hasClickHandler": True,
                    "disabled": False
                },
                {
                    "tag": "BUTTON",
                    "text": "Hidden Button",
                    "id": "btn2",
                    "role": "button",
                    "ariaLabel": None,
                    "visible": False,
                    "position": {"x": 0, "y": 0, "width": 0, "height": 0},
                    "hasClickHandler": True,
                    "disabled": False
                },
                {
                    "tag": "A",
                    "text": "Hidden Link",
                    "id": "link1",
                    "role": "link",
                    "ariaLabel": None,
                    "visible": False,
                    "position": {"x": 0, "y": 0, "width": 0, "height": 0},
                    "hasClickHandler": False,
                    "disabled": False
                }
            ]
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": elements_data}
        }

        cmd = GetClickableElementsCommand(context)
        result = await cmd.execute(visible_only=False)

        # Verify visible_only=false in JS code
        call_args = mock_cdp.evaluate.call_args[1]
        js_code = call_args["expression"]
        assert "const visibleOnly = false" in js_code

        assert result["success"] is True
        assert result["count"] == 3
        # Should include both visible and hidden elements
        visible_count = sum(1 for el in result["elements"] if el["visible"])
        hidden_count = sum(1 for el in result["elements"] if not el["visible"])
        assert visible_count == 1
        assert hidden_count == 2

    @pytest.mark.asyncio
    async def test_elements_with_disabled_state(self, context, mock_cdp):
        """Test elements with disabled state"""
        elements_data = {
            "success": True,
            "count": 2,
            "elements": [
                {
                    "tag": "BUTTON",
                    "text": "Enabled Button",
                    "id": "btn1",
                    "role": "button",
                    "ariaLabel": None,
                    "visible": True,
                    "position": {"x": 100, "y": 200, "width": 120, "height": 40},
                    "hasClickHandler": True,
                    "disabled": False
                },
                {
                    "tag": "BUTTON",
                    "text": "Disabled Button",
                    "id": "btn2",
                    "role": "button",
                    "ariaLabel": None,
                    "visible": True,
                    "position": {"x": 100, "y": 300, "width": 120, "height": 40},
                    "hasClickHandler": True,
                    "disabled": True
                }
            ]
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": elements_data}
        }

        cmd = GetClickableElementsCommand(context)
        result = await cmd.execute()

        assert result["success"] is True
        assert result["elements"][0]["disabled"] is False
        assert result["elements"][1]["disabled"] is True

    @pytest.mark.asyncio
    async def test_elements_with_onclick_handler(self, context, mock_cdp):
        """Test elements with onclick handlers"""
        elements_data = {
            "success": True,
            "count": 2,
            "elements": [
                {
                    "tag": "DIV",
                    "text": "Clickable Div",
                    "id": "div1",
                    "role": None,
                    "ariaLabel": None,
                    "visible": True,
                    "position": {"x": 200, "y": 300, "width": 150, "height": 50},
                    "hasClickHandler": True,  # Has onclick
                    "disabled": False
                },
                {
                    "tag": "SPAN",
                    "text": "Normal Span",
                    "id": "span1",
                    "role": None,
                    "ariaLabel": None,
                    "visible": True,
                    "position": {"x": 400, "y": 500, "width": 100, "height": 30},
                    "hasClickHandler": False,
                    "disabled": False
                }
            ]
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": elements_data}
        }

        cmd = GetClickableElementsCommand(context)
        result = await cmd.execute()

        assert result["success"] is True
        assert result["elements"][0]["hasClickHandler"] is True
        assert result["elements"][1]["hasClickHandler"] is False

    @pytest.mark.asyncio
    async def test_limit_to_50_elements(self, context, mock_cdp):
        """Test limiting to 50 elements (slice(0, 50))"""
        # Create 100 elements
        elements = [
            {
                "tag": "BUTTON",
                "text": f"Button {i}",
                "id": f"btn{i}",
                "role": "button",
                "ariaLabel": None,
                "visible": True,
                "position": {"x": 100, "y": 100 + i * 50, "width": 120, "height": 40},
                "hasClickHandler": True,
                "disabled": False
            }
            for i in range(100)
        ]

        elements_data = {
            "success": True,
            "count": 100,  # Total count
            "elements": elements[:50]  # Sliced to 50
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": elements_data}
        }

        cmd = GetClickableElementsCommand(context)
        result = await cmd.execute()

        # Verify slice in JS code
        call_args = mock_cdp.evaluate.call_args[1]
        js_code = call_args["expression"]
        assert ".slice(0, 50)" in js_code

        assert result["success"] is True
        assert result["count"] == 100
        # Only 50 elements returned
        assert len(result["elements"]) == 50

    @pytest.mark.asyncio
    async def test_text_filter_with_special_characters(self, context, mock_cdp):
        """Test text filter with special characters (apostrophe)"""
        elements_data = {
            "success": True,
            "count": 1,
            "elements": [
                {
                    "tag": "BUTTON",
                    "text": "Don't Click",
                    "id": "btn1",
                    "role": "button",
                    "ariaLabel": None,
                    "visible": True,
                    "position": {"x": 100, "y": 200, "width": 120, "height": 40},
                    "hasClickHandler": True,
                    "disabled": False
                }
            ]
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": elements_data}
        }

        cmd = GetClickableElementsCommand(context)
        result = await cmd.execute(text_filter="Don't")

        # Text filter should be in JS code
        call_args = mock_cdp.evaluate.call_args[1]
        js_code = call_args["expression"]
        # Should have the filter (might be escaped)
        assert "Don't" in js_code or "Don\\'t" in js_code

        assert result["success"] is True
        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_no_clickable_elements_found(self, context, mock_cdp):
        """Test when no clickable elements found"""
        elements_data = {
            "success": True,
            "count": 0,
            "elements": []
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": elements_data}
        }

        cmd = GetClickableElementsCommand(context)
        result = await cmd.execute()

        assert result["success"] is True
        assert result["count"] == 0
        assert result["elements"] == []

    @pytest.mark.asyncio
    async def test_text_truncation_to_60_chars(self, context, mock_cdp):
        """Test text content truncation to 60 characters"""
        long_text = "This is a very long button text that exceeds 60 characters and should be truncated"
        elements_data = {
            "success": True,
            "count": 1,
            "elements": [
                {
                    "tag": "BUTTON",
                    "text": long_text[:60],  # Truncated in JS
                    "id": "btn1",
                    "role": "button",
                    "ariaLabel": None,
                    "visible": True,
                    "position": {"x": 100, "y": 200, "width": 120, "height": 40},
                    "hasClickHandler": True,
                    "disabled": False
                }
            ]
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": elements_data}
        }

        cmd = GetClickableElementsCommand(context)
        result = await cmd.execute()

        # Verify truncation in JS code
        call_args = mock_cdp.evaluate.call_args[1]
        js_code = call_args["expression"]
        assert ".substring(0, 60)" in js_code

        assert result["success"] is True
        assert len(result["elements"][0]["text"]) <= 60

    @pytest.mark.asyncio
    async def test_cdp_evaluation_error(self, context, mock_cdp):
        """Test CDP evaluation error"""
        mock_cdp.evaluate.side_effect = RuntimeError("CDP connection lost")

        cmd = GetClickableElementsCommand(context)
        result = await cmd.execute()

        assert result["success"] is False
        assert "Failed to get clickable elements" in result["message"]
        assert "CDP connection lost" in result["error"]

    @pytest.mark.asyncio
    async def test_general_exception_handling(self, context, mock_cdp):
        """Test general exception handling"""
        mock_cdp.evaluate.side_effect = Exception("Tab stopped")

        cmd = GetClickableElementsCommand(context)
        result = await cmd.execute()

        assert result["success"] is False
        assert "Failed to get clickable elements" in result["message"]
        assert "Tab stopped" in result["error"]

    @pytest.mark.asyncio
    async def test_to_mcp_tool(self):
        """Test MCP tool conversion"""
        tool = GetClickableElementsCommand.to_mcp_tool()
        assert tool["name"] == "get_clickable_elements"
        assert "Get all clickable elements" in tool["description"]
        assert "text_filter" in tool["inputSchema"]["properties"]
        assert "visible_only" in tool["inputSchema"]["properties"]


# ============================================================================
# Diagnostics Commands Metadata Tests
# ============================================================================

class TestDiagnosticsCommandsMetadata:
    """Tests for all Diagnostics commands metadata"""

    @pytest.mark.asyncio
    async def test_enable_console_logging_to_mcp_tool(self):
        """Test EnableConsoleLoggingCommand MCP tool conversion"""
        tool = EnableConsoleLoggingCommand.to_mcp_tool()
        assert tool["name"] == "enable_console_logging"
        assert "Force enable console logging" in tool["description"]
        assert tool["inputSchema"]["type"] == "object"

    @pytest.mark.asyncio
    async def test_diagnose_page_to_mcp_tool(self):
        """Test DiagnosePageCommand MCP tool conversion"""
        tool = DiagnosePageCommand.to_mcp_tool()
        assert tool["name"] == "diagnose_page"
        assert "Diagnose page state" in tool["description"]
        assert tool["inputSchema"]["type"] == "object"

    @pytest.mark.asyncio
    async def test_get_clickable_elements_to_mcp_tool(self):
        """Test GetClickableElementsCommand MCP tool conversion"""
        tool = GetClickableElementsCommand.to_mcp_tool()
        assert tool["name"] == "get_clickable_elements"
        assert "Get all clickable elements" in tool["description"]
        assert tool["inputSchema"]["type"] == "object"
