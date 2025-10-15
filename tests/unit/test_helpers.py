"""
Unit tests for commands/helpers.py

Tests:
- DebugElementCommand: Element debugging with selector + text search
- ForceClickCommand: Force click with multiple aggressive strategies

Coverage target: 50%+ (38% → 50%+)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from commands.helpers import DebugElementCommand, ForceClickCommand
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
def mock_cursor():
    """Mock AICursor"""
    cursor = AsyncMock()
    cursor.initialize = AsyncMock()
    cursor.move = AsyncMock()
    return cursor


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
def context_with_cursor(mock_tab, mock_cdp, mock_cursor):
    """CommandContext with cursor"""
    return CommandContext(
        tab=mock_tab,
        cursor=mock_cursor,
        browser=None,
        cdp=mock_cdp,
        connection=None
    )


# ============================================================================
# DebugElementCommand Tests
# ============================================================================

class TestDebugElementCommand:
    """Tests for DebugElementCommand (element debugging)"""

    @pytest.mark.asyncio
    async def test_metadata(self):
        """Test command metadata"""
        assert DebugElementCommand.name == "debug_element"
        assert "Debug an element to see all ways to interact with it" in DebugElementCommand.description

        schema = DebugElementCommand.input_schema
        assert "text" in schema["properties"]
        assert "selector" in schema["properties"]
        assert schema["properties"]["text"]["type"] == "string"
        assert schema["properties"]["selector"]["type"] == "string"

    @pytest.mark.asyncio
    async def test_debug_element_by_text(self, context, mock_cdp):
        """Test debugging element by text search"""
        debug_data = {
            "success": True,
            "count": 2,
            "showing": 2,
            "elements": [
                {
                    "index": 0,
                    "tagName": "BUTTON",
                    "text": "Submit Form",
                    "visible": True,
                    "position": {"x": 100, "y": 200, "width": 120, "height": 40},
                    "selectors": ["#submit-btn", "button.primary"],
                    "attributes": [
                        {"name": "id", "value": "submit-btn"},
                        {"name": "class", "value": "primary"}
                    ],
                    "styles": {
                        "display": "block",
                        "visibility": "visible",
                        "opacity": "1",
                        "pointerEvents": "auto",
                        "cursor": "pointer",
                        "zIndex": "auto"
                    },
                    "clickable": {
                        "hasClickHandler": True,
                        "hasEventListeners": "unknown",
                        "isButton": True,
                        "isLink": False,
                        "hasRole": False,
                        "role": None
                    },
                    "parent": {
                        "tagName": "FORM",
                        "classes": "form-container"
                    }
                },
                {
                    "index": 1,
                    "tagName": "A",
                    "text": "Submit Now",
                    "visible": True,
                    "position": {"x": 50, "y": 300, "width": 80, "height": 30},
                    "selectors": ["a.link"],
                    "attributes": [
                        {"name": "href", "value": "#"},
                        {"name": "class", "value": "link"}
                    ],
                    "styles": {
                        "display": "inline",
                        "visibility": "visible",
                        "opacity": "1",
                        "pointerEvents": "auto",
                        "cursor": "pointer",
                        "zIndex": "1"
                    },
                    "clickable": {
                        "hasClickHandler": False,
                        "hasEventListeners": "unknown",
                        "isButton": False,
                        "isLink": True,
                        "hasRole": False,
                        "role": None
                    },
                    "parent": {
                        "tagName": "DIV",
                        "classes": "container"
                    }
                }
            ]
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": debug_data}
        }

        cmd = DebugElementCommand(context)
        result = await cmd.execute(text="Submit")

        # Verify CDP call
        mock_cdp.evaluate.assert_called_once()
        call_args = mock_cdp.evaluate.call_args[1]
        js_code = call_args["expression"]
        assert "if ('Submit')" in js_code
        assert "document.querySelectorAll('*')" in js_code
        assert "el.textContent.includes" in js_code
        assert "getBoundingClientRect" in js_code
        assert "getComputedStyle" in js_code
        assert call_args["returnByValue"] is True

        # Verify result
        assert result["success"] is True
        assert result["count"] == 2
        assert result["showing"] == 2
        assert len(result["elements"]) == 2
        assert result["elements"][0]["tagName"] == "BUTTON"
        assert result["elements"][0]["text"] == "Submit Form"
        assert result["elements"][0]["clickable"]["isButton"] is True
        assert result["elements"][1]["tagName"] == "A"
        assert result["elements"][1]["clickable"]["isLink"] is True

    @pytest.mark.asyncio
    async def test_debug_element_by_selector(self, context, mock_cdp):
        """Test debugging element by CSS selector"""
        debug_data = {
            "success": True,
            "count": 1,
            "showing": 1,
            "elements": [
                {
                    "index": 0,
                    "tagName": "INPUT",
                    "text": "",
                    "visible": True,
                    "position": {"x": 200, "y": 150, "width": 300, "height": 35},
                    "selectors": ["#email-input", "input.email"],
                    "attributes": [
                        {"name": "id", "value": "email-input"},
                        {"name": "type", "value": "email"},
                        {"name": "class", "value": "email"}
                    ],
                    "styles": {
                        "display": "block",
                        "visibility": "visible",
                        "opacity": "1",
                        "pointerEvents": "auto",
                        "cursor": "text",
                        "zIndex": "auto"
                    },
                    "clickable": {
                        "hasClickHandler": False,
                        "hasEventListeners": "unknown",
                        "isButton": False,
                        "isLink": False,
                        "hasRole": True,
                        "role": "textbox"
                    },
                    "parent": {
                        "tagName": "FORM",
                        "classes": "login-form"
                    }
                }
            ]
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": debug_data}
        }

        cmd = DebugElementCommand(context)
        result = await cmd.execute(selector="#email-input")

        # Verify CDP call
        call_args = mock_cdp.evaluate.call_args[1]
        js_code = call_args["expression"]
        assert "else if ('#email-input')" in js_code
        assert "document.querySelectorAll('#email-input')" in js_code

        # Verify result
        assert result["success"] is True
        assert result["count"] == 1
        assert result["elements"][0]["tagName"] == "INPUT"
        assert "#email-input" in result["elements"][0]["selectors"]
        assert result["elements"][0]["clickable"]["role"] == "textbox"

    @pytest.mark.asyncio
    async def test_debug_element_not_found(self, context, mock_cdp):
        """Test debugging when element not found"""
        debug_data = {
            "success": False,
            "message": "No elements found for text='Nonexistent'"
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": debug_data}
        }

        cmd = DebugElementCommand(context)
        result = await cmd.execute(text="Nonexistent")

        assert result["success"] is False
        assert "No elements found" in result["message"]

    @pytest.mark.asyncio
    async def test_debug_element_limit_to_5(self, context, mock_cdp):
        """Test debugging limits to 5 elements (slice(0, 5))"""
        # Create 10 elements
        elements = [
            {
                "index": i,
                "tagName": "BUTTON",
                "text": f"Button {i}",
                "visible": True,
                "position": {"x": 100, "y": 100 + i * 50, "width": 120, "height": 40},
                "selectors": [f"#btn{i}"],
                "attributes": [{"name": "id", "value": f"btn{i}"}],
                "styles": {
                    "display": "block",
                    "visibility": "visible",
                    "opacity": "1",
                    "pointerEvents": "auto",
                    "cursor": "pointer",
                    "zIndex": "auto"
                },
                "clickable": {
                    "hasClickHandler": True,
                    "hasEventListeners": "unknown",
                    "isButton": True,
                    "isLink": False,
                    "hasRole": False,
                    "role": None
                },
                "parent": {"tagName": "DIV", "classes": "container"}
            }
            for i in range(5)  # Only 5 returned
        ]

        debug_data = {
            "success": True,
            "count": 10,  # Total count
            "showing": 5,  # Sliced to 5
            "elements": elements
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": debug_data}
        }

        cmd = DebugElementCommand(context)
        result = await cmd.execute(text="Button")

        # Verify slice in JS code
        call_args = mock_cdp.evaluate.call_args[1]
        js_code = call_args["expression"]
        assert ".slice(0, 5)" in js_code

        assert result["success"] is True
        assert result["showing"] == 5
        assert len(result["elements"]) == 5

    @pytest.mark.asyncio
    async def test_debug_element_with_hidden_element(self, context, mock_cdp):
        """Test debugging includes visibility checks"""
        debug_data = {
            "success": True,
            "count": 1,
            "showing": 1,
            "elements": [
                {
                    "index": 0,
                    "tagName": "DIV",
                    "text": "Hidden Element",
                    "visible": False,  # Hidden
                    "position": {"x": 0, "y": 0, "width": 0, "height": 0},
                    "selectors": ["#hidden-div"],
                    "attributes": [{"name": "id", "value": "hidden-div"}],
                    "styles": {
                        "display": "none",  # Hidden
                        "visibility": "hidden",
                        "opacity": "0",
                        "pointerEvents": "none",
                        "cursor": "default",
                        "zIndex": "auto"
                    },
                    "clickable": {
                        "hasClickHandler": False,
                        "hasEventListeners": "unknown",
                        "isButton": False,
                        "isLink": False,
                        "hasRole": False,
                        "role": None
                    },
                    "parent": {"tagName": "BODY", "classes": ""}
                }
            ]
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": debug_data}
        }

        cmd = DebugElementCommand(context)
        result = await cmd.execute(selector="#hidden-div")

        # Verify visibility check in JS code
        call_args = mock_cdp.evaluate.call_args[1]
        js_code = call_args["expression"]
        assert "rect.width > 0" in js_code
        assert "style.display !== 'none'" in js_code
        assert "style.visibility !== 'hidden'" in js_code
        assert "parseFloat(style.opacity) > 0" in js_code

        assert result["success"] is True
        assert result["elements"][0]["visible"] is False
        assert result["elements"][0]["styles"]["display"] == "none"

    @pytest.mark.asyncio
    async def test_debug_element_text_truncation(self, context, mock_cdp):
        """Test text content truncation to 100 characters"""
        long_text = "A" * 150  # 150 characters
        debug_data = {
            "success": True,
            "count": 1,
            "showing": 1,
            "elements": [
                {
                    "index": 0,
                    "tagName": "P",
                    "text": long_text[:100],  # Truncated in JS
                    "visible": True,
                    "position": {"x": 50, "y": 50, "width": 600, "height": 100},
                    "selectors": ["p.long-text"],
                    "attributes": [{"name": "class", "value": "long-text"}],
                    "styles": {
                        "display": "block",
                        "visibility": "visible",
                        "opacity": "1",
                        "pointerEvents": "auto",
                        "cursor": "text",
                        "zIndex": "auto"
                    },
                    "clickable": {
                        "hasClickHandler": False,
                        "hasEventListeners": "unknown",
                        "isButton": False,
                        "isLink": False,
                        "hasRole": False,
                        "role": None
                    },
                    "parent": {"tagName": "DIV", "classes": ""}
                }
            ]
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": debug_data}
        }

        cmd = DebugElementCommand(context)
        result = await cmd.execute(selector="p.long-text")

        # Verify truncation in JS code
        call_args = mock_cdp.evaluate.call_args[1]
        js_code = call_args["expression"]
        assert ".substring(0, 100)" in js_code

        assert result["success"] is True
        assert len(result["elements"][0]["text"]) == 100

    @pytest.mark.asyncio
    async def test_debug_element_with_event_listeners(self, context, mock_cdp):
        """Test debugging element with event listeners"""
        debug_data = {
            "success": True,
            "count": 1,
            "showing": 1,
            "elements": [
                {
                    "index": 0,
                    "tagName": "BUTTON",
                    "text": "Interactive Button",
                    "visible": True,
                    "position": {"x": 100, "y": 200, "width": 120, "height": 40},
                    "selectors": ["#interactive-btn"],
                    "attributes": [{"name": "id", "value": "interactive-btn"}],
                    "styles": {
                        "display": "block",
                        "visibility": "visible",
                        "opacity": "1",
                        "pointerEvents": "auto",
                        "cursor": "pointer",
                        "zIndex": "auto"
                    },
                    "clickable": {
                        "hasClickHandler": True,  # Has onclick
                        "hasEventListeners": True,  # Has event listeners (if available)
                        "isButton": True,
                        "isLink": False,
                        "hasRole": False,
                        "role": None
                    },
                    "parent": {"tagName": "FORM", "classes": ""}
                }
            ]
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": debug_data}
        }

        cmd = DebugElementCommand(context)
        result = await cmd.execute(selector="#interactive-btn")

        # Verify event listener check in JS code
        call_args = mock_cdp.evaluate.call_args[1]
        js_code = call_args["expression"]
        assert "el.onclick !== null" in js_code
        assert "getEventListeners" in js_code

        assert result["success"] is True
        assert result["elements"][0]["clickable"]["hasClickHandler"] is True
        assert result["elements"][0]["clickable"]["hasEventListeners"] is True

    @pytest.mark.asyncio
    async def test_cdp_evaluation_error(self, context, mock_cdp):
        """Test CDP evaluation error"""
        mock_cdp.evaluate.side_effect = RuntimeError("CDP connection lost")

        cmd = DebugElementCommand(context)
        result = await cmd.execute(text="Test")

        assert result["success"] is False
        assert "Failed to debug element" in result["message"]
        assert "CDP connection lost" in result["error"]

    @pytest.mark.asyncio
    async def test_general_exception_handling(self, context, mock_cdp):
        """Test general exception handling"""
        mock_cdp.evaluate.side_effect = Exception("Tab stopped")

        cmd = DebugElementCommand(context)
        result = await cmd.execute(selector="#test")

        assert result["success"] is False
        assert "Failed to debug element" in result["message"]
        assert "Tab stopped" in result["error"]

    @pytest.mark.asyncio
    async def test_to_mcp_tool(self):
        """Test MCP tool conversion"""
        tool = DebugElementCommand.to_mcp_tool()
        assert tool["name"] == "debug_element"
        assert "Debug an element" in tool["description"]
        assert "text" in tool["inputSchema"]["properties"]
        assert "selector" in tool["inputSchema"]["properties"]


# ============================================================================
# ForceClickCommand Tests
# ============================================================================

class TestForceClickCommand:
    """Tests for ForceClickCommand (force click with multiple strategies)"""

    @pytest.mark.asyncio
    async def test_metadata(self):
        """Test command metadata"""
        assert ForceClickCommand.name == "force_click"
        assert "Force click on element using all available methods" in ForceClickCommand.description
        assert ForceClickCommand.requires_cursor is True

        schema = ForceClickCommand.input_schema
        assert "x" in schema["properties"]
        assert "y" in schema["properties"]
        assert "text" in schema["properties"]
        assert schema["properties"]["x"]["type"] == "integer"
        assert schema["properties"]["y"]["type"] == "integer"
        assert schema["properties"]["text"]["type"] == "string"

    @pytest.mark.asyncio
    async def test_force_click_by_coordinates(self, context_with_cursor, mock_cdp, mock_cursor):
        """Test force click at specific coordinates"""
        click_result = {
            "success": True,
            "element": {
                "tagName": "BUTTON",
                "id": "submit-btn",
                "text": "Submit",
                "role": "button"
            },
            "methods": ["click()", "MouseEvent", "PointerEvent", "TouchEvent", "focus+onclick"],
            "position": {"x": 100, "y": 200},
            "message": "Executed 5 click methods"
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": click_result}
        }

        cmd = ForceClickCommand(context_with_cursor)
        result = await cmd.execute(x=100, y=200)

        # Verify cursor initialized
        mock_cursor.initialize.assert_called_once()

        # Verify CDP call
        mock_cdp.evaluate.assert_called_once()
        call_args = mock_cdp.evaluate.call_args[1]
        js_code = call_args["expression"]
        assert "const x = 100" in js_code
        assert "const y = 200" in js_code
        assert "document.elementFromPoint(x, y)" in js_code
        assert "window.__moveAICursor__" in js_code
        assert "window.__clickAICursor__" in js_code
        assert "el.click()" in js_code
        assert "new MouseEvent" in js_code
        assert "new PointerEvent" in js_code
        assert "new TouchEvent" in js_code
        assert "el.focus()" in js_code
        assert "el.onclick" in js_code
        assert call_args["returnByValue"] is True
        assert call_args["awaitPromise"] is True

        # Verify result
        assert result["success"] is True
        assert result["element"]["tagName"] == "BUTTON"
        assert len(result["methods"]) == 5
        assert "click()" in result["methods"]
        assert "MouseEvent" in result["methods"]
        assert "PointerEvent" in result["methods"]
        assert "TouchEvent" in result["methods"]
        assert "focus+onclick" in result["methods"]
        assert result["position"]["x"] == 100
        assert result["position"]["y"] == 200

    @pytest.mark.asyncio
    async def test_force_click_by_text(self, context_with_cursor, mock_cdp, mock_cursor):
        """Test force click by text search"""
        click_result = {
            "success": True,
            "element": {
                "tagName": "A",
                "id": "home-link",
                "text": "Home"
            },
            "methods": ["click()", "MouseEvent", "focus+onclick"],
            "position": {"x": 50, "y": 100},
            "message": "Executed 3 click methods on text: Home"
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": click_result}
        }

        cmd = ForceClickCommand(context_with_cursor)
        result = await cmd.execute(text="Home")

        # Verify cursor initialized
        mock_cursor.initialize.assert_called_once()

        # Verify CDP call
        call_args = mock_cdp.evaluate.call_args[1]
        js_code = call_args["expression"]
        assert "const searchText = 'Home'" in js_code
        assert "document.querySelectorAll('*')" in js_code
        assert "el.textContent.includes(searchText)" in js_code
        assert "el.scrollIntoView" in js_code
        assert "window.__moveAICursor__" in js_code
        assert "window.__clickAICursor__" in js_code

        # Verify result
        assert result["success"] is True
        assert result["element"]["text"] == "Home"
        assert len(result["methods"]) == 3
        assert "Home" in result["message"]

    @pytest.mark.asyncio
    async def test_force_click_no_element_at_coordinates(self, context_with_cursor, mock_cdp, mock_cursor):
        """Test force click when no element at coordinates"""
        click_result = {
            "success": False,
            "message": "No element at coordinates (500, 600)"
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": click_result}
        }

        cmd = ForceClickCommand(context_with_cursor)
        result = await cmd.execute(x=500, y=600)

        assert result["success"] is False
        assert "No element at coordinates" in result["message"]

    @pytest.mark.asyncio
    async def test_force_click_element_not_found_by_text(self, context_with_cursor, mock_cdp, mock_cursor):
        """Test force click when element not found by text"""
        click_result = {
            "success": False,
            "message": "No elements with text: Nonexistent"
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": click_result}
        }

        cmd = ForceClickCommand(context_with_cursor)
        result = await cmd.execute(text="Nonexistent")

        assert result["success"] is False
        assert "No elements with text" in result["message"]

    @pytest.mark.asyncio
    async def test_force_click_no_parameters(self, context_with_cursor, mock_cdp, mock_cursor):
        """Test force click with no parameters (error)"""
        cmd = ForceClickCommand(context_with_cursor)
        result = await cmd.execute()

        # Should not call CDP
        mock_cdp.evaluate.assert_not_called()

        assert result["success"] is False
        assert "Provide either x,y coordinates or text" in result["message"]

    @pytest.mark.asyncio
    async def test_force_click_requires_cursor(self, context):
        """Test force click requires cursor (raises ValueError if missing)"""
        with pytest.raises(ValueError) as exc:
            cmd = ForceClickCommand(context)

        assert "requires cursor" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_force_click_partial_methods_success(self, context_with_cursor, mock_cdp, mock_cursor):
        """Test force click with partial methods success (some fail)"""
        click_result = {
            "success": True,
            "element": {
                "tagName": "DIV",
                "id": "clickable-div",
                "text": "Clickable Area",
                "role": "button"
            },
            "methods": ["click()", "MouseEvent"],  # Only 2 methods succeeded
            "position": {"x": 300, "y": 400},
            "message": "Executed 2 click methods"
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": click_result}
        }

        cmd = ForceClickCommand(context_with_cursor)
        result = await cmd.execute(x=300, y=400)

        assert result["success"] is True
        assert len(result["methods"]) == 2  # Only 2 methods worked
        assert "click()" in result["methods"]
        assert "MouseEvent" in result["methods"]

    @pytest.mark.asyncio
    async def test_force_click_with_cursor_animation(self, context_with_cursor, mock_cdp, mock_cursor):
        """Test force click includes cursor animation"""
        click_result = {
            "success": True,
            "element": {"tagName": "BUTTON", "id": "btn", "text": "Click", "role": None},
            "methods": ["click()"],
            "position": {"x": 100, "y": 200},
            "message": "Executed 1 click methods"
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": click_result}
        }

        cmd = ForceClickCommand(context_with_cursor)
        result = await cmd.execute(x=100, y=200)

        # Verify cursor animation in JS code
        call_args = mock_cdp.evaluate.call_args[1]
        js_code = call_args["expression"]
        assert "window.__moveAICursor__(x, y, 300)" in js_code
        assert "window.__clickAICursor__()" in js_code
        assert "setTimeout" in js_code
        assert "350" in js_code  # Animation delay

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_force_click_text_scrolls_into_view(self, context_with_cursor, mock_cdp, mock_cursor):
        """Test force click by text scrolls element into view"""
        click_result = {
            "success": True,
            "element": {"tagName": "BUTTON", "id": "btn", "text": "Submit"},
            "methods": ["click()"],
            "position": {"x": 100, "y": 800},
            "message": "Executed 1 click methods on text: Submit"
        }

        mock_cdp.evaluate.return_value = {
            "result": {"value": click_result}
        }

        cmd = ForceClickCommand(context_with_cursor)
        result = await cmd.execute(text="Submit")

        # Verify scroll into view in JS code
        call_args = mock_cdp.evaluate.call_args[1]
        js_code = call_args["expression"]
        assert "el.scrollIntoView" in js_code
        assert "behavior: 'smooth'" in js_code
        assert "block: 'center'" in js_code

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_cdp_evaluation_error(self, context_with_cursor, mock_cdp, mock_cursor):
        """Test CDP evaluation error"""
        mock_cdp.evaluate.side_effect = RuntimeError("CDP connection lost")

        cmd = ForceClickCommand(context_with_cursor)
        result = await cmd.execute(x=100, y=200)

        assert result["success"] is False
        assert "Failed to force click" in result["message"]
        assert "CDP connection lost" in result["error"]

    @pytest.mark.asyncio
    async def test_general_exception_handling(self, context_with_cursor, mock_cdp, mock_cursor):
        """Test general exception handling"""
        mock_cdp.evaluate.side_effect = Exception("Tab stopped")

        cmd = ForceClickCommand(context_with_cursor)
        result = await cmd.execute(text="Test")

        assert result["success"] is False
        assert "Failed to force click" in result["message"]
        assert "Tab stopped" in result["error"]

    @pytest.mark.asyncio
    async def test_to_mcp_tool(self):
        """Test MCP tool conversion"""
        tool = ForceClickCommand.to_mcp_tool()
        assert tool["name"] == "force_click"
        assert "Force click on element" in tool["description"]
        assert "x" in tool["inputSchema"]["properties"]
        assert "y" in tool["inputSchema"]["properties"]
        assert "text" in tool["inputSchema"]["properties"]


# ============================================================================
# Helpers Commands Metadata Tests
# ============================================================================

class TestHelpersCommandsMetadata:
    """Tests for all Helpers commands metadata"""

    @pytest.mark.asyncio
    async def test_debug_element_to_mcp_tool(self):
        """Test DebugElementCommand MCP tool conversion"""
        tool = DebugElementCommand.to_mcp_tool()
        assert tool["name"] == "debug_element"
        assert "Debug an element" in tool["description"]
        assert tool["inputSchema"]["type"] == "object"

    @pytest.mark.asyncio
    async def test_force_click_to_mcp_tool(self):
        """Test ForceClickCommand MCP tool conversion"""
        tool = ForceClickCommand.to_mcp_tool()
        assert tool["name"] == "force_click"
        assert "Force click on element" in tool["description"]
        assert tool["inputSchema"]["type"] == "object"
